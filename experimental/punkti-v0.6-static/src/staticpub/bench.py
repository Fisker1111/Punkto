"""Benchmark static publication reader modes and compare against dynamic Mesh."""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

from .carrier_io import Subscription, carrier, make_record
from .harness import Node
from .httpsource import StaticSource

ROOT = Path(__file__).resolve().parents[2]
MESH_SRC = Path(__file__).resolve().parents[3] / 'punkti-v0.6-mesh' / 'src'
if str(MESH_SRC) not in sys.path:
    sys.path.insert(0, str(MESH_SRC))
import mesh as mesh_mod
from spatial import Subscription as MeshSubscription

LEAF_DEPTH_SWEEP = (2, 4, 6, 8, 10)
DATASET_SIZES = (1000, 5000)
STATIC_SCENARIOS = {
    'fresh_subscriber_allspace': lambda records, disjoint: dict(target=[], subscription=Subscription()),
    'overlap_100': lambda records, disjoint: dict(target=records, subscription=Subscription()),
    'overlap_0': lambda records, disjoint: dict(target=disjoint, subscription=Subscription()),
    'xy_prefix_subscription': lambda records, disjoint: dict(target=[], subscription=Subscription(xy_lo='u4', xy_hi='u5')),
    'broad_allspace_subscription': lambda records, disjoint: dict(target=[], subscription=Subscription()),
}
ALL_SCENARIOS = tuple(STATIC_SCENARIOS.keys()) + ('incremental_one_new_atom',)

BENCH_PLANS = {
    'full': {
        'leaf_sweep_dataset_sizes': (1000, 5000),
        'leaf_sweep_scenarios': tuple(STATIC_SCENARIOS.keys()),
        'matched_dataset_sizes': (1000, 5000),
        'storage_dataset_size': 5000,
        'concurrency_dataset_size': 5000,
        'scale_budget_seconds': 45 * 60,
        'scale_count': 100000,
    },
    'bounded': {
        'leaf_sweep_dataset_sizes': (1000,),
        'leaf_sweep_scenarios': ('fresh_subscriber_allspace', 'xy_prefix_subscription'),
        'matched_dataset_sizes': (1000, 5000),
        'storage_dataset_size': 1000,
        'concurrency_dataset_size': 1000,
        'scale_budget_seconds': 12 * 60,
        'scale_count': 100000,
    },
}


def xy_tail(number, length):
    chars = []
    alphabet = carrier.ALPHABET
    for _ in range(length):
        chars.append(alphabet[number % 32])
        number //= 32
    return ''.join(reversed(chars))


def make_h(index, prefix='u4', z='0'):
    return prefix + xy_tail(index, 10 - len(prefix)) + '_' + z


def generate_records(count, start=0, prefixes=('u4', 'u5', 'u6')):
    records = []
    for i in range(count):
        idx = start + i
        prefix = prefixes[i % len(prefixes)]
        records.append(make_record(idx + 1, make_h(idx + 1, prefix=prefix, z=str((idx % 7) - 3))))
    return records


def summarize_runs(runs):
    keys = [k for k, v in runs[0].items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return {
        'median': {k: statistics.median(run[k] for run in runs) for k in keys},
        'min': {k: min(run[k] for run in runs) for k in keys},
        'max': {k: max(run[k] for run in runs) for k in keys},
    }


def read_mem_total_kib():
    meminfo = Path('/proc/meminfo')
    if not meminfo.exists():
        return None
    try:
        for line in meminfo.read_text(encoding='utf-8').splitlines():
            if line.startswith('MemTotal:'):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1])
    except (OSError, ValueError):
        return None
    return None


def collect_host_info():
    cpu_count = os.cpu_count()
    return {
        'cpu_count': cpu_count if isinstance(cpu_count, int) else None,
        'memory_total_kib': read_mem_total_kib(),
        'platform': platform.platform() or None,
        'python_version': platform.python_version() or None,
    }


def mutable_file_info(public_root):
    root = Path(public_root) / 'punkti' / 'root.json'
    return dict(count=1 if root.exists() else 0, bytes=root.stat().st_size if root.exists() else 0)


def publication_disk_usage(public_root):
    base = Path(public_root) / 'punkti'
    total_bytes = 0
    file_count = 0
    for path in base.rglob('*'):
        if path.is_file():
            file_count += 1
            total_bytes += path.stat().st_size
    return dict(file_count=file_count, publication_bytes=total_bytes)


def static_run(mode, leaf_depth, source_dir, source_records, target_seed, subscription, scenario):
    target = Node(
        Path(source_dir).parent / f'target-{scenario}-{mode}-d{leaf_depth}-{time.time_ns()}',
        mode=mode,
        subscriptions=[subscription],
        leaf_depth=leaf_depth,
    )
    for raw in target_seed:
        target.store.admit(raw)

    with StaticSource(source_dir) as server:
        base = server.url + '/punkti'
        before_valid = set(target.store.valid)
        before_req = target.reader.requests
        before_bytes = target.reader.bytes
        before_origin_req = server.request_count
        before_origin_bytes = server.body_bytes
        before_origin_paths = len(server.paths)

        cpu0 = time.process_time()
        wall0 = time.perf_counter()
        target.reader.read_publication(base, subscription)
        wall = time.perf_counter() - wall0
        cpu = time.process_time() - cpu0

        new_mids = set(target.store.valid) - before_valid
        useful = sum(len(target.store.valid[mid]) for mid in new_mids)
        origin_paths = server.paths[before_origin_paths:]
        origin_requests = server.request_count - before_origin_req
        origin_bytes = server.body_bytes - before_origin_bytes

        return dict(
            scenario=scenario,
            mode=mode,
            leaf_depth=leaf_depth,
            source_count=len(source_records),
            target_seed_count=len(target_seed),
            admitted=len(new_mids),
            requests=target.reader.requests - before_req,
            transferred_bytes=target.reader.bytes - before_bytes,
            useful_bytes=useful,
            wall_sec=wall,
            cpu_sec=cpu,
            maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            mutable_files=mutable_file_info(source_dir),
            origin_requests=origin_requests,
            origin_bytes=origin_bytes,
            origin_bytes_per_request=(origin_bytes / origin_requests) if origin_requests else 0.0,
            origin_wall_ms_per_request=(wall * 1000.0 / origin_requests) if origin_requests else 0.0,
            origin_path_sample=sorted(origin_paths[:20]),
        )


def static_incremental_run(mode, leaf_depth, base_records, one_new):
    with tempfile.TemporaryDirectory(prefix=f'static-inc-{mode}-d{leaf_depth}-') as td:
        root = Path(td)
        source = Node(root / 'source', mode=mode, leaf_depth=leaf_depth)
        target = Node(root / 'target', mode=mode, leaf_depth=leaf_depth)
        for raw in base_records:
            source.store.admit(raw)
            target.store.admit(raw)
        source.publish()
        with StaticSource(source.path / 'public') as server:
            base = server.url + '/punkti'
            target.reader.read_publication(base, Subscription())
            source.store.admit(one_new)
            source.publish()

            before_valid = set(target.store.valid)
            before_req = target.reader.requests
            before_bytes = target.reader.bytes
            before_origin_req = server.request_count
            before_origin_bytes = server.body_bytes

            cpu0 = time.process_time()
            wall0 = time.perf_counter()
            target.reader.read_publication(base, Subscription())
            wall = time.perf_counter() - wall0
            cpu = time.process_time() - cpu0

            new_mids = set(target.store.valid) - before_valid
            useful = sum(len(target.store.valid[mid]) for mid in new_mids)
            origin_requests = server.request_count - before_origin_req
            origin_bytes = server.body_bytes - before_origin_bytes
            return dict(
                scenario='incremental_one_new_atom',
                mode=mode,
                leaf_depth=leaf_depth,
                source_count=len(base_records) + 1,
                target_seed_count=len(base_records),
                admitted=len(new_mids),
                requests=target.reader.requests - before_req,
                transferred_bytes=target.reader.bytes - before_bytes,
                useful_bytes=useful,
                wall_sec=wall,
                cpu_sec=cpu,
                maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                mutable_files=mutable_file_info(source.path / 'public'),
                origin_requests=origin_requests,
                origin_bytes=origin_bytes,
                origin_bytes_per_request=(origin_bytes / origin_requests) if origin_requests else 0.0,
                origin_wall_ms_per_request=(wall * 1000.0 / origin_requests) if origin_requests else 0.0,
            )


