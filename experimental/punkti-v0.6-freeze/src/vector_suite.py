"""Black-box fixtures and assertions. Never import either protocol implementation."""
import base64
from contextlib import ExitStack, contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import threading
from urllib.parse import urlencode, urlsplit, parse_qs

HOME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOME.parent / 'nairobidot-l3' / 'interop'))
from driver import Adapter, http, HERE

SEED = 'punkti-0.6-freeze-vectors'
KEYS = ('atom', 'C', 'S', 'MID', 'address', 'R', 'sig', 'state')


def packed(obj):
    return json.dumps(obj, ensure_ascii=True, separators=(',', ':'), sort_keys=True)


def b64(raw):
    return base64.b64encode(raw).decode('ascii')


def spec(**kw):
    value = dict(seed=SEED, t=1700000000000, h='s00000000000_23',
                 x='opaque freeze payload \0 世界 🌍',
                 refs=[dict(target='unknown/a:00ff', rel='unrecognized/关系'),
                       dict(target='future/v9:abcd', rel='')], ext=b64(b'\0\xff\0'), alg='ed25519')
    value.update(kw)
    return value


def item(m, raw=None):
    raw = base64.b64decode(m['R']) if raw is None else raw
    return dict(address=m['address'], sha256=hashlib.sha256(raw).hexdigest(), record=b64(raw))


def altitude(h):
    return h.split('_')[1]


def equal(actual, expected, label=''):
    if actual != expected:
        raise AssertionError(f'{label}: {actual!r} != {expected!r}')


@contextmanager
def adapter(kind, serve=True):
    a = Adapter(kind, dict(subscriptions=[{}], peers=[], port=0) if serve else None)
    try:
        yield a
    finally:
        a.close()


def fixtures():
    specs = {'canonical': spec(), 'zero': spec(t=0),
             'opaque': spec(alg='future-signature', x='opaque\0 🌍 e\u0301', ext=b64(b'\xff\0opaque'))}
    for i, h in enumerate(('000000000000_-18', 's00000000000_23', 's00000000001_23.025', 'zzzzzzzzzzzz_9000')):
        specs['spatial' + str(i)] = spec(h=h, x='boundary-' + str(i))
    for name, h in [('height23','u3butz7k9q_23'),('negative','u3butz7k9q_-18'),('decimal','u3butz7k9q_23.025')]:
        specs[name] = spec(h=h)
    for i, h in enumerate(('u3bu_23','u3butz7k9q_23','u3c0_23','u3bu_23.02',
                           'u3bu_23.025','u3bu_22.999','u3bu_-18','')):
        specs['selection'+str(i)] = spec(h=h)
    result = {}
    with adapter('ref', False) as a, adapter('nb', False) as b:
        for name, s in specs.items():
            left, right = a.rpc('mint', spec=s), b.rpc('mint', spec=s)
            for key in KEYS + ('sha256',):
                equal(left[key], right[key], name + ':' + key)
            result[name] = dict(spec=s, **{k: left[k] for k in KEYS}, sha256_R=left['sha256'])
    return result


def request(query=None, body=None):
    if query is not None:
        return dict(method='GET', target='/pull?' + urlencode({'q': packed(query)}), query=query)
    return dict(method='POST', target='/push', body_utf8=packed(body))


