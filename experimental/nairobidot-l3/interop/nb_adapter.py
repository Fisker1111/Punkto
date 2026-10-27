"""Clean-room-only process entry point."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nairobidot import carrier, spatial
from nairobidot.node import Node
from adapter_common import run
if __name__ == '__main__':
    run(carrier, Node, spatial_codec=spatial)
