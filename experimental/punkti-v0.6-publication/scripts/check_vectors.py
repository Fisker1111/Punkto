#!/usr/bin/env python3
"""Generate twice in temporary directories and compare with committed artifacts."""
import hashlib
from pathlib import Path
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'src'))
from pubnorm.vectors import write_artifacts

with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
    for tmp in (first, second):
        (Path(tmp) / 'docs').mkdir()
        write_artifacts(tmp)
    for name in ('vectors.json', 'docs/NORMATIVE_VECTORS.md'):
        saved = (ROOT / name).read_bytes()
        assert saved == (Path(first) / name).read_bytes() == (Path(second) / name).read_bytes(), name
        print(f'{name}: byte-identical on two regenerations; SHA256={hashlib.sha256(saved).hexdigest()}')