def definitions(f):
    good = item(f['canonical'])
    raw = base64.b64decode(f['canonical']['R'])
    tampered = item(f['canonical'], raw[:-1] + bytes([raw[-1] ^ 1]))
    truncated = item(f['canonical'], raw[:-5])
    A, B = sorted(f[k]['address'] for k in ('spatial0', 'spatial1'))
    alts = {f['spatial'+str(i)]['atom']['h']: altitude(f['spatial'+str(i)]['atom']['h']) for i in range(4)}
    h0, h1 = 's00000000000', 's00000000001'
    z0, z1 = '23', '23.025'
    assert z0 < z1, 'profile altitude order changed: revise/document bounds before publishing'
    scope = dict(xy_lo=h0, xy_hi='s00000000002')
    vectors = []

    def add(id, title, description, data, expectation, expected, transition):
        final_valid = dict(V1=1, V2=3, V3=1, V4=4, V5=0, V6=1,
                           V7=0, V8=1, V9=1, V10=0, V11=0, V12=0, V13=8)[id]
        final_candidates = int(id == 'V9')
        vectors.append(dict(id=id, title=title, input=dict(description=description, **data),
                            expected=dict(description=expectation, **expected),
                            state_transition=dict(description=transition,
                                final_per_node=dict(valid=final_valid, candidates=final_candidates,
                                                    log=final_valid + final_candidates))))

    add('V1', 'canonical-record', 'Import exact JSON; decode R; push twice into empty node.',
        dict(fixture='canonical', json_utf8=packed(f['canonical']['atom']), request=request(body={'records':[good]})),
        'VALID; canonical values equal pinned fixture; complete framing; first admission then duplicate.',
        dict(import_ok=True, state='VALID', http_status=200, admitted=[True, False], duplicate_reason='duplicate'),
        'Empty → one VALID record/log entry → unchanged on duplicate.')
    add('V2', 'initial-mid-cursor', 'Empty MID request twice; empty spatial; seed three fixtures then two MID pages, echoing the first token.',
        dict(fixtures=['spatial0','spatial1','spatial2'], empty_mid=request({'mode':'mid'}),
             empty_spatial=request({'mode':'spatial','limit':1}), first=request({'mode':'mid','limit':1}),
             continuation='Same first query plus cursor equal to the complete first response token.'),
        'Empty MID after=null, empty spatial after=0; nonempty MID after=[address,sha256_R]; repeated empty request identical.',
        dict(http_status=200, empty_records=[], empty_end=True, empty_mid_after=None, empty_spatial_after=0,
             page_addresses=sorted(f['spatial'+str(i)]['address'] for i in range(3))[:2], scope_pattern='[0-9a-f]{64}'),
        'PULL does not change store/candidates/log/epoch.')
    queries = [({'mode':'mid','lo':A,'hi':A},400), ({'mode':'mid','lo':B,'hi':A},400),
               ({'mode':'spatial','scope':{'xy_lo':'g','xy_hi':'g'}},400), ({'scope':{'xy_lo':'t','xy_hi':'g'}},400),
               ({'mode':'spatial','scope':{'z_min':'1','z_max':'1'}},400), ({'scope':{'z_min':'1','z_max':'-1'}},400),
               ({'mode':'mid','lo':A},200), ({'mode':'spatial','scope':{'xy_lo':'g'}},200), ({'scope':{'z_max':'1'}},200)]
    add('V3', 'range-rejection', 'Seed canonical record; issue each exact range request.',
        dict(fixtures=['canonical'], requests=[request(q) for q,_ in queries], A=A, B=B),
        'Equal/reversed bounds reject; single unbounded endpoints accept.', dict(statuses=[s for _,s in queries]),
        'Each request leaves store, candidates, log and epoch unchanged.')
    scopes = [dict(xy_lo=h0,xy_hi=h1), dict(scope,z_min=z0,z_max=z1),
              dict(scope,z_max=z0),dict(scope,z_min=z1)]
    add('V4', 'spatial-boundary', 'Four-record store; lower-edge XY and exact decimal Z half-open boundaries.',
        dict(fixtures=['spatial'+str(i) for i in range(4)], altitudes=alts,
             requests=[request(dict(mode='spatial',scope=s)) for s in scopes]),
        'Exactly lower boundary for XY and bounded Z; none below lower altitude; exactly upper record at z_min=alt1.',
        dict(http_status=200, addresses=[[f['spatial1']['address']],[f['spatial1']['address']],[],[f['spatial2']['address']]]),
        'PULL only: no store/candidate/log/epoch mutation. The XY scope excludes both extreme h fixtures.')
    bad_digest = dict(good, sha256='f'*64)
    bad_address = dict(good, address='punkti/0.6:' + '0'*64)
    cases = [[good,bad_digest],[bad_address],[dict(good,extra=1)],[dict(good,record=good['record']+'=')]]
    add('V5','descriptor-errors','Malformed wrappers are prevalidated before admission; empty batch is observational only.',
        dict(requests=[request(body={'records':c}) for c in cases],
             empty_batch=dict(non_normative=True, request=request(body={'records':[]}))),
        'All four normative descriptor cases HTTP 400; store and log empty.',
        dict(statuses=[400]*4, empty_batch=dict(non_normative=True, ref=[400,{'error':'push batch size'}], nb=[200,{'results':[]}])),
        'Descriptor error → no admission from the entire request; empty batch does not mutate state.')
    add('V6','content-errors','Push VALID and signature-flipped R together; then structurally truncated R with correct digest.',
        dict(requests=[request(body={'records':[good,tampered]}),request(body={'records':[truncated]})]),
        'HTTP 200 per request; content failure does not poison the valid address.',
        dict(http_status=200, results=[[dict(state='VALID',admitted=True),dict(state='INVALID-provenance',admitted=False)],
                                      [dict(state='INVALID-structural',admitted=False)]], valid=[f['canonical']['address']]),
        'Empty → exactly one VALID record/log entry; no candidate retained for either invalid item.')
    zero = packed(f['zero']['atom'])
    spellings = ['0','-0','-1','01','1.0','1e3','+1']
    add('V7','timestamp-grammar','Exact UTF-8 JSON bytes passed as base64 to import_json; only t spelling changes.',
        dict(fixture='zero', cases=[dict(spelling=s,json_utf8=zero.replace('"t":0,','"t":'+s+',')) for s in spellings]),
        'Only unsigned integer spelling 0 accepts; accepted object has the pinned zero fixture canonical bytes.',
        dict(ok=[True]+[False]*6), 'JSON import only; no store mutation.')
    stubhello = dict(protocol='punkti-mesh/0.6-draft',epoch='stub-epoch',subscriptions=[{}],peers=[])
    binding = hashlib.sha256(packed(dict(mode='spatial',scope=dict(xy_lo=None,xy_hi=None,z_min=None,z_max=None),lo=None,hi=None)).encode()).hexdigest()
    token = dict(epoch='stub-epoch',scope=binding,after=1,ceiling=1)
    clean = dict(records=[good],end=True,cursor=token)
    badpage = dict(records=[good,tampered],end=True,cursor=dict(token,after=2,ceiling=2))
    add('V8','interrupted-page-atomicity','Fresh target for each failure mode; stub first page is short HTTP or decoded invalid-content batch, then clean retry and cursor-resume probe.',
        dict(adapter_command='pull_from', mode='spatial', scope={},
             hello_utf8=packed(stubhello), clean_page_utf8=packed(clean), invalid_page_utf8=packed(badpage),
             truncated_body_utf8=packed(clean)[:-1], declared_length=len(packed(clean).encode())+32,
             resume_page_utf8=packed(dict(records=[],end=True,cursor=token))),
        'First pull fails without admission; retry succeeds from null; next pull echoes the successful token.',
        dict(ok=[False,True,True], cursors=[None,None,token], valid=[f['canonical']['address']],log_count=1),
        'Failed page → empty store/log and retained null cursor; success → one admission then cursor advances; resume adds nothing.')
    add('V9','opaque-preservation','Mint future-signature with opaque Unicode/refs/ext; push to unrestricted source, pull into second node; retain a distinct VALID fixture at both.',
        dict(fixture='opaque',valid_fixture='canonical',request=request(body={'records':[item(f['opaque'])]})),
        'Exact R and decoded atom preserved on both nodes; unsupported algorithm remains candidate.',
        dict(http_status=200,state='UNVERIFIABLE-alg',admitted=True,valid=[f['canonical']['address']],candidates=[f['opaque']['address']]),
        'Each node retains one VALID and one candidate; unsupported algorithm never promotes or replaces VALID.')
    add('V10','hello-limits','GET /hello on fresh served node.',dict(method='GET',target='/hello'),
        'Exact normative limits, capabilities and protocol.',
        dict(http_status=200,limits=dict(body=1048576,record=2097152,page=32,http=8388608,candidates=128),
             capabilities=['push','range-mid','range-spatial','opaque-wrapper'],protocol='punkti-mesh/0.6-draft'),
        'No state mutation.')
    invalid_z = ['+23','2.3e1','023','23.','23.0','23.50','-0','0.0','0.00','٢٣','.5','23 ','23\n']
    invalid_h = ['u3bu_'+z for z in invalid_z] + [
        'u3b_23','u'*13+'_0','u3bu23','u3bu__23','u3bu_','u3bu_'+'1'*28,
        'u3butz7k9q_'+'1'*22, 's00000000000']
    order = ['-99999999999999999999999999','-18','-0.5','0','0.05','0.5','23',
             '23.02','23.025','999999999999999999999999998','999999999999999999999999999']
    add('V11','canonical-XY_Z-and-order','Historical signed addresses, rejected spellings and all pairs of exact Z order.',
        dict(fixtures=['height23','negative','decimal'],invalid_h=invalid_h,order=order),
        'Distinct h/C/MID/address for same XY with different Z; structural rejection of every malformed h; exact total Z order.',
        dict(state='VALID',invalid_state='INVALID-structural'), 'Mint and validate only; no store mutation.')
    rows = [(55.675398,12.561895,'u3butz7k9q7v'),(51.5074,-.1278,'gcpvj0duq533'),
            (35.6762,139.6503,'xn76cydhzven'),(40.7128,-74.006,'dr5regw3ppyz'),
            (59.9139,10.7522,'u4xsudvxb2mq'),(0.,0.,'s000000000000'),
            (-90.,-180.,'000000000000'),(90.,180.,'zzzzzzzzzzzz')]
    cells = []
    alphabet = '0123456789bcdefghjkmnpqrstuvwxyz'
    for lat,lon,full in rows:
        for precision in (4,10,12):
            xy = full[:precision]
            bits = ''.join(format(alphabet.index(c),'05b') for c in xy)
            xbits,ybits = bits[::2],bits[1::2]
            x,y = int(xbits,2),int(ybits,2)
            dx,dy = 360/2**len(xbits),180/2**len(ybits)
            cells.append(dict(lat=lat,lon=lon,precision=precision,xy=xy,
                decoded=dict(lon_min=-180+x*dx,lon_max=-180+(x+1)*dx,
                             lat_min=-90+y*dy,lat_max=-90+(y+1)*dy,
                             lon=-180+(x+.5)*dx,lat=-90+(y+.5)*dy)))
    add('V12','geohash-ground-truth','All eight profile rows at precisions 4, 10 and 12, including endpoints and midpoint.',
        dict(cells=cells), 'Encode equals pinned XY; decode equals independent integer-grid oracle; centre re-encodes.',
        dict(count=24), 'Pure codec operations; no store mutation.')
    selections = [({},list(range(8))),({'xy_lo':'u3b','xy_hi':'u3c'},[0,1,3,4,5,6]),
        ({'xy_lo':'u3bu','xy_hi':'u3bu000001'},[0,3,4,5,6]),
        ({'xy_lo':'u3butz7k9q','xy_hi':'u3butz7k9r'},[1]),
        ({'z_min':'23','z_max':'23.025'},[0,1,2,3]),
        ({'xy_lo':'u3b','xy_hi':'u3c','z_min':'23','z_max':'23.025'},[0,1,3])]
    invalid_scopes = [{'xy_lo':'u3b','xy_hi':'u3b0'}, {'xy_lo':'u3b0','xy_hi':'u3b'},
        {'xy_lo':'u3c','xy_hi':'u3b'}, {'z_min':'23','z_max':'23'},
        {'z_min':'23.025','z_max':'23'}, {'z_min':23}, {'z_min':'٢٣'}, {'z_min':'23.0'},
        {'xy_lo':''}, {'xy_hi':'u'*13}, {'xy_lo':'U'}, {'h_lo':'u3b'}]
    add('V13','exact-XY_Z-wire-scopes','Seed coarse/fine XY, Z endpoints and unanchored fixtures; issue exact PULL queries.',
        dict(fixtures=['selection'+str(i) for i in range(8)],
             requests=[request(dict(mode='spatial',scope=scope)) for scope,_ in selections],
             invalid_requests=[request(dict(mode='spatial',scope=scope)) for scope in invalid_scopes]),
        'Lower-edge containment regardless of region size; exact half-open Z; equal padded keys and malformed bounds HTTP 400.',
        dict(addresses=[sorted(f['selection'+str(i)]['address'] for i in indexes) for _,indexes in selections],
             invalid_statuses=[400]*len(invalid_scopes)), 'Eight seeded records; PULL and rejected queries never mutate state.')
    return dict(format='punkti-freeze-vectors/1', seed_literal=SEED,
                seed_hex=hashlib.sha256(SEED.encode()).hexdigest(), fixtures=f, vectors=vectors)


