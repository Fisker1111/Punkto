#!/usr/bin/env python3
"""
Punkto Node Doctor — Check a Punkto node for public-readiness health.

Usage:
    python scripts/node-doctor.py https://node1.punkto.xyz \
        --expect-ip 46.101.118.157 \
        --expect-name "Punkto Reference Node 1"

Optional --local checks (requires SSH-access or local filesystem):
    python scripts/node-doctor.py https://node1.punkto.xyz --local /path/to/punkto
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request


def http_get(url, timeout=15):
    """Fetch a URL and return (status, headers, body)."""
    req = urllib.request.Request(url, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, dict(e.headers), body
    except Exception as e:
        return 0, {}, str(e)


def check(label, ok, detail=""):
    """Print PASS/WARN/FAIL for a check."""
    tag = "PASS" if ok else "FAIL"
    msg = f"  [{tag}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


def parse_json(text):
    """Safely parse JSON, returning (data, error)."""
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, str(e)


def check_no_secrets(text, label):
    """Check that common secret patterns are not exposed."""
    patterns = [
        r"private_key",
        r"PRIVATE_KEY",
        r"secret",
        r"SECRET",
        r"token",
        r"TOKEN",
        r"\.env",
        r"ENV",
        r"password",
        r"PASSWORD",
        r"api_key",
        r"API_KEY",
    ]
    for pat in patterns:
        if re.search(pat, text):
            return check(label, False, f"Found: '{pat}' pattern")
    return check(label, True, "No secrets exposed")


def check_dns(hostname):
    """Resolve hostname and return list of IPs."""
    try:
        import socket
        ips = socket.getaddrinfo(hostname, 443)
        unique = list(set(a[4][0] for a in ips))
        return unique
    except Exception as e:
        return [f"ERROR: {e}"]


def run_local_checks(local_path):
    """Run optional local filesystem checks."""
    results = []
    
    # Config file exists
    config_paths = [
        os.path.join(local_path, "config", "punkto-node.yml"),
    ]
    found_config = None
    for cp in config_paths:
        if os.path.exists(cp):
            found_config = cp
            break
    results.append(check("Config file exists", found_config is not None,
                         found_config or "not found in config/"))
    
    # Atom log exists
    atom_log = os.path.join(local_path, "data", "atoms.log.jsonl")
    exists = os.path.exists(atom_log)
    if exists:
        size = os.path.getsize(atom_log)
        with open(atom_log) as f:
            line_count = sum(1 for _ in f)
        results.append(check("Atom log (/data/atoms.log.jsonl) exists", True,
                             f"{size} bytes, {line_count} lines"))
    else:
        results.append(check("Atom log (/data/atoms.log.jsonl) exists", False,
                             "not found"))
    
    # Docker containers (try docker ps)
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}} {{.Image}} {{.Status}}"],
            timeout=10, text=True
        )
        containers = out.strip().split("\n")
        has_web = any("punkto-web" in c for c in containers)
        has_relay = any("punkto-relay" in c for c in containers)
        results.append(check("Docker: punkto-web running", has_web,
                             [c for c in containers if "punkto-web" in c][0] if has_web else ""))
        results.append(check("Docker: punkto-relay running", has_relay,
                             [c for c in containers if "punkto-relay" in c][0] if has_relay else ""))
    except Exception as e:
        results.append(check("Docker containers (docker ps)", False, str(e)))
    
    # Disk space
    try:
        out = subprocess.check_output(["df", "-h", "/"], timeout=5, text=True)
        lines = out.strip().split("\n")
        if len(lines) > 1:
            fields = lines[1].split()
            if len(fields) >= 4:
                pct = fields[4] if len(fields) > 4 else "?"
                results.append(check("Disk space ok", 
                                     int(pct.rstrip("%")) < 90 if pct.rstrip("%").isdigit() else True,
                                     f"{pct} used"))
    except Exception:
        pass
    
    return all(results)


def main():
    parser = argparse.ArgumentParser(
        description="Punkto Node Doctor — verify a node is healthy and public-ready",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://node1.punkto.xyz --expect-ip 46.101.118.157 --expect-name "Punkto Reference Node 1"
  %(prog)s https://node2.punkto.xyz --expect-ip 159.65.115.166 --expect-name "Punkto Reference Node 2"
  %(prog)s https://node1.punkto.xyz --expect-ip 46.101.118.157
  %(prog)s https://punkto.xyz
  %(prog)s https://node1.punkto.xyz --local /home/user/punkto
"""
    )
    parser.add_argument("url", help="Node base URL (e.g. https://node1.punkto.xyz)")
    parser.add_argument("--expect-ip", help="Expected public IP of the node")
    parser.add_argument("--expect-name", help="Expected node name from /node/info")
    parser.add_argument("--local", help="Path to local punkto directory for extra checks")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    
    args = parser.parse_args()
    
    base = args.url.rstrip("/")
    timeout = args.timeout
    
    # Parse hostname from URL
    hostname = re.sub(r"^https?://", "", base).split("/")[0].split(":")[0]
    
    print(f"Punkto Node Doctor")
    print(f"=" * 50)
    print(f"  Target: {base}")
    print(f"  Hostname: {hostname}")
    if args.expect_ip:
        print(f"  Expected IP: {args.expect_ip}")
    if args.expect_name:
        print(f"  Expected Node Name: {args.expect_name}")
    if args.local:
        print(f"  Local path: {args.local}")
    print()
    
    all_pass = True
    warn_count = 0
    
    # ── 1. DNS resolution ──
    print("── DNS Resolution ──")
    ips = check_dns(hostname)
    if ips and not any("ERROR" in ip for ip in ips):
        check("DNS resolves", True, f"{', '.join(ips)}")
        if args.expect_ip and args.expect_ip not in ips:
            all_pass = check("DNS IP matches --expect-ip", False,
                             f"Expected {args.expect_ip}, got {', '.join(ips)}")
        elif args.expect_ip:
            check("DNS IP matches --expect-ip", True)
    else:
        all_pass = check("DNS resolves", False, f"{', '.join(ips)}")
    print()
    
    # ── 2. HTTPS reachability ──
    print("── HTTPS Reachability ──")
    status, headers, body = http_get(base, timeout)
    if status == 0:
        all_pass = check("HTTPS reachable", False, body)
    else:
        check("HTTPS reachable", True, f"HTTP {status}")
    print()
    
    # ── 3. /health ──
    print("── /health ──")
    status, _, body = http_get(f"{base}/health", timeout)
    if status == 200:
        data, err = parse_json(body)
        if data:
            ok_status = data.get("status") == "ok"
            all_pass &= check("/health returns ok", ok_status,
                              f"status={data.get('status')}")
            node = data.get("node", "?")
            check("/health node present", bool(node), node)
        else:
            all_pass &= check("/health valid JSON", False, err)
    else:
        all_pass &= check("/health HTTP 200", False, f"HTTP {status}")
    print()
    
    # ── 4. /node/info ──
    print("── /node/info ──")
    status, _, body = http_get(f"{base}/node/info", timeout)
    if status == 200:
        data, err = parse_json(body)
        if data:
            check("/node/info valid JSON", True)
            
            # config_loaded
            config_loaded = data.get("config", {}).get("loaded", False)
            all_pass &= check("config_loaded=true", config_loaded is True,
                              str(config_loaded))
            
            # node_name
            node_name = data.get("node", {}).get("name", "")
            if node_name:
                check("node_name present", True, node_name)
                if args.expect_name:
                    match = node_name == args.expect_name
                    all_pass &= check("node_name matches --expect-name", match,
                                      f"got '{node_name}'")
            else:
                check("node_name present", False, "missing")
                all_pass = False
            
            # No private_key in response
            check_no_secrets(body, "/node/info no private_key/secrets")
            
            # serving policy
            serving = data.get("serving", {})
            if serving:
                srh = serving.get("serve_recent_hours", "?")
                check("serving.serve_recent_hours present", 
                      srh != "?", str(srh))
                sa = serving.get("serve_archive", "?")
                check("serving.serve_archive present",
                      sa != "?", str(sa))
            else:
                check("serving policy present", False, "missing")
                warn_count += 1
            
            # acceptance policy
            acceptance = data.get("acceptance", {})
            if acceptance:
                arh = acceptance.get("accept_recent_hours", "?")
                check("acceptance.accept_recent_hours present",
                      arh != "?", str(arh))
            else:
                check("acceptance policy present", False, "missing")
                warn_count += 1
        else:
            all_pass &= check("/node/info valid JSON", False, err)
    else:
        all_pass &= check("/node/info HTTP 200", False, f"HTTP {status}")
    print()
    
    # ── 5. /status ──
    print("── /status ──")
    status, _, body = http_get(f"{base}/status", timeout)
    if status == 200:
        check("/status HTTP 200", True)
        check("/status contains 'Punkto Node Status'",
              "Punkto Node Status" in body,
              "text found" if "Punkto Node Status" in body else "text missing")
        check("/status contains 'Data flow'",
              "Data flow" in body,
              "found" if "Data flow" in body else "missing")
        check_no_secrets(body, "/status no private_key/secrets")
    else:
        all_pass &= check("/status HTTP 200", False, f"HTTP {status}")
    print()
    
    # ── 6. /feed ──
    print("── /feed ──")
    status, _, body = http_get(f"{base}/feed", timeout)
    if status == 200:
        data, err = parse_json(body)
        if isinstance(data, list):
            check("/feed valid JSON array", True, f"{len(data)} atoms")
        elif isinstance(data, dict):
            check("/feed valid JSON object", True, str(list(data.keys()))[:80])
        else:
            all_pass &= check("/feed valid JSON", False, err or "unexpected type")
    else:
        all_pass &= check("/feed HTTP 200", False, f"HTTP {status}")
    print()
    
    # ── 7. /app.js marker (optional) ──
    print("── App Marker ──")
    status, _, body = http_get(f"{base}/app.js", timeout)
    if status == 200:
        marker_match = re.search(r"hard-marker[^\"']*|[A-Z]+_APP_VERSION[\s=:]+\"[^\"]+\"", body)
        if marker_match:
            check("/app.js marker found", True, marker_match.group(0)[:60])
        else:
            check("/app.js marker found", False, "no marker pattern matched")
            warn_count += 1
    else:
        check("/app.js HTTP 200", False, f"HTTP {status} (optional check)")
        warn_count += 1
    print()
    
    # ── 8. Local checks ──
    if args.local:
        print("── Local Checks ──")
        local_ok = run_local_checks(args.local)
        if not local_ok:
            all_pass = False
        print()
    
    # ── Summary ──
    print("=" * 50)
    if all_pass:
        print(f"  RESULT: PASS  (no failures)")
    else:
        print(f"  RESULT: FAIL  (one or more checks failed)")
    if warn_count > 0:
        print(f"  Warnings: {warn_count}")
    print()
    
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
