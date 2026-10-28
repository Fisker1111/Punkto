"""Store-local cursors, half-open scopes and arrival order over real HTTP."""
import itertools
import unittest
from urllib.parse import urlencode
from hostile.cases_protocol import *
from hostile.harness import Runner, Adapter, http, item, spec
import direct_ref
import direct_nb


def page(n,q): return http(n.url,'/pull?'+urlencode({'q':json.dumps(q,separators=(',',':'))}))
def tearDownModule():
    report('C-cursors'); report('D-spatial')

class Cursors(unittest.TestCase):
    def test_invalid_cursors_and_limits(self):
        for k in ('ref','nb'):
            with Runner('cursor',k) as r:
                n=r.node(); records=r.seed(n,9000,3)
                code,p=page(n,dict(limit=1)); self.assertEqual(code,200)
                token=p['cursor']
                changes=[('epoch','wrong'),('scope','0'*64),('after',4),('ceiling',4),('after',-1),('ceiling',-1),('after',1.5),('ceiling',1.5),('after','1'),('ceiling','1')]
                for i,(field,value) in enumerate(changes):
                    q=dict(limit=1,cursor=dict(token,**{field:value})); code,result=page(n,q)
                    self.assertEqual(code,400)
                    # Epoch itself is deliberately nondeterministic; exact attack token
                    # is represented with an explicit symbolic store-local substitution.
                    evidence=deepcopy(q); evidence['cursor']['epoch']='<node.epoch>' if field!='epoch' else 'wrong'
                    row('C-cursors',f'invalid-{field}-{i}',k,'HTTP 400',dict(status=code,response=result),False,raw=dumps(evidence))
                code,restarted=page(n,{})
                self.assertEqual(restarted['records'],[item(m) for m in records])
                row('C-cursors','null-restart-no-loss',k,3,len(restarted['records']),raw=b'{}')
                for limit in (0,33,1.5,'16',1,32):
                    code,result=page(n,dict(limit=limit))
                    expected=200 if limit in (1,32) else (413 if limit==33 else 400)
                    self.assertEqual(code,expected)
                    if code==200: self.assertEqual(len(result['records']),min(limit,3))
                    row('C-cursors','limit-'+repr(limit),k,'accept 1..32; refuse others',dict(status=code,**({'response':result} if code!=200 else {'count':len(result['records'])})),code==200,'AGREE',raw=dumps(dict(limit=limit)))
    def test_sweeps(self):
        for k in ('ref','nb'):
            with Runner('sweeps',k) as r:
                n=r.node(); records=r.seed(n,9100,3)
                _,first=page(n,dict(limit=1)); _,second=page(n,dict(limit=32,cursor=first['cursor']))
                self.assertEqual(first['records'],[item(records[0])]); self.assertEqual(second['records'],list(map(item,records[1:])))
                new=r.seed(n,9103,1); _,resumed=page(n,dict(cursor=second['cursor']))
                self.assertEqual(resumed['records'],list(map(item,new)))
                row('C-cursors','spatial-completed-resume',k,[1,2,1],[len(first['records']),len(second['records']),len(resumed['records'])],raw=dumps([item(m) for m in records+new]))
                # MID empty page preserves the implementation's exact initial sentinel.
                empty=r.node(); _,p=page(empty,dict(mode='mid')); _,p2=page(empty,dict(mode='mid',cursor=p['cursor']))
                self.assertEqual(p,p2); sentinel=None; self.assertEqual(p['cursor']['after'],sentinel)
                row('C-cursors','mid-empty-sentinel',k,None,sentinel,classification='AGREE',raw=b'{"mode":"mid"}')
                addresses=sorted(m['address'] for m in records+new)
                _,bounded=page(n,dict(mode='mid',lo=addresses[1],hi=addresses[3]))
                self.assertEqual([w['address'] for w in bounded['records']],addresses[1:3])
                row('C-cursors','mid-half-open',k,addresses[1:3],[w['address'] for w in bounded['records']],raw=dumps(dict(mode='mid',lo=addresses[1],hi=addresses[3])))
                for name,lo,hi in [('equal',addresses[1],addresses[1]),('reversed',addresses[2],addresses[1])]:
                    q=dict(mode='mid',lo=lo,hi=hi); code,p=page(n,q)
                    self.assertEqual((code,p),(400,{'error':'MID bounds'} if k=='ref' else {'kind':'request','reason':'equal or reversed bounds'}))
                    row('C-cursors','mid-'+name,k,'reject lo >= hi',dict(status=code,response=p),False,'AGREE',raw=dumps(q),note='The spec now requires HTTP 400 for equal or reversed bounds.')
                # Pick a deterministic lower MID from three fixed records. Admit it
                # only after opening a sweep over the higher two addresses.
                target=r.node(); minted=[r.call(target,'mint',spec=spec(i)) for i in range(9200,9203)]
                minted.sort(key=lambda m:m['address'])
                for m in minted[1:]: self.assertEqual(http(target.url,'/push',dict(records=[item(m)]))[0],200)
                _,p=page(target,dict(mode='mid',limit=1))
                http(target.url,'/push',dict(records=[item(minted[0])]))
                _,continuation=page(target,dict(mode='mid',cursor=p['cursor']))
                self.assertEqual(continuation['records'],[item(minted[2])])
                _,fresh=page(target,dict(mode='mid'))
                self.assertEqual(fresh['records'],list(map(item,minted)))
                row('C-cursors','insert-behind-active-sweep',k,[1,1,3],[len(p['records']),len(continuation['records']),len(fresh['records'])],raw=dumps(list(map(item,minted))),note='Active ceiling excludes new insertion; fresh null sweep includes it.')
    def test_all_arrival_permutations(self):
        for k in ('ref','nb'):
            with Runner('permutations',k) as r:
                source=r.node(); records=[r.call(source,'mint',spec=spec(i)) for i in range(9300,9303)]
                for permutation in itertools.permutations(range(3)):
                    n=r.node(); ordered=[records[i] for i in permutation]
                    http(n.url,'/push',dict(records=list(map(item,ordered))))
                    r.equal([n],records)
                    self.assertEqual([e['address'] for e in r.state(n)['log']],[m['address'] for m in ordered])
                    row('C-cursors','arrival-'+''.join(map(str,permutation)),k,list(permutation),list(permutation),True,raw=dumps(list(map(item,ordered))),note='Sequence 1..3 follows arrival, not protocol/MID order; final exact store identical.')

