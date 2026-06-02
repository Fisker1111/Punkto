from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "node-doctor.py"
spec = importlib.util.spec_from_file_location("node_doctor", SCRIPT)
assert spec and spec.loader
node_doctor = importlib.util.module_from_spec(spec)
sys.modules["node_doctor"] = node_doctor
spec.loader.exec_module(node_doctor)


def test_normalize_base_url_adds_https_and_strips_path() -> None:
    assert node_doctor.normalize_base_url("node1.punkto.xyz/") == "https://node1.punkto.xyz"
    assert node_doctor.normalize_base_url("https://node1.punkto.xyz/status") == "https://node1.punkto.xyz"


def test_forbidden_secret_scanner_catches_private_key() -> None:
    hits = node_doctor.scan_for_forbidden_secrets('{"operator":{"private_key":"abc"}}')
    assert "private_key" in hits


def test_doctor_json_result_shape() -> None:
    doctor = node_doctor.Doctor()
    doctor.add(node_doctor.PASS, "example", "example ok", answer=42)
    result = doctor.to_json("https://node1.punkto.xyz")
    assert result["tool"] == "punkto-node-doctor"
    assert result["target"] == "https://node1.punkto.xyz"
    assert result["status"] == node_doctor.PASS
    assert result["checks"][0]["details"] == {"answer": 42}
    json.dumps(result)


def test_policy_warning_logic_flags_archive_and_large_windows() -> None:
    status, message, details = node_doctor.evaluate_policy(
        {
            "serving": {"serve_recent_hours": 240, "serve_archive": True, "serve_pinned": True},
            "acceptance": {"accept_recent_hours": 240},
        }
    )
    assert status == node_doctor.WARN
    assert "serve_archive=true" in message
    assert "accept_recent_hours is large" in message
    assert details["serve_recent_hours"] == 240


def test_policy_passes_live_forward_baseline() -> None:
    status, message, details = node_doctor.evaluate_policy(
        {
            "serving": {"serve_recent_hours": 24, "serve_archive": False, "serve_pinned": True},
            "acceptance": {"accept_recent_hours": 24},
        }
    )
    assert status == node_doctor.PASS
    assert "accept=24h" in message
    assert details["serve_archive"] is False


def test_feed_parsing_helper_accepts_documented_shapes() -> None:
    assert node_doctor.validate_feed_shape([])[0] is True
    assert node_doctor.validate_feed_shape({"atoms": []})[0] is True
    assert node_doctor.validate_feed_shape({"items": []})[0] is True
    ok, message = node_doctor.validate_feed_shape({"cursor": 0})
    assert ok is False
    assert "no atoms/items" in message
