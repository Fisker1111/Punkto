"""Real HTTP admission, candidate preservation, replay and wrapper attacks."""
import unittest
from hostile.cases_protocol import *
from hostile.harness import Runner, http, item, spec


def tearDownModule(): report('B-provenance')

def wrapper(raw,address=None):
    csize=int.from_bytes(raw[:4],'big')
    return dict(record=b64(raw),sha256=hashlib.sha256(raw).hexdigest(),address=address or 'punkti/0.6:'+hashlib.sha256(b'PUNKTI-L3-MID\0'+raw[4:4+csize]).hexdigest())

def push(n,w): return http(n.url,'/push',dict(records=[w]))

class Provenance(unittest.TestCase):
    def test_mutations_and_keys(self):
        for k in ('ref','nb'):
            with Runner('mutations',k) as r:
                n=r.node(); original=atom()
                for field,value in dict(t=1,h='gggj00000000_0',x='changed',pk=b64(bytes(32)),refs=[dict(target='future:ab',rel='r')],ext='YQ==',alg='ED25519').items():
                    a=deepcopy(original); a[field]=value; w=wrapper(wire(a))
                    code,result=push(n,w); self.assertEqual(code,200)
                    expected=U if field=='alg' else P
                    self.assertEqual(result['results'][0],dict(state=expected,admitted=field=='alg',**({'reason':'signature-failed'} if k=='nb' and field!='alg' else {})))
                    row('B-provenance','mutate-'+field,k,expected,expected,field=='alg',raw=dumps(w),note='Unknown algorithm cannot be signature-verified; retained only as candidate.' if field=='alg' else '')
                self.assertEqual(r.state(n)['valid'],[])
                self.assertEqual(len(r.state(n)['candidates']),1)
                records=[r.call(n,'add',spec=dict(spec(8000),seed=seed)) for seed in ('key-one','key-two')]
                self.assertNotEqual(records[0]['address'],records[1]['address'])
                self.assertTrue(all(m['admission']['admitted'] for m in records))
                row('B-provenance','key-substitution',k,'two VALID distinct MIDs','two VALID distinct MIDs',True,raw=dumps([item(m) for m in records]))
    def test_forgery_then_replay(self):
        for k in ('ref','nb'):
            with Runner('replay',k) as r:
                n=r.node(); raw=wire(atom()); good=wrapper(raw); forged=wrapper(raw[:-1]+bytes([raw[-1]^1]),good['address'])
                code,response=push(n,forged); self.assertEqual(code,200)
                self.assertEqual(response['results'][0]['state'],P)
                self.assertFalse(response['results'][0]['admitted']); r.equal([n],[])
                row('B-provenance','forged-first',k,P,P,False,raw=dumps(forged))
                flags=[]
                for _ in range(100):
                    code,result=push(n,good); self.assertEqual(code,200); flags.append(result['results'][0]['admitted'])
                self.assertEqual(flags,[True]+[False]*99)
                state=r.state(n); self.assertEqual(len(state['log']),1); self.assertEqual(state['candidates'],[])
                self.assertEqual(state['valid'][0]['sha256'],good['sha256'])
                row('B-provenance','valid-after-forgery-100-replays',k,[1,99,1],[sum(flags),len(flags)-sum(flags),len(state['log'])],True,raw=dumps(good))
                wrong=dict(good,address='punkti/0.6:'+'0'*64)
                code,result=push(n,wrong)
                expected=(400,{'error':'address mismatch'}) if k=='ref' else (400,{'kind':'request','reason':'address-mismatch'})
                self.assertEqual((code,result),expected); self.assertEqual(r.state(n),state)
                row('B-provenance','wrong-declared-address',k,'HTTP 400; no admission',list(expected),False,'AGREE',raw=dumps(wrong))
    def test_unknown_and_opaque(self):
        for k in ('ref','nb'):
            with Runner('candidates',k) as r:
                n=r.node()
                for alg in ('ml-dsa-65','future/x'):
                    w=wrapper(wire(atom(alg=alg)))
                    code,result=push(n,w); self.assertEqual((code,result),(200,{'results':[dict(state=U,admitted=True)]}))
                    # Retrieve original R over the public page API, not just a digest assertion.
                    from urllib.parse import urlencode
                    code,page=http(n.url,'/pull?'+urlencode({'q':json.dumps({})}))
                    self.assertIn(w,page['records']); self.assertEqual(r.state(n)['valid'],[])
                    row('B-provenance','unknown-'+alg,k,U,U,True,raw=dumps(w))
                opaque=wrapper(b'\x00future\xffopaque\x00','punkti/0.9:'+'ab'*32)
                code,result=push(n,opaque); self.assertEqual((code,result),(200,{'results':[dict(state='OPAQUE-version',admitted=True)]}))
                code,page=http(n.url,'/pull?'+urlencode({'q':'{}'})); self.assertIn(opaque,page['records'])
                row('B-provenance','opaque-version',k,'OPAQUE-version','OPAQUE-version',True,raw=dumps(opaque))
                corrupt=dict(opaque,sha256='0'*64); code,result=push(n,corrupt)
                expected=(400,dict(error='transport digest mismatch')) if k=='ref' else (400,dict(kind='request',reason='transport-digest'))
                self.assertEqual((code,result),expected)
                row('B-provenance','opaque-corrupt-digest',k,'HTTP 400; no admission',list(expected),False,'AGREE',raw=dumps(corrupt))
                good=wrapper(wire(atom())); self.assertTrue(push(n,good)[1]['results'][0]['admitted'])
                before=r.state(n); collision=dict(opaque,address=good['address'])
                code,result=push(n,collision); self.assertEqual(code,200); self.assertEqual(result['results'][0]['state'],S); self.assertFalse(result['results'][0]['admitted']); self.assertEqual(r.state(n),before)
                row('B-provenance','opaque-claims-verified-address',k,S,S,False,raw=dumps(collision))
