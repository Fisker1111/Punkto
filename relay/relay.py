#!/usr/bin/env python3
"""
punkto-relay v0.1 — Flow TV relay node

Single-file Python 3 server. Stdlib + `requests`.

Roles:
  - Accept POST /atom from clients
  - Maintain a bounded rolling buffer of recent atoms backed by an append-only JSONL log
  - Serve GET /latest, GET /feed?since=<cursor>, GET /health, GET /info
  - Server-render GET /p/<atom_id> with OpenGraph meta for share cards
  - Pull from configured peers via /latest (fallback /feed) on a background thread

See ../punkto.relay.md for the spec.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import re
import socket
import sys
import threading
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    import base64 as _base64
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False
    Ed25519PublicKey = None  # type: ignore[assignment]
    InvalidSignature = None  # type: ignore[assignment]


try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

try:
    import requests
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "punkto-relay requires the `requests` library. "
        "pip install -r requirements.txt\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration (env vars)
# ---------------------------------------------------------------------------

VERSION = "v0.1"
STARTED_AT = time.time()

HOST = os.environ.get("PUNKTO_HOST", "127.0.0.1")
PORT = int(os.environ.get("PUNKTO_PORT", "8000"))

DATA_DIR = os.environ.get("PUNKTO_DATA_DIR", "./data/")
NODE_NAME = os.environ.get("PUNKTO_NODE_NAME", f"relay-{socket.gethostname()}")

_PEERS_RAW = os.environ.get("PUNKTO_PEERS", "")
PEERS = [p.strip().rstrip("/") for p in _PEERS_RAW.split(",") if p.strip()]

BUFFER_ATOMS = int(os.environ.get("PUNKTO_BUFFER_ATOMS", "10000"))
BUFFER_HOURS = int(os.environ.get("PUNKTO_BUFFER_HOURS", "168"))
LATEST_LIMIT = int(os.environ.get("PUNKTO_LATEST_LIMIT", "100"))
SYNC_INTERVAL = int(os.environ.get("PUNKTO_SYNC_INTERVAL", "30"))

# Basic per-IP rate limit for POST /atom (alpha abuse guard).
# Sliding window: at most MAX_POSTS accepted POST /atom attempts per WINDOW per IP.
RATE_LIMIT_WINDOW_SECONDS = int(
    os.environ.get("PUNKTO_RATE_LIMIT_WINDOW_SECONDS", "60")
)
RATE_LIMIT_MAX_POSTS = int(os.environ.get("PUNKTO_RATE_LIMIT_MAX_POSTS", "30"))

DEFAULT_ATOM_LOG_PATH = "/data/atoms.log.jsonl"
ATOM_LOG_FILE = os.environ.get("PUNKTO_ATOM_LOG_PATH", DEFAULT_ATOM_LOG_PATH)
SYNC_STATE_FILE = os.path.join(DATA_DIR, "sync_state.json")

MAX_BODY_BYTES = 65_536  # 64 KB
PUNKTO_RE = re.compile(r"^p:[0-9a-z]{12}(-[a-zA-Z0-9]+)?$")
ATOM_ID_RE = re.compile(r"^[0-9a-f]{64}$")
RELATION_VALUES = {"root", "reply"}
ROOT_REPLY_ID_MAX_BYTES = 256
LOCATION_SOURCE_VALUES = {"root"}
LOCATION_IDENTITY_FIELDS = (
    "punkto",
    "lat",
    "lon",
    "altitude_m",
    "alt",
    "z",
    "floor",
    "level",
)

# Reasonable timestamp window: 2020-01-01 .. now+1day
_T_MIN = 1_577_836_800_000  # 2020-01-01T00:00:00Z

DEFAULT_NODE_CONFIG_PATH = "/config/punkto-node.yml"
NODE_CONFIG_PATH = os.environ.get("PUNKTO_NODE_CONFIG", DEFAULT_NODE_CONFIG_PATH)
DEFAULT_NODE_KEY_PATH = "/data/node-key.json"
NODE_KEY_PATH = os.environ.get("PUNKTO_NODE_KEY", DEFAULT_NODE_KEY_PATH)

DEFAULT_NODE_CONFIG: Dict[str, Any] = {
    "node": {
        "name": "Punkto Node",
        "public_url": "",
        "type": "flow",
        "operator_contact": "",
        "description": "",
    },
    "admin": {
        "enabled": False,
        "public_admin_enabled": False,
    },
    "serving": {
        "serve_recent_hours": 24,
        "serve_pinned": True,
        "serve_archive": False,
        "pinned_atoms": [],
    },
    "acceptance": {
        "accept_recent_hours": 24,
        "trusted_backfill_nodes": [],
    },
    "serving_policy": {
        "serve_recent": True,
        "recent_days": 30,
        "serve_genesis": True,
        "serve_pinned": True,
        "serve_verified_only": False,
        "allow_unsigned": True,
        "require_sig": False,
        "archive_enabled": False,
    },
    "bootstrap": {
        "seed_nodes": list(PEERS),
        "peer_discovery_enabled": True,
        "allow_user_added_peers": True,
        "blocked_nodes": [],
    },
    "moderation": {
        "blocked_authors": [],
        "blocked_punktis": [],
        "blocked_keywords": [],
    },
    "retention": {
        "stale_after_days": 30,
        "delete_after_days": None,
        "keep_pinned_forever": True,
        "keep_genesis_forever": True,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def _clean_node_config(candidate: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _deep_merge(DEFAULT_NODE_CONFIG, candidate)

    if not isinstance(cfg.get("node"), dict):
        cfg["node"] = deepcopy(DEFAULT_NODE_CONFIG["node"])
    if not isinstance(cfg.get("admin"), dict):
        cfg["admin"] = deepcopy(DEFAULT_NODE_CONFIG["admin"])
    if not isinstance(cfg.get("serving"), dict):
        cfg["serving"] = deepcopy(DEFAULT_NODE_CONFIG["serving"])
    if not isinstance(cfg.get("acceptance"), dict):
        cfg["acceptance"] = deepcopy(DEFAULT_NODE_CONFIG["acceptance"])
    if not isinstance(cfg.get("serving_policy"), dict):
        cfg["serving_policy"] = deepcopy(DEFAULT_NODE_CONFIG["serving_policy"])
    if not isinstance(cfg.get("bootstrap"), dict):
        cfg["bootstrap"] = deepcopy(DEFAULT_NODE_CONFIG["bootstrap"])
    if not isinstance(cfg.get("moderation"), dict):
        cfg["moderation"] = deepcopy(DEFAULT_NODE_CONFIG["moderation"])
    if not isinstance(cfg.get("retention"), dict):
        cfg["retention"] = deepcopy(DEFAULT_NODE_CONFIG["retention"])

    cfg["node"]["name"] = str(cfg["node"].get("name") or DEFAULT_NODE_CONFIG["node"]["name"])
    cfg["node"]["public_url"] = str(cfg["node"].get("public_url") or "")
    cfg["node"]["type"] = str(cfg["node"].get("type") or DEFAULT_NODE_CONFIG["node"]["type"])
    cfg["node"]["operator_contact"] = str(cfg["node"].get("operator_contact") or "")
    cfg["node"]["description"] = str(cfg["node"].get("description") or "")

    for section, keys in {
        "admin": ["enabled", "public_admin_enabled"],
        "serving": ["serve_pinned", "serve_archive"],
        "serving_policy": ["serve_recent", "serve_genesis", "serve_pinned", "serve_verified_only", "allow_unsigned", "require_sig", "archive_enabled"],
        "bootstrap": ["peer_discovery_enabled", "allow_user_added_peers"],
        "retention": ["keep_pinned_forever", "keep_genesis_forever"],
    }.items():
        for key in keys:
            cfg[section][key] = bool(cfg[section].get(key))

    for section, key, dflt in [
        ("serving", "serve_recent_hours", DEFAULT_NODE_CONFIG["serving"]["serve_recent_hours"]),
        ("acceptance", "accept_recent_hours", DEFAULT_NODE_CONFIG["acceptance"]["accept_recent_hours"]),
        ("serving_policy", "recent_days", DEFAULT_NODE_CONFIG["serving_policy"]["recent_days"]),
        ("retention", "stale_after_days", DEFAULT_NODE_CONFIG["retention"]["stale_after_days"]),
    ]:
        try:
            v = int(cfg[section].get(key, dflt))
            cfg[section][key] = v if v > 0 else dflt
        except (TypeError, ValueError):
            cfg[section][key] = dflt

    delete_after = cfg["retention"].get("delete_after_days")
    if delete_after is None or delete_after == "":
        cfg["retention"]["delete_after_days"] = None
    else:
        try:
            cfg["retention"]["delete_after_days"] = max(1, int(delete_after))
        except (TypeError, ValueError):
            cfg["retention"]["delete_after_days"] = None

    for section, key in [("serving", "pinned_atoms"), ("acceptance", "trusted_backfill_nodes"), ("bootstrap", "seed_nodes"), ("bootstrap", "blocked_nodes"), ("moderation", "blocked_authors"), ("moderation", "blocked_punktis"), ("moderation", "blocked_keywords")]:
        value = cfg[section].get(key, [])
        cfg[section][key] = [str(x).strip() for x in value if str(x).strip()] if isinstance(value, list) else []

    return cfg


def load_node_config(path: str) -> Tuple[Dict[str, Any], bool, str]:
    config_path = path or DEFAULT_NODE_CONFIG_PATH
    if not os.path.exists(config_path):
        log(f"node config missing at {config_path}; using safe defaults")
        return _clean_node_config({}), False, config_path

    if yaml is None:
        log(f"node config present at {config_path} but PyYAML is unavailable; using safe defaults")
        return _clean_node_config({}), False, config_path

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            parsed = yaml.safe_load(f)
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            log(f"node config at {config_path} is not a mapping; using safe defaults")
            return _clean_node_config({}), False, config_path
        log(f"node config loaded from {config_path}")
        return _clean_node_config(parsed), True, config_path
    except Exception as exc:
        log(f"node config parse error at {config_path}: {exc}; using safe defaults")
        return _clean_node_config({}), False, config_path


NODE_CONFIG: Dict[str, Any] = {}
NODE_CONFIG_LOADED = False
NODE_CONFIG_PATH_USED = NODE_CONFIG_PATH
NODE_IDENTITY: Dict[str, Any] = {}
NODE_IDENTITY_LOADED = False
NODE_IDENTITY_PATH_USED = NODE_KEY_PATH
NODE_IDENTITY_CREATED_NOW = False


def _list_strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]




def _int_config(section: str, key: str, default: int) -> int:
    value = NODE_CONFIG.get(section, {}).get(key) if isinstance(NODE_CONFIG.get(section), dict) else default
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _normalize_node_url(url: Any) -> str:
    return str(url or "").strip().rstrip("/")


def _serving_policy() -> Dict[str, Any]:
    serving = NODE_CONFIG.get("serving") if isinstance(NODE_CONFIG.get("serving"), dict) else {}
    serving_policy = NODE_CONFIG.get("serving_policy") if isinstance(NODE_CONFIG.get("serving_policy"), dict) else {}
    return {
        "serve_recent_hours": _int_config("serving", "serve_recent_hours", 24),
        "serve_pinned": bool(serving.get("serve_pinned", serving_policy.get("serve_pinned", True))),
        "serve_archive": bool(serving.get("serve_archive", serving.get("archive_enabled", serving_policy.get("archive_enabled", False)))),
        "pinned_atoms": _list_strings(serving.get("pinned_atoms")),
    }


def _acceptance_policy() -> Dict[str, Any]:
    acceptance = NODE_CONFIG.get("acceptance") if isinstance(NODE_CONFIG.get("acceptance"), dict) else {}
    return {
        "accept_recent_hours": _int_config("acceptance", "accept_recent_hours", 24),
        "trusted_backfill_nodes": [
            _normalize_node_url(url) for url in _list_strings(acceptance.get("trusted_backfill_nodes"))
        ],
    }


def _is_trusted_backfill_peer(peer: str) -> bool:
    normalized = _normalize_node_url(peer)
    return bool(normalized and normalized in set(_acceptance_policy()["trusted_backfill_nodes"]))


def _atom_id_value(atom: Dict[str, Any]) -> str:
    existing = atom.get("atom_id")
    if isinstance(existing, str) and ATOM_ID_RE.match(existing):
        return existing
    return compute_atom_id(atom)


def _is_pinned_atom(atom: Dict[str, Any]) -> bool:
    policy = _serving_policy()
    if not policy["serve_pinned"]:
        return False
    return _atom_id_value(atom) in set(policy["pinned_atoms"])


def _atom_within_recent_window(atom: Dict[str, Any], hours: int) -> bool:
    t = atom.get("t")
    if not isinstance(t, int):
        return False
    return t >= _now_ms() - (max(1, int(hours)) * 3600 * 1000)


def atom_is_publicly_served(atom: Dict[str, Any]) -> bool:
    policy = _serving_policy()
    if policy["serve_archive"]:
        return True
    if _is_pinned_atom(atom):
        return True
    return _atom_within_recent_window(atom, int(policy["serve_recent_hours"]))


def validate_acceptance_policy(atom: Dict[str, Any], *, trusted_backfill: bool = False) -> Tuple[bool, Optional[Dict[str, Any]]]:
    if trusted_backfill:
        return True, None
    policy = _acceptance_policy()
    max_age_hours = int(policy["accept_recent_hours"])
    if not _atom_within_recent_window(atom, max_age_hours):
        return False, {
            "ok": False,
            "error": "atom_too_old",
            "message": f"field 't' is older than the live acceptance window ({max_age_hours}h)",
            "max_age_hours": max_age_hours,
        }
    return True, None


POLICY_STATS_LOCK = threading.Lock()
POLICY_STATS: Dict[str, int] = {
    "old_rejected": 0,
    "backfilled_accepted": 0,
}


def _inc_policy_stat(key: str) -> None:
    with POLICY_STATS_LOCK:
        POLICY_STATS[key] = int(POLICY_STATS.get(key, 0)) + 1


def _policy_stats_snapshot() -> Dict[str, int]:
    with POLICY_STATS_LOCK:
        return dict(POLICY_STATS)


def _safe_public_config() -> Dict[str, Any]:
    core = NODE_CONFIG.get("core") if isinstance(NODE_CONFIG.get("core"), dict) else {}
    node = NODE_CONFIG.get("node") if isinstance(NODE_CONFIG.get("node"), dict) else {}
    operator = NODE_CONFIG.get("operator") if isinstance(NODE_CONFIG.get("operator"), dict) else {}
    roles = NODE_CONFIG.get("roles") if isinstance(NODE_CONFIG.get("roles"), dict) else {}
    network = NODE_CONFIG.get("network") if isinstance(NODE_CONFIG.get("network"), dict) else {}
    serving = NODE_CONFIG.get("serving") if isinstance(NODE_CONFIG.get("serving"), dict) else {}
    serving_policy = NODE_CONFIG.get("serving_policy") if isinstance(NODE_CONFIG.get("serving_policy"), dict) else {}
    bootstrap = NODE_CONFIG.get("bootstrap") if isinstance(NODE_CONFIG.get("bootstrap"), dict) else {}

    public_url = str(core.get("public_url") or node.get("public_url") or "")
    seed_nodes = _list_strings(network.get("seed_nodes")) or _list_strings(bootstrap.get("seed_nodes")) or list(PEERS)
    known_nodes = _list_strings(network.get("known_nodes"))
    hostnames = _list_strings(core.get("hostnames")) or _list_strings(node.get("hostnames"))

    return {
        "node_name": str(operator.get("node_name") or core.get("node_name") or core.get("name") or node.get("name") or NODE_NAME),
        "public_url": public_url,
        "domain_dns": str(core.get("domain_dns") or core.get("domain") or node.get("domain_dns") or ""),
        "hostnames": hostnames,
        "roles": {
            "web": bool(roles.get("web", True)),
            "relay": bool(roles.get("relay", True)),
            "db_sharing": bool(roles.get("db_sharing", True)),
        },
        "serving": {
            "serve_recent": bool(serving.get("serve_recent", serving_policy.get("serve_recent", True))),
            "serve_recent_hours": _serving_policy()["serve_recent_hours"],
            "serve_pinned": _serving_policy()["serve_pinned"],
            "serve_archive": _serving_policy()["serve_archive"],
            "pinned_atom_count": len(_serving_policy()["pinned_atoms"]),
        },
        "acceptance": {
            "accept_recent_hours": _acceptance_policy()["accept_recent_hours"],
            "trusted_backfill_nodes_count": len(_acceptance_policy()["trusted_backfill_nodes"]),
        },
        "seed_nodes": seed_nodes,
        "known_nodes": known_nodes,
    }


def _node_info_payload(buffer: "Buffer", sync_state: Optional["SyncState"] = None) -> Dict[str, Any]:
    public_cfg = _safe_public_config()
    known_nodes = list(public_cfg["known_nodes"])
    if sync_state is not None:
        known_nodes.extend(sync_state.peers())
    known_nodes = sorted(set(str(url).rstrip("/") for url in known_nodes if str(url).strip()))

    return {
        "ok": True,
        "software": {
            "name": "Punkto",
            "version": VERSION,
            "runtime": "relay",
        },
        "node": {
            "name": public_cfg["node_name"],
            "public_url": public_cfg["public_url"],
            "domain_dns": public_cfg["domain_dns"],
            "hostnames": public_cfg["hostnames"],
            "fingerprint": NODE_IDENTITY.get("fingerprint", ""),
            "key_alg": NODE_IDENTITY.get("key_alg", ""),
            "identity_loaded": NODE_IDENTITY_LOADED,
            "identity_created_at": NODE_IDENTITY.get("created_at"),
        },
        "roles": public_cfg["roles"],
        "serving": public_cfg["serving"],
        "acceptance": public_cfg["acceptance"],
        "network": {
            "seed_nodes": public_cfg["seed_nodes"],
            "known_nodes": known_nodes,
        },
        "storage": {
            "mode": "append_only_log",
            "log_path": DEFAULT_ATOM_LOG_PATH,
            "log_loaded": buffer.log_loaded(),
            "corrupt_lines": buffer.corrupt_lines(),
        },
        "stats": {
            "atom_count": buffer.size(),
            "buffer_size": buffer.size(),
            "oldest_t": buffer.oldest_t(),
            "newest_t": buffer.newest_t(),
            "old_rejected_count": _policy_stats_snapshot().get("old_rejected", 0),
            "backfilled_accepted_count": _policy_stats_snapshot().get("backfilled_accepted", 0),
        },
        "config": {
            "loaded": NODE_CONFIG_LOADED,
            "path": DEFAULT_NODE_CONFIG_PATH if NODE_CONFIG_LOADED else None,
        },
        "health": {
            "status": "ok",
            "node": NODE_NAME,
        },
        # Backwards-compatible public aliases for the earlier /node/info shape.
        "node_fingerprint": NODE_IDENTITY.get("fingerprint", ""),
        "node_key_alg": NODE_IDENTITY.get("key_alg", ""),
        "node_identity_loaded": NODE_IDENTITY_LOADED,
        "node_identity_created_at": NODE_IDENTITY.get("created_at"),
        "config_loaded": NODE_CONFIG_LOADED,
    }


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def log(msg: str) -> None:
    sys.stdout.write(f"[RELAY] [{_ts()}] {msg}\n")
    sys.stdout.flush()


NODE_CONFIG, NODE_CONFIG_LOADED, NODE_CONFIG_PATH_USED = load_node_config(NODE_CONFIG_PATH)


def _iso_utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _node_fingerprint(public_key: str) -> str:
    digest = hashlib.sha256(public_key.encode("utf-8")).hexdigest()
    return f"node:{digest[:12]}"


def _new_node_identity() -> Dict[str, Any]:
    # Relay currently has no Ed25519 dependency. Keep a stable local-only
    # identity secret with deterministic public identity + fingerprint.
    private_key = secrets.token_hex(32)
    public_key = hashlib.sha256(private_key.encode("utf-8")).hexdigest()
    return {
        "version": 1,
        "key_alg": "sha256-secret-v1",
        "created_at": _iso_utc_now(),
        "public_key": public_key,
        "private_key": private_key,
        "fingerprint": _node_fingerprint(public_key),
    }


def _validate_node_identity(data: Any, path: str) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"node identity file {path} must contain a JSON object")
    required = ["version", "key_alg", "created_at", "public_key", "private_key", "fingerprint"]
    for key in required:
        if key not in data:
            raise ValueError(f"node identity file {path} missing required field {key!r}")
    if int(data["version"]) != 1:
        raise ValueError(f"node identity file {path} has unsupported version {data['version']!r}")
    if not isinstance(data["public_key"], str) or not data["public_key"]:
        raise ValueError(f"node identity file {path} has invalid public_key")
    if not isinstance(data["private_key"], str) or not data["private_key"]:
        raise ValueError(f"node identity file {path} has invalid private_key")
    expected_public = hashlib.sha256(data["private_key"].encode("utf-8")).hexdigest()
    if data["public_key"] != expected_public:
        raise ValueError(f"node identity file {path} failed integrity validation")
    expected_fingerprint = _node_fingerprint(data["public_key"])
    if data["fingerprint"] != expected_fingerprint:
        raise ValueError(f"node identity file {path} has mismatched fingerprint")
    return data


def load_or_create_node_identity(path: str) -> Tuple[Dict[str, Any], bool, str, bool]:
    key_path = path or DEFAULT_NODE_KEY_PATH
    key_dir = os.path.dirname(key_path) or "."
    os.makedirs(key_dir, exist_ok=True)
    if os.path.exists(key_path):
        try:
            with open(key_path, "r", encoding="utf-8") as f:
                parsed = json.load(f)
            identity = _validate_node_identity(parsed, key_path)
            log(f"Loaded existing node identity node_fingerprint={identity['fingerprint']} path={key_path}")
            return identity, True, key_path, False
        except Exception as exc:
            log(f"ERROR: invalid node identity file at {key_path}: {exc}")
            raise SystemExit(1) from exc

    identity = _new_node_identity()
    try:
        with open(key_path, "x", encoding="utf-8") as f:
            json.dump(identity, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except Exception as exc:
        log(f"ERROR: cannot persist node identity to {key_path}: {exc}")
        raise SystemExit(1) from exc
    log(f"Created new node identity node_fingerprint={identity['fingerprint']} path={key_path}")
    return identity, True, key_path, True


NODE_IDENTITY, NODE_IDENTITY_LOADED, NODE_IDENTITY_PATH_USED, NODE_IDENTITY_CREATED_NOW = load_or_create_node_identity(NODE_KEY_PATH)


# ---------------------------------------------------------------------------
# Atom helpers
# ---------------------------------------------------------------------------


def canonical_bytes(atom: Dict[str, Any]) -> bytes:
    """Canonical JSON bytes for atom_id: sorted keys, no whitespace, UTF-8, no `sig`."""
    payload = {k: v for k, v in atom.items() if k != "sig"}
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def compute_atom_id(atom: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(atom)).hexdigest()


# ---------------------------------------------------------------------------
# Signature enforcement (PUNKTO_REQUIRE_SIG)
# ---------------------------------------------------------------------------

def require_signature_enabled() -> bool:
    """Return True if relay is configured to require atom signatures."""
    sp = NODE_CONFIG.get("serving_policy") if isinstance(NODE_CONFIG.get("serving_policy"), dict) else {}
    env_val = os.environ.get("PUNKTO_REQUIRE_SIG", "").strip().lower()
    if env_val in ("true", "1", "yes"):
        return True
    if env_val in ("false", "0", "no"):
        return False
    return bool(sp.get("require_sig", False))


def canonical_atom_for_signing(atom: Dict[str, Any]) -> bytes:
    """Canonical bytes for signing and atom_id — identical function.

    Excludes ONLY 'sig'. pubkey IS included when present.
    This matches the authoritative spec in punkto.sync.md and punkto.identity.md:
      canonical_bytes = UTF-8(json_sorted_no_whitespace(atom_without_sig))
    Signing and atom_id share the same canonical-bytes definition.

    Signing workflow:
      1. Build atom payload (including pubkey if signing).
      2. Call canonical_atom_for_signing(atom) — sig excluded, pubkey included.
      3. Sign the result.
      4. Add sig field to atom.
    """
    return canonical_bytes(atom)


def verify_atom_signature(atom: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Verify Ed25519 signature on atom. Returns None on success, error dict on failure."""
    if not _HAS_CRYPTO:
        return {"error": "sig_unsupported", "message": "cryptography library not installed"}
    sig_b64 = atom.get("sig")
    pubkey_b64 = atom.get("pubkey")
    if not sig_b64:
        return {"error": "missing_sig", "message": "atom missing required field 'sig'"}
    if not pubkey_b64:
        return {"error": "missing_pubkey", "message": "atom missing required field 'pubkey'"}
    try:
        sig_bytes = _base64.b64decode(sig_b64, validate=True)
        pubkey_bytes = _base64.b64decode(pubkey_b64, validate=True)
        pub_key = Ed25519PublicKey.from_public_bytes(pubkey_bytes)
        pub_key.verify(sig_bytes, canonical_atom_for_signing(atom))
        return None
    except (ValueError, TypeError) as exc:
        return {"error": "invalid_sig_encoding", "message": f"sig/pubkey decode error: {exc}"}
    except InvalidSignature:
        return {"error": "invalid_sig", "message": "signature does not match atom content"}
    except Exception as exc:  # noqa: BLE001
        return {"error": "sig_error", "message": f"signature check failed: {exc}"}


