#!/usr/bin/env python3
"""Transport exact record bytes; use custody_verify.py for custody verification."""
import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request


def sha256_arg(value):
    if not re.fullmatch(r'[0-9a-fA-F]{64}', value):
        raise argparse.ArgumentTypeError('SHA-256 must be 64 hexadecimal characters')
    return value.lower()


def http_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise argparse.ArgumentTypeError('an HTTP or HTTPS URL is required')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise argparse.ArgumentTypeError('URL must not contain credentials, query or fragment')
    return value.rstrip('/')


def request_bytes(url, data=None):
    headers = {'Accept-Encoding': 'identity'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f'expected HTTP 200, got {response.status}')
        return response.read()


def digest(raw, expected=None):
    actual = hashlib.sha256(raw).hexdigest()
    if expected is not None and actual != expected:
        raise ValueError(f'SHA-256 mismatch: expected {expected}, got {actual}')
    return actual


def fetch(args):
    target = Path(args.out)
    if os.path.lexists(target) and not args.force:
        raise ValueError(f'output already exists: {target}; use --force to overwrite')
    raw = request_bytes(args.url)
    sha = digest(raw, args.sha256)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.' + target.name + '.',
                                         delete=False) as output:
            temporary = output.name
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        if not args.force:
            # Publish complete bytes exclusively: no empty placeholder or clobber.
            os.link(temporary, target)
        os.replace(temporary, target)
    finally:
        # replace may be a no-op when both paths already name the same inode.
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)
    print(json.dumps(dict(file=str(target), bytes=len(raw), sha256=sha)))


def derive_address(raw):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'punkti_node'))
    try:
        import carrier
    except ImportError as error:
        raise ValueError('repository carrier unavailable; supply --address explicitly') from error
    observation = carrier.validate(raw)
    if not observation.address:
        raise ValueError('carrier could not derive MID; verify the record with custody_verify.py')
    return observation.address


def submit(args):
    raw = Path(args.file).read_bytes()
    sha = digest(raw, args.sha256)
    address = args.address if args.address is not None else derive_address(raw)
    payload = dict(records=[dict(record=base64.b64encode(raw).decode('ascii'),
                                 sha256=sha, address=address)])
    response = json.loads(request_bytes(args.base + '/submit', json.dumps(payload).encode('utf-8')))
    print(json.dumps(response))
    results = response.get('results') if isinstance(response, dict) else None
    if (not isinstance(results, list) or len(results) != 1 or
            not isinstance(results[0], dict) or results[0].get('admitted') is not True or
            results[0].get('sha256') != sha or results[0].get('address') != address):
        raise ValueError('response does not report this record as admitted')


def seed(args):
    raw = Path(args.file).read_bytes()
    sha = digest(raw, args.sha256)
    address = args.address if args.address is not None else derive_address(raw)
    line = (json.dumps(dict(address=address, sha256=sha,
                           record=base64.b64encode(raw).decode('ascii')),
                       separators=(',', ':')) + '\n').encode('utf-8')
    directory = Path(args.data_dir)
    target = directory / 'atoms.jsonl'
    if not args.append and os.path.lexists(target):
        raise ValueError(f'output already exists: {target}; use --append to add a record')
    directory.mkdir(parents=True, exist_ok=True)
    if args.append:
        # Unbuffered append: one O_APPEND write of the complete wrapper line.
        with target.open('ab', buffering=0) as output:
            if output.write(line) != len(line):
                raise OSError('short append write')
            os.fsync(output.fileno())
    else:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, prefix='.atoms.jsonl.',
                                             delete=False) as output:
                temporary = output.name
                output.write(line)
                output.flush()
                os.fsync(output.fileno())
            # Reserve the complete inode exclusively before replace, so a concurrent
            # creator cannot be clobbered between the existence check and publication.
            os.link(temporary, target)
            os.replace(temporary, target)
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)
    print(json.dumps(dict(file=str(target), appended=args.append, bytes=len(raw), sha256=sha)))


def check(args):
    url = args.base + '/publication/records/' + args.sha256[:2] + '/' + args.sha256
    raw = request_bytes(url)
    if len(raw) != args.expect_bytes:
        raise ValueError(f'byte length mismatch: expected {args.expect_bytes}, got {len(raw)}')
    sha = digest(raw, args.sha256)
    print(json.dumps(dict(ok=True, url=url, status=200, bytes=len(raw), sha256=sha)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('fetch')
    p.add_argument('--url', required=True, type=http_url)
    p.add_argument('--out', required=True)
    p.add_argument('--sha256', type=sha256_arg)
    p.add_argument('--force', action='store_true')
    p.set_defaults(run=fetch)
    p = commands.add_parser('submit')
    p.add_argument('--base', required=True, type=http_url)
    p.add_argument('--file', required=True)
    p.add_argument('--sha256', type=sha256_arg)
    p.add_argument('--address')
    p.set_defaults(run=submit)
    p = commands.add_parser('seed')
    p.add_argument('--data-dir', required=True)
    p.add_argument('--file', required=True)
    p.add_argument('--sha256', type=sha256_arg)
    p.add_argument('--address')
    p.add_argument('--append', action='store_true')
    p.set_defaults(run=seed)
    p = commands.add_parser('check')
    p.add_argument('--base', required=True, type=http_url)
    p.add_argument('--sha256', required=True, type=sha256_arg)
    p.add_argument('--expect-bytes', required=True, type=int)
    p.set_defaults(run=check)
    args = parser.parse_args(argv)
    try:
        args.run(args)
    except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
