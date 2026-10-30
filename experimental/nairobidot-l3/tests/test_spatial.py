"""Independent checks of the XY_Z profile candidate."""
import unittest
from decimal import Decimal
from nairobidot.carrier import StructuralError, from_atom
from nairobidot.spatial import (altitude, matches, normalize, subscribed, encode_xy,
                               decode_xy, parse_z, format_z, compare_z, parse_h)
from vectors import atom

class SpatialTests(unittest.TestCase):
    def test_ground_truth(self):
        rows=[(55.675398,12.561895,'u3butz7k9q7v'),(51.5074,-.1278,'gcpvj0duq533'),
              (35.6762,139.6503,'xn76cydhzven'),(40.7128,-74.006,'dr5regw3ppyz'),
              (59.9139,10.7522,'u4xsudvxb2mq'),(0,0,'s000000000000'),
              (-90,-180,'000000000000'),(90,180,'zzzzzzzzzzzz')]
        for lat,lon,expected in rows:
            for n in [4,10,12]:
                with self.subTest(lat=lat,precision=n):
                    self.assertEqual(encode_xy(lat,lon,n),expected[:n])
                    cell=decode_xy(expected[:n])
                    self.assertLessEqual(cell['lat_min'],lat)
                    self.assertGreaterEqual(cell['lat_max'],lat)
                    self.assertLessEqual(cell['lon_min'],lon)
                    self.assertGreaterEqual(cell['lon_max'],lon)
                    self.assertEqual(encode_xy(cell['lat'],cell['lon'],n),expected[:n])

    def test_scopes(self):
        h='gggh00000000_23'
        self.assertTrue(matches(h,{'xy_lo':'gggh','xy_hi':'gggj'}))
        self.assertFalse(matches('gggj00000000_23',{'xy_hi':'gggj'}))
        self.assertFalse(matches('ggggzzzzzzzz_23',{'xy_lo':'gggh'}))
        for scope in ({},{'xy_lo':'0'},{'xy_hi':'z'},{'z_min':'-1000'},{'z_max':'9000'}):
            with self.assertRaises(StructuralError): matches('',scope)
        # None here is internal opaque-future-version metadata, not a v0.6 h.
        # v0.6 parse_h(None) must still fail before algorithm dispatch.
        with self.assertRaises(StructuralError): parse_h(None)
        self.assertTrue(matches(None,{}))
        self.assertFalse(matches(None,{'z_min':'-1000'}))
        self.assertFalse(subscribed(h,[]))
        self.assertTrue(subscribed(h,[{'xy_hi':'0'},{'xy_lo':'g'}]))

    def test_bad_scopes(self):
        for s in ({'xy_lo':'g','xy_hi':'g'},{'xy_lo':'z','xy_hi':'0'},
                  {'z_min':'1','z_max':'1'},{'z_min':'1','z_max':'-1'},
                  {'xy_lo':'u3b','xy_hi':'u3b0'},{'xy_lo':''},{'xy_hi':'i'},
                  {'z_min':True},{'z_min':23},{'z_min':float('inf')},{'z_min':'٢٣'},
                  {'z_max':'23.0'},{'h_lo':'u'},{'x':''},[]):
            with self.subTest(scope=s), self.assertRaises(StructuralError): normalize(s)

    def test_historical_identity(self):
        records=[from_atom(atom(h='u3butz7k9q_'+height)) for height in ['23','-18','23.025']]
        for field in ['C','mid','address']:
            self.assertEqual(len({getattr(record,field) for record in records}),3)
        self.assertEqual(altitude('u3butz7k9q_-18'),Decimal('-18'))

    def test_spelling_rejection(self):
        for z in ['-0','0.0','0.00','23.0','23.50','023','+23','2.3e1','23.','.5','23 ','٢٣','1\n']:
            with self.assertRaises(StructuralError): parse_z(z)
        for h in ['u3b_23','u'*13+'_0','u3bu23','u3bu__23','u3bu_','u3bu_'+'1'*28]:
            with self.assertRaises(StructuralError): parse_h(h)

    def test_decimal_order(self):
        values=['-18','-0.5','0','0.05','0.5','23','23.02','23.025',
                '999999999999999999999999998','999999999999999999999999999']
        for i,left in enumerate(values):
            for j,right in enumerate(values): self.assertEqual(compare_z(left,right),(i>j)-(i<j))

    def test_boundary_exactness(self):
        scope={'z_min':'23','z_max':'23.025'}
        for z,accepted in [('23',True),('23.02',True),('23.025',False),('22.999',False)]:
            self.assertEqual(matches('u3bu_'+z,scope),accepted)

    def test_lower_edge_selection(self):
        self.assertTrue(matches('u3bu_0',{'xy_lo':'u3bu','xy_hi':'u3bu000001'}))
        self.assertFalse(matches('u3bu_0',{'xy_lo':'u3butz7k9q','xy_hi':'u3butz7k9r'}))
        for xy in ['u3bu','u3butz7k9q','u3c0']:
            self.assertEqual(matches(xy+'_0',{'xy_lo':'u3b','xy_hi':'u3c'}),xy!='u3c0')

    def test_client_format(self):
        self.assertEqual(format_z(23.0254),'23.025')
        self.assertEqual(format_z(-.0001),'0')
        self.assertEqual(format_z(Decimal('23.50')),'23.5')
        with self.assertRaises(StructuralError): format_z('23.50')
