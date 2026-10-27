#!/usr/bin/env python3
"""One-shot process for static-only publication/replication evidence."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=['publish', 'read'])
parser.add_argument('implementation', choices=['reference', 'independent'])
parser.add_argument('location')
parser.add_argument('--input')
parser.add_argument('--packs', action='store_true')
args = parser.parse_args()
records = [bytes.fromhex(r) for r in json.loads(Path(args.input).read_text())] if args.input else []
if args.implementation == 'independent':
    from pubnorm.independent import Reader, publish
else:
    from pubnorm.reader import Reader
    from pubnorm.publisher import Publisher
    def publish(location, records, packs):
        return Publisher(location, packs).publish(records)
if args.operation == 'publish':
    print(json.dumps(publish(args.location, records, args.packs), sort_keys=True))
else:
    reader = Reader(packs=args.packs)
    result = reader.read_publication(args.location)
    print(json.dumps(dict(result=result, valid={k: v.hex() for k, v in reader.store.valid.items()},
                         candidates={k: v.hex() for k, v in reader.store.candidates.items()},
                         paths=reader.paths), sort_keys=True))
