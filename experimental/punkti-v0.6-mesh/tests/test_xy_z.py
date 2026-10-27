import unittest
from decimal import Decimal
from support import atom
from carrier import canonical, record, validate
from spatial import encode_xy, decode_xy, parse_z, format_z, compare_z, parse_h, Subscription

class XY_ZTests(unittest.TestCase):
    def test_ground_truth(self):
        for lat,lon,xy in [(55.675398,12.561895,'u3butz7k9q7v'),(51.5074,-.1278,'gcpvj0duq533'),
                           (35.6762,139.6503,'xn76cydhzven'),(40.7128,-74.006,'dr5regw3ppyz'),
                           (59.9139,10.7522,'u4xsudvxb2mq'),(0,0,'s000000000000'),
                           (-90,-180,'000000000000'),(90,180,'zzzzzzzzzzzz')]:
            for p in (4,10,12):
                self.assertEqual(encode_xy(lat,lon,p),xy[:p])
                cell=decode_xy(xy[:p])
                self.assertTrue(cell['lat_min'] <= lat <= cell['lat_max'])
                self.assertTrue(cell['lon_min'] <= lon <= cell['lon_max'])
                self.assertEqual(encode_xy(cell['lat'],cell['lon'],p),xy[:p])

    def test_canonical_and_exact_z(self):
        ordered=['-99999999999999999999999999','-18','-0.5','0','0.05','0.5','23','23.02','23.025','999999999999999999999999998','999999999999999999999999999']
        for a,b in zip(ordered,ordered[1:]): self.assertEqual(compare_z(a,b),-1)
        for z in ['+23','2.3e1','023','23.','23.0','23.50','-0','0.0','٢٣','.5','23\n']:
            with self.assertRaises(ValueError): parse_z(z)
        self.assertEqual(format_z(23.0254),'23.025')
        self.assertEqual(format_z(-.0001),'0')
        self.assertEqual(format_z(Decimal('23.025000')),'23.025')

    def test_carrier_grammar_and_identity(self):
        atoms=[atom(h='u3butz7k9q_'+z) for z in ('23','-18','23.025')]
        self.assertEqual(len({canonical(a) for a in atoms}),3)
        self.assertEqual(len({validate(record(a)).address for a in atoms}),3)
        for h in ['u3b_0','u'*13+'_0','u3bu0','u3bu__0','u3bu_','u3bu_'+'1'*28,'u3bu_٢٣']:
            with self.assertRaises(ValueError): canonical(dict(atoms[0],h=h))
        self.assertIsNone(parse_h(''))

    def test_key_containment(self):
        self.assertTrue(Subscription('u3bu','u3bu000001').matches('u3bu_23'))
        self.assertFalse(Subscription('u3butz7k9q','u3butz7k9r').matches('u3bu_23'))
        for xy in ('u3bu','u3butz7k9q'): self.assertTrue(Subscription('u3b','u3c').matches(xy+'_23'))
        self.assertFalse(Subscription('u3b','u3c').matches('u3c0_23'))
        with self.assertRaises(ValueError): Subscription('u3b','u3b0')

    def test_exact_half_open(self):
        s=Subscription(z_min='23',z_max='23.025')
        self.assertEqual([s.matches('u3bu_'+z) for z in ('23','23.02','23.025','22.999')],[True,True,False,False])
        for bounds in [dict(z_min=23),dict(z_min='23.0'),dict(z_min='1',z_max='1')]:
            with self.assertRaises(ValueError): Subscription(**bounds)
