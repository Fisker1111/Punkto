"""Import the real carrier/mesh without modifying it or creating bytecode there."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'punkti-v0.6-mesh' / 'src'))
import base64
import json
import carrier
from mesh import Node, packed

request = json.load(sys.stdin)
atom = request['atom']
if request['mode'] == 'canonical':
    print(json.dumps({'body': base64.b64encode(carrier.canonical(atom)).decode()}))
else:
    raw = carrier.record(atom)
    parsed, body, sig = carrier.decode(raw)
    assert parsed['x'].encode() == atom['x'].encode()
    assert parsed['x'].startswith('brth/1:')
    assert carrier.validate(raw).state == carrier.State.VALID
    # Exercise the actual mesh store, paginated transport wrappers and admission.
    # JSON serialization represents the transport boundary, without network I/O.
    first, second = Node(epoch='test-a'), Node(epoch='test-b')
    assert first.add(raw)['admitted']
    page = json.loads(packed(first.page({'limit': 1})))
    assert second.admit(page['records'][0])['admitted']
    received = second.log[0].raw
    assert received == raw
    received_atom, received_body, _ = carrier.decode(received)
    assert received_body == body
    assert received_atom['x'].encode() == atom['x'].encode()
    # A nonsensical BRTH payload is equally opaque to this carrier.
    opaque = dict(atom, x='brth/1:this is not JSON')
    assert carrier.decode(carrier.record(opaque))[0]['x'] == opaque['x']
    print(json.dumps({'x': received_atom['x'], 'record': base64.b64encode(received).decode(),
                      'body': base64.b64encode(received_body).decode(), 'state': 'VALID',
                      'opaque': True, 'stored': len(second.store)}))