def validate_signature_policy(atom: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]]]:
    """Return (True, None) if atom passes signature policy, else (False, error_dict)."""
    if not require_signature_enabled():
        return True, None
    err = verify_atom_signature(atom)
    if err is not None:
        return False, {"ok": False, **err}
    return True, None


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _bounded_optional_string(
    atom: Dict[str, Any], field: str
) -> Optional[Dict[str, str]]:
    value = atom.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        return {
            "error": f"invalid_{field}",
            "message": f"field '{field}' must be a string when present",
        }
    if len(value.encode("utf-8")) > ROOT_REPLY_ID_MAX_BYTES:
        return {
            "error": f"invalid_{field}",
            "message": f"field '{field}' must be at most {ROOT_REPLY_ID_MAX_BYTES} bytes",
        }
    return None


def atom_relation(atom: Dict[str, Any]) -> str:
    """Return the effective relation implied by relation/parent_id metadata."""
    parent_id = atom.get("parent_id")
    if not _is_blank(parent_id):
        return "reply"
    relation = atom.get("relation")
    if relation == "reply":
        return "reply"
    return "root"


def validate_atom(atom: Any) -> Tuple[bool, Optional[Dict[str, str]]]:
    """Return (ok, error_dict). Required: punkto, t. Other fields are advisory."""
    if not isinstance(atom, dict):
        return False, {"error": "invalid_json", "message": "atom must be a JSON object"}
    p = atom.get("punkto")
    if not isinstance(p, str) or not p.startswith("p:"):
        return False, {
            "error": "invalid_punkto",
            "message": "field 'punkto' must be a string starting with 'p:'",
        }
    if not PUNKTO_RE.match(p):
        return False, {
            "error": "invalid_punkto",
            "message": (
                "field 'punkto' must match p:[0-9a-z]{12}(-[a-zA-Z0-9]+)? "
                f"\u2014 got {p!r}"
            ),
        }
    t = atom.get("t")
    if isinstance(t, bool) or not isinstance(t, int):
        return False, {
            "error": "invalid_timestamp",
            "message": "field 't' must be an integer (Unix ms)",
        }
    t_max = _now_ms() + 86_400_000
    if not (_T_MIN <= t <= t_max):
        return False, {
            "error": "invalid_timestamp",
            "message": (
                f"field 't' must be between {_T_MIN} and now+1day (got {t})"
            ),
        }

    relation = atom.get("relation")
    if relation is not None:
        if not isinstance(relation, str) or relation not in RELATION_VALUES:
            return False, {
                "error": "invalid_relation",
                "message": "field 'relation' must be either 'root' or 'reply' when present",
            }

    for field in ("parent_id", "root_id"):
        err = _bounded_optional_string(atom, field)
        if err is not None:
            return False, err

    parent_id = atom.get("parent_id")
    has_parent = not _is_blank(parent_id)
    if relation == "reply" and not has_parent:
        return False, {
            "error": "invalid_parent_id",
            "message": "field 'parent_id' is required when relation is 'reply'",
        }
    if relation == "root" and has_parent:
        return False, {
            "error": "invalid_parent_id",
            "message": "field 'parent_id' must be absent, null, or empty when relation is 'root'",
        }

    location_lock = atom.get("location_lock")
    if location_lock is not None and not isinstance(location_lock, bool):
        return False, {
            "error": "invalid_location_lock",
            "message": "field 'location_lock' must be a boolean when present",
        }
    if (
        atom_relation(atom) == "reply"
        and location_lock is not None
        and location_lock is not True
    ):
        return False, {
            "error": "invalid_location_lock",
            "message": "field 'location_lock' must be true for replies when present",
        }

    location_source = atom.get("location_source")
    if location_source is not None:
        if (
            not isinstance(location_source, str)
            or location_source not in LOCATION_SOURCE_VALUES
        ):
            return False, {
                "error": "invalid_location_source",
                "message": "field 'location_source' must be 'root' when present",
            }

    return True, None


