#!/usr/bin/env python3
"""Fetch one DMI weather station and emit a Punkto atom candidate.

This tool is intentionally narrow: it targets one known station and prints the
atom JSON that a later loop can post through the normal Punkto relay path.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import geohash3d  # noqa: E402


DMI_BASE_URL = "https://opendataapi.dmi.dk/v2/metObs"
DMI_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
DMI_TERMS_URL = "https://www.dmi.dk/friedata/dokumentation/terms-of-use"
DEFAULT_STATION_ID = "06126"


class DmiImportError(RuntimeError):
    """Raised when DMI data cannot be converted without inventing values."""


def rfc3339_to_ms(value: str) -> int:
    if not isinstance(value, str) or not value:
        raise DmiImportError("missing RFC3339 timestamp")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DmiImportError(f"invalid RFC3339 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def endpoint(collection: str, params: Dict[str, str]) -> str:
    return f"{DMI_BASE_URL}/collections/{collection}/items?{urllib.parse.urlencode(params)}"


def fetch_json(url: str) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "PunktoDmiVerifier/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def first_feature(payload: Dict[str, Any], label: str) -> Tuple[Dict[str, Any], str]:
    if payload.get("type") != "FeatureCollection":
        raise DmiImportError(f"{label} response is not a GeoJSON FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise DmiImportError(f"{label} response contains no features")
    timestamp = payload.get("timeStamp")
    if not isinstance(timestamp, str) or not timestamp:
        raise DmiImportError(f"{label} response is missing timeStamp")
    feature = features[0]
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise DmiImportError(f"{label} response first item is not a GeoJSON Feature")
    return feature, timestamp


def station_parts(feature: Dict[str, Any], station_id: str) -> Tuple[str, str, float, float, float]:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        raise DmiImportError("station geometry is not a GeoJSON Point")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        raise DmiImportError("station geometry is missing coordinates")
    lon = coords[0]
    lat = coords[1]
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise DmiImportError("station coordinates are not numeric")

    props = feature.get("properties")
    if not isinstance(props, dict):
        raise DmiImportError("station feature is missing properties")
    actual_station_id = props.get("stationId")
    if actual_station_id != station_id:
        raise DmiImportError(f"stationId mismatch: expected {station_id}, got {actual_station_id!r}")
    name = props.get("name")
    if not isinstance(name, str) or not name.strip():
        raise DmiImportError("station name is missing")
    height = props.get("stationHeight")
    if not isinstance(height, (int, float)):
        raise DmiImportError("selected station has no numeric stationHeight")

    return actual_station_id, name.strip(), float(lat), float(lon), float(height)


def observation_parts(feature: Dict[str, Any], station_id: str) -> Tuple[str, Any, str, int]:
    props = feature.get("properties")
    if not isinstance(props, dict):
        raise DmiImportError("observation feature is missing properties")
    actual_station_id = props.get("stationId")
    if actual_station_id != station_id:
        raise DmiImportError(f"observation stationId mismatch: expected {station_id}, got {actual_station_id!r}")
    parameter_id = props.get("parameterId")
    if not isinstance(parameter_id, str) or not parameter_id.strip():
        raise DmiImportError("observation parameterId is missing")
    if "value" not in props:
        raise DmiImportError("observation value is missing")
    observed = props.get("observed")
    observed_ms = rfc3339_to_ms(observed)
    return parameter_id.strip(), props.get("value"), observed, observed_ms


def build_atom(
    station_payload: Dict[str, Any],
    observation_payload: Dict[str, Any],
    station_id: str = DEFAULT_STATION_ID,
) -> Dict[str, Any]:
    station_feature, station_response_timestamp = first_feature(station_payload, "station")
    observation_feature, observation_response_timestamp = first_feature(observation_payload, "observation")

    station_id, name, lat, lon, altitude_m = station_parts(station_feature, station_id)
    parameter_id, value, observed, observed_ms = observation_parts(observation_feature, station_id)

    spatial = geohash3d.encode(lat, lon, altitude_m)
    punkto = f"p:{spatial}-dmi{station_id}"
    value_text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    return {
        "punkto": punkto,
        "t": observed_ms,
        "f": "DMI",
        "x": (
            f"DMI weather station: {name} ({station_id})\n"
            "Official DMI import\n"
            f"Coordinates: {lat:.6f}, {lon:.6f}, {altitude_m:g} m\n"
            f"Observation: {parameter_id} = {value_text}\n"
            f"Observed: {observed}\n"
            "Source: Danish Meteorological Institute (DMI), CC BY 4.0"
        ),
        "kind": "DMI_STATION_OBSERVATION",
        "category": "INFO",
        "relation": "root",
        "lat": lat,
        "lon": lon,
        "altitude_m": altitude_m,
        "source": "DMI",
        "source_name": "Danish Meteorological Institute",
        "source_license": "CC BY 4.0",
        "source_license_url": DMI_LICENSE_URL,
        "source_terms_url": DMI_TERMS_URL,
        "source_station_id": station_id,
        "source_station_name": name,
        "source_station_feature_id": station_feature.get("id"),
        "source_station_timestamp": station_response_timestamp,
        "source_observation_feature_id": observation_feature.get("id"),
        "source_observation_timestamp": observed,
        "source_observation_parameter": parameter_id,
        "source_observation_value": value,
        "source_observation_response_timestamp": observation_response_timestamp,
        "imported": True,
        "import_source": "official_dmi_metobs",
    }


def fetch_station_atom(station_id: str = DEFAULT_STATION_ID) -> Tuple[Dict[str, Any], Dict[str, str]]:
    station_url = endpoint("station", {"stationId": station_id, "limit": "1"})
    observation_url = endpoint(
        "observation",
        {"stationId": station_id, "period": "latest", "limit": "1"},
    )
    station_payload = fetch_json(station_url)
    observation_payload = fetch_json(observation_url)
    atom = build_atom(station_payload, observation_payload, station_id)
    return atom, {"station_url": station_url, "observation_url": observation_url}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station-id", default=DEFAULT_STATION_ID)
    args = parser.parse_args()
    try:
        atom, urls = fetch_station_atom(args.station_id)
    except DmiImportError as exc:
        print(f"DMI import failed: {exc}", file=sys.stderr)
        return 1
    output = {"source_urls": urls, "atom": atom}
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
