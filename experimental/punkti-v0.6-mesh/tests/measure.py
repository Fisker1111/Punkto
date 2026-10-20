"""Reproducible real-HTTP measurements; print results only after assertions pass."""
import json
from urllib.parse import urlencode
from support import fixture
from carrier import validate
from mesh import Node, packed, request


def network():
    nodes = []
    try:
        for i in range(3):
            nodes.append(Node(epoch=f'measure-store-{i}').start())
        for node in nodes:
            node.peers.update(n.url for n in nodes if n is not node)
        return nodes
    except BaseException:
        for node in nodes:
            node.stop()
        raise


def counters(nodes):
    return {key: sum(n.metrics[key] for n in nodes) for key in nodes[0].metrics}


def subsets(size):
    nodes = network()
    try:
        records = [fixture(i) for i in range(size)]
        initial = [records[:size//2], list(reversed(records[size//3:3*size//4])), records[2*size//3:]]
        for node, group in zip(nodes, initial):
            for raw in group:
                node.add(raw)
        expected = {validate(raw).address for group in initial for raw in group}
        rounds = 0
        while not all(set(n.store) == expected for n in nodes):
            rounds += 1
            if rounds > 5:
                raise AssertionError('failed to converge in five rounds')
            for left, right in ((0, 1), (1, 2), (2, 0)):
                nodes[left].connect(nodes[right].url)
        return dict(size=size, initial_sizes=list(map(len, initial)), union=len(expected),
                    rounds=rounds, connections=rounds*3, atomic_snapshot=False,
                    **counters(nodes))
    finally:
        for node in nodes:
            node.stop()


def churn(size=512):
    nodes = network()
    a, b, c = nodes
    try:
        records = sorted([fixture(i) for i in range(size)], key=lambda r: validate(r).address)
        delayed = records[:32]
        for raw in records[32:]:
            a.add(raw)
        # First sweep starts before the 32 behind-cursor inserts.
        first = request(a.url, '/pull?' + urlencode({'q': packed(dict(mode='mid', limit=16)).decode()}))
        for item in first['records']:
            b.admit(item)
        c.pull(a.url, limit=16)  # C has a spatial high-water before the churn.
        for raw in delayed:
            a.add(raw)
        page = first
        while not page['end']:
            query = dict(mode='mid', limit=16, cursor=page['cursor'])
            page = request(a.url, '/pull?' + urlencode({'q': packed(query).decode()}))
            for item in page['records']:
                b.admit(item)
        first_count = len(b.store)
        assert first_count == size - 32
        before = a.metrics['pull_records']
        b.pull(a.url, mode='mid', limit=16)
        sweep_records = a.metrics['pull_records'] - before
        before = a.metrics['pull_records']
        c.pull(a.url, limit=16)
        resumed_records = a.metrics['pull_records'] - before
        assert set(a.store) == set(b.store) == set(c.store)
        assert resumed_records == 32
        return dict(size=size, inserted_behind_cursor=32, first_sweep_count=first_count,
                    mid_sweeps=2, fresh_sweep_records=sweep_records,
                    spatial_resume_records=resumed_records, final_count=len(a.store), **counters(nodes))
    finally:
        for node in nodes:
            node.stop()


if __name__ == '__main__':
    print(json.dumps(dict(subsets=[subsets(n) for n in (12, 96, 384)], churn=churn()), indent=2))
