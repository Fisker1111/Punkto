"""Strict YAML configuration; environment overrides YAML overrides defaults."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import yaml
from urllib.parse import urlsplit
from .mesh import peer_url
from .spatial import Subscription

DEFAULTS = {
    'web': {'enabled': True, 'root': '/srv/pwa', 'spa_fallback': False, 'pages': {'/ai': 'ai.html'}},
    'bootstrap': {'nodes': []},
    'publication': {'enabled': True, 'path': None, 'packs': False, 'serve_prefix': '/publication'},
    'node': {'name': 'punkti-node', 'public_url': '', 'description': '', 'operator_contact': ''},
    'network': {'listen_host': '0.0.0.0', 'listen_port': 8000, 'advertise_url': '',
                'peers': [], 'sync_interval_seconds': 30},
    'subscriptions': [{}], 'storage': {'data_path': '/data'},
    'logging': {'level': 'info'}, 'branding': {'display_name': 'Punkti Node'},
}
ENV = {
    'PUNKTO_BOOTSTRAP_NODES': ('bootstrap', 'nodes', json.loads),
    'PUNKTO_WEB_ENABLED': ('web', 'enabled', lambda s: s.lower() not in ('0', 'false', 'no', 'off')),
    'PUNKTO_WEB_ROOT': ('web', 'root', str),
    'PUNKTO_HOST': ('network', 'listen_host', str),
    'PUNKTO_PORT': ('network', 'listen_port', int),
    'PUNKTO_NODE_NAME': ('node', 'name', str),
    'PUNKTO_PEERS': ('network', 'peers', lambda s: [p.strip() for p in s.split(',') if p.strip()]),
    'PUNKTO_DATA_DIR': ('storage', 'data_path', str),
    'PUNKTO_SYNC_INTERVAL': ('network', 'sync_interval_seconds', float),
    'PUNKTO_LOG_LEVEL': ('logging', 'level', str),
    'PUNKTO_PUBLICATION_ENABLED': ('publication', 'enabled', lambda s: s.lower() not in ('0', 'false', 'no', 'off')),
    'PUNKTO_PUBLICATION_PATH': ('publication', 'path', str),
    'PUNKTO_PUBLICATION_PACKS': ('publication', 'packs', lambda s: s.lower() not in ('0', 'false', 'no', 'off')),
    'PUNKTO_PUBLICATION_SERVE_PREFIX': ('publication', 'serve_prefix', str),
}


def load_config(path=None, environ=None):
    env = os.environ if environ is None else environ
    path = env.get('PUNKTO_NODE_CONFIG', path)
    config = deepcopy(DEFAULTS)
    if path:
        with open(path, encoding='utf-8') as source:
            supplied = yaml.safe_load(source)
        if not isinstance(supplied, dict):
            raise ValueError('configuration must be a YAML mapping')
        for section, value in supplied.items():
            if section not in DEFAULTS:
                raise ValueError(f'unknown configuration section: {section}')
            if section == 'subscriptions':
                config[section] = value
            else:
                if not isinstance(value, dict) or set(value) - set(DEFAULTS[section]):
                    raise ValueError(f'invalid configuration section: {section}')
                config[section].update(value)
    for variable, (section, key, convert) in ENV.items():
        if variable in env:
            try:
                config[section][key] = convert(env[variable])
            except (ValueError, TypeError) as exc:
                raise ValueError(f'invalid {variable}') from exc
    for section, keys in DEFAULTS.items():
        if isinstance(keys, dict):
            for key, default in keys.items():
                if isinstance(default, str) and not isinstance(config[section][key], str):
                    raise ValueError(f'{section}.{key} must be a string')
    nodes = config['bootstrap']['nodes']
    if not isinstance(nodes, list):
        raise ValueError('bootstrap.nodes must be a list')
    for entry in nodes:
        if (not isinstance(entry, dict) or
                not {'id', 'base', 'publication'} <= set(entry) or
                set(entry) - {'id', 'base', 'publication', 'submit', 'index'}):
            raise ValueError('invalid bootstrap node members')
        if not isinstance(entry['id'], str) or not entry['id'].strip():
            raise ValueError('bootstrap node id must be non-empty')
        for key in ('base', 'publication', 'submit', 'index'):
            if key not in entry:
                continue
            value = entry[key]
            if not isinstance(value, str) or not value or value.endswith('/') or any(c.isspace() for c in value):
                raise ValueError('invalid bootstrap URL')
            parsed = urlsplit(value)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError('invalid bootstrap URL')
            try:
                parsed.port
            except ValueError as exc:
                raise ValueError('invalid bootstrap URL port') from exc
    web = config['web']
    pages = web['pages']
    if not isinstance(pages, dict):
        raise ValueError('web.pages must be a mapping')
    for route, filename in pages.items():
        if (not isinstance(route, str) or not route.startswith('/') or
                any(c in route for c in ('\\', '%', '?', '#', '\x00')) or
                any(part in ('', '.', '..') for part in route.split('/')[1:])):
            raise ValueError('invalid web.pages path')
        if (not isinstance(filename, str) or not filename or Path(filename).is_absolute() or
                any(c in filename for c in ('\\', '%', '\x00')) or
                any(part in ('', '.', '..') for part in filename.split('/'))):
            raise ValueError('invalid web.pages file')
    if type(web['enabled']) is not bool or type(web['spa_fallback']) is not bool:
        raise ValueError('web.enabled and web.spa_fallback must be booleans')
    if web['enabled']:
        if not Path(web['root']).is_absolute():
            raise ValueError('web.root must be an absolute path')
        if not Path(web['root']).is_dir():
            raise ValueError('web.root directory does not exist: ' + web['root'])

    publication = config['publication']
    if type(publication['enabled']) is not bool or type(publication['packs']) is not bool:
        raise ValueError('publication.enabled and publication.packs must be booleans')
    if publication['path'] in (None, ''):
        publication['path'] = str(Path(config['storage']['data_path']) / 'publication')
    if not isinstance(publication['path'], str):
        raise ValueError('publication.path must be a string')
    if not Path(publication['path']).is_absolute():
        raise ValueError('publication.path must be an absolute path')
    if not isinstance(publication['serve_prefix'], str) or not publication['serve_prefix'].startswith('/'):
        raise ValueError('publication.serve_prefix must start with /')
    if publication['serve_prefix'] != '/' and publication['serve_prefix'].endswith('/'):
        raise ValueError('publication.serve_prefix must not end with /')
    if any(part in ('', '.', '..') for part in publication['serve_prefix'].split('/')[1:]):
        raise ValueError('publication.serve_prefix must be a clean path prefix')
    net = config['network']
    if not net['listen_host'] or any(c.isspace() for c in net['listen_host']):
        raise ValueError('network.listen_host must be a host')
    if type(net['listen_port']) is not int or not 0 <= net['listen_port'] <= 65535:
        raise ValueError('network.listen_port must be an integer from 0 to 65535')
    interval = net['sync_interval_seconds']
    if type(interval) not in (int, float) or not math.isfinite(interval) or interval <= 0:
        raise ValueError('network.sync_interval_seconds must be positive and finite')
    if not config['storage']['data_path']:
        raise ValueError('storage.data_path must not be empty')
    if config['logging']['level'] not in ('debug', 'info', 'warning', 'error'):
        raise ValueError('logging.level must be debug, info, warning or error')
    if not isinstance(net['peers'], list) or any(not isinstance(p, str) for p in net['peers']):
        raise ValueError('network.peers must be a list of origins')
    for origin in net['peers'] + [net['advertise_url'], config['node']['public_url']]:
        if origin:
            peer_url(origin)
        elif origin in net['peers']:
            raise ValueError('network.peers cannot contain an empty origin')
    if not isinstance(config['subscriptions'], list):
        raise ValueError('subscriptions must be a list (use [] to accept nothing)')
    try:
        config['subscriptions'] = [Subscription(**s).wire() for s in config['subscriptions']]
    except (TypeError, ValueError) as exc:
        raise ValueError(f'invalid subscription: {exc}') from exc
    config['config_loaded'] = bool(path)
    config['config_path'] = Path(path).name if path else None
    return config
