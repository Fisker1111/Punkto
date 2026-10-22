"""Scenario assertions are shared verbatim by local and bidirectional suites."""
from concurrent.futures import ThreadPoolExecutor
import json
import time
from urllib.parse import urlencode, urlsplit
from hostile.harness import body, http, item, query


def partition_rejoin(r):
    # Default topology is A(ref), B(clean-room), C(ref); direction swaps A/B kinds.
    a = r.node()
    b = r.node('nb' if r.direction == 'ref' else 'ref')
    p = r.proxy(b)
    c = r.node('ref')
    pa = r.proxy(a)
    pc = r.proxy(c)
    r.call(b, 'configure', peers=[pa.url, pc.url])
    r.call(c, 'configure', peers=[pa.url, p.url, b.url])
    r.call(a, 'configure', peers=[b.url, c.url, p.url, pc.url])
    first = r.seed(a, 0, 40)
    r.call(b, 'sync_known')
    r.call(c, 'sync_known')
    r.equal([a, b, c], first)
    isolated_before = r.state(b)
    # Isolate every configured outbound B link and inbound B proxy. Do not run
    # callbacks with B's real origin while isolated; only B initiates attempts.
    for proxy in (p, pa, pc):
        proxy.partition(True)
    more = r.seed(a, 40, 40) + r.seed(c, 80, 15)
    failed = r.call(b, 'sync_known')['result']
    assert failed and failed != {pa.url: 'ok', pc.url: 'ok'}, failed
    r.errors.append({'partition_sync': failed})
    r.equal([b], first)
    assert r.state(b) == isolated_before
    r.notes['partition_store_sizes'] = [len(isolated_before['valid']), len(r.state(b)['valid'])]
    assert all(x.stats().get('partition', 0) >= 1 for x in (pa, pc))
    for proxy in (p, pa, pc):
        proxy.partition(False)
    expected = sorted(m['address'] for m in first + more)
    for rounds in range(1, 3):
        r.retries += 1
        r.call(b, 'sync_known')
        r.call(c, 'sync_known')
        if all(sorted(e['address'] for e in r.state(n)['valid']) == expected
               for n in (a, b, c)):
            break
    r.notes['healing_rounds'] = rounds
    return r.finish([a, b, c], first + more)


def long_offline(r):
    a, b, p = r.pair()
    c = r.node('ref')
    old = r.seed(a, 100, 3)
    pa = r.proxy(a)
    assert r.pull(b, pa.url)['ok']  # persist a cursor bound to A's old epoch
    stale = body(r.pulls(pa)[-1])['cursor']
    old_epoch, port, kind = a.epoch, urlsplit(a.url).port, a.kind
    a.process.kill()
    a.process.wait(timeout=5)
    more = r.seed(b, 103, 100) + r.seed(c, 203, 100)
    r.fail(lambda: r.pull(b, pa.url))
    a = r.node(kind, port)
    assert a.epoch != old_epoch
    r.equal([a], [])
    status, rejection = http(pa.url, '/pull?' + urlencode({'q': json.dumps({'cursor': stale})}))
    assert status == 400, rejection
    r.notes['stale_cursor'] = dict(token=stale, rejection=rejection, status=status)
    assert r.pull(a, p.url)['ok']
    pc = r.proxy(c)
    assert r.pull(a, pc.url)['ok']
    # B's saved old-epoch cursor must reset to null against the replacement A.
    before = len(r.pulls(pa))
    assert r.pull(b, pa.url)['ok']
    assert query(r.pulls(pa)[before])['cursor'] is None
    assert r.pull(c, pa.url)['ok']
    r.retries += 1
    return r.finish([a, b, c], old + more)


def duplicate_replay(r):
    a, b, p = r.pair()
    records = r.seed(a, 400, 4)
    batch = {'records': list(map(item, records))}
    p.plan(['duplicate'] * 20 + ['pass'] * 50)
    for i in range(20):
        status, response = http(p.url, '/push', batch)
        assert status == 200
        assert [x['admitted'] for x in response['results']] == [i == 0] * 4
    for _ in range(50):
        status, response = http(p.url, '/push', {'records': [item(records[0])]})
        assert status == 200 and response['results'][0]['admitted'] is False
    assert p.stats()['duplicate'] == 20
    for exchange in p.exchanges:
        if exchange['fault'] == 'duplicate':
            assert all(x['admitted'] is False for x in body(exchange, 'duplicate_response')['results'])
    r.call(a, 'push_to', peer=p.url)
    return r.finish([a, b], records)


def dropped_response_retry(r):
    a, b, p = r.pair()
    records = r.seed(a, 500, 1)
    p.plan(['pass', 'drop_after'])
    r.fail(lambda: a.rpc('push_to', peer=p.url))
    r.equal([b], records)  # admission happened before the unacknowledged response
    assert p.stats()['drop_after'] == 1
    r.retries += 1
    before = len(p.exchanges)
    r.call(a, 'push_to', peer=p.url)
    p.idle()
    retried = [e for e in list(p.exchanges)[before:] if e['path'] == '/push']
    assert len(retried) == 1, 'push cursor skipped unacknowledged record'
    assert body(retried[0])['results'][0]['admitted'] is False
    assert json.loads(retried[0]['request'].split(b'\r\n\r\n', 1)[1])['records'] == [item(records[0])]
    more = r.seed(a, 501, 1)
    r.call(a, 'push_to', peer=p.url)
    return r.finish([a, b], records + more)


