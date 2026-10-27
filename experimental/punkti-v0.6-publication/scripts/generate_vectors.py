#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pubnorm.vectors import write_artifacts
write_artifacts(ROOT)
print('Generated vectors.json and docs/NORMATIVE_VECTORS.md (V1-V9)')
