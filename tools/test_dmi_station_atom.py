#!/usr/bin/env python3
"""Tests for the single-station DMI atom mapper."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import geohash3d, punkto  # noqa: E402
from tools.dmi_station_atom import build_atom  # noqa: E402


STATION_FIXTURE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "station-feature-id",
            "geometry": {"type": "Point", "coordinates": [10.4398, 55.3088]},
            "properties": {
                "stationId": "06126",
                "name": "Aarslev",
                "stationHeight": 49.2,
            },
        }
    ],
    "timeStamp": "2026-06-17T18:46:34Z",
    "numberReturned": 1,
    "links": [],
}

OBSERVATION_FIXTURE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "observation-feature-id",
            "geometry": {"type": "Point", "coordinates": [10.4398, 55.3088]},
            "properties": {
                "stationId": "06126",
                "observed": "2026-06-17T18:40:00Z",
                "parameterId": "temp_soil",
                "value": 15.11,
            },
        }
    ],
    "timeStamp": "2026-06-17T18:46:35Z",
    "numberReturned": 1,
    "links": [],
}


class DmiStationAtomTest(unittest.TestCase):
    def test_build_atom_preserves_dmi_identity_location_and_observation(self) -> None:
        atom = build_atom(STATION_FIXTURE, OBSERVATION_FIXTURE)

        self.assertTrue(punkto.validate(atom["punkto"]))
        self.assertTrue(atom["punkto"].endswith("-dmi06126"))
        self.assertEqual(atom["t"], 1781721600000)
        self.assertEqual(atom["source"], "DMI")
        self.assertEqual(atom["source_station_id"], "06126")
        self.assertEqual(atom["source_station_name"], "Aarslev")
        self.assertEqual(atom["source_station_timestamp"], "2026-06-17T18:46:34Z")
        self.assertEqual(atom["source_observation_timestamp"], "2026-06-17T18:40:00Z")
        self.assertEqual(atom["source_observation_parameter"], "temp_soil")
        self.assertEqual(atom["source_observation_value"], 15.11)
        self.assertTrue(atom["imported"])
        self.assertEqual(atom["import_source"], "official_dmi_metobs")

        spatial = atom["punkto"][2:].split("-", 1)[0]
        decoded = geohash3d.decode(spatial)
        self.assertLessEqual(abs(decoded.lat - atom["lat"]), decoded.error_lat + 1e-12)
        self.assertLessEqual(abs(decoded.lon - atom["lon"]), decoded.error_lon + 1e-12)
        self.assertLessEqual(abs(decoded.alt - atom["altitude_m"]), decoded.error_alt + 1e-12)

    def test_build_atom_rejects_missing_station_height_for_selected_station(self) -> None:
        station = {
            **STATION_FIXTURE,
            "features": [
                {
                    **STATION_FIXTURE["features"][0],
                    "properties": {
                        **STATION_FIXTURE["features"][0]["properties"],
                        "stationHeight": None,
                    },
                }
            ],
        }

        with self.assertRaisesRegex(Exception, "stationHeight"):
            build_atom(station, OBSERVATION_FIXTURE)


if __name__ == "__main__":
    unittest.main()