def validate_reply_location(
    atom: Dict[str, Any], parent: Dict[str, Any]
) -> Tuple[bool, Optional[Dict[str, str]]]:
    """Require a known reply parent/root to share Punkto's exact location identity."""
    mismatched_fields = []
    for field in LOCATION_IDENTITY_FIELDS:
        if field in atom or field in parent:
            if atom.get(field) != parent.get(field):
                mismatched_fields.append(field)
    if mismatched_fields:
        return False, {
            "error": "reply_location_mismatch",
            "message": (
                "reply location must exactly match the known parent/root location "
                f"({', '.join(mismatched_fields)})"
            ),
        }
    return True, None


def _html_escape(s: Any) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _html_value(value: Any, empty: str = "unknown") -> str:
    if value is None:
        return _html_escape(empty)
    if isinstance(value, bool):
        return "yes" if value else "no"
    text = str(value).strip()
    return _html_escape(text if text else empty)


def _format_utc_ms(value: Any) -> str:
    if not isinstance(value, int):
        return "not available"
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(value / 1000))
    except (OverflowError, OSError, ValueError):
        return "not available"


def _format_duration(seconds: float) -> str:
    seconds_i = max(0, int(seconds))
    days, rem = divmod(seconds_i, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    if minutes or parts:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _status_row(label: str, value: Any, *, mono: bool = False, multiline: bool = False) -> str:
    classes = []
    if mono:
        classes.append("mono")
    if multiline:
        classes.append("multiline")
    class_attr = f' class="{" ".join(classes)}"' if classes else ""
    return (
        "<tr>"
        f"<th scope=\"row\">{_html_escape(label)}</th>"
        f"<td{class_attr}>{_html_value(value)}</td>"
        "</tr>"
    )


def _status_html_row(
    label: str, value_html: str, *, mono: bool = False, multiline: bool = False
) -> str:
    classes = []
    if mono:
        classes.append("mono")
    if multiline:
        classes.append("multiline")
    class_attr = f' class="{" ".join(classes)}"' if classes else ""
    return (
        "<tr>"
        f"<th scope=\"row\">{_html_escape(label)}</th>"
        f"<td{class_attr}>{value_html}</td>"
        "</tr>"
    )


def _status_bool_rows(values: Any) -> str:
    if not isinstance(values, dict) or not values:
        return "unknown"
    return "\n".join(
        f"{key}: {'yes' if value is True else 'no' if value is False else 'unknown'}"
        for key, value in sorted(values.items())
    )


def _status_list(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "none"
    return "\n".join(str(item) for item in values if str(item).strip()) or "none"


def _status_link(path: str, label: Optional[str] = None) -> str:
    safe_path = _html_escape(path)
    safe_label = _html_escape(label or path)
    return f'<a href="{safe_path}" class="mono">{safe_label}</a>'


def _status_serving_summary(serving: Any) -> str:
    if not isinstance(serving, dict) or not serving:
        return "unknown"
    labels = {
        "serve_recent": "recent",
        "serve_pinned": "pinned",
        "serve_archive": "archive",
    }
    rows = []
    for key in ("serve_recent", "serve_pinned", "serve_archive"):
        value = serving.get(key)
        label = labels[key]
        state = (
            "enabled"
            if value is True
            else "disabled"
            if value is False
            else "unknown"
        )
        rows.append(f"{label}: {state}")
    rows.append(f"recent_hours: {serving.get('serve_recent_hours', 'unknown')}")
    rows.append(f"pinned_atom_count: {serving.get('pinned_atom_count', 'unknown')}")
    return "\n".join(rows)


def _recent_atom_preview_rows(atoms: List[Dict[str, Any]]) -> str:
    if not atoms:
        return '<tr><td colspan="5" class="muted">No public atoms in the recent buffer.</td></tr>'
    rows = []
    for atom in atoms[:5]:
        atom_id = str(atom.get("atom_id") or compute_atom_id(atom))
        relation = atom.get("relation") or "root"
        category = atom.get("category") or atom.get("type") or atom.get("k") or "unknown"
        timestamp = _format_utc_ms(atom.get("t"))
        rows.append(
            "<tr>"
            f'<td class="mono">{_html_escape(atom_id[:12])}</td>'
            f"<td>{_html_value(relation)}</td>"
            f"<td>{_html_value(category)}</td>"
            f"<td>{_html_value(timestamp)}</td>"
            f'<td class="mono">{_html_value(atom.get("punkto"))}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def render_status_page(buffer: "Buffer", sync_state: Optional["SyncState"] = None) -> str:
    """Render the public, read-only human node status page.

    The page intentionally uses the same public-safe data builder as /node/info,
    then formats that already-filtered payload as static HTML.
    """
    info = _node_info_payload(buffer, sync_state)
    software = info.get("software") if isinstance(info.get("software"), dict) else {}
    node = info.get("node") if isinstance(info.get("node"), dict) else {}
    network = info.get("network") if isinstance(info.get("network"), dict) else {}
    stats = info.get("stats") if isinstance(info.get("stats"), dict) else {}
    serving = info.get("serving") if isinstance(info.get("serving"), dict) else {}
    acceptance = info.get("acceptance") if isinstance(info.get("acceptance"), dict) else {}
    storage = info.get("storage") if isinstance(info.get("storage"), dict) else {}
    config = info.get("config") if isinstance(info.get("config"), dict) else {}
    health = info.get("health") if isinstance(info.get("health"), dict) else {}

    health_status = str(health.get("status") or "unknown")
    badge_label = "healthy" if health_status == "ok" else "degraded"
    recent_atoms = buffer.latest(5)
    recent_feed_size = len(buffer.latest(LATEST_LIMIT))
    seed_count = (
        len(network.get("seed_nodes"))
        if isinstance(network.get("seed_nodes"), list)
        else 0
    )
    known_peer_count = (
        len(network.get("known_nodes"))
        if isinstance(network.get("known_nodes"), list)
        else 0
    )
    roles = info.get("roles") if isinstance(info.get("roles"), dict) else {}
    current_time = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    uptime = _format_duration(time.time() - STARTED_AT)
    title = "Punkto Node Status"
    description = "Public, read-only status page for a Punkto node."

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html_escape(title)}</title>
<meta name="description" content="{_html_escape(description)}">
<style>
:root {{ color-scheme: dark; --bg:#071019; --panel:#0d1a27; --line:#24415c; --text:#eef7ff; --muted:#a9bed2; --good:#6ee7a8; --warn:#ffd166; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 32px 16px; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }}
main {{ max-width: 920px; margin: 0 auto; }}
header, section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 16px 50px rgba(0,0,0,.24); }}
h1 {{ margin: 0 0 8px; font-size: clamp(1.8rem, 4vw, 2.6rem); }}
h2 {{ margin: 0 0 12px; font-size: 1.1rem; }}
p {{ margin: 8px 0; color: var(--muted); }}
.badge {{ display: inline-flex; align-items: center; gap: 8px; margin-top: 12px; padding: 6px 10px; border-radius: 999px; border: 1px solid var(--line); color: var(--text); }}
.badge::before {{ content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--warn); }}
.badge.healthy::before {{ background: var(--good); }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 9px 0; border-top: 1px solid rgba(255,255,255,.08); vertical-align: top; }}
tr:first-child th, tr:first-child td {{ border-top: 0; }}
th {{ width: 34%; padding-right: 18px; text-align: left; color: var(--muted); font-weight: 600; }}
td {{ color: var(--text); word-break: break-word; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: .92em; }}
.multiline {{ white-space: pre-line; }}
.note {{ border-color: rgba(110,231,168,.35); }}
.muted {{ color: var(--muted); }}
a {{ color: #8bd3ff; }}
</style>
</head>
<body>
<main>
<header>
<h1>Punkto Node Status</h1>
<p>{_html_value(node.get("name"), "Punkto Node")}</p>
<p class="mono">{_html_value(node.get("public_url"), "public URL not configured")}</p>
<div class="badge {_html_escape(badge_label)}">{_html_escape(badge_label)}</div>
</header>

<section>
<h2>Node identity</h2>
<table>
{_status_row("Node name", node.get("name"))}
{_status_row("Public URL", node.get("public_url"), mono=True)}
{_status_row("domain_dns", node.get("domain_dns"), mono=True)}
{_status_row("Hostnames", _status_list(node.get("hostnames")), mono=True, multiline=True)}
{_status_row("Fingerprint", node.get("fingerprint"), mono=True)}
{_status_row("Identity loaded", node.get("identity_loaded"))}
</table>
</section>

<section>
<h2>Software</h2>
<table>
{_status_row("Punkto / relay version", f'{software.get("name", "Punkto")} {software.get("version", "unknown")}')}
{_status_row("Runtime", software.get("runtime"))}
{_status_row("Current time", current_time)}
{_status_row("Uptime", uptime)}
</table>
</section>

<section>
<h2>Configuration</h2>
<table>
{_status_row("Config loaded", config.get("loaded"))}
{_status_row("Config path", config.get("path") or "not available", mono=True)}
{_status_row("Roles", _status_bool_rows(info.get("roles")), multiline=True)}
{_status_row("Serving policy", _status_serving_summary(serving), multiline=True)}
{_status_row("Acceptance policy", f"accept_recent_hours: {acceptance.get('accept_recent_hours', 'unknown')}\ntrusted_backfill_nodes_count: {acceptance.get('trusted_backfill_nodes_count', 'unknown')}", multiline=True)}
</table>
</section>

<section>
<h2>Network</h2>
<table>
{_status_row("Seed nodes", _status_list(network.get("seed_nodes")), mono=True, multiline=True)}
{_status_row("Known nodes / peers", _status_list(network.get("known_nodes")), mono=True, multiline=True)}
</table>
</section>

<section>
<h2>Data flow</h2>
<p>Public atom data enters the node, is held in the recent feed buffer, and is exposed through public read-only endpoints for clients and readers.</p>
<table>
{_status_html_row("Public feed endpoint", _status_link("/feed"))}
{_status_html_row("Latest public recent endpoint", _status_link("/latest"))}
{_status_row("Live stream endpoint", "not enabled")}
{_status_html_row("Node info endpoint", _status_link("/node/info"))}
{_status_html_row("Health endpoint", _status_link("/health"))}
</table>
</section>

<section>
<h2>Public feed health</h2>
<table>
{_status_row("buffer_size", stats.get("buffer_size", "not available"))}
{_status_row("oldest_t", _format_utc_ms(stats.get("oldest_t")))}
{_status_row("newest_t", _format_utc_ms(stats.get("newest_t")))}
{_status_row("storage_mode", storage.get("mode", "not available"))}
{_status_row("atom_log_path", storage.get("log_path", "not available"), mono=True)}
{_status_row("atom_log_loaded", storage.get("log_loaded", "not available"))}
{_status_row("corrupt_lines", storage.get("corrupt_lines", "not available"))}
{_status_row("Known peer count", known_peer_count)}
{_status_row("Seed node count", seed_count)}
{_status_row("db_sharing role", "enabled" if roles.get("db_sharing") is True else "disabled" if roles.get("db_sharing") is False else "unknown")}
{_status_row("Serving policy", _status_serving_summary(serving), multiline=True)}
{_status_row("Acceptance policy", f"accept_recent_hours: {acceptance.get('accept_recent_hours', 'unknown')}\ntrusted_backfill_nodes_count: {acceptance.get('trusted_backfill_nodes_count', 'unknown')}", multiline=True)}
{_status_row("Old atoms rejected", stats.get("old_rejected_count", "not available"))}
{_status_row("Backfilled atoms accepted", stats.get("backfilled_accepted_count", "not available"))}
{_status_row("Recent feed size", recent_feed_size)}
</table>
</section>

<section>
<h2>Recent public atoms</h2>
<p>Newest five atoms only; this is a compact preview, not a raw database dump.</p>
<table>
<thead><tr><th scope="col">Atom id</th><th scope="col">Relation</th><th scope="col">Category/type</th><th scope="col">Timestamp</th><th scope="col">Punkto</th></tr></thead>
<tbody>
{_recent_atom_preview_rows(recent_atoms)}
</tbody>
</table>
</section>

<section>
<h2>Health</h2>
<table>
{_status_row("Status", health_status)}
</table>
</section>

<section class="note">
<h2>Safety note</h2>
<p>This page is public and read-only.</p>
<p>Configuration is changed by the node operator on the server.</p>
</section>
</main>
</body>
</html>
"""
    return html


# ---------------------------------------------------------------------------
# Buffer — in-memory rolling store backed by append-only atom log
# ---------------------------------------------------------------------------


class Buffer:
    """Thread-safe rolling buffer of atoms backed by durable JSONL storage.

    Invariants (under self._lock):
      - self._atoms is a bounded runtime list of dicts in append order.
      - self._atom_ids maps buffered atom_id -> index in _atoms.
      - self._seen_atom_ids contains every atom_id loaded from or appended to the log.
      - self.atoms_file is append-only durable truth: one accepted atom JSON object
        per line, never rewritten for runtime buffer pruning.
    """

    def __init__(self, atoms_file: str, max_atoms: int, max_hours: int) -> None:
        self.atoms_file = atoms_file
        self.max_atoms = max(1, int(max_atoms))
        self.max_age_ms = max(1, int(max_hours)) * 3600 * 1000
        self._lock = threading.Lock()
        self._atoms: List[Dict[str, Any]] = []
        self._atom_ids: Dict[str, int] = {}
        self._seen_atom_ids: set[str] = set()
        self._pruned_ever: bool = False
        self._log_loaded: bool = False
        self._corrupt_lines: int = 0
        # Track current append-only log size for /feed cursor compatibility.
        self._file_size: int = 0
        # Monotonically increasing log sequence number assigned to each accepted atom.
        # Distinct from the byte-offset cursor used by /feed?since= and peer sync.
        self._next_log_seq: int = 1

    # -- lifecycle -----------------------------------------------------------

    def load(self) -> None:
        os.makedirs(os.path.dirname(self.atoms_file) or ".", exist_ok=True)
        if not os.path.exists(self.atoms_file):
            with open(self.atoms_file, "ab"):
                pass
            with self._lock:
                self._file_size = 0
                self._log_loaded = True
                self._corrupt_lines = 0
            return

        with self._lock:
            self._atoms.clear()
            self._atom_ids.clear()
            self._seen_atom_ids.clear()
            self._corrupt_lines = 0
            with open(self.atoms_file, "rb") as f:
                data = f.read()
            self._file_size = len(data)
            for raw_line in data.decode("utf-8", errors="replace").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    self._corrupt_lines += 1
                    continue
                # Support both legacy raw atoms and new wrapped records.
                # New format: {"log_seq": N, "atom_id": "...", "atom": {...}}
                # Compat: also accept old 'cursor' key written before this rename.
                # Legacy format: raw atom dict (e.g. {"punkto": "...", "t": ...})
                if isinstance(record, dict) and "atom" in record and isinstance(record["atom"], dict):
                    atom = record["atom"]
                    stored_seq = record.get("log_seq") or record.get("cursor")
                    if isinstance(stored_seq, int) and stored_seq >= self._next_log_seq:
                        self._next_log_seq = stored_seq + 1
                else:
                    atom = record
                ok, _ = validate_atom(atom)
                if not ok:
                    continue
                aid = compute_atom_id(atom)
                if aid in self._seen_atom_ids:
                    continue
                self._seen_atom_ids.add(aid)
                self._atom_ids[aid] = len(self._atoms)
                self._atoms.append(atom)
            self._maybe_prune_locked()
            self._log_loaded = True
        log(
            f"buffer loaded: {len(self._atoms)} atoms, file_size={self._file_size}, "
            f"corrupt_lines={self._corrupt_lines}"
        )

    # -- read API ------------------------------------------------------------

    def size(self) -> int:
        with self._lock:
            return len(self._atoms)

    def log_loaded(self) -> bool:
        with self._lock:
            return self._log_loaded

    def corrupt_lines(self) -> int:
        with self._lock:
            return self._corrupt_lines

    def oldest_t(self) -> Optional[int]:
        with self._lock:
            if not self._atoms:
                return None
            vals = [a.get("t") for a in self._atoms if isinstance(a.get("t"), int)]
            return min(vals) if vals else None

    def newest_t(self) -> Optional[int]:
        with self._lock:
            if not self._atoms:
                return None
            vals = [a.get("t") for a in self._atoms if isinstance(a.get("t"), int)]
            return max(vals) if vals else None

    def has(self, atom_id: str) -> bool:
        with self._lock:
            return atom_id in self._seen_atom_ids

    def get_by_id(self, atom_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            idx = self._atom_ids.get(atom_id)
            if idx is None:
                return None
            return dict(self._atoms[idx])

    def latest_at_punkto(self, canonical: str) -> Optional[Dict[str, Any]]:
        """Return the most recent atom whose `punkto` field equals `canonical`."""
        with self._lock:
            atoms = [a for a in self._atoms if a.get("punkto") == canonical]
        if not atoms:
            return None
        atoms.sort(key=lambda a: int(a.get("t", 0)), reverse=True)
        return dict(atoms[0])

    def count_at_punkto(self, canonical: str) -> int:
        with self._lock:
            return sum(1 for a in self._atoms if a.get("punkto") == canonical)

    def latest(self, limit: int) -> List[Dict[str, Any]]:
        """Return up to `limit` publicly served atoms, newest first by `t`."""
        with self._lock:
            atoms = [a for a in self._atoms if atom_is_publicly_served(a)]
        atoms.sort(key=lambda a: int(a.get("t", 0)), reverse=True)
        return atoms[: max(0, int(limit))]

    def feed_since(
        self, cursor: int
    ) -> Tuple[List[Dict[str, Any]], int, bool]:
        """Return (atoms, new_cursor, buffer_underflow).

        The cursor is a **byte offset** in atoms.log.jsonl.
        This is the authoritative cursor model per punkto.sync.md §236.
        Each accepted atom is also assigned a sequential log_seq in the log
        wrapper, but that value is for record ordering only — it is distinct
        from the byte-offset cursor returned here and used by /feed?since= and
        peer sync. Runtime buffer pruning does not rewrite the durable log, so
        byte-offset cursors remain stable across relay restarts.
        """
        with self._lock:
            file_size = self._file_size
            pruned = self._pruned_ever
            atoms_snapshot = list(self._atoms)
        if cursor < 0:
            cursor = 0
        if cursor == 0:
            # Full public snapshot from start.
            return [a for a in atoms_snapshot if atom_is_publicly_served(a)], file_size, False
        if cursor > file_size:
            # Cursor past EOF - either client cached a stale offset or we pruned.
            return [], file_size, True
        if pruned:
            # The append-only log is not rewritten during runtime buffer pruning,
            # so mid-log offsets remain safe.
            pass
        # Safe to read from append-only log at offset.
        atoms_out: List[Dict[str, Any]] = []
        try:
            with open(self.atoms_file, "rb") as f:
                f.seek(cursor)
                data = f.read()
        except OSError:
            return [], file_size, True
        new_cursor = cursor + len(data)
        for raw_line in data.decode("utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Unwrap new format {cursor, atom_id, atom} or accept legacy raw atom.
            atom = record["atom"] if isinstance(record, dict) and "atom" in record and isinstance(record["atom"], dict) else record
            ok, _ = validate_atom(atom)
            if ok and atom_is_publicly_served(atom):
                atoms_out.append(atom)
        return atoms_out, new_cursor, False

    # -- write API -----------------------------------------------------------

    def append(self, atom: Dict[str, Any]) -> Tuple[str, bool]:
        """Append atom if new. Returns (atom_id, was_new)."""
        atom_id = compute_atom_id(atom)
        with self._lock:
            if atom_id in self._seen_atom_ids:
                return atom_id, False
            log_seq = self._next_log_seq
            self._next_log_seq += 1
            record = {"log_seq": log_seq, "atom_id": atom_id, "atom": atom}
            line = json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n"
            encoded = line.encode("utf-8")
            with open(self.atoms_file, "ab") as f:
                f.write(encoded)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            self._file_size += len(encoded)
            self._seen_atom_ids.add(atom_id)
            self._atom_ids[atom_id] = len(self._atoms)
            self._atoms.append(atom)
            self._maybe_prune_locked()
        return atom_id, True

    def _maybe_prune_locked(self) -> None:
        """Prune non-pinned runtime atoms if over count or age limits. Caller holds lock."""
        now = _now_ms()
        cutoff = now - self.max_age_ms
        over_count_to_drop = max(0, len(self._atoms) - self.max_atoms)
        dropped_for_count = 0
        keep_set: List[Dict[str, Any]] = []

        for atom in self._atoms:
            if _is_pinned_atom(atom):
                keep_set.append(atom)
                continue
            t = atom.get("t")
            if isinstance(t, int) and t < cutoff:
                continue
            if dropped_for_count < over_count_to_drop:
                dropped_for_count += 1
                continue
            keep_set.append(atom)

        if len(keep_set) != len(self._atoms):
            self._rewrite_locked(keep_set)

    def _rewrite_locked(self, new_atoms: List[Dict[str, Any]]) -> None:
        """Replace only runtime buffer contents. Caller holds lock.

        Despite the historical method name, this never rewrites the durable atom
        log. /data/atoms.log.jsonl remains append-only truth.
        """
        before = len(self._atoms)
        self._atoms = list(new_atoms)
        self._atom_ids = {compute_atom_id(a): i for i, a in enumerate(self._atoms)}
        self._pruned_ever = True
        log(
            f"runtime prune: {before} -> {len(self._atoms)} atoms (max_atoms={self.max_atoms}, "
            f"max_hours={self.max_age_ms // 3600000})"
        )


# ---------------------------------------------------------------------------
# Sync state — per-peer cursors and timestamps
# ---------------------------------------------------------------------------


class SyncState:
    """Persistent per-peer sync metadata."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._state: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._state = data
        except (OSError, json.JSONDecodeError):
            self._state = {}

    def _save_locked(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    def get(self, peer: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state.get(peer, {}))

    def peers(self) -> List[str]:
        with self._lock:
            return [str(peer) for peer in self._state.keys() if str(peer).strip()]

    def update(self, peer: str, **fields: Any) -> None:
        with self._lock:
            entry = self._state.setdefault(peer, {})
            entry.update(fields)
            try:
                self._save_locked()
            except OSError as exc:
                log(f"sync state save failed: {exc}")


# ---------------------------------------------------------------------------
# Peer sync loop
# ---------------------------------------------------------------------------


def _sync_one_peer(buffer: Buffer, sync_state: SyncState, peer: str) -> int:
    """Pull from one peer, append new atoms. Returns count of new atoms."""
    state = sync_state.get(peer)
    new_count = 0
    used_endpoint = "latest"

    # Try /latest first; fallback to /feed?since=<cursor>
    try:
        url = f"{peer}/latest"
        r = requests.get(url, timeout=15, headers={"User-Agent": f"PunktoRelay/{VERSION}"})
        if r.status_code == 200:
            payload = r.json()
            atoms = payload.get("atoms") or []
        else:
            atoms = None
    except Exception as exc:
        log(f"sync: peer {peer} /latest failed: {exc}")
        atoms = None

    if atoms is None:
        used_endpoint = "feed"
        cursor = int(state.get("cursor", 0))
        try:
            url = f"{peer}/feed?since={cursor}"
            r = requests.get(url, timeout=20, headers={"User-Agent": f"PunktoRelay/{VERSION}"})
            r.raise_for_status()
            payload = r.json()
            atoms = payload.get("atoms") or []
            new_cursor = int(payload.get("cursor", cursor))
            sync_state.update(peer, cursor=new_cursor)
        except Exception as exc:
            log(f"sync: peer {peer} /feed failed: {exc}")
            sync_state.update(peer, last_error=str(exc), last_attempt_at=_now_ms())
            return 0

    if not isinstance(atoms, list):
        return 0

    trusted_backfill = _is_trusted_backfill_peer(peer)
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        ok, _ = validate_atom(atom)
        if not ok:
            continue
        accepted_by_policy, _ = validate_acceptance_policy(atom, trusted_backfill=trusted_backfill)
        if not accepted_by_policy:
            _inc_policy_stat("old_rejected")
            continue
        if atom_relation(atom) == "reply":
            location_anchors = [
                anchor
                for anchor in (
                    buffer.get_by_id(str(atom.get("parent_id", ""))),
                    buffer.get_by_id(str(atom.get("root_id", ""))),
                )
                if anchor is not None
            ]
            location_ok = True
            for location_anchor in location_anchors:
                ok, _ = validate_reply_location(atom, location_anchor)
                if not ok:
                    location_ok = False
                    break
            if not location_ok:
                continue
        atom_id = compute_atom_id(atom)
        if buffer.has(atom_id):
            continue
        _, was_new = buffer.append(atom)
        if was_new:
            new_count += 1
            if trusted_backfill and not _atom_within_recent_window(atom, int(_acceptance_policy()["accept_recent_hours"])):
                _inc_policy_stat("backfilled_accepted")
            log(
                f"atom appended (sync<-{peer}): {atom.get('punkto')} "
                f"id={atom_id[:12]} buffer_size={buffer.size()}"
            )

    sync_state.update(
        peer,
        last_synced_at=_now_ms(),
        last_endpoint=used_endpoint,
        last_new_count=new_count,
        last_error=None,
    )
    return new_count


def _sync_loop(buffer: Buffer, sync_state: SyncState) -> None:
    time.sleep(2)
    while True:
        if PEERS:
            total_new = 0
            for peer in PEERS:
                try:
                    total_new += _sync_one_peer(buffer, sync_state, peer)
                except Exception as exc:
                    log(f"sync: unexpected error for {peer}: {exc}")
            if total_new:
                log(f"sync cycle: +{total_new} new atoms across {len(PEERS)} peers")
        time.sleep(SYNC_INTERVAL)


# ---------------------------------------------------------------------------
# Rate limiting (per-IP sliding window, in-memory)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Thread-safe in-memory per-IP sliding-window rate limiter.

    Allows at most ``max_events`` events per ``window_seconds`` per key (IP).
    State is process-local and resets on restart \u2014 a deliberately simple
    alpha abuse guard, not a distributed quota system.
    """

    def __init__(self, window_seconds: int, max_events: int) -> None:
        self.window_seconds = max(1, int(window_seconds))
        self.max_events = max(0, int(max_events))
        self._hits: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        """Record an attempt for ``key``; return False if over the limit."""
        if self.max_events <= 0:
            return True
        ts = time.time() if now is None else now
        cutoff = ts - self.window_seconds
        with self._lock:
            hits = [h for h in self._hits.get(key, ()) if h > cutoff]
            if len(hits) >= self.max_events:
                self._hits[key] = hits
                return False
            hits.append(ts)
            self._hits[key] = hits
            # Opportunistic cleanup so idle IPs don't accumulate forever.
            if len(self._hits) > 4096:
                for k in [k for k, v in self._hits.items()
                          if not any(h > cutoff for h in v)]:
                    self._hits.pop(k, None)
            return True


_post_rate_limiter = RateLimiter(RATE_LIMIT_WINDOW_SECONDS, RATE_LIMIT_MAX_POSTS)


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class RelayHandler(BaseHTTPRequestHandler):
    server_version = f"PunktoRelay/{VERSION}"
    sys_version = ""

    # Class-level injected resources, set in main()
    buffer: Buffer = None  # type: ignore[assignment]
    sync_state: SyncState = None  # type: ignore[assignment]

    def log_message(self, fmt: str, *args: Any) -> None:
        log(f"{self.address_string()} {fmt % args}")

    # -- helpers -------------------------------------------------------------


    def _send(self, code: int, body: bytes, content_type: str, extra: Optional[Dict[str, str]] = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_json(self, code: int, obj: Any) -> None:
        body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _send_text(self, code: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        self._send(code, text.encode("utf-8"), content_type)

    def _send_html(self, code: int, html: str) -> None:
        self._send_text(code, html, content_type="text/html; charset=utf-8")

    def _send_error_json(self, code: int, key: str, msg: str) -> None:
        self._send_json(code, {"error": key, "message": msg})

    def _cors(self) -> Dict[str, str]:
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }

    def _client_ip(self) -> str:
        """Best-effort client IP. Behind Caddy/CDN the real client is the
        first hop of X-Forwarded-For; fall back to the socket peer."""
        fwd = self.headers.get("X-Forwarded-For", "")
        if fwd:
            first = fwd.split(",")[0].strip()
            if first:
                return first
        try:
            return self.client_address[0]
        except (AttributeError, IndexError, TypeError):
            return "unknown"

    # -- methods -------------------------------------------------------------

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        for k, v in self._cors().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._send_json(
                200,
                {"status": "ok", "node": NODE_NAME, "buffer_size": self.buffer.size()},
            )
            return

        if path == "/info":
            self._send_json(200, {
                "node": NODE_NAME,
                "version": VERSION,
                "peers": PEERS,
                "buffer_size": self.buffer.size(),
                "buffer_oldest_t": self.buffer.oldest_t(),
                "buffer_atoms_max": BUFFER_ATOMS,
                "buffer_hours_max": BUFFER_HOURS,
                "latest_limit": LATEST_LIMIT,
                "sync_interval": SYNC_INTERVAL,
                "serving": _safe_public_config()["serving"],
                "acceptance": _safe_public_config()["acceptance"],
                "capabilities": ["write", "latest", "feed", "sync"],
            })
            return

        if path == "/node/info":
            self._send_json(200, _node_info_payload(self.buffer, self.sync_state))
            return

        if path == "/status":
            self._send_html(200, render_status_page(self.buffer, self.sync_state))
            return

        if path == "/latest":
            atoms = self.buffer.latest(LATEST_LIMIT)
            self._send_json(
                200,
                {
                    "atoms": atoms,
                    "served_at": _now_ms(),
                    "node": NODE_NAME,
                    "buffer_size": self.buffer.size(),
                    "buffer_oldest_t": self.buffer.oldest_t(),
                },
            )
            return

        if path == "/feed":
            try:
                cursor = int(qs.get("since", ["0"])[0])
            except (ValueError, IndexError):
                self._send_error_json(
                    400, "invalid_cursor", "'since' must be an integer byte offset"
                )
                return
            atoms, new_cursor, underflow = self.buffer.feed_since(cursor)
            resp: Dict[str, Any] = {"atoms": atoms, "cursor": new_cursor}
            if underflow:
                resp["buffer_underflow"] = True
            self._send_json(200, resp)
            return

        if path.startswith("/p/"):
            raw = unquote(path[len("/p/"):])
            self._render_atom_page(raw)
            return

        if path == "/":
            self._send_html(
                200,
                f"<!doctype html><meta charset=utf-8>"
                f"<title>punkto-relay {VERSION}</title>"
                f"<h1>punkto-relay {VERSION}</h1>"
                f"<p>Node: <code>{_html_escape(NODE_NAME)}</code></p>"
                f"<p>Buffer: {self.buffer.size()} atoms.</p>"
                f"<ul>"
                f"<li><a href='/latest'>/latest</a></li>"
                f"<li><a href='/info'>/info</a></li>"
                f"<li><a href='/health'>/health</a></li>"
                f"</ul>",
            )
            return

        self._send_error_json(404, "not_found", f"No endpoint: {path}")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path != "/atom":
            self._send_error_json(404, "not_found", f"No endpoint: {path}")
            return

        if not _post_rate_limiter.allow(self._client_ip()):
            _inc_policy_stat("rate_limited")
            self._send_json(429, {"ok": False, "error": "rate_limited"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_error_json(400, "invalid_length", "Content-Length is invalid")
            return
        if length <= 0:
            self._send_error_json(400, "empty_body", "Request body is empty")
            return
        if length > MAX_BODY_BYTES:
            self._send_error_json(
                413, "payload_too_large", f"Body exceeds {MAX_BODY_BYTES} bytes"
            )
            return

        try:
            raw = self.rfile.read(length)
            atom = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_error_json(400, "invalid_json", f"Could not parse JSON: {exc}")
            return

        ok, err = validate_atom(atom)
        if not ok:
            assert err is not None
            status = 422 if err["error"] == "invalid_punkto" else 400
            self._send_json(status, err)
            return

        accepted_by_policy, policy_err = validate_acceptance_policy(atom)
        if not accepted_by_policy:
            assert policy_err is not None
            _inc_policy_stat("old_rejected")
            self._send_json(422, policy_err)
            return

        sig_ok, sig_err = validate_signature_policy(atom)
        if not sig_ok:
            assert sig_err is not None
            self._send_json(403, sig_err)
            return

        if atom_relation(atom) == "reply":
            location_anchors = [
                anchor
                for anchor in (
                    self.buffer.get_by_id(str(atom.get("parent_id", ""))),
                    self.buffer.get_by_id(str(atom.get("root_id", ""))),
                )
                if anchor is not None
            ]
            for location_anchor in location_anchors:
                ok, err = validate_reply_location(atom, location_anchor)
                if not ok:
                    assert err is not None
                    self._send_json(400, err)
                    return

        atom_id, was_new = self.buffer.append(atom)
        if was_new:
            log(
                f"atom appended: {atom['punkto']} id={atom_id[:12]} "
                f"buffer_size={self.buffer.size()}"
            )
            self._send_json(
                201,
                {
                    "status": "accepted",
                    "atom_id": atom_id,
                    "punkto": atom["punkto"],
                },
            )
        else:
            self._send_json(
                200,
                {
                    "status": "duplicate",
                    "atom_id": atom_id,
                    "punkto": atom["punkto"],
                },
            )

    # -- /p/<atom_id> --------------------------------------------------------

    def _render_atom_page(self, raw: str) -> None:
        """Server-render an OG/Twitter card page for /p/<input>.

        Accepts two formats:
          1. 64-hex `atom_id` \u2014 lookup the exact atom in the buffer.
          2. Canonical Punkto string (`p:<spatial>[-<id>]` or bare `<spatial>[-<id>]`)
             \u2014 render the most recent atom at that location. Mirrors the legacy
             /p/ behavior of pwa/node.py so existing share URLs keep working.
        Anything else falls through to a generic page.
        """
        host = self.headers.get("Host", NODE_NAME)
        canonical_url = f"https://{host}/p/{_html_escape(raw)}"

        atom: Optional[Dict[str, Any]] = None
        lookup_kind = "unknown"        # 'atom_id' | 'canonical' | 'unknown'
        canonical_punkto: Optional[str] = None
        atom_count_at_punkto = 0

        if ATOM_ID_RE.match(raw):
            lookup_kind = "atom_id"
            atom = self.buffer.get_by_id(raw)
        else:
            # Canonical Punkto: accept either 'p:<spatial>...' or bare '<spatial>...'
            cand = raw if raw.startswith("p:") else f"p:{raw}"
            if PUNKTO_RE.match(cand):
                lookup_kind = "canonical"
                canonical_punkto = cand
                atom = self.buffer.latest_at_punkto(cand)
                atom_count_at_punkto = self.buffer.count_at_punkto(cand)

        if atom is not None:
            punkto = atom.get("punkto", "")
            text = str(atom.get("x") or "").strip()
            author = str(atom.get("f") or "anonymous").strip() or "anonymous"
            t_ms = int(atom.get("t") or 0)
            when = (
                time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(t_ms / 1000))
                if t_ms
                else ""
            )
            title_txt = text if text else f"{punkto}"
            if len(title_txt) > 60:
                title_txt = title_txt[:57] + "\u2026"
            title = f"{title_txt} \u00b7 Punkto"
            description = (
                text.replace("\n", " ")[:197] + ("\u2026" if len(text) > 200 else "")
                if text
                else "Append-only atom anchored to a real-world 3D coordinate."
            )
            identifier = raw if lookup_kind == "atom_id" else (canonical_punkto or punkto)
            ld = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": title,
                "description": description,
                "url": canonical_url,
                "identifier": identifier,
                "author": author,
                "dateCreated": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_ms / 1000)
                )
                if t_ms
                else None,
            }
            extra = ""
            if lookup_kind == "canonical" and atom_count_at_punkto > 1:
                extra = (
                    f"<p class=ids>{atom_count_at_punkto} atoms at this Punkto in the live buffer.</p>\n"
                )
            body_html = (
                f"<h1>{_html_escape(punkto)}</h1>\n"
                f"<p class=meta><strong>{_html_escape(author)}</strong> "
                f"<time>{_html_escape(when)}</time></p>\n"
                f"<p class=text>{_html_escape(text) or '<em>(no text)</em>'}</p>\n"
                f"<p class=ids><code>{_html_escape(identifier)}</code></p>\n"
                f"{extra}"
            )
        else:
            title = "Punkto"
            description = (
                "Append-only atoms anchored to real-world 3D coordinates. "
                "This atom may have aged out of the relay's live buffer."
            )
            ld = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "headline": title,
                "description": description,
                "url": canonical_url,
            }
            if lookup_kind == "canonical":
                msg = (
                    "<p>No atoms at this Punkto in the live buffer.</p>\n"
                    "<p>They may have aged out, or none have been written here yet.</p>\n"
                )
            elif lookup_kind == "atom_id":
                msg = (
                    "<p>This atom is not in the live buffer.</p>\n"
                    "<p>It may have aged out, or never existed on this relay.</p>\n"
                )
            else:
                msg = (
                    "<p>Unrecognized identifier.</p>\n"
                    "<p>Use either a 64-hex atom_id or a canonical Punkto string "
                    "like <code>p:u07qsuustfsh</code>.</p>\n"
                )
            body_html = "<h1>Punkto</h1>\n" + msg

        html = (
            "<!DOCTYPE html>\n"
            "<html lang=en><head>\n"
            "<meta charset=utf-8>\n"
            '<meta name=viewport content="width=device-width, initial-scale=1">\n'
            f"<title>{_html_escape(title)}</title>\n"
            f'<meta name=description content="{_html_escape(description)}">\n'
            f'<link rel=canonical href="{_html_escape(canonical_url)}">\n'
            f'<meta property="og:title" content="{_html_escape(title)}">\n'
            f'<meta property="og:description" content="{_html_escape(description)}">\n'
            f'<meta property="og:url" content="{_html_escape(canonical_url)}">\n'
            '<meta property="og:type" content="article">\n'
            '<meta property="og:site_name" content="Punkto">\n'
            '<meta name="twitter:card" content="summary">\n'
            f'<meta name="twitter:title" content="{_html_escape(title)}">\n'
            f'<meta name="twitter:description" content="{_html_escape(description)}">\n'
            '<script type="application/ld+json">'
            + json.dumps({k: v for k, v in ld.items() if v is not None}, separators=(",", ":"))
            + "</script>\n"
            "<style>body{font-family:system-ui,-apple-system,sans-serif;background:#0a0a0a;"
            "color:#d0d0d0;max-width:680px;margin:2em auto;padding:1em;line-height:1.5}"
            "a{color:#7df}h1{font-size:1.25em;color:#fff}.meta{color:#888;font-size:.9em}"
            ".text{background:#141414;border-left:3px solid #444;padding:.75em 1em;"
            "border-radius:4px;white-space:pre-wrap}.ids{color:#666;font-size:.8em}</style>\n"
            "</head><body>\n"
            f"{body_html}"
            '<p><a href="/">&larr; Map view</a></p>\n'
            "</body></html>\n"
        )
        self._send_html(200, html)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_server(
    host: str = HOST, port: int = PORT
) -> Tuple[ThreadingHTTPServer, Buffer, SyncState]:
    """Build (but do not start) the HTTP server. Used by tests too."""
    buffer = Buffer(ATOM_LOG_FILE, BUFFER_ATOMS, BUFFER_HOURS)
    buffer.load()
    sync_state = SyncState(SYNC_STATE_FILE)
    RelayHandler.buffer = buffer
    RelayHandler.sync_state = sync_state
    server = ThreadingHTTPServer((host, port), RelayHandler)
    return server, buffer, sync_state


def main() -> None:
    server, buffer, sync_state = build_server()
    log(f"punkto-relay {VERSION} listening on http://{HOST}:{PORT}")
    log(f"node={NODE_NAME} data_dir={DATA_DIR} atom_log={ATOM_LOG_FILE} buffer_atoms={BUFFER_ATOMS} buffer_hours={BUFFER_HOURS}")
    if PEERS:
        log(f"peers: {PEERS}")
        t = threading.Thread(target=_sync_loop, args=(buffer, sync_state), daemon=True, name="sync-loop")
        t.start()
    else:
        log("peers: (none configured)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("shutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