class Spatial(unittest.TestCase):
    def test_decoders_and_scopes(self):
        samples=['000000000000_-18','zzzzzzzzzzzz_9000','gggh00000000_0',
                 'u3butz7k9q_23','u3butz7k9q_23.025']
        for h in samples:
            for k,m in [('ref',direct_ref),('nb',direct_nb)]:
                self.assertEqual(str(m.altitude(h)),h.split('_')[1])
                row('D-spatial','decode-'+h,k,h.split('_')[1],str(m.altitude(h)),raw=h.encode(),note='Z is an exact decimal claim, independent of XY.')
        h='u3bu_23'
        cases=[('exact-cell',dict(xy_lo='u3bu',xy_hi='u3bv'),True),
               ('lower-inclusive',dict(xy_lo='u3bu'),True),('upper-exclusive',dict(xy_hi='u3bu'),False),
               ('span',dict(xy_lo='g',xy_hi='z'),True),('full',{},True),
               ('xy-reversed',dict(xy_lo='t',xy_hi='g'),'REJECT'),
               ('xy-equal-key',dict(xy_lo='u3b',xy_hi='u3b0'),'REJECT'),
               ('coarse-in-fine',dict(xy_lo='u3bu',xy_hi='u3bu000001'),True),
               ('coarse-overlap-only',dict(xy_lo='u3butz7k9q',xy_hi='u3butz7k9r'),False),
               ('z-equal',dict(z_min='23',z_max='23'),'REJECT'),
               ('z-reversed',dict(z_min='1',z_max='-1'),'REJECT'),
               ('z-number',dict(z_min=23),'REJECT'),
               ('z-negative',dict(z_min='-18',z_max='0'),False),
               ('z-fractional',dict(z_min='23',z_max='23.025'),True),
               ('z-upper-exclusive',dict(z_max='23'),False),
               ('null',dict(xy_lo=None,xy_hi=None,z_min=None,z_max=None),True)]
        for name,scope,expected in cases:
            for k,m in [('ref',direct_ref),('nb',direct_nb)]:
                observed=m.scope(h,scope)
                self.assertEqual(observed,expected)
                row('D-spatial',name,k,expected,observed,classification='AGREE',raw=dumps(dict(h=h,scope=scope)))
        for k,m in [('ref',direct_ref),('nb',direct_nb)]:
            scope=dict(z_min='23',z_max='23.025')
            addresses=['u3bu_'+z for z in ('23','23.02','23.025','22.999')]
            selected=[m.scope(address,scope) for address in addresses]
            self.assertEqual(selected,[True,True,False,False])
            row('D-spatial','same-XY-Z-boundary',k,[True,True,False,False],selected,raw=dumps(dict(h=addresses,scope=scope)),note='Exact decimal half-open boundary, no float comparison.')

    def test_equal_padded_bounds_http(self):
        for k in ('ref','nb'):
            with Runner('xy-z-invalid-scope',k) as r:
                node=r.node()
                for scope in [dict(xy_lo='u3b',xy_hi='u3b0'),dict(z_min=23),dict(z_min='23.0')]:
                    status,result=page(node,dict(scope=scope))
                    self.assertEqual(status,400)
                    row('D-spatial','wire-'+str(scope),k,400,status,raw=dumps(scope))

    def test_overlapping_nodes(self):
        for k in ('ref','nb'):
            with Runner('overlap',k) as r:
                source=r.node()
                records=[r.call(source,'mint',spec=dict(spec(9400+i),h=h)) for i,h in enumerate(['000000000000_-18','gggh00000000_0','s00000000000_23','zzzzzzzzzzzz_9000'])]
                scopes=[[dict(xy_lo='0',xy_hi='t'),dict(xy_lo='g',xy_hi='z')],[dict(xy_lo='g',xy_hi='z')]]
                nodes=[]
                for i,subs in enumerate(scopes):
                    n=Adapter(k,dict(subscriptions=subs,peers=[])); r.nodes.append(n); nodes.append(n)
                    code,p=http(n.url,'/push',dict(records=list(map(item,records))))
                    expected=[True,True,True,False] if i==0 else [False,True,True,False]
                    self.assertEqual(code,200); self.assertEqual([a['admitted'] for a in p['results']],expected)
                    for accepted,a in zip(expected,p['results']):
                        if not accepted: self.assertEqual(a['reason'],'out-of-scope')
                    r.equal([n],[m for m,yes in zip(records,expected) if yes])
                    row('D-spatial','overlap-node-'+str(i),k,expected,[a['admitted'] for a in p['results']],raw=dumps(dict(subscriptions=subs,records=list(map(item,records)))))
                left={e['address']:e['sha256'] for e in r.state(nodes[0])['valid']}; right={e['address']:e['sha256'] for e in r.state(nodes[1])['valid']}
                self.assertEqual({a:left[a] for a in right},right)
