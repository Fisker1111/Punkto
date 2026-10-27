import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT.parent / 'punkti-v0.6-static/src'))
from staticpub.httpsource import StaticSource
from pubnorm import objects as o, independent
from pubnorm.reader import Reader
from pubnorm.publisher import Publisher
from pubnorm.vectors import fixture, snapshot, rewrite, materialize, add
READERS = (Reader, independent.Reader)
