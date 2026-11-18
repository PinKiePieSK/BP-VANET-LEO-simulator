"""The Slovak extract must be selected only for wholly covered sites."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import simulator_osm_local_extract as local
import simulator_osm_road_graph as roads


class SlovakiaLocalPbfTest(unittest.TestCase):
    def test_country_boundary_and_concave_cutout(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            pbf, manifest, polygon = (base / name for name in ("data.pbf", "manifest.json", "country.poly"))
            pbf.write_bytes(b"x")
            manifest.write_text("{}")
            polygon.write_text("test\n1\n0 0\n4 0\n4 4\n3 4\n3 1\n1 1\n1 4\n0 4\n0 0\nEND\nEND\n")
            with patch.object(local, "PBF", pbf), patch.object(local, "MANIFEST", manifest), patch.object(local, "POLYGON", polygon):
                self.assertTrue(local.covers((0.2, 0.2, 0.8, 0.8)))
                self.assertFalse(local.covers((0.5, 0.5, 3.5, 3.5)))
                self.assertFalse(local.covers((4.2, 0.2, 4.8, 0.8)))

    def test_local_provenance_and_existing_api_fallback(self):
        geo = {"frame": "WGS84_ENU", "anchor_x_m": 1000, "anchor_y_m": 1000,
               "latitude_deg": 48.145, "longitude_deg": 17.11, "height_m": 0}
        raw = (b'<osm version="0.6"><node id="1" lat="48.145" lon="17.11"/>'
               b'<node id="2" lat="48.1451" lon="17.1101"/>'
               b'<way id="3"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way></osm>')
        box = roads.bbox_for(geo)
        meta = {"sha256": "a" * 64, "source_data_utc": "2026-10-31T21:23:06Z"}
        with patch.object(local, "covers", return_value=False), patch.object(local, "extract", return_value=([(box, raw)], meta)), patch.object(roads, "download") as network:
            result = roads.load(geo)
            network.assert_not_called()
            self.assertEqual(result["source"]["provider"], "geofabrik-slovakia-pbf")
            self.assertEqual(result["source"]["dataset_sha256"], "a" * 64)
            self.assertTrue(result["roads"])
        with patch.object(local, "covers", return_value=False), patch.object(local, "extract", return_value=None), patch.object(roads, "download", return_value=[(box, raw)]) as network:
            result = roads.load(geo)
            network.assert_called_once_with(box)
            self.assertEqual(result["source"]["provider"], "openstreetmap-api-v0.6")


if __name__ == "__main__":
    unittest.main()
