"""Initialize the volume, then permanently drop root before running the service."""
import os
from pathlib import Path
import sys

sys.path.insert(0, '/app')
from punkti_node.config import load_config

for variable, filename in [('PUNKTO_BUILD_VERSION', 'build-version'), ('PUNKTO_BUILD_REVISION', 'build-revision')]:
    path = Path('/app') / filename
    if path.exists():
        os.environ.setdefault(variable, path.read_text().strip())

config_path = os.environ.get('PUNKTO_NODE_CONFIG', '/config/punkto-node.yml')
config = load_config(config_path)
data = Path(config['storage']['data_path'])
if os.geteuid() == 0:
    data.mkdir(parents=True, exist_ok=True)
    if data.is_symlink():
        raise SystemExit('data directory must not be a symlink')
    info = data.stat()
    if (info.st_uid, info.st_gid) != (10001, 10001):
        # One-time ownership repair for a fresh bind mount. Existing stores are
        # already owned by the runtime user and are never walked again.
        os.chown(data, 10001, 10001)
        for root, dirs, files in os.walk(data, followlinks=False):
            for name in dirs + files:
                path = Path(root) / name
                if not path.is_symlink():
                    os.chown(path, 10001, 10001, follow_symlinks=False)
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
os.execvp('python', ['python', '-m', 'punkti_node', '--config', config_path, *sys.argv[1:]])