class Runner:
    def __init__(self, kind, document):
        self.kind, self.doc = kind, document
        self.f = document['fixtures']
        self.stack = ExitStack()
        self.nodes = []

    def node(self):
        node = self.stack.enter_context(adapter(self.kind))
        self.nodes.append(node)
        return node

    def seed(self, node, name):
        f = self.f[name]
        actual = node.rpc('add',spec=f['spec'])
        self.canonical(actual,f)
        equal(actual['admission']['admitted'],True,'seed admission')

    def canonical(self, actual, fixture):
        for k in KEYS:
            equal(actual[k],fixture[k],self.kind+':'+k)
        equal(actual['sha256'],fixture['sha256_R'],'sha256_R')

    def call(self,node,r):
        return http(node.url,r['target'],r.get('body_utf8', '').encode() if r['method']=='POST' else None)

    def pull(self,node,q):
        return self.call(node,request(q))

    def snapshot(self,node):
        return node.rpc('state')

    def store(self,node,valid=(),candidates=(),log_count=None):
        s = self.snapshot(node)
        equal(sorted(e['address'] for e in s['valid']), sorted(valid),'VALID store')
        equal(sorted(e['address'] for e in s['candidates']), sorted(candidates),'candidate store')
        equal(len(s['log']),len(valid)+len(candidates) if log_count is None else log_count,'log count')
        for e in s['valid']+s['candidates']:
            expected = next(f for f in self.f.values() if f['address']==e['address'])
            equal(e['sha256'],expected['sha256_R'],'stored digest')

    def run(self,v):
        try:
            result = getattr(self,v['id'])(v['input'],v['expected'])
            for node in self.nodes:
                state = self.snapshot(node)
                for key, count in v['state_transition']['final_per_node'].items():
                    equal(len(state[key]), count, v['id'] + ':final ' + key)
            return result
        finally:
            self.stack.close()
            equal([k for k in sys.modules if k in ('carrier','mesh','spatial') or k.startswith('nairobidot')],[], 'harness isolation')

    def V1(self,i,e):
        n = self.node(); f = self.f[i['fixture']]
        equal(n.rpc('import_json',json=b64(i['json_utf8'].encode())),{'ok':e['import_ok']})
        self.canonical(n.rpc('mint',spec=f['spec']),f)
        decoded=n.rpc('decode',record=f['R'])
        for k in ('atom','C','S','MID','address','state'):
            equal(decoded[k],f[k])
        raw=base64.b64decode(f['R']); length=int.from_bytes(raw[:4],'big'); start=4+length
        equal(raw[4:start].hex(),f['C'])
        siglen=int.from_bytes(raw[start:start+4],'big')
        equal(len(raw),start+4+siglen,'full framing consumption')
        equal(b64(raw[start+4:]),f['sig'])
        equal(n.rpc('decode',record=b64(raw+b'!'))['state'],'INVALID-structural')
        results=[]
        for admitted in e['admitted']:
            equal(n.rpc('import_json',json=b64(i['json_utf8'].encode()))['ok'],True)
            status,response=self.call(n,i['request']);equal(status,e['http_status'])
            r=response['results'][0];equal(r['state'],e['state']);equal(r['admitted'],admitted)
            if not admitted: equal(r['reason'],e['duplicate_reason'])
            self.store(n,[f['address']]);results.append(dict(state=r['state'],admitted=r['admitted']))
        return results

    def V2(self,i,e):
        n=self.node();before=self.snapshot(n)
        status,empty=self.call(n,i['empty_mid']);equal(status,e['http_status'])
        equal(empty['records'],e['empty_records']);equal(empty['end'],e['empty_end'])
        equal(empty['cursor']['after'],e['empty_mid_after'])
        equal(self.call(n,i['empty_mid']),(status,empty),'identical empty body/token')
        equal(self.pull(n,dict(mode='mid',cursor=empty['cursor'])),(status,empty))
        status,spatial=self.call(n,i['empty_spatial']);equal(status,e['http_status'])
        equal(spatial['cursor']['after'],e['empty_spatial_after']);equal(spatial['end'],True);equal(spatial['records'],[])
        equal(self.snapshot(n),before)
        for name in i['fixtures']: self.seed(n,name)
        before=self.snapshot(n);query=i['first']['query'].copy();out=[]
        hello=http(n.url,'/hello')[1]
        for address in e['page_addresses']:
            status,page=self.pull(n,query);equal(status,e['http_status']);equal(len(page['records']),1)
            record=page['records'][0];equal(record['address'],address)
            equal(page['cursor']['after'],[address,record['sha256']]);equal(page['cursor']['epoch'],hello['epoch'])
            equal(bool(re.fullmatch(e['scope_pattern'],page['cursor']['scope'])),True)
            equal(record,item(next(f for f in self.f.values() if f['address']==address)))
            out.append(dict(record=record,after=page['cursor']['after'],scope=page['cursor']['scope'],end=page['end']))
            query['cursor']=page['cursor']
        equal(self.snapshot(n),before)
        return out

    def V3(self,i,e):
        n=self.node()
        for name in i['fixtures']: self.seed(n,name)
        before=self.snapshot(n);out=[]
        for r,status in zip(i['requests'],e['statuses']):
            actual,_=self.call(n,r);equal(actual,status);equal(self.snapshot(n),before);out.append(actual)
        return out

    def V4(self,i,e):
        n=self.node()
        for name in i['fixtures']:
            self.seed(n,name);h=self.f[name]['atom']['h'];equal(altitude(h),i['altitudes'][h])
        before=self.snapshot(n);out=[]
        for r,addresses in zip(i['requests'],e['addresses']):
            status,page=self.call(n,r);equal(status,e['http_status'])
            equal(sorted(a['address'] for a in page['records']),sorted(addresses));equal(page['end'],True)
            equal(self.snapshot(n),before);out.append(page['records'])
        return out

    def V5(self,i,e):
        n=self.node();before=self.snapshot(n);out=[]
        for r,status in zip(i['requests'],e['statuses']):
            actual,_=self.call(n,r);equal(actual,status);equal(self.snapshot(n),before);out.append(actual)
        # Observation is deliberately excluded from normative equality/pass totals.
        observed=self.call(n,i['empty_batch']['request'])
        self.non_normative={'empty_push':list(observed)}
        equal(self.snapshot(n),before)
        return out

    def V6(self,i,e):
        n=self.node();out=[]
        for req,expected in zip(i['requests'],e['results']):
            status,body=self.call(n,req);equal(status,e['http_status'])
            actual=[dict(state=r['state'],admitted=r['admitted']) for r in body['results']]
            equal(actual,expected);self.store(n,e['valid']);out.append(actual)
        return out

    def V7(self,i,e):
        n=self.node();before=self.snapshot(n);out=[];f=self.f[i['fixture']]
        self.canonical(n.rpc('mint',spec=f['spec']),f)
        for case,ok in zip(i['cases'],e['ok']):
            raw=case['json_utf8'].encode();r=n.rpc('import_json',json=b64(raw))
            equal(r['ok'],ok,case['spelling'])
            if ok:
                equal(json.loads(raw),f['atom']);equal(r,{'ok':True})
            else:
                equal(isinstance(r.get('error'),str),True)
            out.append(r['ok'])
        equal(self.snapshot(n),before)
        return out

    def V8(self,i,e):
        out=[]
        for mode in ('truncated','invalid'):
            n=self.node()
            with stub(i,mode) as peer:
                for index,ok in enumerate(e['ok']):
                    equal(n.rpc(i['adapter_command'], peer=peer.url,
                                mode=i['mode'], scope=i['scope'])['ok'],ok,mode+':pull_from')
                    self.store(n,e['valid'] if index else [],log_count=e['log_count'] if index else 0)
                equal(peer.cursors,e['cursors'],mode+':retry/resume cursor')
                out.append(dict(cursors=peer.cursors,valid=e['valid'],log_count=e['log_count']))
        return out

    def V9(self,i,e):
        source,target=self.node(),self.node();f=self.f[i['fixture']]
        self.canonical(source.rpc('mint',spec=f['spec']),f)
        for n in (source,target): self.seed(n,i['valid_fixture'])
        status,body=self.call(source,i['request']);equal(status,e['http_status'])
        for key in ('state','admitted'):equal(body['results'][0][key],e[key])
        equal(target.rpc('pull',peer=source.url),{'ok':True})
        out=[]
        for n in (source,target):
            self.store(n,e['valid'],e['candidates'])
            status,page=self.pull(n,{'mode':'mid'});equal(status,200)
            record=next(r for r in page['records'] if r['address']==f['address'])
            equal(record,item(f));decoded=n.rpc('decode',record=record['record'])
            equal(decoded['atom'],f['atom']);equal(decoded['state'],e['state']);out.append(record)
        return out

    def V10(self,i,e):
        n=self.node();before=self.snapshot(n);status,body=http(n.url,i['target']);equal(status,e['http_status'])
        for k in ('limits','capabilities','protocol'):equal(body[k],e[k])
        equal(all(type(v) is int for v in body['limits'].values()),True)
        equal(self.snapshot(n),before)
        return {k:body[k] for k in ('limits','capabilities','protocol')}

    def V11(self,i,e):
        n=self.node();out=[]
        for name in i['fixtures']:
            fixture=self.f[name];actual=n.rpc('mint',spec=fixture['spec'])
            self.canonical(actual,fixture);equal(actual['state'],e['state'])
            out.append({key:actual[key] for key in KEYS})
        for key in ('C','MID','address'):
            equal(len({a[key] for a in out}),len(out),'different Z changes '+key)
        for h in i['invalid_h']:
            # Send malformed signed content through each carrier's structural decoder.
            fixture=self.f[i['fixtures'][0]]
            atom=dict(fixture['atom'],h=h)
            equal(n.rpc('import_json',json=b64(packed(atom).encode()))['ok'],False,h)
            body=bytes.fromhex(fixture['C'])
            old=fixture['atom']['h'].encode();new=h.encode()
            body=body.replace(len(old).to_bytes(4,'big')+old,len(new).to_bytes(4,'big')+new,1)
            signature=base64.b64decode(fixture['sig'])
            raw=len(body).to_bytes(4,'big')+body+len(signature).to_bytes(4,'big')+signature
            equal(n.rpc('decode',record=b64(raw))['state'],e['invalid_state'],h)
        for a,left in enumerate(i['order']):
            for b,right in enumerate(i['order']):
                equal(n.rpc('spatial',operation='compare_z',args=[left,right]),{'value':(a>b)-(a<b)})
        return out

    def V12(self,i,e):
        n=self.node();out=[]
        equal(len(i['cells']),e['count'])
        for cell in i['cells']:
            equal(n.rpc('spatial',operation='encode_xy',args=[cell['lat'],cell['lon'],cell['precision']]),{'value':cell['xy']})
            result=n.rpc('spatial',operation='decode_xy',args=[cell['xy']])
            equal(result,{'value':cell['decoded']})
            equal(n.rpc('spatial',operation='encode_xy',args=[cell['decoded']['lat'],cell['decoded']['lon'],cell['precision']]),{'value':cell['xy']})
            out.append(result)
        return out

    def V13(self,i,e):
        n=self.node()
        for name in i['fixtures']: self.seed(n,name)
        before=self.snapshot(n);out=[]
        for req,addresses in zip(i['requests'],e['addresses']):
            status,page=self.call(n,req);equal(status,200)
            actual=sorted(r['address'] for r in page['records']);equal(actual,addresses)
            equal(self.snapshot(n),before);out.append(actual)
        for req,expected in zip(i['invalid_requests'],e['invalid_statuses']):
            status,_=self.call(n,req);equal(status,expected)
            equal(self.snapshot(n),before);out.append(status)
        return out


@contextmanager
def stub(i,mode):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            if self.path=='/hello':
                raw=i['hello_utf8'].encode();length=len(raw)
            else:
                equal(urlsplit(self.path).path,'/pull')
                query=json.loads(parse_qs(urlsplit(self.path).query)['q'][0])
                server.cursors.append(query.get('cursor'));count=len(server.cursors)
                if count==1 and mode=='truncated':
                    raw=i['truncated_body_utf8'].encode();length=i['declared_length']
                else:
                    key=('invalid_page_utf8' if count==1 else 'clean_page_utf8' if count==2 else 'resume_page_utf8')
                    raw=i[key].encode();length=len(raw)
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(length));self.end_headers();self.wfile.write(raw)
            self.close_connection=True
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.cursors=[]
    server.url='http://127.0.0.1:'+str(server.server_port)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
    try:yield server
    finally:server.shutdown();server.server_close();thread.join()
