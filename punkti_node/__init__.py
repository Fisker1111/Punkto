"""Self-contained operational packaging of the unchanged draft carrier/spatial modules."""
import builtins
import importlib.util
from pathlib import Path
import sys

VERSION = '0.6.0-draft.1'


def _load_reference(name):
    """Resolve reference absolute imports locally, without polluting sys.path/modules."""
    fullname = f'{__name__}.{name}'
    spec = importlib.util.spec_from_file_location(fullname, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    original_import = builtins.__import__

    def local_import(target, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and target in ('carrier', 'spatial', 'mesh'):
            target_fullname = f'{__name__}.{target}'
            if target_fullname in sys.modules:
                return sys.modules[target_fullname]
        return original_import(target, globals, locals, fromlist, level)

    module.__dict__['__builtins__'] = dict(vars(builtins), __import__=local_import)
    sys.modules[fullname] = module
    spec.loader.exec_module(module)
    return module


spatial = _load_reference('spatial')
carrier = _load_reference('carrier')
mesh = _load_reference('mesh')