def _interrupted(r, persisted):
    a, b, p = r.pair()
    records = r.seed(b, 600, 70)
    p.plan(['pass'] + (['pass'] if persisted else []) + ['truncate:700'])
    r.fail(lambda: r.pull(a, p.url))
    r.equal([a], records[:32] if persisted else [])
    assert p.stats()['truncate'] == 1
    failed = r.pulls(p)[-1]
    assert failed['response_bytes'] == 700 < failed['upstream_response_bytes']
    # Original upstream page is incomplete sweep; a broken page cannot signal success.
    assert body(failed)['end'] is False
    before = len(r.pulls(p))
    r.retry_pull(a, p)
    resumed = r.pulls(p)[before:]
    cursor = query(resumed[0])['cursor']
    assert (cursor['after'] if cursor else 0) == (32 if persisted else 0)
    transferred = [x['address'] for e in resumed for x in body(e)['records']]
    assert transferred == [m['address'] for m in records[32 if persisted else 0:]]
    return r.finish([a, b], records)


def interrupted_pull(r):
    return _interrupted(r, False)


def interrupted_pull_persisted(r):
    return _interrupted(r, True)


def corrupt_page(r):
    a, b, p = r.pair()
    old = r.seed(b, 700, 3)
    assert r.pull(a, p.url)['ok']
    records = r.seed(b, 703, 4)
    p.plan(['pass', 'corrupt'])
    r.fail(lambda: r.pull(a, p.url))
    r.equal([a], old)
    assert p.stats()['corrupt'] == 1
    e = r.pulls(p)[-1]
    assert sum(x != y for x, y in zip(e['upstream_response'], e['response'])) == 1
    assert e['upstream_response'].split(b'\r\n\r\n')[0] == e['response'].split(b'\r\n\r\n')[0]
    r.retry_pull(a, p)
    assert query(r.pulls(p)[-1])['cursor']['after'] == 3
    assert [x['address'] for x in body(r.pulls(p)[-1])['records']] == [m['address'] for m in records]
    return r.finish([a, b], old + records)


def out_of_order(r):
    a, b, p = r.pair()
    records = r.seed(a, 800, 12)
    p.plan(['shuffle', 'shuffle'])
    for batch in (records[6:], records[:6]):
        status, result = http(p.url, '/push', {'records': list(map(item, batch))})
        assert status == 200 and all(x['admitted'] for x in result['results'])
    assert p.stats()['shuffle'] == 2
    assert [e['address'] for e in r.state(b)['log']] == [m['address'] for m in records[:5:-1] + records[5::-1]]
    r.call(a, 'push_to', peer=p.url)
    more = r.seed(b, 812, 2)
    assert r.pull(a, p.url)['ok']
    assert query(r.pulls(p)[0])['cursor'] is None
    return r.finish([a, b], records + more)


def slow_peer(r):
    a, b, p = r.pair()
    records = r.seed(b, 900, 2)
    # Error wording is not specified; pin bounded failure and store integrity.
    r.notes['timeout_error_shapes'] = []
    for fault in ('drop_before', 'delay:5100', 'stall:5.1', 'slowdrip:1:5100'):
        p.plan([fault])
        started = time.monotonic()
        error = r.fail(lambda: r.pull(a, p.url))
        elapsed = time.monotonic() - started
        assert elapsed < 20, (fault, elapsed, error)
        r.notes['timeout_error_shapes'].append(
            dict(implementation=a.kind, fault=fault, payload=error, elapsed_seconds=elapsed))
        r.equal([a], [])
        assert p.stats().get(fault.split(':')[0]) == 1
    p.plan(['delay:5', 'slowdrip:1024:1'])
    r.retry_pull(a, p)
    assert p.stats()['delay'] == 2 and p.stats()['slowdrip'] == 2
    return r.finish([a, b], records)


def peer_vanish_mid_session(r):
    a, b, p = r.pair()
    records = r.seed(b, 1000, 70)
    # A proxy event fires after receipt of the first page, before its delayed
    # delivery. Kill the real process then; no scheduling sleep chooses the cut.
    p.plan(['pass', 'delay:300'])
    p.hold_fault('delay')
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(r.pull, a, p.url)
        # Synchronize using the server's upstream page completion via a dedicated
        # barrier installed only on this proxy's delay (see wait_fault).
        assert p.wait_fault('delay', 10)
        epoch, port, kind = b.epoch, urlsplit(b.url).port, b.kind
        b.process.kill()
        b.process.wait(timeout=5)
        p.release_fault()
        r.fail(lambda: future.result(timeout=15))
    r.equal([a], records[:32])
    b = r.node(kind, port)
    assert b.epoch != epoch
    r.seed(b, 1000, 70)
    before = len(r.pulls(p))
    r.retry_pull(a, p)
    assert query(r.pulls(p)[before])['cursor'] is None
    return r.finish([a, b], records)


SCENARIOS = [partition_rejoin, long_offline, duplicate_replay, dropped_response_retry,
             interrupted_pull, interrupted_pull_persisted, corrupt_page, out_of_order,
             slow_peer, peer_vanish_mid_session]
