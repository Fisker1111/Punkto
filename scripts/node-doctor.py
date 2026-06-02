#!/usr/bin/env python3
"""Punkto public node doctor.

Checks a Punkto node from the outside, with optional local server checks.
Uses only the Python standard library so it can run on fresh servers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"private[_-]?key", re.IGNORECASE)),
    ("secret", re.compile(r"\bsecrets?\b|secret[_-]?(key|token|value)?", re.IGNORECASE)),
    ("token", re.compile(r"\btoken\b|access[_-]?token|refresh[_-]?token", re.IGNORECASE)),
    (".env", re.compile(r"\.env\b|secrets\.env\b", re.IGNORECASE)),
    ("pem private key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE)),
    ("raw private key material", re.compile(r"\b(ed25519|ecdsa|rsa)[_-]?private\b", re.IGNORECASE)),
)

HARD_MARKER_RE = re.compile(r"v\d+(?:\.\d+)?-hard-marker-\d{4}-\d{2}-\d{2}-\d+")
APP_VERSION_RE = re.compile(r"PUNKTO_APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]")


@dataclass
class Check:
    name: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class Doctor:
    def __init__(self) -> None:
        self.checks: list[Check] = []

    def add(self, status: str, name: str, message: str, **details: Any) -> None:
        self.checks.append(Check(name=name, status=status, message=message, details=details))

    def overall_status(self) -> str:
        if any(check.status == FAIL for check in self.checks):
            return FAIL
        if any(check.status == WARN for check in self.checks):
            return WARN
        return PASS

    def to_json(self, target: str) -> dict[str, Any]:
        return {
            "tool": "punkto-node-doctor",
            "target": target,
            "status": self.overall_status(),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "message": check.message,
                    "details": check.details,
                }
                for check in self.checks
            ],
        }


def normalize_base_url(raw_url: str) -> str:
    """Normalize an operator-supplied target to a no-trailing-slash base URL."""
    value = raw_url.strip()
    if not value:
        raise ValueError("target URL is empty")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if not parsed.netloc:
        raise ValueError(f"target URL has no hostname: {raw_url!r}")
    path = parsed.path.rstrip("/")
    if path and path != "/":
        # Base targets should be host roots; endpoint paths are appended by the doctor.
        path = ""
    return urlunparse((parsed.scheme.lower(), parsed.netloc, path, "", "", "")).rstrip("/")


def resolve_hostname(hostname: str) -> list[str]:
    records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    ips = sorted({record[4][0] for record in records})
    return ips


def http_request(base_url: str, path: str = "/", timeout: float = 10.0) -> tuple[int, str, bytes, dict[str, str]]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, headers={"User-Agent": "punkto-node-doctor/1"})
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            body = response.read()
            headers = {k.lower(): v for k, v in response.headers.items()}
            charset = response.headers.get_content_charset() or "utf-8"
            text = body.decode(charset, errors="replace")
            return response.status, text, body, headers
    except HTTPError as exc:
        body = exc.read()
        charset = exc.headers.get_content_charset() or "utf-8"
        text = body.decode(charset, errors="replace")
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, text, body, headers


def parse_json_response(text: str) -> Any:
    return json.loads(text)


def scan_for_forbidden_secrets(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            hits.append(label)
    return hits


def validate_feed_shape(payload: Any) -> tuple[bool, str]:
    if isinstance(payload, list):
        return True, "feed is a JSON array"
    if isinstance(payload, dict):
        atoms = payload.get("atoms")
        if isinstance(atoms, list):
            return True, "feed has atoms array"
        if isinstance(payload.get("items"), list):
            return True, "feed has items array"
        return False, "feed object has no atoms/items array"
    return False, f"feed JSON is {type(payload).__name__}, not an array or documented object"


def evaluate_policy(info: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    serving = info.get("serving") if isinstance(info.get("serving"), dict) else {}
    acceptance = info.get("acceptance") if isinstance(info.get("acceptance"), dict) else {}
    details: dict[str, Any] = {
        "serve_recent_hours": serving.get("serve_recent_hours"),
        "accept_recent_hours": acceptance.get("accept_recent_hours"),
        "serve_archive": serving.get("serve_archive"),
        "serve_pinned": serving.get("serve_pinned"),
    }
    warnings: list[str] = []
    serve_archive = details["serve_archive"]
    accept_hours = details["accept_recent_hours"]
    serve_hours = details["serve_recent_hours"]
    if serve_archive is True:
        warnings.append("serve_archive=true")
    if isinstance(accept_hours, (int, float)) and accept_hours > 168:
        warnings.append(f"accept_recent_hours is large ({accept_hours})")
    if isinstance(serve_hours, (int, float)) and serve_hours > 168:
        warnings.append(f"serve_recent_hours is large ({serve_hours})")
    if warnings:
        return WARN, "; ".join(warnings), details
    if serving or acceptance:
        return PASS, (
            f"live-forward policy: accept={accept_hours}h serve={serve_hours}h "
            f"archive={str(serve_archive).lower()} pinned={str(details['serve_pinned']).lower()}"
        ), details
    return WARN, "policy fields not exposed by /node/info", details


def extract_app_marker(app_js: str) -> str | None:
    version_match = APP_VERSION_RE.search(app_js)
    if version_match:
        return version_match.group(1)
    marker_match = HARD_MARKER_RE.search(app_js)
    if marker_match:
        return marker_match.group(0)
    if "PUNKTO_APP_VERSION" in app_js:
        return "PUNKTO_APP_VERSION present"
    return None


def json_line_count(path: Path, max_bytes: int = 50_000_000) -> int | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        with path.open("rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return None


def run_command(command: list[str], timeout: float = 20.0) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return completed.returncode, completed.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def find_first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def perform_remote_checks(
    doctor: Doctor,
    base_url: str,
    timeout: float,
    expect_ip: str | None,
    expect_name: str | None,
    expect_marker: str | None,
) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https":
        doctor.add(FAIL, "https", "target must use https://", scheme=parsed.scheme)
    hostname = parsed.hostname
    if not hostname:
        doctor.add(FAIL, "dns", "target URL has no hostname")
        return

    try:
        ips = resolve_hostname(hostname)
        if expect_ip and expect_ip not in ips:
            doctor.add(FAIL, "dns", f"DNS resolves, but expected IP {expect_ip} was not found", ips=ips)
        else:
            doctor.add(PASS, "dns", f"DNS resolves: {', '.join(ips)}", ips=ips)
    except socket.gaierror as exc:
        doctor.add(FAIL, "dns", f"DNS resolution failed: {exc}")

    try:
        status, _, _, _ = http_request(base_url, "/", timeout)
        if parsed.scheme == "https":
            doctor.add(PASS, "https", f"HTTPS reachable: HTTP {status}", http_status=status)
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        doctor.add(FAIL, "https", f"HTTPS/TLS connection failed: {exc}")

    health_json: Any = None
    try:
        status, text, _, _ = http_request(base_url, "/health", timeout)
        if status != 200:
            doctor.add(FAIL, "health", f"/health returned HTTP {status}", http_status=status)
        else:
            try:
                health_json = parse_json_response(text)
                if isinstance(health_json, dict) and health_json.get("status") not in (None, "ok"):
                    doctor.add(FAIL, "health", f"/health status is {health_json.get('status')!r}")
                else:
                    doctor.add(PASS, "health", "/health ok")
            except json.JSONDecodeError as exc:
                doctor.add(FAIL, "health", f"/health is not valid JSON: {exc}")
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        doctor.add(FAIL, "health", f"/health request failed: {exc}")

    node_info: dict[str, Any] | None = None
    node_info_text = ""
    try:
        status, text, _, _ = http_request(base_url, "/node/info", timeout)
        node_info_text = text
        if status != 200:
            doctor.add(FAIL, "node_info", f"/node/info returned HTTP {status}", http_status=status)
        else:
            try:
                parsed_info = parse_json_response(text)
                if not isinstance(parsed_info, dict):
                    doctor.add(FAIL, "node_info", "/node/info JSON is not an object")
                else:
                    node_info = parsed_info
                    failures: list[str] = []
                    warnings: list[str] = []
                    config = parsed_info.get("config") if isinstance(parsed_info.get("config"), dict) else {}
                    node = parsed_info.get("node") if isinstance(parsed_info.get("node"), dict) else {}
                    if config.get("loaded") is not True:
                        failures.append("config.loaded is not true")
                    node_name = node.get("name")
                    if not node_name:
                        failures.append("node.name missing")
                    if expect_name and node_name != expect_name:
                        failures.append(f"node.name {node_name!r} did not match expected {expect_name!r}")
                    if "public_url" not in node:
                        warnings.append("node.public_url not exposed")
                    if not isinstance(parsed_info.get("roles"), dict):
                        failures.append("roles missing")
                    if not isinstance(parsed_info.get("serving"), dict):
                        failures.append("serving policy missing")
                    if "acceptance" in parsed_info and not isinstance(parsed_info.get("acceptance"), dict):
                        failures.append("acceptance policy is not an object")
                    if "storage" in parsed_info and not isinstance(parsed_info.get("storage"), dict):
                        failures.append("storage is not an object")
                    if "stats" in parsed_info and not isinstance(parsed_info.get("stats"), dict):
                        failures.append("stats is not an object")
                    if failures:
                        doctor.add(FAIL, "node_info", "/node/info failed validation: " + "; ".join(failures))
                    elif warnings:
                        doctor.add(WARN, "node_info", "/node/info ok with warnings: " + "; ".join(warnings), node_name=node_name)
                    else:
                        doctor.add(PASS, "node_info", f"/node/info ok: {node_name}", node_name=node_name)
            except json.JSONDecodeError as exc:
                doctor.add(FAIL, "node_info", f"/node/info is not valid JSON: {exc}")
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        doctor.add(FAIL, "node_info", f"/node/info request failed: {exc}")

    status_text = ""
    try:
        status, text, _, _ = http_request(base_url, "/status", timeout)
        status_text = text
        if status != 200:
            doctor.add(FAIL, "status", f"/status returned HTTP {status}", http_status=status)
        else:
            required = ["Punkto Node Status", "public and read-only", "Data flow"]
            missing = [needle for needle in required if needle not in text]
            forbidden = scan_for_forbidden_secrets(text)
            if missing:
                doctor.add(FAIL, "status", "/status missing required text: " + ", ".join(missing))
            elif forbidden:
                doctor.add(FAIL, "status", "/status exposes forbidden words/material: " + ", ".join(forbidden), hits=forbidden)
            else:
                doctor.add(PASS, "status", "/status ok")
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        doctor.add(FAIL, "status", f"/status request failed: {exc}")

    try:
        status, text, _, _ = http_request(base_url, "/feed", timeout)
        if status != 200:
            doctor.add(FAIL, "feed", f"/feed returned HTTP {status}", http_status=status)
        else:
            try:
                payload = parse_json_response(text)
                ok, message = validate_feed_shape(payload)
                if ok:
                    count = len(payload) if isinstance(payload, list) else len(payload.get("atoms", payload.get("items", [])))
                    doctor.add(PASS, "feed", f"/feed ok: {message}", item_count=count)
                else:
                    doctor.add(FAIL, "feed", message)
            except json.JSONDecodeError as exc:
                doctor.add(FAIL, "feed", f"/feed is not valid JSON: {exc}")
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        doctor.add(FAIL, "feed", f"/feed request failed: {exc}")

    try:
        status, text, _, _ = http_request(base_url, "/app.js", timeout)
        if status == 200:
            marker = extract_app_marker(text)
            if expect_marker and expect_marker not in text:
                doctor.add(FAIL, "app_marker", f"expected app marker {expect_marker!r} not found", marker=marker)
            elif marker:
                doctor.add(PASS, "app_marker", f"app marker: {marker}", marker=marker)
            else:
                doctor.add(WARN, "app_marker", "/app.js found but no PUNKTO_APP_VERSION or hard marker was detected")
        elif expect_marker:
            doctor.add(FAIL, "app_marker", f"/app.js returned HTTP {status}; expected marker required", http_status=status)
        else:
            doctor.add(WARN, "app_marker", f"/app.js not found or not public: HTTP {status}", http_status=status)
    except (URLError, TimeoutError, ssl.SSLError, OSError) as exc:
        if expect_marker:
            doctor.add(FAIL, "app_marker", f"/app.js request failed while expected marker is required: {exc}")
        else:
            doctor.add(WARN, "app_marker", f"/app.js check skipped after request failure: {exc}")

    if node_info is not None:
        policy_status, policy_message, policy_details = evaluate_policy(node_info)
        doctor.add(policy_status, "policy", policy_message, **policy_details)

    combined_public_text = status_text + "\n" + node_info_text
    forbidden = scan_for_forbidden_secrets(combined_public_text)
    if forbidden:
        doctor.add(FAIL, "safety", "public endpoints expose forbidden words/material: " + ", ".join(forbidden), hits=forbidden)
    else:
        doctor.add(PASS, "safety", "no private_key/secrets exposed")


def perform_local_checks(doctor: Doctor) -> None:
    config = find_first_existing([Path("./config/punkto-node.yml"), Path("/config/punkto-node.yml")])
    if config is None:
        doctor.add(WARN, "local_config", "no local config found at ./config/punkto-node.yml or /config/punkto-node.yml")
    elif os.access(config, os.R_OK):
        doctor.add(PASS, "local_config", f"config file readable: {config}")
    else:
        doctor.add(FAIL, "local_config", f"config file exists but is not readable: {config}")

    data_dir = find_first_existing([Path("./data"), Path("/data")])
    if data_dir is None:
        doctor.add(WARN, "local_data", "no local data directory found at ./data or /data")
    else:
        atom_log = data_dir / "atoms.log.jsonl"
        if not atom_log.exists():
            doctor.add(WARN, "local_data", f"data directory exists, but atom log is missing: {atom_log}")
        else:
            size = atom_log.stat().st_size
            lines = json_line_count(atom_log)
            if lines is None:
                doctor.add(PASS, "local_data", f"atom log exists: {atom_log} ({size} bytes; line count skipped)", bytes=size)
            else:
                doctor.add(PASS, "local_data", f"atom log exists: {atom_log} ({size} bytes, {lines} lines)", bytes=size, lines=lines)

    if shutil.which("docker") is None:
        doctor.add(WARN, "local_docker", "docker CLI not available")
    else:
        compose_cmd = ["docker", "compose", "ps"]
        code, output = run_command(compose_cmd)
        if code != 0:
            doctor.add(WARN, "local_docker", "docker compose ps could not run", output=output[-2000:])
        else:
            lowered = output.lower()
            failures: list[str] = []
            warnings: list[str] = []
            if "relay" not in lowered:
                warnings.append("relay container not visible")
            if "web" not in lowered and "caddy" not in lowered:
                warnings.append("web container not visible")
            if "restarting" in lowered or "restart" in lowered:
                failures.append("possible restart loop detected")
            if "exited" in lowered or "dead" in lowered:
                failures.append("stopped/dead container detected")
            if failures:
                doctor.add(FAIL, "local_docker", "docker compose ps has problems: " + "; ".join(failures), output=output[-4000:])
            elif warnings:
                doctor.add(WARN, "local_docker", "docker compose ps warnings: " + "; ".join(warnings), output=output[-4000:])
            else:
                doctor.add(PASS, "local_docker", "docker compose ps shows relay/web containers", output=output[-4000:])

        caddy_cmd = ["docker", "exec", "punkto-web-1", "caddy", "adapt", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
        code, output = run_command(caddy_cmd)
        if code == 0:
            doctor.add(PASS, "local_caddy", "Caddyfile validates with caddy adapt")
        elif "No such container" in output or "not running" in output or code == 127:
            doctor.add(WARN, "local_caddy", "Caddy validation not possible", output=output[-2000:])
        else:
            doctor.add(FAIL, "local_caddy", "caddy adapt failed", output=output[-4000:])

    usage = shutil.disk_usage(Path.cwd())
    used_pct = (usage.used / usage.total) * 100 if usage.total else 0.0
    details = {"used_percent": round(used_pct, 1), "free_bytes": usage.free, "total_bytes": usage.total}
    if used_pct > 90:
        doctor.add(FAIL, "local_disk", f"disk usage critical: {used_pct:.1f}% used", **details)
    elif used_pct > 80:
        doctor.add(WARN, "local_disk", f"disk usage high: {used_pct:.1f}% used", **details)
    else:
        doctor.add(PASS, "local_disk", f"disk space ok: {used_pct:.1f}% used", **details)


def print_human_report(result: dict[str, Any]) -> None:
    print("Punkto node doctor")
    print(f"Target: {result['target']}")
    print()
    icons = {PASS: "✅", WARN: "⚠️", FAIL: "❌"}
    for check in result["checks"]:
        print(f"{icons.get(check['status'], '•')} {check['message']}")
    print()
    print(f"Node doctor: {result['status']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify a Punkto node from public endpoints, with optional local server checks.")
    parser.add_argument("target", help="Base URL or hostname, e.g. https://node1.punkto.xyz")
    parser.add_argument("--expect-ip", help="Require DNS to include this IP address")
    parser.add_argument("--expect-name", help="Require /node/info node.name to match this value")
    parser.add_argument("--expect-marker", help="Require /app.js to contain this marker/version string")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON result")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP/DNS check timeout in seconds (default: 10)")
    parser.add_argument("--local", action="store_true", help="Also run local filesystem/Docker/Caddy/disk checks on the server")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        base_url = normalize_base_url(args.target)
    except ValueError as exc:
        print(f"node doctor: {exc}", file=sys.stderr)
        return 2

    doctor = Doctor()
    start = time.time()
    perform_remote_checks(doctor, base_url, args.timeout, args.expect_ip, args.expect_name, args.expect_marker)
    if args.local:
        perform_local_checks(doctor)
    result = doctor.to_json(base_url)
    result["duration_seconds"] = round(time.time() - start, 3)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human_report(result)

    return 1 if result["status"] == FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
