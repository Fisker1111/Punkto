#!/usr/bin/env python3
"""
punkto-relay v0.1 — Flow TV relay node

Single-file Python 3 server. Stdlib + `requests`.

Roles:
  - Accept POST /atom from clients
  - Maintain a bounded rolling buffer of recent atoms (atoms.ndjson)
  - Serve GET /latest, GET /feed?since=<cursor>, GET /health, GET /info
  - Server-render GET /p/<atom_id> with OpenGraph meta for share cards
  - Pull from configured peers via /latest (fallback /feed) on a background thread

See ../punkto.relay.md for the spec.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote

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

ATOMS_FILE = os.path.join(DATA_DIR, "atoms.ndjson")
SYNC_STATE_FILE = os.path.join(DATA_DIR, "sync_state.json")

MAX_BODY_BYTES = 65_536  # 64 KB
PUNKTO_RE = re.compile(r"^p:[0-9a-z]{12}(-[a-zA-Z0-9]+)?$")
ATOM_ID_RE = re.compile(r"^[0-9a-f]{64}$")

# Reasonable timestamp window: 2020-01-01 .. now+1day
_T_MIN = 1_577_836_800_000  # 2020-01-01T00:00:00Z


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def log(msg: str) -> None:
    sys.stdout.write(f"[RELAY] [{_ts()}] {msg}\n")
    sys.stdout.flush()


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


# ---------------------------------------------------------------------------
# Buffer — in-memory rolling store backed by atoms.ndjson
# ---------------------------------------------------------------------------


class Buffer:
    """Thread-safe rolling buffer of atoms.

    Invariants (under self._lock):
      - self._atoms is a list of dicts in append order.
      - self._atom_ids maps atom_id -> index in _atoms.
      - atoms.ndjson on disk holds exactly the atoms in self._atoms, one per line.
    """

    def __init__(self, atoms_file: str, max_atoms: int, max_hours: int) -> None:
        self.atoms_file = atoms_file
        self.max_atoms = max(1, int(max_atoms))
        self.max_age_ms = max(1, int(max_hours)) * 3600 * 1000
        self._lock = threading.Lock()
        self._atoms: List[Dict[str, Any]] = []
        self._atom_ids: Dict[str, int] = {}
        self._pruned_ever: bool = False
        # Track current file size for /feed cursor compat
        self._file_size: int = 0

    # -- lifecycle -----------------------------------------------------------

    def load(self) -> None:
        os.makedirs(os.path.dirname(self.atoms_file) or ".", exist_ok=True)
        if not os.path.exists(self.atoms_file):
            with open(self.atoms_file, "a"):
                pass
            self._file_size = 0
            return
        with self._lock:
            self._atoms.clear()
            self._atom_ids.clear()
            with open(self.atoms_file, "rb") as f:
                data = f.read()
            self._file_size = len(data)
            for raw_line in data.decode("utf-8", errors="replace").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    atom = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ok, _ = validate_atom(atom)
                if not ok:
                    continue
                aid = compute_atom_id(atom)
                if aid in self._atom_ids:
                    continue
                self._atom_ids[aid] = len(self._atoms)
                self._atoms.append(atom)
        log(
            f"buffer loaded: {len(self._atoms)} atoms, file_size={self._file_size}"
        )

    # -- read API ------------------------------------------------------------

    def size(self) -> int:
        with self._lock:
            return len(self._atoms)

    def oldest_t(self) -> Optional[int]:
        with self._lock:
            if not self._atoms:
                return None
            return min(int(a.get("t", 0)) for a in self._atoms)

    def has(self, atom_id: str) -> bool:
        with self._lock:
            return atom_id in self._atom_ids

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
        """Return up to `limit` atoms, newest first by `t`."""
        with self._lock:
            atoms = list(self._atoms)
        atoms.sort(key=lambda a: int(a.get("t", 0)), reverse=True)
        return atoms[: max(0, int(limit))]

    def feed_since(
        self, cursor: int
    ) -> Tuple[List[Dict[str, Any]], int, bool]:
        """Return (atoms, new_cursor, buffer_underflow).

        The cursor is a byte offset in atoms.ndjson. After any prune, old
        cursors become unreliable; we report buffer_underflow so clients reset.
        """
        with self._lock:
            file_size = self._file_size
            pruned = self._pruned_ever
            atoms_snapshot = list(self._atoms)
        if cursor < 0:
            cursor = 0
        if cursor == 0:
            # Full snapshot from start.
            return atoms_snapshot, file_size, False
        if cursor > file_size:
            # Cursor past EOF - either client cached a stale offset or we pruned.
            return [], file_size, True
        if pruned:
            # We can't trust mid-file offsets after a prune.
            return [], file_size, True
        # No prunes yet; safe to read from disk at offset.
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
                atoms_out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return atoms_out, new_cursor, False

    # -- write API -----------------------------------------------------------

    def append(self, atom: Dict[str, Any]) -> Tuple[str, bool]:
        """Append atom if new. Returns (atom_id, was_new)."""
        atom_id = compute_atom_id(atom)
        with self._lock:
            if atom_id in self._atom_ids:
                return atom_id, False
            line = json.dumps(atom, separators=(",", ":"), ensure_ascii=False) + "\n"
            encoded = line.encode("utf-8")
            with open(self.atoms_file, "ab") as f:
                f.write(encoded)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            self._file_size += len(encoded)
            self._atom_ids[atom_id] = len(self._atoms)
            self._atoms.append(atom)
            self._maybe_prune_locked()
        return atom_id, True

    def _maybe_prune_locked(self) -> None:
        """Prune oldest atoms if over count or age limits. Caller holds lock."""
        now = _now_ms()
        cutoff = now - self.max_age_ms
        # Determine how many to drop.
        n_over = max(0, len(self._atoms) - self.max_atoms)
        # Drop atoms older than cutoff (by `t`).
        drop_indices: List[int] = []
        for i, a in enumerate(self._atoms):
            t = a.get("t")
            if isinstance(t, int) and t < cutoff:
                drop_indices.append(i)
        # Combine: drop the union of (oldest n_over) and (any older than cutoff).
        keep_set: List[Dict[str, Any]] = []
        if n_over > 0:
            kept_after_count = self._atoms[n_over:]
        else:
            kept_after_count = list(self._atoms)
        if drop_indices or n_over > 0:
            keep_set = [a for a in kept_after_count if isinstance(a.get("t"), int) and a["t"] >= cutoff]
            if len(keep_set) == len(self._atoms):
                return  # nothing pruned
            self._rewrite_locked(keep_set)

    def _rewrite_locked(self, new_atoms: List[Dict[str, Any]]) -> None:
        """Atomically rewrite atoms.ndjson with new_atoms. Caller holds lock."""
        before = len(self._atoms)
        tmp = self.atoms_file + ".tmp"
        with open(tmp, "wb") as f:
            for atom in new_atoms:
                line = json.dumps(atom, separators=(",", ":"), ensure_ascii=False) + "\n"
                f.write(line.encode("utf-8"))
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, self.atoms_file)
        self._atoms = list(new_atoms)
        self._atom_ids = {compute_atom_id(a): i for i, a in enumerate(self._atoms)}
        try:
            self._file_size = os.path.getsize(self.atoms_file)
        except OSError:
            self._file_size = 0
        self._pruned_ever = True
        log(
            f"prune: {before} -> {len(self._atoms)} atoms (max_atoms={self.max_atoms}, "
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

    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        ok, _ = validate_atom(atom)
        if not ok:
            continue
        atom_id = compute_atom_id(atom)
        if buffer.has(atom_id):
            continue
        _, was_new = buffer.append(atom)
        if was_new:
            new_count += 1
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
            self._send_json(
                200,
                {
                    "node": NODE_NAME,
                    "version": VERSION,
                    "peers": PEERS,
                    "buffer_size": self.buffer.size(),
                    "buffer_oldest_t": self.buffer.oldest_t(),
                    "buffer_atoms_max": BUFFER_ATOMS,
                    "buffer_hours_max": BUFFER_HOURS,
                    "latest_limit": LATEST_LIMIT,
                    "sync_interval": SYNC_INTERVAL,
                    "capabilities": ["write", "latest", "feed", "sync"],
                },
            )
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
    buffer = Buffer(ATOMS_FILE, BUFFER_ATOMS, BUFFER_HOURS)
    buffer.load()
    sync_state = SyncState(SYNC_STATE_FILE)
    RelayHandler.buffer = buffer
    RelayHandler.sync_state = sync_state
    server = ThreadingHTTPServer((host, port), RelayHandler)
    return server, buffer, sync_state


def main() -> None:
    server, buffer, sync_state = build_server()
    log(f"punkto-relay {VERSION} listening on http://{HOST}:{PORT}")
    log(f"node={NODE_NAME} data_dir={DATA_DIR} buffer_atoms={BUFFER_ATOMS} buffer_hours={BUFFER_HOURS}")
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
