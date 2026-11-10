#!/usr/bin/env python3
"""Offline, stdlib-only guard for the review-only www candidate package."""
from pathlib import Path
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []


def require(condition, message):
    if not condition:
        errors.append(message)


def read(relative):
    path = ROOT / relative
    if not path.is_file():
        errors.append(f'{relative}: missing file')
        return ''
    text = path.read_text()
    require(bool(text.strip()), f'{relative}: empty file')
    return text


def parse(text, label):
    """Parse the deliberately small line-oriented candidate grammar, fail closed."""
    root = []
    stack = [root]
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        if line == '}':
            if len(stack) == 1:
                errors.append(f'{label}:{number}: unmatched closing brace')
            else:
                stack.pop()
        elif line.endswith('{'):
            children = []
            stack[-1].append((line[:-1].strip(), children))
            stack.append(children)
        elif '{' in line or '}' in line:
            errors.append(f'{label}:{number}: unsupported inline brace syntax')
        else:
            stack[-1].append((line, None))
    require(len(stack) == 1, f'{label}: unclosed block')
    return root


def block(nodes, name, label):
    found = [children for directive, children in nodes if directive == name and children is not None]
    require(len(found) == 1, f'{label}: require exactly one {name} block')
    return found[0] if found else []


def lines(nodes):
    return [directive for directive, children in nodes if children is None]


for node, peer in [('node1', '159.65.115.166'), ('node2', '46.101.118.157')]:
    label = f'deploy/candidate/www/{node}.Caddyfile.www'
    text = read(label)
    tree = parse(text, label)
    site = block(tree, 'www.punkto.xyz', label)
    require(len(tree) == 1, f'{label}: only one www.punkto.xyz site block permitted')
    active = '\n'.join(raw.split('#', 1)[0] for raw in text.splitlines())
    require(not re.search(r'\bredir\b', active), f'{label}: redirects forbidden')
    require('tls /etc/caddy/www-tls/fullchain.pem /etc/caddy/www-tls/key.pem' in lines(site),
            f'{label}: require node-local explicit certificate/key paths')
    require('encode gzip' in lines(site), f'{label}: missing encode gzip')
    headers = block(site, 'header', label)
    require(set(lines(headers)) == {
        'X-Content-Type-Options nosniff', 'X-Frame-Options DENY',
        'Referrer-Policy strict-origin-when-cross-origin', '-Server'},
        f'{label}: require exactly the four security headers')
    submit = block(site, '@submit_write', label)
    require(set(lines(submit)) == {'method POST', 'path /submit /api/submit'},
            f'{label}: submit guard must match both POST paths without exceptions')
    push = block(site, '@push_write', label)
    require(set(lines(push)) == {'method POST', 'path /push /sync /api/push /api/sync',
                               f'not remote_ip {peer}'},
            f'{label}: push guard must match four POST paths, except sibling {peer}')
    require('@mcp path /mcp' in lines(site), f'{label}: missing exact-path MCP matcher')
    route = block(site, 'route', label)
    require([name for name, _ in route] == [
        'respond @submit_write 403', 'respond @push_write 403',
        'reverse_proxy @mcp https://punkto-mcp.sunebech.workers.dev',
        'reverse_proxy 172.22.0.3:8000'],
        f'{label}: require ordered 403 guards, MCP proxy and node-local fallback only')
    mcp = block(route, 'reverse_proxy @mcp https://punkto-mcp.sunebech.workers.dev', label)
    require(set(lines(mcp)) == {'header_up Host punkto-mcp.sunebech.workers.dev', 'flush_interval -1'},
            f'{label}: MCP requires Host override and flush_interval -1')
    allowed = {'tls /etc/caddy/www-tls/fullchain.pem /etc/caddy/www-tls/key.pem',
               'header', 'encode gzip', '@submit_write', '@push_write', '@mcp path /mcp', 'route'}
    require(len(site) == len(allowed) and {name for name, _ in site} == allowed,
            f'{label}: unexpected or duplicate site directives')

runbook = read('docs/operator/www-round-robin-runbook.md')
for term in ('46.101.118.157', '159.65.115.166', 'DNS-01', 'rollback',
             'no automatic failover', 'no guaranteed 50/50 split'):
    require(term.lower() in runbook.lower(), f'runbook: missing {term!r}')
for ip in ('46.101.118.157', '159.65.115.166'):
    require(f'| Add | www | A | {ip} | 600 |' in runbook,
            f'runbook: missing exact target A record {ip} TTL 600')
read('deploy/candidate/www/README.md')
script = ROOT / 'scripts/verify-www-roundrobin.sh'
read('scripts/verify-www-roundrobin.sh')
require(os.access(script, os.X_OK), 'verify script: must be executable')
if script.is_file():
    result = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
    require(result.returncode == 0, f'verify script: bash -n failed: {result.stderr.strip()}')
if errors:
    for message in errors:
        print(f'FAIL {message}', file=sys.stderr)
    sys.exit(1)
print('PASS www candidate lint: both vhosts, policies, headers, runbook and executable verifier')
