"""Durable exact-R store. Candidates cannot occupy valid MID slots."""
import os
from pathlib import Path
from .carrier_io import carrier, digest


def durable_write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Sync each ancestor so newly created directory entries survive a crash.
    for directory in (path.parent, *path.parent.parents):
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    temp = path.with_name('.' + path.name + '.tmp')
    try:
        with temp.open('wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


class Store:
    """Single writer. Revalidate persisted bytes on restart; no trust in filenames."""
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.valid, self.candidates = {}, {}
        if self.path:
            for kind in ('valid', 'candidates'):
                for file in sorted((self.path / kind).glob('*')):
                    if not file.name.startswith('.'):
                        raw = file.read_bytes()
                        if digest(raw) != file.name:
                            raise ValueError('corrupt durable store')
                        self.admit(raw, persist=False)

    def admit(self, raw, *, persist=True):
        observation = carrier.validate(raw)
        if observation.state == carrier.State.VALID:
            target, key, kind = self.valid, observation.address, 'valid'
        elif observation.state in (carrier.State.ALGORITHM, carrier.State.KEY):
            target, key, kind = self.candidates, digest(raw), 'candidates'
        else:
            return observation.state.value
        if key not in target:
            if self.path and persist:
                durable_write(self.path / kind / digest(raw), raw)
            target[key] = raw
        return observation.state.value