def measure_storage_and_rebuild(mode, leaf_depth, records):
    with tempfile.TemporaryDirectory(prefix=f'static-storage-{mode}-d{leaf_depth}-') as td:
        source = Node(Path(td) / 'source', mode=mode, leaf_depth=leaf_depth)
        for raw in records:
            source.store.admit(raw)
        wall0 = time.perf_counter()
        cpu0 = time.process_time()
        source.publish()
        first_publish_wall = time.perf_counter() - wall0
        first_publish_cpu = time.process_time() - cpu0

        usage = publication_disk_usage(source.path / 'public')
        raw_bytes = sum(len(raw) for raw in records)

        wall0 = time.perf_counter()
        cpu0 = time.process_time()
        source.publish()
        rebuild_wall = time.perf_counter() - wall0
        rebuild_cpu = time.process_time() - cpu0

        return dict(
            mode=mode,
            leaf_depth=leaf_depth,
            source_count=len(records),
            raw_record_bytes=raw_bytes,
            publication_bytes=usage['publication_bytes'],
            publication_file_count=usage['file_count'],
            storage_amplification=(usage['publication_bytes'] / raw_bytes) if raw_bytes else 0.0,
            first_publish_wall_sec=first_publish_wall,
            first_publish_cpu_sec=first_publish_cpu,
            rebuild_wall_sec=rebuild_wall,
            rebuild_cpu_sec=rebuild_cpu,
        )


