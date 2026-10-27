"""Isolated adapter for public discover() absent from the original RPC adapter.

Exactly one implementation is imported per child. No methods are patched.
"""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4]
kind,peer=sys.argv[1:]
if kind=='ref':
    sys.path.insert(0,str(ROOT/'experimental/punkti-v0.6-mesh/src'))
    from mesh import Node
    node=Node(peers=[peer]).start()
else:
    sys.path.insert(0,str(ROOT/'experimental/nairobidot-l3/src'))
    from nairobidot.node import Node
    node=Node([{}],[peer]).start()
try:
    for line in sys.stdin:
        command=json.loads(line)
        if command=='stop': break
        before=node.hello()
        try:
            hints=node.discover() if kind=='ref' else node.discover(peer)
            result=dict(state='returned',hints=sorted(hints))
        except Exception as exc:
            result=dict(state=type(exc).__name__,message=str(exc),hints=[])
        result.update(peers_unchanged=before['peers']==node.hello()['peers'],
                      valid=len(node.store),candidates=len(node.candidates),log=len(node.log),url=node.url)
        print(json.dumps(result),flush=True)
finally:
    node.stop()
