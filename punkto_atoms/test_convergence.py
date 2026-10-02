"""Deterministic real-HTTP convergence proof; run pytest -v -s to see steps."""
import time
import threading
from contextlib import contextmanager

import pytest
import requests

from .make_atom import make_atom
from .server import AtomService, Config, make_server
from .store import AtomStore


@contextmanager
def node(path):
    store = AtomStore(path)
    service = AtomService(store, Config(db=str(path)))
    server = make_server(service, '127.0.0.1', 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    service.url = f'http://127.0.0.1:{server.server_port}'
    try:
        yield service
    finally:
        service.stop.set()
        server.shutdown()
        thread.join()
        server.server_close()
        store.close()


def atom(message):
    return make_atom(55.6, 12.5, 20, int(time.time()*1000), message, 'test-author')


def mids(service):
    return {a['mid'] for a in service.store.inventory()}


def submit(service, value, status=201):
    response = requests.post(service.url+'/atoms/v1', json=value, timeout=5)
    assert response.status_code == status, response.text
    assert response.json()['mid'] == value['mid']


def test_convergence(tmp_path):
    labels = [
        'A: node1 -> node2', 'B: node2 -> node1', 'duplicate stored once',
        'disconnect node2', 'write more on node1', 'reconnect node2',
        'node2 catches up', 'reverse outage and catch-up',
        'restart both stores retains expected MIDs', 'full MID sets identical']
    step = 0

    def passed():
        nonlocal step
        print(f'STEP {step+1}: PASS — {labels[step]}', flush=True)
        step += 1

    expected = set()
    path1, path2 = tmp_path/'one.db', tmp_path/'two.db'
    try:
        with node(path1) as one, node(path2) as two:
            one.config.peers = [two.url]
            two.config.peers = [one.url]
            a = atom('A')
            submit(one, a)
            expected.add(a['mid'])
            assert two.sync_once() == 1
            assert mids(two) == expected
            passed()
            b = atom('B')
            submit(two, b)
            expected.add(b['mid'])
            assert one.sync_once() == 1
            assert mids(one) == expected
            passed()
            before = one.store.stats()
            submit(one, a, 200)
            alternate = dict(a, sig='different signature, same MID')
            submit(one, alternate, 200)
            assert one.store.stats() == before
            assert one.store.fetch(a['mid']) == a
            passed()
            one.config.peers = []
            two.config.peers = []
            assert one.sync_once() == two.sync_once() == 0
            passed()
            for message in ('C', 'D', 'E'):
                value = atom(message)
                submit(one, value)
                expected.add(value['mid'])
            assert len(mids(two)) == 2 and mids(one) == expected
            passed()
            one.config.peers = [two.url]
            two.config.peers = [one.url]
            assert two.config.peers == [one.url]
            passed()
            assert two.sync_once() == 3
            assert mids(two) == expected
            passed()
            one.config.peers = []
            two.config.peers = []
            for message in ('F', 'G', 'H'):
                value = atom(message)
                submit(two, value)
                expected.add(value['mid'])
            assert len(mids(one)) == 5
            one.config.peers = [two.url]
            two.config.peers = [one.url]
            assert one.sync_once() == 3
            assert mids(one) == mids(two) == expected
            assert one.sync_once() == two.sync_once() == 0
            passed()
        with node(path1) as one, node(path2) as two:
            assert mids(one) == expected and mids(two) == expected
            assert one.store.stats() == two.store.stats() == {'count': 8, 'head_seq': 8}
            passed()
            assert mids(one) == mids(two) == expected
            passed()
    except Exception:
        print(f'STEP {step+1}: FAIL — {labels[step]}', flush=True)
        for index in range(step+1, 10):
            print(f'STEP {index+1}: FAIL (not reached) — {labels[index]}', flush=True)
        print('CONVERGENCE: FAIL', flush=True)
        raise
    print('CONVERGENCE: PASS', flush=True)


@pytest.mark.xfail(strict=True, reason='Specified local-head cursor misses independent writes at equal heads')
def test_independent_writes_known_design_limitation(tmp_path):
    with node(tmp_path/'a.db') as one, node(tmp_path/'b.db') as two:
        one.config.peers = [two.url]
        two.config.peers = [one.url]
        submit(one, atom('independent A'))
        submit(two, atom('independent B'))
        expected = mids(one) | mids(two)
        one.sync_once()
        two.sync_once()
        assert mids(one) == mids(two) == expected


def test_validation_feed_and_inventory(tmp_path):
    with node(tmp_path/'atoms.db') as service:
        base = service.url+'/atoms/v1'
        valid = atom('valid 🌍')
        for changes in ({'t': True}, {'t': 0}, {'t': int(time.time()*1000)+172800000},
                        {'h': 'z'*11}, {'h': 'a'*12}, {'x': '🌍'*1025},
                        {'fp': 'a'*513}, {'sig': ''}, {'mid': '0'*64}, {'x': None}):
            bad = dict(valid, **changes)
            response = requests.post(base, json=bad, timeout=5)
            assert response.status_code == 400
            assert response.headers['Access-Control-Allow-Origin'] == '*'
        assert requests.post(base, data=b'x'*65537, timeout=5).status_code == 413
        submit(service, valid)
        assert requests.get(base+'/mid/'+valid['mid'], timeout=5).json() == valid
        assert requests.get(base+'/mid/missing', timeout=5).status_code == 404
        assert requests.get(base+'/sync?since=0', timeout=5).json() == [valid]
        assert requests.get(base+'/sync?since=1', timeout=5).json() == []
        assert requests.get(base+'/feed?max_lat=0', timeout=5).json() == []
        assert requests.get(base+f"/feed?max_t={valid['t']-1}", timeout=5).json() == []
        items = requests.get(base+f"/feed?min_lat=55&max_lat=56&min_lon=12&max_lon=13&min_t={valid['t']}&max_t={valid['t']}", timeout=5).json()
        assert len(items) == 1 and items[0]['mid'] == valid['mid']
        assert all(key in items[0] for key in ('lat', 'lon', 'alt'))
        for query in ('limit=-1', 'min_lat=nan', 'min_lon=10&max_lon=0', 'min_t=oops'):
            assert requests.get(base+'/feed?'+query, timeout=5).status_code == 400
        service.config.peers = [service.url+'/unreachable']
        before = service.store.stats()
        assert service.sync_once() == 0
        assert service.last_sync_status == 'error'
        assert service.store.stats() == before
        service.config.peers = []
        service.sync_once()
        assert service.last_sync_status == 'ok'
