#!/usr/bin/env python3
"""
cli.py — Punkto command-line interface

Usage:
    python -m core.cli <command> [args]

Commands:
    make   <lat> <lon> [alt] [--id ID]           Generate canonical Punkto address
    bare   <lat> <lon> [alt]                     Generate spatial-only address (no id)
    decode <canonical>                           Decode address to lat/lon/alt
    resolve <any-form>                           Resolve any form to canonical
    validate <s>                                 Validate canonical format
    uri    <canonical>                           Convert to punkto:// URI
    https  <canonical>                           Convert to HTTPS URL
    near   <a> <b> [--prefix N]                  Check if two Punktos are near
    id     [--length N]                          Generate a random short ID
    write  <lat> <lon> <alt> <payload>           Write an atom to a node
           [--id ID] [--node URL] [--field f=v]
    read   <canonical> [--node URL]              Read atoms at a Punkto
    feed   [--node URL] [--since CURSOR]         Pull atom feed from a node
    info   [--node URL]                          Show node info
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Allow running as `python core/cli.py` from project root
if __name__ == '__main__' and __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    __package__ = 'core'

from . import geohash3d, punkto as pk

DEFAULT_NODE = 'https://punkto.xyz'


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'PunktoCLI/0.1'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            err = json.loads(body)
        except Exception:
            err = {'error': str(e), 'message': body}
        _die(f"HTTP {e.code}: {err.get('message', err)}")
    except urllib.error.URLError as e:
        _die(f"Connection error: {e.reason}")


def _post(url: str, data: dict) -> dict:
    body = json.dumps(data, separators=(',', ':')).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'PunktoCLI/0.1',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            err = json.loads(body)
        except Exception:
            err = {'error': str(e), 'message': body}
        _die(f"HTTP {e.code}: {err.get('message', err)}")
    except urllib.error.URLError as e:
        _die(f"Connection error: {e.reason}")


def _die(msg: str, code: int = 1) -> None:
    print(f'error: {msg}', file=sys.stderr)
    sys.exit(code)


def _out(obj) -> None:
    if isinstance(obj, dict) or isinstance(obj, list):
        print(json.dumps(obj, indent=2))
    else:
        print(obj)


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def cmd_make(args) -> None:
    canonical = pk.make(args.lat, args.lon, args.alt, id=args.id)
    _out(canonical)


def cmd_bare(args) -> None:
    _out(pk.make_bare(args.lat, args.lon, args.alt))


def cmd_decode(args) -> None:
    try:
        d = pk.decode(args.canonical)
    except ValueError as e:
        _die(str(e))
    _out({
        'canonical': args.canonical,
        'lat':  round(d.lat, 7),
        'lon':  round(d.lon, 7),
        'alt':  round(d.alt, 2),
        'error': {
            'lat': round(d.error_lat, 7),
            'lon': round(d.error_lon, 7),
            'alt': round(d.error_alt, 2),
        },
    })


def cmd_resolve(args) -> None:
    try:
        _out(pk.resolve(args.form))
    except ValueError as e:
        _die(str(e))


def cmd_validate(args) -> None:
    ok = pk.validate(args.s)
    print('valid' if ok else 'invalid')
    sys.exit(0 if ok else 1)


def cmd_uri(args) -> None:
    try:
        _out(pk.to_uri(args.canonical))
    except ValueError as e:
        _die(str(e))


def cmd_https(args) -> None:
    try:
        _out(pk.to_https(args.canonical))
    except ValueError as e:
        _die(str(e))


def cmd_near(args) -> None:
    result = pk.near(args.a, args.b, prefix_length=args.prefix)
    print('near' if result else 'far')
    sys.exit(0 if result else 1)


def cmd_id(args) -> None:
    _out(pk.short_id(length=args.length))


def cmd_write(args) -> None:
    canonical = pk.make(args.lat, args.lon, args.alt, id=args.id)
    atom: dict = {
        'punkto': canonical,
        't': int(time.time() * 1000),  # Unix ms
        'x': args.payload,
    }
    # extra fields like author, f (field name)
    if args.field:
        for kv in args.field:
            if '=' not in kv:
                _die(f"--field must be key=value, got: {kv!r}")
            k, v = kv.split('=', 1)
            atom[k] = v

    node = args.node.rstrip('/')
    result = _post(f'{node}/atom', atom)
    _out(result)
    if result.get('status') == 'accepted':
        # Print canonical for easy piping
        print(canonical, file=sys.stderr)


def cmd_read(args) -> None:
    try:
        canonical = pk.resolve(args.canonical)
    except ValueError as e:
        _die(str(e))
    node = args.node.rstrip('/')
    result = _get(f'{node}/punkto/{urllib.parse.quote(canonical, safe="")}')
    _out(result)


def cmd_feed(args) -> None:
    node = args.node.rstrip('/')
    url = f'{node}/feed'
    if args.since is not None:
        url += f'?since={args.since}'
    _out(_get(url))


def cmd_info(args) -> None:
    node = args.node.rstrip('/')
    _out(_get(f'{node}/info'))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _lat_lon_alt_args(p: argparse.ArgumentParser, alt_default: float = 0.0) -> None:
    p.add_argument('lat',  type=float, help='Latitude [-90, 90]')
    p.add_argument('lon',  type=float, help='Longitude [-180, 180]')
    p.add_argument('alt',  type=float, nargs='?', default=alt_default,
                   help=f'Altitude metres [-500, 8500] (default {alt_default})')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='punkto',
        description='Punkto — 3D spatial address CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command', metavar='command')
    sub.required = True

    # make
    p = sub.add_parser('make', help='Generate canonical Punkto address')
    _lat_lon_alt_args(p)
    p.add_argument('--id', default=None, help='Custom alphanumeric id (auto-generated if omitted)')
    p.set_defaults(func=cmd_make)

    # bare
    p = sub.add_parser('bare', help='Generate spatial-only Punkto (no id)')
    _lat_lon_alt_args(p)
    p.set_defaults(func=cmd_bare)

    # decode
    p = sub.add_parser('decode', help='Decode canonical Punkto to lat/lon/alt')
    p.add_argument('canonical', help='Canonical Punkto string (p:...)')
    p.set_defaults(func=cmd_decode)

    # resolve
    p = sub.add_parser('resolve', help='Resolve any Punkto form to canonical')
    p.add_argument('form', help='Any Punkto representation (p:, punkto://, https://...)')
    p.set_defaults(func=cmd_resolve)

    # validate
    p = sub.add_parser('validate', help='Validate canonical Punkto format')
    p.add_argument('s', help='String to validate')
    p.set_defaults(func=cmd_validate)

    # uri
    p = sub.add_parser('uri', help='Convert canonical to punkto:// URI')
    p.add_argument('canonical', help='Canonical Punkto string')
    p.set_defaults(func=cmd_uri)

    # https
    p = sub.add_parser('https', help=f'Convert canonical to HTTPS URL ({DEFAULT_NODE}/p/...)')
    p.add_argument('canonical', help='Canonical Punkto string')
    p.set_defaults(func=cmd_https)

    # near
    p = sub.add_parser('near', help='Check if two Punktos are near each other')
    p.add_argument('a', help='First canonical Punkto')
    p.add_argument('b', help='Second canonical Punkto')
    p.add_argument('--prefix', type=int, default=8,
                   help='Geohash prefix length to compare (default 8 ≈ 1 m)')
    p.set_defaults(func=cmd_near)

    # id
    p = sub.add_parser('id', help='Generate a random short alphanumeric id')
    p.add_argument('--length', type=int, default=6, help='Id length (default 6)')
    p.set_defaults(func=cmd_id)

    # write
    p = sub.add_parser('write', help='Write an atom to a Punkto node')
    _lat_lon_alt_args(p)
    p.add_argument('payload', help='Atom payload text')
    p.add_argument('--id', default=None, help='Custom id (auto-generated if omitted)')
    p.add_argument('--node', default=DEFAULT_NODE, help=f'Node URL (default {DEFAULT_NODE})')
    p.add_argument('--field', action='append', metavar='key=value',
                   help='Extra atom fields (repeatable)')
    p.set_defaults(func=cmd_write)

    # read
    p = sub.add_parser('read', help='Read all atoms at a Punkto')
    p.add_argument('canonical', help='Canonical Punkto (or any valid form)')
    p.add_argument('--node', default=DEFAULT_NODE, help=f'Node URL (default {DEFAULT_NODE})')
    p.set_defaults(func=cmd_read)

    # feed
    p = sub.add_parser('feed', help='Pull atom feed from a node')
    p.add_argument('--node', default=DEFAULT_NODE, help=f'Node URL (default {DEFAULT_NODE})')
    p.add_argument('--since', type=int, default=None,
                   help='Byte-offset cursor to resume from')
    p.set_defaults(func=cmd_feed)

    # info
    p = sub.add_parser('info', help='Show node info')
    p.add_argument('--node', default=DEFAULT_NODE, help=f'Node URL (default {DEFAULT_NODE})')
    p.set_defaults(func=cmd_info)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
