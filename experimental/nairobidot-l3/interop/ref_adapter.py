"""Reference-only process entry point."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'punkti-v0.6-mesh' / 'src'))
import carrier
import spatial
from mesh import Node
from spatial import Subscription
from adapter_common import run
if __name__ == '__main__':
    run(carrier, Node, Subscription, spatial)
