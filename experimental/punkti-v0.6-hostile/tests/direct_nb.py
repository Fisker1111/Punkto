"""Direct clean-room imports only; no reference path here."""
import sys
from hostile.cases_protocol import ROOT, classify
sys.path.insert(0,str(ROOT/'experimental/nairobidot-l3/src'))
from nairobidot import carrier, spatial

def check(case):
    return classify(carrier,'nb',case)

def scope(h,s):
    try: return spatial.matches(h,s)
    except ValueError: return 'REJECT'

def altitude(h): return spatial.altitude(h)