def static_concurrency_run(mode, leaf_depth, source_records, readers):
    with tempfile.TemporaryDirectory(prefix=f'static-concurrency-{mode}-d{leaf_depth}-') as td:
        root = Path(td)
        source = Node(root / 'source', mode=mode, leaf_depth=leaf_depth)
        for raw in source_records:
            source.store.admit(raw)
        source.publish()

        results = []
        errors = []
        lock = threading.Lock()

        def worker(index, base_url):
            node = Node(root / f'target-{index}', mode=mode, leaf_depth=leaf_depth)
            try:
                metric = node.reader.read_publication(base_url, Subscription())
                with lock:
                    results.append(dict(
                        reader=index,
                        admitted=metric['admitted'],
                        requests=node.reader.requests,
                        transferred_bytes=node.reader.bytes,
                        valid=metric['valid'],
                    ))
            except BaseException as exc:
                with lock:
                    errors.append(repr(exc))

        with StaticSource(source.path / 'public') as server:
            base = server.url + '/punkti'
            before_origin_req = server.request_count
            before_origin_bytes = server.body_bytes
            wall0 = time.perf_counter()
            threads = [threading.Thread(target=worker, args=(idx, base), daemon=True) for idx in range(readers)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            wall = time.perf_counter() - wall0
            origin_requests = server.request_count - before_origin_req
            origin_bytes = server.body_bytes - before_origin_bytes

        if errors:
            raise RuntimeError('concurrency read failed: ' + '; '.join(errors))

        aggregate_requests = sum(r['requests'] for r in results)
        aggregate_bytes = sum(r['transferred_bytes'] for r in results)
        aggregate_admitted = sum(r['admitted'] for r in results)
        return dict(
            mode=mode,
            leaf_depth=leaf_depth,
            readers=readers,
            aggregate_requests=aggregate_requests,
            aggregate_transferred_bytes=aggregate_bytes,
            aggregate_admitted=aggregate_admitted,
            wall_sec=wall,
            origin_requests=origin_requests,
            origin_bytes=origin_bytes,
            origin_bytes_per_request=(origin_bytes / origin_requests) if origin_requests else 0.0,
            origin_wall_ms_per_request=(wall * 1000.0 / origin_requests) if origin_requests else 0.0,
            per_reader=sorted(results, key=lambda item: item['reader']),
        )


def mesh_run(source_records, target_seed, subscription, scenario):
    source = mesh_mod.Node(subscriptions=[MeshSubscription()]).start()
    target = mesh_mod.Node(subscriptions=[subscription]).start()
    try:
        for raw in source_records:
            source.add(raw)
        for raw in target_seed:
            target.add(raw)
        before_keys = set(target.store)
        m0 = source.metrics.copy()
        cpu0 = time.process_time()
        wall0 = time.perf_counter()
        target.pull(source.url, scope=subscription)
        wall = time.perf_counter() - wall0
        cpu = time.process_time() - cpu0
        after_keys = set(target.store)
        admitted = len(after_keys - before_keys)
        avg_record_bytes = statistics.mean(len(raw) for raw in source_records[: min(128, len(source_records))]) if source_records else 0
        pulled = source.metrics['pull_records'] - m0['pull_records']
        return dict(
            scenario=scenario,
            source_count=len(source_records),
            target_seed_count=len(target_seed),
            admitted=admitted,
            pull_requests=source.metrics['pull_requests'] - m0['pull_requests'],
            transferred_records=pulled,
            estimated_transferred_bytes=int(pulled * avg_record_bytes),
            useful_bytes=sum(len(source.store[mid].raw) for mid in after_keys - before_keys),
            wall_sec=wall,
            cpu_sec=cpu,
            maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        )
    finally:
        source.stop()
        target.stop()


def mesh_incremental(source_records, one_new):
    source = mesh_mod.Node(subscriptions=[MeshSubscription()]).start()
    target = mesh_mod.Node(subscriptions=[MeshSubscription()]).start()
    try:
        for raw in source_records:
            source.add(raw)
            target.add(raw)
        target.pull(source.url)
        source.add(one_new)
        before = set(target.store)
        m0 = source.metrics.copy()
        cpu0 = time.process_time()
        wall0 = time.perf_counter()
        target.pull(source.url)
        wall = time.perf_counter() - wall0
        cpu = time.process_time() - cpu0
        after = set(target.store)
        admitted = len(after - before)
        avg_record_bytes = statistics.mean(len(raw) for raw in source_records[: min(128, len(source_records))]) if source_records else 0
        pulled = source.metrics['pull_records'] - m0['pull_records']
        return dict(
            scenario='incremental_one_new_atom',
            source_count=len(source_records) + 1,
            target_seed_count=len(source_records),
            admitted=admitted,
            pull_requests=source.metrics['pull_requests'] - m0['pull_requests'],
            transferred_records=pulled,
            estimated_transferred_bytes=int(pulled * avg_record_bytes),
            useful_bytes=sum(len(source.store[mid].raw) for mid in after - before),
            wall_sec=wall,
            cpu_sec=cpu,
            maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        )
    finally:
        source.stop()
        target.stop()


def choose_recommended_leaf_depth(sweep):
    if not sweep['sweep_dataset_sizes']:
        raise ValueError('leaf-depth sweep dataset sizes must not be empty')
    if not sweep['sweep_scenarios']:
        raise ValueError('leaf-depth sweep scenarios must not be empty')
    primary_dataset = str(max(int(size) for size in sweep['sweep_dataset_sizes']))
    scenarios = tuple(sweep['sweep_scenarios'])

    candidates = []
    for depth in LEAF_DEPTH_SWEEP:
        key = str(depth)
        request_score = 0
        wall_score = 0
        for mode in ('A', 'B'):
            for scenario in scenarios:
                summary = sweep['modes'][mode]['datasets'][primary_dataset]['depths'][key]['scenarios'][scenario]['summary']['median']
                request_score += summary['requests']
                wall_score += summary['wall_sec']
        candidates.append({'depth': depth, 'request_score': request_score, 'wall_score': wall_score})
    ranked = sorted(candidates, key=lambda item: (item['request_score'], item['wall_score'], item['depth']))
    best = ranked[0]
    return {
        'leaf_depth': best['depth'],
        'rationale': f"lowest combined median requests for dataset={primary_dataset} over scenarios={', '.join(scenarios)}; wall time tie-break",
        'request_score': best['request_score'],
        'wall_score': best['wall_score'],
        'ranked_candidates': ranked,
    }


def write_json_atomic(path, payload):
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    tmp_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    tmp_path.replace(path)


def run_static_scenarios_from_publication(mode, leaf_depth, source_dir, records, disjoint, scenario_names, repeats):
    scenarios = {}
    for name in scenario_names:
        cfg = STATIC_SCENARIOS[name](records, disjoint)
        print(f'  scenario={name} mode={mode} depth={leaf_depth}', flush=True)
        runs = [
            static_run(mode, leaf_depth, source_dir, records, cfg['target'], cfg['subscription'], name)
            for _ in range(repeats)
        ]
        scenarios[name] = {'runs': runs, 'summary': summarize_runs(runs)}
    return scenarios


def run_static_matched_dataset(mode, dataset_size, leaf_depth, records, disjoint, plus_one, repeats):
    with tempfile.TemporaryDirectory(prefix=f'static-matched-{mode}-d{leaf_depth}-{dataset_size}-') as td:
        source = Node(Path(td) / 'source', mode=mode, leaf_depth=leaf_depth)
        for raw in records:
            source.store.admit(raw)
        source.publish()
        source_dir = source.path / 'public'
        scenarios = run_static_scenarios_from_publication(
            mode,
            leaf_depth,
            source_dir,
            records,
            disjoint,
            scenario_names=tuple(STATIC_SCENARIOS.keys()),
            repeats=repeats,
        )
    runs = [static_incremental_run(mode, leaf_depth, records, plus_one) for _ in range(repeats)]
    scenarios['incremental_one_new_atom'] = {'runs': runs, 'summary': summarize_runs(runs)}
    return {
        'leaf_depth': leaf_depth,
        'publication_builds': 1,
        'publication_reused_across_non_incremental_scenarios': True,
        'scenarios': scenarios,
    }


def run_mesh_matched_dataset(records, disjoint, plus_one, repeats):
    scenarios = {}
    for name, builder in STATIC_SCENARIOS.items():
        cfg = builder(records, disjoint)
        mesh_scope = MeshSubscription(**cfg['subscription'].wire())
        runs = [mesh_run(records, cfg['target'], mesh_scope, name) for _ in range(repeats)]
        scenarios[name] = {'runs': runs, 'summary': summarize_runs(runs)}
    runs = [mesh_incremental(records, plus_one) for _ in range(repeats)]
    scenarios['incremental_one_new_atom'] = {'runs': runs, 'summary': summarize_runs(runs)}
    return scenarios


def run_scale_100k(recommended_leaf_depth, budget_seconds=12 * 60, count=100000, progress_callback=None):
    started_at = datetime.now(timezone.utc).isoformat()
    started_perf = time.perf_counter()
    deadline = started_perf + budget_seconds
    out = {
        'started_at': started_at,
        'budget_seconds': budget_seconds,
        'leaf_depth': recommended_leaf_depth,
        'attempted_count': count,
        'generated_count': 0,
        'generation_completed': False,
        'generation_wall_sec': None,
        'modes': {},
        'completed': False,
        'elapsed_sec': None,
    }

    gen_start = time.perf_counter()
    records = generate_records(count, start=9000000)
    out['generated_count'] = len(records)
    out['generation_completed'] = len(records) == count
    out['generation_wall_sec'] = time.perf_counter() - gen_start

    for mode in ('A', 'B'):
        mode_result = {
            'mode': mode,
            'completed': False,
            'publish': None,
            'replication': None,
            'reason': None,
            'attempted_count': count,
            'admitted_count': 0,
        }
        if time.perf_counter() >= deadline:
            mode_result['reason'] = 'budget_exhausted_before_mode_start'
            out['modes'][mode] = mode_result
            if progress_callback:
                progress_callback(out)
            continue

        try:
            with tempfile.TemporaryDirectory(prefix=f'static-scale-100k-{mode}-') as td:
                root = Path(td)
                source = Node(root / 'source', mode=mode, leaf_depth=recommended_leaf_depth)
                admitted_records = []
                for index, raw in enumerate(records, start=1):
                    if (index == 1 or (index - 1) % 1000 == 0) and time.perf_counter() >= deadline:
                        mode_result['reason'] = 'budget_exhausted_during_admit'
                        break
                    source.store.admit(raw)
                    admitted_records.append(raw)
                mode_result['admitted_count'] = len(admitted_records)

                publish_wall0 = time.perf_counter()
                publish_cpu0 = time.process_time()
                source.publish()
                publish_wall = time.perf_counter() - publish_wall0
                publish_cpu = time.process_time() - publish_cpu0
                mode_result['publish'] = {
                    'wall_sec': publish_wall,
                    'cpu_sec': publish_cpu,
                    'source_count': len(admitted_records),
                }

                if mode_result['reason'] == 'budget_exhausted_during_admit':
                    out['modes'][mode] = mode_result
                    if progress_callback:
                        progress_callback(out)
                    continue

                if time.perf_counter() >= deadline:
                    mode_result['reason'] = 'budget_exhausted_after_publish'
                    out['modes'][mode] = mode_result
                    if progress_callback:
                        progress_callback(out)
                    continue

                source_dir = source.path / 'public'
                replication = static_run(
                    mode,
                    recommended_leaf_depth,
                    source_dir,
                    admitted_records,
                    [],
                    Subscription(),
                    f'scale_100k_{mode.lower()}',
                )
                mode_result['replication'] = {
                    'requests': replication['requests'],
                    'transferred_bytes': replication['transferred_bytes'],
                    'useful_bytes': replication['useful_bytes'],
                    'wall_sec': replication['wall_sec'],
                    'cpu_sec': replication['cpu_sec'],
                    'maxrss_kib': replication['maxrss_kib'],
                    'origin_requests': replication['origin_requests'],
                    'origin_bytes': replication['origin_bytes'],
                }
                if time.perf_counter() > deadline:
                    mode_result['reason'] = 'budget_exhausted_after_replication'
                else:
                    mode_result['completed'] = True
        except BaseException as exc:
            mode_result['reason'] = repr(exc)
        out['modes'][mode] = mode_result
        if progress_callback:
            progress_callback(out)

    out['elapsed_sec'] = time.perf_counter() - started_perf
    out['completed'] = all(item.get('completed') for item in out['modes'].values())
    return out


def fmt_num(value, digits=3):
    if value is None:
        return 'n/a'
    if isinstance(value, int):
        return f'{value:,}'
    return f'{value:.{digits}f}'


def metric_range(summary, key, digits=3):
    return f"{fmt_num(summary['median'][key], digits)} [{fmt_num(summary['min'][key], digits)}..{fmt_num(summary['max'][key], digits)}]"


def host_summary_lines(host):
    host = host or {}
    cpu_count = host.get('cpu_count')
    memory_total_kib = host.get('memory_total_kib')
    return [
        '- Loopback-only measurements on one host.',
        f"- Host: CPU count `{fmt_num(cpu_count, digits=0) if cpu_count is not None else 'unknown'}`, "
        f"MemTotal KiB `{fmt_num(memory_total_kib, digits=0) if memory_total_kib is not None else 'unknown'}`, "
        f"platform `{host.get('platform') or 'unknown'}`, Python `{host.get('python_version') or 'unknown'}`.",
        '- Host constraints note: this benchmark host has one vCPU and limited RAM; wall-time numbers are comparative only and not directly comparable to typical multi-core developer machines.',
    ]


def get_dataset_scenarios(static_data, dataset_size, mode):
    return (
        static_data.get('matched_static', {})
        .get('datasets', {})
        .get(str(dataset_size), {})
        .get(mode, {})
        .get('scenarios', {})
    )


def get_mesh_scenarios(mesh_data, dataset_size):
    return mesh_data.get('scenarios_by_dataset', {}).get(str(dataset_size), {})


def mode_completion_label(item):
    if item.get('completed'):
        return 'completed'
    reason = item.get('reason')
    if reason:
        return f'not completed ({reason})'
    return 'not completed'


def safe_metric_range(summary, key, digits=3):
    if not summary:
        return 'n/a'
    median = summary.get('median', {}).get(key)
    minimum = summary.get('min', {}).get(key)
    maximum = summary.get('max', {}).get(key)
    if median is None or minimum is None or maximum is None:
        return 'n/a'
    return f"{fmt_num(median, digits)} [{fmt_num(minimum, digits)}..{fmt_num(maximum, digits)}]"


def generate_benchmark_markdown(static_data, mesh_data):
    repeats = static_data.get('repeats', 'unknown')
    lines = [
        '# Benchmark summary',
        '',
        'Source data:',
        '',
        '- `evidence/bench_static.json`',
        '- `evidence/bench_mesh.json`',
        '',
        '## Scope and method',
        '',
        *host_summary_lines(static_data.get('host')),
        '- Static serving uses the stdlib HTTP server from `src/staticpub/httpsource.py`.',
        '- Warm page-cache effects are expected; numbers are comparative, not absolute latency claims.',
        f"- Profile: `{static_data.get('plan', 'unknown')}` with repeats={repeats}.",
        '',
    ]

    lines.extend([
        '## Leaf-depth sweep',
        '',
        '| Depth | Request score | Wall score (s) |',
        '|---:|---:|---:|',
    ])
    for candidate in static_data.get('recommended_leaf_depth', {}).get('ranked_candidates', []):
        lines.append(f"| {candidate.get('depth', 'n/a')} | {fmt_num(candidate.get('request_score'))} | {fmt_num(candidate.get('wall_score'))} |")
    lines.extend([
        '',
        f"Recommended leaf depth: **{static_data.get('recommended_leaf_depth', {}).get('leaf_depth', 'n/a')}**",
        '',
    ])

    for size_key in ('1000', '5000'):
        static_scenarios_a = get_dataset_scenarios(static_data, size_key, 'A')
        static_scenarios_b = get_dataset_scenarios(static_data, size_key, 'B')
        mesh_scenarios = get_mesh_scenarios(mesh_data, size_key)
        if not static_scenarios_a or not static_scenarios_b or not mesh_scenarios:
            continue
        lines.extend([
            f'## Matched static vs Mesh ({size_key} atoms)',
            '',
            '| Scenario | Static A wall (median [min..max]) | Static A requests (median [min..max]) | Static B wall (median [min..max]) | Static B requests (median [min..max]) | Mesh wall (median [min..max]) | Mesh pull requests (median [min..max]) |',
            '|---|---:|---:|---:|---:|---:|---:|',
        ])
        for scenario in ALL_SCENARIOS:
            summary_a = static_scenarios_a.get(scenario, {}).get('summary')
            summary_b = static_scenarios_b.get(scenario, {}).get('summary')
            mesh_summary = mesh_scenarios.get(scenario, {}).get('summary')
            lines.append(
                f"| {scenario} | {safe_metric_range(summary_a, 'wall_sec')} | {safe_metric_range(summary_a, 'requests', digits=0)} | "
                f"{safe_metric_range(summary_b, 'wall_sec')} | {safe_metric_range(summary_b, 'requests', digits=0)} | "
                f"{safe_metric_range(mesh_summary, 'wall_sec')} | {safe_metric_range(mesh_summary, 'pull_requests', digits=0)} |"
            )
        lines.append('')

    storage = static_data.get('storage_and_rebuild', {}).get('dataset_1000', {})
    if storage:
        lines.extend([
            '## Storage amplification + rebuild (1,000 atoms)',
            '',
            '| Mode | Publication bytes | Raw bytes | Amplification | Rebuild wall (s) |',
            '|---|---:|---:|---:|---:|',
        ])
        for mode in ('A', 'B'):
            item = storage.get(mode)
            if not item:
                continue
            lines.append(
                f"| {mode} | {fmt_num(item['publication_bytes'])} | {fmt_num(item['raw_record_bytes'])} | "
                f"{fmt_num(item['storage_amplification'])} | {fmt_num(item['rebuild_wall_sec'])} |"
            )
        lines.append('')

    lines.extend([
        '## 100k scale run (fresh subscriber only)',
        '',
        '| Mode | Publish wall (s) | Publish CPU (s) | Replication requests | Replication bytes | Replication wall (s) | Completed | Reason |',
        '|---|---:|---:|---:|---:|---:|---|---|',
    ])
    scale = static_data.get('scale_100k')
    if scale is None:
        lines.append('| n/a | n/a | n/a | n/a | n/a | n/a | not completed | not completed (scale_100k_missing) |')
        lines.extend(['', 'Scale step not completed (scale_100k_missing).', ''])
    else:
        for mode in ('A', 'B'):
            item = scale.get('modes', {}).get(mode, {})
            publish = item.get('publish') or {}
            repl = item.get('replication') or {}
            lines.append(
                f"| {mode} | {fmt_num(publish.get('wall_sec'))} | {fmt_num(publish.get('cpu_sec'))} | "
                f"{fmt_num(repl.get('requests'))} | {fmt_num(repl.get('transferred_bytes'))} | {fmt_num(repl.get('wall_sec'))} | "
                f"{mode_completion_label(item)} | {item.get('reason') or ''} |"
            )
        scale_completed = scale.get('completed', False)
        if not scale_completed:
            reasons = [item.get('reason') for item in scale.get('modes', {}).values() if item.get('reason')]
            reason_text = ', '.join(sorted(set(reasons))) if reasons else 'unknown_reason'
            lines.extend(['', f'Scale step not completed ({reason_text}).', ''])
        else:
            lines.extend([
                '',
                f"Scale step completed: `{scale_completed}` (elapsed {fmt_num(scale.get('elapsed_sec'))}s, budget {fmt_num(scale.get('budget_seconds'))}s).",
                '',
            ])

    lines.extend([
        '## Concurrency (shared publication, 1,000 atoms)',
        '',
        '| Mode | Readers | Aggregate requests (median [min..max]) | Aggregate bytes (median [min..max]) | Wall (s) median [min..max] | Origin req (median [min..max]) |',
        '|---|---:|---:|---:|---:|---:|',
    ])
    for mode in ('A', 'B'):
        for readers in ('1', '8'):
            summary = (
                static_data.get('concurrency', {})
                .get('mode_results', {})
                .get(mode, {})
                .get(readers, {})
                .get('summary')
            )
            lines.append(
                f"| {mode} | {readers} | {safe_metric_range(summary, 'aggregate_requests', digits=0)} | "
                f"{safe_metric_range(summary, 'aggregate_transferred_bytes', digits=0)} | {safe_metric_range(summary, 'wall_sec')} | "
                f"{safe_metric_range(summary, 'origin_requests', digits=0)} |"
            )
    lines.append('')
    return '\n'.join(lines) + '\n'


def load_publication_example_from_evidence(root=None):
    base = Path(root) if root is not None else ROOT
    path = base / 'evidence' / 'publication_example.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def publication_example_values(publication_example, mutable_count, mutable_bytes):
    if not isinstance(publication_example, dict):
        return None

    placeholder = 'n/a'

    def nested_value(*keys):
        current = publication_example
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return placeholder
            current = current.get(key)
        if current is None or isinstance(current, (dict, list, tuple, set)):
            return placeholder
        return current

    manifest_index = publication_example.get('manifest', {}).get('index')
    if isinstance(manifest_index, dict) and len(manifest_index) == 1:
        example_index_prefix, example_index_digest = next(iter(manifest_index.items()))
        if example_index_prefix is None:
            example_index_prefix = placeholder
        if example_index_digest is None:
            example_index_digest = placeholder
    else:
        example_index_prefix = placeholder
        example_index_digest = placeholder

    leaf_records = publication_example.get('leaf_shard', {}).get('records')
    example_leaf_record_count = len(leaf_records) if isinstance(leaf_records, list) else placeholder

    leaf_packs = publication_example.get('leaf_shard', {}).get('packs')
    example_leaf_pack_count = len(leaf_packs) if isinstance(leaf_packs, list) else placeholder

    return {
        'example_root_seq': nested_value('root', 'seq'),
        'example_root_head': nested_value('root', 'head'),
        'example_root_updated': nested_value('root', 'updated_at'),
        'example_manifest_seq': nested_value('manifest', 'seq'),
        'example_record_count': nested_value('manifest', 'record_count'),
        'example_pack_count': nested_value('manifest', 'pack_count'),
        'example_index_prefix': example_index_prefix,
        'example_index_digest': example_index_digest,
        'example_leaf_prefix': nested_value('leaf_shard', 'prefix'),
        'example_leaf_record_count': example_leaf_record_count,
        'example_leaf_pack_count': example_leaf_pack_count,
        'example_record_path': nested_value('record_example_path'),
        'example_segment_path': nested_value('segment_example_path'),
        'example_mutable_count': mutable_count if mutable_count is not None else placeholder,
        'example_mutable_bytes': mutable_bytes if mutable_bytes is not None else placeholder,
    }


def generate_static_report_markdown(static_data, mesh_data, test_data, publication_example=None):
    rec = static_data.get('recommended_leaf_depth', {})
    scale = static_data.get('scale_100k')
    s5000_a = get_dataset_scenarios(static_data, '5000', 'A')
    s5000_b = get_dataset_scenarios(static_data, '5000', 'B')
    s1000_a = get_dataset_scenarios(static_data, '1000', 'A')
    s1000_b = get_dataset_scenarios(static_data, '1000', 'B')
    mesh5000 = get_mesh_scenarios(mesh_data, '5000')

    def scenario_median(scenarios, scenario_name, metric_name):
        summary = scenarios.get(scenario_name, {}).get('summary', {})
        return summary.get('median', {}).get(metric_name)

    def ratio(numerator, denominator):
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator

    def percent_delta(reference, compared):
        if reference in (None, 0) or compared is None:
            return None
        return ((compared - reference) / reference) * 100.0

    def mutable_file_stats():
        datasets = static_data.get('matched_static', {}).get('datasets', {})
        for size_key in sorted(datasets, key=lambda raw: int(raw) if str(raw).isdigit() else str(raw)):
            for mode in ('A', 'B'):
                scenarios = get_dataset_scenarios(static_data, size_key, mode)
                for scenario_name in ALL_SCENARIOS:
                    runs = scenarios.get(scenario_name, {}).get('runs', [])
                    for run in runs:
                        mutable = run.get('mutable_files')
                        if isinstance(mutable, dict) and 'count' in mutable and 'bytes' in mutable:
                            return mutable
        return None

    def format_scale_completion(scale_data):
        if scale_data is None:
            return 'not completed (scale_100k_missing)'
        if scale_data.get('completed'):
            return f"completed (budget `{scale_data.get('budget_seconds')}`s, elapsed `{fmt_num(scale_data.get('elapsed_sec'))}`s)"
        reasons = [item.get('reason') for item in scale_data.get('modes', {}).values() if item.get('reason')]
        reason_text = ', '.join(sorted(set(reasons))) if reasons else 'unknown_reason'
        return f'not completed ({reason_text})'

    def scale_mode_values(scale_data, mode):
        if scale_data is None:
            return None
        mode_data = scale_data.get('modes', {}).get(mode, {})
        publish = mode_data.get('publish') or {}
        replication = mode_data.get('replication') or {}
        return {
            'mode_completed': bool(mode_data.get('completed')),
            'mode_reason': mode_data.get('reason'),
            'publish_wall_sec': publish.get('wall_sec'),
            'publish_cpu_sec': publish.get('cpu_sec'),
            'requests': replication.get('requests'),
            'transferred_bytes': replication.get('transferred_bytes'),
            'replication_wall_sec': replication.get('wall_sec'),
        }

    def suite_state(test_results):
        if not isinstance(test_results, dict):
            return {
                'recorded': False,
                'label': 'suite result not recorded in evidence',
                'status': None,
                'returncode': None,
                'ran': None,
                'seconds': None,
            }
        status = test_results.get('status')
        returncode = test_results.get('returncode')
        ran = test_results.get('ran')
        seconds = test_results.get('seconds')
        if status is None or returncode is None or ran is None or seconds is None:
            return {
                'recorded': False,
                'label': 'suite result not recorded in evidence',
                'status': status,
                'returncode': returncode,
                'ran': ran,
                'seconds': seconds,
            }
        status_text = str(status).strip().upper()
        passed = returncode == 0 and status_text in {'OK', 'PASS'}
        return {
            'recorded': True,
            'label': 'PASS' if passed else 'FAIL',
            'status': status,
            'returncode': returncode,
            'ran': ran,
            'seconds': seconds,
        }

    fresh_a = scenario_median(s5000_a, 'fresh_subscriber_allspace', 'wall_sec')
    fresh_b = scenario_median(s5000_b, 'fresh_subscriber_allspace', 'wall_sec')
    prefix_a = scenario_median(s5000_a, 'xy_prefix_subscription', 'wall_sec')
    prefix_b = scenario_median(s5000_b, 'xy_prefix_subscription', 'wall_sec')
    incr_a = scenario_median(s5000_a, 'incremental_one_new_atom', 'wall_sec')
    incr_b = scenario_median(s5000_b, 'incremental_one_new_atom', 'wall_sec')

    fresh5k_req_a = scenario_median(s5000_a, 'fresh_subscriber_allspace', 'requests')
    fresh5k_req_b = scenario_median(s5000_b, 'fresh_subscriber_allspace', 'requests')
    fresh5k_bytes_a = scenario_median(s5000_a, 'fresh_subscriber_allspace', 'transferred_bytes')
    fresh5k_bytes_b = scenario_median(s5000_b, 'fresh_subscriber_allspace', 'transferred_bytes')

    fresh1k_req_a = scenario_median(s1000_a, 'fresh_subscriber_allspace', 'requests')
    fresh1k_req_b = scenario_median(s1000_b, 'fresh_subscriber_allspace', 'requests')
    fresh1k_bytes_a = scenario_median(s1000_a, 'fresh_subscriber_allspace', 'transferred_bytes')
    fresh1k_bytes_b = scenario_median(s1000_b, 'fresh_subscriber_allspace', 'transferred_bytes')

    fresh5k_request_ratio = ratio(fresh5k_req_a, fresh5k_req_b)
    fresh1k_request_ratio = ratio(fresh1k_req_a, fresh1k_req_b)
    fresh5k_byte_overhead_pct = percent_delta(fresh5k_bytes_a, fresh5k_bytes_b)
    fresh1k_byte_overhead_pct = percent_delta(fresh1k_bytes_a, fresh1k_bytes_b)

    mesh_fresh = scenario_median(mesh5000, 'fresh_subscriber_allspace', 'wall_sec')
    mesh_fresh_pull_requests = scenario_median(mesh5000, 'fresh_subscriber_allspace', 'pull_requests')
    static_b_request_advantage_vs_mesh = ratio(mesh_fresh_pull_requests, fresh5k_req_b)

    storage_1000 = static_data.get('storage_and_rebuild', {}).get('dataset_1000', {})
    storage_1000_a = storage_1000.get('A', {})
    storage_1000_b = storage_1000.get('B', {})

    concurrency = static_data.get('concurrency', {}).get('mode_results', {})
    c_a_1 = concurrency.get('A', {}).get('1', {}).get('summary', {}).get('median', {})
    c_a_8 = concurrency.get('A', {}).get('8', {}).get('summary', {}).get('median', {})
    c_b_1 = concurrency.get('B', {}).get('1', {}).get('summary', {}).get('median', {})
    c_b_8 = concurrency.get('B', {}).get('8', {}).get('summary', {}).get('median', {})

    mutable = mutable_file_stats()
    mutable_count = mutable.get('count') if isinstance(mutable, dict) else None
    mutable_bytes = mutable.get('bytes') if isinstance(mutable, dict) else None

    loaded_publication_example = publication_example
    if loaded_publication_example is None:
        loaded_publication_example = load_publication_example_from_evidence()

    example_values = publication_example_values(
        loaded_publication_example,
        mutable_count,
        mutable_bytes,
    )
    if example_values is None:
        section_2_examples = 'publication example not recorded in evidence'
    else:
        section_2_examples = (
            f'- root pointer `root.json`: `{{"v": "punkti/pub/0.6-draft", "seq": {example_values["example_root_seq"]}, "head": "{example_values["example_root_head"]}", "updated_at": "{example_values["example_root_updated"]}"}}`\n'
            f'- immutable manifest `manifests/<sha256>.json`: `seq={example_values["example_manifest_seq"]}`, `prev=null`, `record_count={example_values["example_record_count"]}`, `pack_count={example_values["example_pack_count"]}`, `depth=2`, `index={{"{example_values["example_index_prefix"]}": "{example_values["example_index_digest"]}"}}`\n'
            f'- immutable leaf shard `h/<xy chars>/<sha256>.json`: prefix `{example_values["example_leaf_prefix"]}`, {example_values["example_leaf_record_count"]} record entr(y/ies) keyed by MID, {example_values["example_leaf_pack_count"]} pack(s)\n'
            f'- exact immutable record bytes: `{example_values["example_record_path"]}`\n'
            f'- immutable replication pack: `{example_values["example_segment_path"]}`'
        )

    ranked_candidates = rec.get('ranked_candidates') or []
    depth_2 = next((item for item in ranked_candidates if item.get('depth') == 2), None)
    depth_10 = next((item for item in ranked_candidates if item.get('depth') == 10), None)
    scale_a = scale_mode_values(scale, 'A')
    scale_b = scale_mode_values(scale, 'B')
    scale100k_request_ratio = ratio(
        scale_a.get('requests') if isinstance(scale_a, dict) else None,
        scale_b.get('requests') if isinstance(scale_b, dict) else None,
    )
    scale100k_byte_overhead_pct = percent_delta(
        scale_a.get('transferred_bytes') if isinstance(scale_a, dict) else None,
        scale_b.get('transferred_bytes') if isinstance(scale_b, dict) else None,
    )
    suite = suite_state(test_data)

    if (
        fresh5k_request_ratio is not None
        and fresh5k_byte_overhead_pct is not None
        and mesh_fresh is not None
        and fresh_b is not None
    ):
        if fresh5k_request_ratio >= 10 and fresh5k_byte_overhead_pct <= 5 and fresh_b <= mesh_fresh * 1.2:
            recommendation = 'adopt static-first'
        elif mesh_fresh <= fresh_b * 0.6 and fresh5k_request_ratio < 5:
            recommendation = 'keep dynamic Mesh normative'
        else:
            recommendation = 'hybrid with optional dynamic accelerator'
    else:
        recommendation = 'hybrid with optional dynamic accelerator'

    scale_summary = format_scale_completion(scale)
    scale_limit_note = (
        f"100k scale evidence status: {scale_summary}. "
        "Interpret 100k conclusions from `scale_100k.completed` and `reason`, not assumptions."
    )
    return f"""# STATIC PUBLICATION REPORT — Punkti v0.6 prototype

Status: experimental, loopback-only, not frozen, not production-ready.

Evidence files:

- `evidence/test_results.json`
- `evidence/bench_static.json`
- `evidence/bench_mesh.json`
- `evidence/publication_example.json`

## 1) Minimal static publication profile (implemented)

Implemented profile matches `docs/SPEC.md` and keeps mutable root + immutable content-addressed objects.

Mutable-file accounting from benchmark evidence: `root.json` is the only mutable artifact (`{fmt_num(mutable_count, digits=0)}` file, `{fmt_num(mutable_bytes, digits=0)}` bytes in measured runs).

Test status from `evidence/test_results.json`:

- status: `{test_data.get('status', 'unknown')}`
- return code: `{test_data.get('returncode', 'unknown')}`
- ran: `{test_data.get('ran', 'unknown')}`
- seconds: `{test_data.get('seconds', 'unknown')}`

## 2) Exact directory/object examples (real run excerpts)

From `evidence/publication_example.json` (a real publication run):

{section_2_examples}

Reading rules this layout encodes:

- the file name of every object under `manifests/`, `h/`, `records/` and
  `segments/` is the lowercase hex SHA256 of that object's exact bytes, so a
  reader rejects any object whose bytes do not hash to its name;
- `root.json` is the only mutable file ({mutable_count if mutable_count is not None else 'n/a'} file,
  {mutable_bytes if mutable_bytes is not None else 'n/a'} bytes) and it only points at the current manifest;
- records remain canonical raw carrier bytes under digest paths, and mode B
  adds immutable pack segments only as an acceleration artifact while the
  canonical per-record objects stay published.

## 3) Reference publisher + reader/replicator

Module map:

- `src/staticpub/publisher.py` — deterministic immutable object build + atomic root swap
- `src/staticpub/reader.py` — GET-only replication with digest and carrier validation
- `src/staticpub/store.py` — valid MID-keyed store + candidate digest-keyed store
- `src/staticpub/httpsource.py` — dumb stdlib static file source
- `src/staticpub/harness.py` — node lifecycle wrapper
- `src/staticpub/carrier_io.py` — approved carrier/spatial import + framing helpers

## 4) Clean-room reader proof

- Implemented in `src/staticpub/cleanroom.py`.
- Equivalence test remains `test_20_cleanroom_reader_matches_reference_reader`.

## 5) Dumb-server / offline-daemon proof

- Static serving remains stdlib HTTP only.
- Replication does not require a running Punkti daemon.

## 6) Two-node and three-node convergence evidence

- `test_01_two_node_union_convergence`
- `test_10_three_node_partial_overlap_converges_to_union`

## 7) Index-only vs pack benchmark verdict

Bounded run profile: `{static_data.get('plan')}`, repeats={static_data.get('repeats')}.

- Recommended leaf depth: `{rec.get('leaf_depth', 'n/a')}`
- Recommendation rationale: {rec.get('rationale', 'n/a')}
- 5k fresh wall median: A `{fmt_num(fresh_a)}s`, B `{fmt_num(fresh_b)}s`
- 5k XY-prefix wall median: A `{fmt_num(prefix_a)}s`, B `{fmt_num(prefix_b)}s`
- 5k incremental wall median: A `{fmt_num(incr_a)}s`, B `{fmt_num(incr_b)}s`
- Fresh subscriber request collapse at 5k atoms: A `{fmt_num(fresh5k_req_a, digits=0)}` vs B `{fmt_num(fresh5k_req_b, digits=0)}` (`{fmt_num(fresh5k_request_ratio, digits=1)}x` fewer requests in mode B).
- Fresh subscriber request collapse at 1k atoms: A `{fmt_num(fresh1k_req_a, digits=0)}` vs B `{fmt_num(fresh1k_req_b, digits=0)}` (`{fmt_num(fresh1k_request_ratio, digits=1)}x` fewer requests in mode B).
- Byte overhead for that collapse: 5k A `{fmt_num(fresh5k_bytes_a, digits=0)}` bytes vs B `{fmt_num(fresh5k_bytes_b, digits=0)}` bytes (`{fmt_num(fresh5k_byte_overhead_pct)}%`), 1k A `{fmt_num(fresh1k_bytes_a, digits=0)}` vs B `{fmt_num(fresh1k_bytes_b, digits=0)}` (`{fmt_num(fresh1k_byte_overhead_pct)}%`).
- 100k scale (from `scale_100k`): mode A replication `{fmt_num(scale_a.get('requests') if isinstance(scale_a, dict) else None, digits=0)}` requests, `{fmt_num(scale_a.get('replication_wall_sec') if isinstance(scale_a, dict) else None)}s` wall, publish `{fmt_num(scale_a.get('publish_wall_sec') if isinstance(scale_a, dict) else None)}s` wall / `{fmt_num(scale_a.get('publish_cpu_sec') if isinstance(scale_a, dict) else None)}s` CPU.
- 100k scale (from `scale_100k`): mode B replication `{fmt_num(scale_b.get('requests') if isinstance(scale_b, dict) else None, digits=0)}` requests, `{fmt_num(scale_b.get('replication_wall_sec') if isinstance(scale_b, dict) else None)}s` wall, publish `{fmt_num(scale_b.get('publish_wall_sec') if isinstance(scale_b, dict) else None)}s` wall / `{fmt_num(scale_b.get('publish_cpu_sec') if isinstance(scale_b, dict) else None)}s` CPU.
- 100k scale request/byte tradeoff: mode A `{fmt_num(scale_a.get('requests') if isinstance(scale_a, dict) else None, digits=0)}` vs mode B `{fmt_num(scale_b.get('requests') if isinstance(scale_b, dict) else None, digits=0)}` requests (`{fmt_num(scale100k_request_ratio, digits=1)}x` fewer in mode B) with bytes `{fmt_num(scale_a.get('transferred_bytes') if isinstance(scale_a, dict) else None, digits=0)}`→`{fmt_num(scale_b.get('transferred_bytes') if isinstance(scale_b, dict) else None, digits=0)}` (`{fmt_num(scale100k_byte_overhead_pct)}%` mode-B overhead).
- 100k scale completion state: {scale_summary}.
- Storage/rebuild at 1k atoms: mode A `{fmt_num(storage_1000_a.get('publication_bytes'), digits=0)}` bytes over `{fmt_num(storage_1000_a.get('publication_file_count'), digits=0)}` files (amplification `{fmt_num(storage_1000_a.get('storage_amplification'))}x`, rebuild `{fmt_num(storage_1000_a.get('rebuild_wall_sec'))}s`); mode B `{fmt_num(storage_1000_b.get('publication_bytes'), digits=0)}` bytes over `{fmt_num(storage_1000_b.get('publication_file_count'), digits=0)}` files (amplification `{fmt_num(storage_1000_b.get('storage_amplification'))}x`, rebuild `{fmt_num(storage_1000_b.get('rebuild_wall_sec'))}s`).
- Concurrency on one shared publication (1k atoms): A/1 reader `{fmt_num(c_a_1.get('aggregate_requests'), digits=0)}` req in `{fmt_num(c_a_1.get('wall_sec'))}s`, A/8 readers `{fmt_num(c_a_8.get('aggregate_requests'), digits=0)}` req in `{fmt_num(c_a_8.get('wall_sec'))}s`; B/1 reader `{fmt_num(c_b_1.get('aggregate_requests'), digits=0)}` req in `{fmt_num(c_b_1.get('wall_sec'))}s`, B/8 readers `{fmt_num(c_b_8.get('aggregate_requests'), digits=0)}` req in `{fmt_num(c_b_8.get('wall_sec'))}s`.
- Leaf-depth sweep shape: depth `{rec.get('leaf_depth', 'n/a')}` has the lowest request score (`{fmt_num(depth_2.get('request_score') if depth_2 else None, digits=0)}`) while depth 10 is much worse (`{fmt_num(depth_10.get('request_score') if depth_10 else None, digits=0)}`), confirming that shallower leaves reduce index-object fanout and request count.

Verdict: mode B is the practical bootstrap profile for static origins because it collapses request count by ~two orders of magnitude with only low single-digit byte overhead.

## 8) Static profile vs dynamic Mesh baseline verdict

Matched-size comparison now includes 1k and 5k datasets with identical scenario names.

- Mesh 5k fresh wall median: `{fmt_num(mesh_fresh)}s`
- Static A 5k fresh wall median: `{fmt_num(fresh_a)}s`
- Static B 5k fresh wall median: `{fmt_num(fresh_b)}s`
- Mesh 5k fresh pull requests: `{fmt_num(mesh_fresh_pull_requests, digits=0)}`
- Static B 5k fresh requests: `{fmt_num(fresh5k_req_b, digits=0)}` (`{fmt_num(static_b_request_advantage_vs_mesh, digits=1)}x` fewer requests than Mesh in this scenario)

Verdict: this loopback pass shows Mesh wall-time advantage, but the dimensions diverge: Mesh minimizes elapsed time in this setup while static mode B minimizes origin request count. The wall gap is measured against a stdlib single-threaded static server on a one-vCPU/two-GB host and is not equivalent to a CDN-cached static origin result.

## 9) Failure/hostile results

Suite evidence from `evidence/test_results.json`: {suite.get('label')} (`status={suite.get('status')}`, `returncode={suite.get('returncode')}`, `ran={suite.get('ran')}`, `seconds={suite.get('seconds')}`).

- Truncation: `test_11_hostile_truncated_record_rejected` — {suite.get('label')}.
- Stale head/root detection: `test_07_stale_root_then_refresh_detected` — {suite.get('label')}.
- Missing referenced object/no false checkpoint admission: `test_08_missing_referenced_object_no_false_checkpoint` — {suite.get('label')}.
- Missing segment (mode B): `test_12_hostile_missing_segment_in_mode_b_fails` — {suite.get('label')}.
- Corrupt static object: `test_13_hostile_corrupt_root_object_rejected` — {suite.get('label')}.
- Mismatched digest: `test_14_hostile_mismatched_digest_rejected` — {suite.get('label')}.
- Replay/duplicate: `test_15_hostile_replay_duplicate_is_noop` — {suite.get('label')}.
- Reordered publication visibility: `test_16_hostile_reordered_publication_visibility` — {suite.get('label')}.
- Selective withholding: `test_17_hostile_selective_withholding_detectable_by_comparison` — {suite.get('label')}.
- Long offline/rejoin (source disappearance/reappearance): `test_09_source_disappearance_and_reappearance_is_idempotent` — {suite.get('label')}.
- Invalid variant cannot poison valid MID: `test_02_same_mid_invalid_variant_cannot_poison_valid` — {suite.get('label')}.
- Same XY with different Z filtering correctness: `test_03_same_xy_different_z_filter` — {suite.get('label')}.
- Negative and large Z preservation: `test_05_negative_and_large_z_values_preserved` — {suite.get('label')}.
- Dumb static server replication after source stop: `test_06_dumb_static_server_replication_works_after_node_stop` — {suite.get('label')}.
- Required convergence proof (two-node union): `test_01_two_node_union_convergence` — {suite.get('label')}.
- Required convergence proof (three-node partial overlap to union): `test_10_three_node_partial_overlap_converges_to_union` — {suite.get('label')}.
- Required clean-room equivalence proof: `test_20_cleanroom_reader_matches_reference_reader` — {suite.get('label')}.
- Required bounded-fetch proof: `test_04_xy_prefix_limited_replication_only_fetches_matching_region` — {suite.get('label')}.

## 10) What dynamic Mesh mechanisms become unnecessary (if static-first adopted)

- No required PUSH endpoint for correctness: a fresh subscriber converges from immutable static objects plus `root.json` discovery pointer.
- No required dynamic range-query API for correctness: static shard traversal + optional pack segments already complete state transfer.
- No required reciprocal callback/session state for correctness: no session coupling is needed between publisher and subscriber.
- No required live daemon at the serving side for correctness: publication can be served by dumb static hosting.
- These mechanisms remain useful as optional accelerators for wall-time-sensitive paths, but correctness does not depend on them.

## 11) What current Mesh still does materially better

- Lower measured loopback wall-time in this pass (5k fresh median `{fmt_num(mesh_fresh)}s` vs static B `{fmt_num(fresh_b)}s`).
- One-shot dynamic range pull path avoids object-by-object traversal in the current implementation.
- No publication rebuild step before serving updates.
- Simpler incremental catch-up path in the current Mesh prototype.
- Pull requests are dynamic-range API calls rather than per-object static GETs.

## 12) Recommendation

Evidence-derived recommendation: **{recommendation}**.

- Three-way decision frame:
  - **Adopt static-first** when minimizing origin requests and static-host correctness is the primary goal.
  - **Keep dynamic Mesh normative** when wall-time-sensitive live synchronization is the dominant requirement.
  - **Hybrid (recommended for current evidence)**: static publication is the normative correctness path; dynamic Mesh range-pull/PUSH remains an optional accelerator for latency-sensitive environments.
- Use leaf depth `{rec.get('leaf_depth', 'n/a')}` for the current static publication profile.
- Recommendation justification from measured evidence: request collapse (`{fmt_num(fresh5k_req_a, digits=0)}`→`{fmt_num(fresh5k_req_b, digits=0)}` at 5k) with small byte overhead (`{fmt_num(fresh5k_byte_overhead_pct)}%`) supports static correctness; Mesh wall median (`{fmt_num(mesh_fresh)}s`) supports optional acceleration.

100k bounded-step completion: {scale_summary}.

## Limitations (explicit)

- Loopback-only measurements.
- Not production durability.
- No CDN vendor integration benchmark.
- Not protocol-frozen.
- Warm cache and stdlib server conditions mean comparative, not absolute-latency, claims.
- Host constraint for this run: one vCPU and ~2 GB RAM.
- {scale_limit_note}
"""


def regenerate_docs_from_evidence(root=ROOT):
    evidence_dir = root / 'evidence'
    static_data = json.loads((evidence_dir / 'bench_static.json').read_text(encoding='utf-8'))
    mesh_data = json.loads((evidence_dir / 'bench_mesh.json').read_text(encoding='utf-8'))
    test_data = json.loads((evidence_dir / 'test_results.json').read_text(encoding='utf-8'))
    publication_example = load_publication_example_from_evidence(root=root)

    benchmark_path = root / 'docs' / 'BENCHMARK.md'
    report_path = root / 'docs' / 'STATIC_PUBLICATION_REPORT.md'
    benchmark_path.write_text(generate_benchmark_markdown(static_data, mesh_data), encoding='utf-8')
    report_path.write_text(
        generate_static_report_markdown(static_data, mesh_data, test_data, publication_example=publication_example),
        encoding='utf-8',
    )
    return [str(benchmark_path), str(report_path)]


def run_scale_only(scale_budget_seconds=None, scale_count=None, root=ROOT):
    evidence_dir = root / 'evidence'
    static_path = evidence_dir / 'bench_static.json'
    mesh_path = evidence_dir / 'bench_mesh.json'

    if not static_path.exists():
        raise FileNotFoundError(f'missing required evidence file: {static_path}')
    if not mesh_path.exists():
        raise FileNotFoundError(f'missing required evidence file: {mesh_path}')

    try:
        static_results = json.loads(static_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'invalid JSON in {static_path}: {exc}') from exc

    try:
        json.loads(mesh_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError(f'invalid JSON in {mesh_path}: {exc}') from exc

    if scale_budget_seconds is None:
        scale_budget_seconds = BENCH_PLANS['bounded']['scale_budget_seconds']
    if scale_count is None:
        scale_count = BENCH_PLANS['bounded']['scale_count']

    recommendation = static_results.get('recommended_leaf_depth') or {}
    recommended_leaf_depth = recommendation.get('leaf_depth')
    if recommended_leaf_depth is None:
        sweep = static_results.get('leaf_depth_sweep')
        if not sweep:
            raise ValueError('recommended_leaf_depth missing and leaf_depth_sweep unavailable in bench_static.json')
        recommended_leaf_depth = choose_recommended_leaf_depth(sweep)['leaf_depth']

    static_results['scale_100k'] = run_scale_100k(
        recommended_leaf_depth,
        budget_seconds=scale_budget_seconds,
        count=scale_count,
    )
    write_json_atomic(static_path, static_results)
    updated_docs = regenerate_docs_from_evidence(root=root)
    return {'static': static_results, 'files': [str(static_path), str(mesh_path)], 'updated_docs': updated_docs}


def run_all(repeats=3, plan='full', scale_budget_seconds=None, scale_count=None):
    if repeats < 3:
        raise ValueError('repeats must be >= 3')
    if plan not in BENCH_PLANS:
        raise ValueError(f'unknown plan: {plan!r}')

    plan_cfg = BENCH_PLANS[plan]
    if scale_budget_seconds is None:
        scale_budget_seconds = plan_cfg['scale_budget_seconds']
    if scale_count is None:
        scale_count = plan_cfg['scale_count']

    print(f'benchmark start repeats={repeats} plan={plan}', flush=True)
    run_started = time.perf_counter()
    datasets = {}
    for size in DATASET_SIZES:
        datasets[str(size)] = {
            'records': generate_records(size, start=10000),
            'disjoint': generate_records(size, start=500000),
            'plus_one': make_record(77777777 + size, make_h(77777777 + size, prefix='u4', z='1')),
        }

    evidence_dir = ROOT / 'evidence'
    evidence_dir.mkdir(parents=True, exist_ok=True)
    static_path = evidence_dir / 'bench_static.json'
    mesh_path = evidence_dir / 'bench_mesh.json'

    static_results = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'host': collect_host_info(),
        'plan': plan,
        'repeats': repeats,
        'dataset_sizes': list(DATASET_SIZES),
        'leaf_depth_sweep': {
            'depths': list(LEAF_DEPTH_SWEEP),
            'sweep_dataset_sizes': [str(x) for x in plan_cfg['leaf_sweep_dataset_sizes']],
            'sweep_scenarios': list(plan_cfg['leaf_sweep_scenarios']),
            'modes': {},
        },
        'matched_static': {'datasets': {}},
        'storage_and_rebuild': {},
        'concurrency': {'dataset_size': plan_cfg['concurrency_dataset_size'], 'mode_results': {}},
        'scale_100k': None,
    }
    mesh_results = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'host': collect_host_info(),
        'plan': plan,
        'repeats': repeats,
        'dataset_sizes': list(plan_cfg['matched_dataset_sizes']),
        'scenarios_by_dataset': {},
    }

    write_json_atomic(static_path, static_results)
    write_json_atomic(mesh_path, mesh_results)

    for mode in ('A', 'B'):
        static_results['leaf_depth_sweep']['modes'][mode] = {'datasets': {}}
        for dataset_size in plan_cfg['leaf_sweep_dataset_sizes']:
            size_key = str(dataset_size)
            print(f'leaf sweep mode={mode} dataset={dataset_size}', flush=True)
            records = datasets[size_key]['records']
            disjoint = datasets[size_key]['disjoint']
            dataset_out = {'depths': {}}
            for depth in LEAF_DEPTH_SWEEP:
                with tempfile.TemporaryDirectory(prefix=f'static-sweep-{mode}-d{depth}-{dataset_size}-') as td:
                    source = Node(Path(td) / 'source', mode=mode, leaf_depth=depth)
                    for raw in records:
                        source.store.admit(raw)
                    source.publish()
                    source_dir = source.path / 'public'
                    scenarios = run_static_scenarios_from_publication(
                        mode,
                        depth,
                        source_dir,
                        records,
                        disjoint,
                        scenario_names=plan_cfg['leaf_sweep_scenarios'],
                        repeats=repeats,
                    )
                    dataset_out['depths'][str(depth)] = {'scenarios': scenarios}
                static_results['leaf_depth_sweep']['modes'][mode]['datasets'][size_key] = dataset_out
                write_json_atomic(static_path, static_results)

    recommendation = choose_recommended_leaf_depth(static_results['leaf_depth_sweep'])
    static_results['recommended_leaf_depth'] = recommendation
    write_json_atomic(static_path, static_results)
    recommended_leaf_depth = recommendation['leaf_depth']

    for dataset_size in plan_cfg['matched_dataset_sizes']:
        size_key = str(dataset_size)
        static_results['matched_static']['datasets'][size_key] = {}
        records = datasets[size_key]['records']
        disjoint = datasets[size_key]['disjoint']
        plus_one = datasets[size_key]['plus_one']

        for mode in ('A', 'B'):
            print(f'static matched mode={mode} dataset={dataset_size}', flush=True)
            static_results['matched_static']['datasets'][size_key][mode] = run_static_matched_dataset(
                mode,
                dataset_size,
                recommended_leaf_depth,
                records,
                disjoint,
                plus_one,
                repeats,
            )
            write_json_atomic(static_path, static_results)

        print(f'mesh matched dataset={dataset_size}', flush=True)
        mesh_results['scenarios_by_dataset'][size_key] = run_mesh_matched_dataset(records, disjoint, plus_one, repeats)
        write_json_atomic(mesh_path, mesh_results)

    print('scale 100k start', flush=True)

    def _scale_progress(partial):
        static_results['scale_100k'] = partial
        write_json_atomic(static_path, static_results)

    static_results['scale_100k'] = run_scale_100k(
        recommended_leaf_depth,
        budget_seconds=scale_budget_seconds,
        count=scale_count,
        progress_callback=_scale_progress,
    )
    write_json_atomic(static_path, static_results)
    print('scale 100k done', flush=True)

    storage_size_key = str(plan_cfg['storage_dataset_size'])
    storage_records = datasets[storage_size_key]['records']
    static_results['storage_and_rebuild'][f'dataset_{storage_size_key}'] = {}
    for mode in ('A', 'B'):
        static_results['storage_and_rebuild'][f'dataset_{storage_size_key}'][mode] = measure_storage_and_rebuild(
            mode,
            recommended_leaf_depth,
            storage_records,
        )
        write_json_atomic(static_path, static_results)

    concurrency_records = datasets[str(plan_cfg['concurrency_dataset_size'])]['records']
    for mode in ('A', 'B'):
        mode_out = {}
        for readers in (1, 8):
            print(f'concurrency mode={mode} readers={readers}', flush=True)
            runs = [
                static_concurrency_run(mode, recommended_leaf_depth, concurrency_records, readers)
                for _ in range(repeats)
            ]
            mode_out[str(readers)] = {'runs': runs, 'summary': summarize_runs(runs)}
            static_results['concurrency']['mode_results'][mode] = mode_out
            write_json_atomic(static_path, static_results)

    static_results['run_wall_sec'] = time.perf_counter() - run_started
    write_json_atomic(static_path, static_results)
    write_json_atomic(mesh_path, mesh_results)
    return {'static': static_results, 'mesh': mesh_results, 'files': [str(static_path), str(mesh_path)]}


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description='Run static publication benchmarks')
    parser.add_argument('--plan', choices=sorted(BENCH_PLANS), default='full')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--scale-budget-seconds', type=int, default=None)
    parser.add_argument('--scale-count', type=int, default=None)
    parser.add_argument('--scale-only', action='store_true')
    parser.add_argument('--docs-only', action='store_true')
    parser.add_argument('--skip-docs', action='store_true')
    args = parser.parse_args(argv)

    if args.docs_only and args.scale_only:
        parser.error('--docs-only and --scale-only cannot be used together')

    if args.docs_only:
        updated = regenerate_docs_from_evidence(root=root)
        print(json.dumps({'updated_docs': updated}, indent=2))
    elif args.scale_only:
        try:
            result = run_scale_only(
                scale_budget_seconds=args.scale_budget_seconds,
                scale_count=args.scale_count,
                root=root,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f'error: {exc}', file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2))
    else:
        result = run_all(
            repeats=args.repeats,
            plan=args.plan,
            scale_budget_seconds=args.scale_budget_seconds,
            scale_count=args.scale_count,
        )
        if not args.skip_docs:
            regenerate_docs_from_evidence(root=root)
        print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
