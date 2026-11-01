#!/usr/bin/env python3
"""Verify byte-exact Punkti 0.6 custody copies using the repository carrier."""
import argparse
import base64
import hashlib
import http.client
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'punkti_node'))
import carrier


class Inputs(argparse.Action):
    """Preserve input order across repeated and mixed source options."""

    def __call__(self, parser, namespace, values, option_string=None):
        inputs = getattr(namespace, 'inputs', None) or []
        inputs.extend((option_string[2:], value) for value in values)
        namespace.inputs = inputs


def verify(kind, source, expected):
    result = dict(source=source, bytes=None, sha256=None, state=None,
                  ed25519='INVALID', mid=None, h=None, refs=[],
                  canonical_body=False, payload_digest_base32_sha1=None,
                  t=None, alg=None, pk=None, sig=None, body_bytes=None,
                  expectations={}, ok=False)
    try:
        if kind == 'file':
            raw = Path(source).read_bytes()
        else:
            request = urllib.request.Request(source, headers={
                'User-Agent': 'Punkti-Custody-Verifier/1.0',
                'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        result.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                      payload_digest_base32_sha1=base64.b32encode(
                          hashlib.sha1(raw).digest()).decode('ascii').rstrip('='))
        result['state'] = carrier.validate(raw).state.value
        atom, body, sig = carrier.decode(raw)
        result.update({key: atom[key] for key in ('h', 't', 'alg', 'refs', 'pk', 'sig')})
        result.update(body_bytes=len(body), canonical_body=carrier.canonical(atom) == body,
                      mid=carrier.VERSION + ':' + hashlib.sha256(
                          carrier.MID_DOMAIN + body).hexdigest())
        if atom['alg'] == 'ed25519':
            try:
                Ed25519PublicKey.from_public_bytes(carrier.unb64(atom['pk'])).verify(
                    sig, carrier.SIGN_DOMAIN + body)
                result['ed25519'] = 'VALID'
            except (InvalidSignature, ValueError):
                pass
    except (OSError, ValueError, TypeError, urllib.error.URLError,
            http.client.HTTPException) as error:
        result['error'] = str(error)
    for key, value in expected.items():
        if key == 'reply_of':
            passed = sum(ref['target'] == value and ref['rel'] == 'reply'
                         for ref in result['refs']) == 1
        else:
            passed = result[key] == value
        result['expectations'][key] = passed
    result['ok'] = (result['state'] == 'VALID' and result['ed25519'] == 'VALID'
                    and result['canonical_body'] and 'error' not in result
                    and all(result['expectations'].values()))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', nargs='+', action=Inputs)
    parser.add_argument('--url', nargs='+', action=Inputs)
    for name in ('sha256', 'mid', 'h', 'reply-of'):
        parser.add_argument('--expect-' + name, action='append')
    args = parser.parse_args(argv)
    inputs = getattr(args, 'inputs', None)
    if not inputs:
        parser.error('at least one --file or --url input is required')
    expectations = {}
    for key in ('sha256', 'mid', 'h', 'reply_of'):
        values = getattr(args, 'expect_' + key)
        if values is not None:
            if len(values) != len(inputs):
                parser.error('--expect-' + key.replace('_', '-') +
                             ' count must match input count')
            expectations[key] = values
    failed = False
    for index, (kind, source) in enumerate(inputs):
        result = verify(kind, source, {key: values[index]
                                      for key, values in expectations.items()})
        print(json.dumps(result, separators=(',', ':')))
        print(('OK' if result['ok'] else 'FAIL') + ': ' + source, file=sys.stderr)
        failed |= not result['ok']
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
