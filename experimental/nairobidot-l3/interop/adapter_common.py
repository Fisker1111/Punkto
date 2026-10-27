"""Shared RPC plumbing only; carrier operations remain implementation-owned."""
import argparse
import base64
import hashlib
import json
import sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def b64(raw):
    return base64.b64encode(raw).decode('ascii')


def run(carrier, Node, Subscription=None, spatial_codec=None):
    ref = Subscription is not None
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--stdin', action='store_true')
    group.add_argument('--serve')
    args = parser.parse_args()
    node = None

    def describe(raw):
        validation = carrier.validate(raw)
        out = dict(C=None, S=None, MID=None, address=None,
                   state=validation.state.value, reason=getattr(validation, 'reason', None))
        try:
            if ref:
                atom, body, _ = carrier.decode(raw)
                address = validation.address
                signed = carrier.SIGN_DOMAIN + body
            else:
                record = carrier.decode_record(raw)
                atom, body, address, signed = record.atom, record.C, record.address, record.S
            out.update(C=body.hex(), S=signed.hex(), MID=address.split(':')[1],
                       address=address, atom=atom)
        except ValueError:
            pass
        return out

    def mint(spec):
        key = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(spec['seed'].encode()).digest())
        atom = dict(v='punkti/0.6', t=spec['t'], h=spec['h'], x=spec['x'],
                    refs=spec['refs'], ext=spec['ext'], alg=spec.get('alg', 'ed25519'),
                    pk=b64(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
                    sig=b64(bytes(64)))
        body = carrier.canonical(atom) if ref else carrier.canonical_body(atom)
        if atom['alg'] == 'ed25519':
            atom['sig'] = b64(key.sign(b'PUNKTI-L3-SIGN\0' + body))
        raw = carrier.record(atom) if ref else carrier.from_atom(atom).R
        out = describe(raw)
        out.update(atom=atom, R=b64(raw), sig=atom['sig'], sha256=hashlib.sha256(raw).hexdigest())
        return out

    def entry(e):
        raw = e.raw
        return dict(address=e.address, sha256=hashlib.sha256(raw).hexdigest(),
                    seq=e.seq if ref else e.sequence)

    try:
        if args.serve:
            with open(args.serve) as stream:
                config = json.load(stream)
            scopes = config.get('subscriptions', [{}])
            peers = config.get('peers', [])
            node = (Node(subscriptions=[Subscription(**s) for s in scopes], peers=peers).start(config.get('port', 0))
                    if ref else Node(scopes, peers, config.get('port', 0)).start())
            print(json.dumps(dict(url=node.url, epoch=node.epoch)), flush=True)
        for line in sys.stdin:
            stop = False
            try:
                req = json.loads(line)
                cmd = req['cmd']
                if cmd == 'spatial':
                    operation = req['operation']
                    if operation not in ('encode_xy', 'decode_xy', 'format_z', 'compare_z', 'parse_h'):
                        raise ValueError('spatial operation')
                    result = {'value': getattr(spatial_codec, operation)(*req['args'])}
                elif cmd == 'mint':
                    result = mint(req['spec'])
                elif cmd == 'import_json':
                    carrier.import_json(base64.b64decode(req['json'], validate=True))
                    result = {'ok': True}
                elif cmd == 'decode':
                    result = describe(carrier.unb64(req['record']))
                elif cmd == 'shutdown':
                    result, stop = {'ok': True}, True
                elif cmd == 'isolation':
                    result = dict(path=sys.path, modules={k: getattr(v, '__file__', None) for k, v in sys.modules.items()
                                  if k in ('carrier', 'mesh', 'spatial') or k.startswith('nairobidot')})
                elif node is None:
                    raise ValueError('server required')
                elif cmd == 'state':
                    result = dict(epoch=node.epoch, valid=[entry(e) for e in node.store.values()],
                                  candidates=[entry(e) for e in node.candidates.values()], log=[entry(e) for e in node.log])
                elif cmd == 'add':
                    result = mint(req['spec'])
                    result['admission'] = node.add(base64.b64decode(result['R']))
                elif cmd == 'hello':
                    result = node.hello()
                elif cmd == 'configure':
                    # Explicit local peer configuration, needed before reciprocal callbacks.
                    from urllib.parse import urlsplit
                    for peer in req['peers']:
                        p = urlsplit(peer)
                        if p.scheme != 'http' or p.hostname != '127.0.0.1' or not p.port:
                            raise ValueError('loopback required')
                    node.peers.update(req['peers'])
                    result = {'ok': True}
                elif cmd == 'sync_known':
                    result = dict(ok=True, result=node.sync_known())
                elif cmd == 'connect':
                    node.connect(req['peer'])
                    result = {'ok': True}
                elif cmd == 'push_to':
                    (node.push_to if ref else node._push_to)(req['peer'])
                    result = {'ok': True}
                elif cmd == 'pull_from':
                    if ref:
                        node.pull(req['peer'], scope=Subscription(**req.get('scope', {})),
                                  mode=req.get('mode', 'spatial'))
                    else:
                        node._pull_from(req['peer'])
                    result = {'ok': True}
                elif cmd == 'pull':
                    opts = {k: req[k] for k in ('mode', 'scope', 'lo', 'hi') if k in req}
                    if ref and 'scope' in opts:
                        opts['scope'] = Subscription(**opts['scope'])
                    node.pull(req['peer'], **opts)
                    result = {'ok': True}
                else:
                    raise ValueError('unknown command')
            except Exception as exc:
                result = dict(ok=False, error=f'{type(exc).__name__}: {exc}')
            print(json.dumps(result, ensure_ascii=True), flush=True)
            if stop:
                break
    except Exception as exc:
        print(json.dumps(dict(ok=False, error=f'{type(exc).__name__}: {exc}')), flush=True)
    finally:
        if node:
            node.stop()
