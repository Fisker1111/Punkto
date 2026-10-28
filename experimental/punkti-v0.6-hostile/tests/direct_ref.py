"""Direct reference imports only; no clean-room path here."""
import sys
from hostile.cases_protocol import ROOT, classify
sys.path.insert(0,str(ROOT/'experimental/punkti-v0.6-mesh/src'))
import carrier
import spatial

def check(case):
    return classify(carrier,'ref',case)

def scope(h,s):
    try: return spatial.Subscription(**s).matches(h)
    except ValueError: return 'REJECT'

def altitude(h): return spatial.altitude(h)
