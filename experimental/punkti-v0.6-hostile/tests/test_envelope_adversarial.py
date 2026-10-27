"""Envelope cases use independent direct modules and original --stdin adapters."""
import unittest
from hostile.cases_protocol import *
from hostile.harness import BaseAdapter, spec
import direct_ref
import direct_nb


def tearDownModule(): report('A-envelope')

class Envelope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapters={k:BaseAdapter(k) for k in ('ref','nb')}
    @classmethod
    def tearDownClass(cls):
        for a in cls.adapters.values(): a.close()
    def test_adapter_mint(self):
        minted=[self.adapters[k].rpc('mint',spec=spec(7000)) for k in ('ref','nb')]
        for key in ('C','S','MID','R','sig'): self.assertEqual(minted[0][key],minted[1][key])
        for k,m in zip(('ref','nb'),minted):
            self.assertEqual(m['state'],V)
            row('A-envelope','adapter-mint',k,V,m['state'],raw=dumps(spec(7000)))
    def test_order_and_unicode(self):
        refs=[dict(target='future:ab',rel='one'),dict(target='future:cd',rel='two')]
        variants=[atom(refs=refs+refs[:1]),atom(refs=list(reversed(refs))+refs[:1]),atom(x='é'),atom(x='e\u0301')]
        for k in ('ref','nb'):
            results=[self.adapters[k].rpc('decode',record=b64(wire(a))) for a in variants]
            self.assertEqual(results[0]['atom']['refs'],refs+refs[:1])
            for i,j in ((0,1),(2,3)):
                self.assertNotEqual(results[i]['C'],results[j]['C']); self.assertNotEqual(results[i]['MID'],results[j]['MID'])
            row('A-envelope','refs-order-duplicates-and-no-normalization',k,'distinct C/MID; ordered duplicates','distinct C/MID; ordered duplicates',raw=dumps(variants))


def make(case):
    def test(self):
        observed={}
        for k,module in [('ref',direct_ref),('nb',direct_nb)]:
            state,raw=module.check(case); observed[k]=state
            self.assertEqual(state,case['pins'][k],(case['name'],k))
            if raw is not None:
                response=self.adapters[k].rpc('decode',record=b64(raw))
                self.assertEqual(response['state'],state)
            elif case['mode']=='wire':
                response=self.adapters[k].rpc('decode',record=b64(case['raw']))
                if state==L: self.assertIn('Resource',response['error'])
                else: self.assertEqual(response['state'],state)
        different=observed['ref']!=observed['nb']
        for k in observed:
            row('A-envelope',case['name'],k,case['expected'],observed[k],classification='DIVERGE' if different else 'AGREE',raw=case['raw'],note='Direct import_json/validate; successfully imported R also checked via original --stdin decode.')
    return test
for case in envelope_cases(): setattr(Envelope,'test_'+case['name'].replace('-','_'),make(case))
