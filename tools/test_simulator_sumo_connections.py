"""A sharp OSM junction must remain traversable after netconvert."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from simulator_sumo import make_inputs, validate, verify_net_connections


@unittest.skipUnless(shutil.which("netconvert") and shutil.which("sumo"), "SUMO tools unavailable")
class SumoConnectionsTest(unittest.TestCase):
    def test_explicit_sharp_turn_is_driven(self):
        # Two one-way OSM ways share node n1 but meet at a near U-turn angle.
        world = {
            "schema_version": 2, "network_execution": "schema_only", "map_source": "osm_live",
            "georeference": {"frame": "WGS84_ENU", "anchor_x_m": 1000, "anchor_y_m": 1000,
                             "latitude_deg": 48.1, "longitude_deg": 17.1, "height_m": 0},
            "simulation": {"duration_s": 80, "step_s": 0.1, "seed": 1,
                           "utc_origin": "2026-11-13T12:00:00Z"},
            "roads": {
                "nodes": [{"id": "n0", "x_m": 783.9, "y_m": 1843.58},
                          {"id": "n1", "x_m": 745.55, "y_m": 1872.75},
                          {"id": "n2", "x_m": 818.36, "y_m": 1778.53}],
                "segments": [
                    {"id": "hummelova_in", "from": "n0", "to": "n1", "oneway": True,
                     "shape": [[783.9, 1843.58], [756.89, 1865.17], [745.55, 1872.75]],
                     "speed_limit_mps": 8.33, "lanes_each_direction": 1},
                    {"id": "hummelova_out", "from": "n1", "to": "n2", "oneway": True,
                     "shape": [[745.55, 1872.75], [753.86, 1862.57], [818.22, 1784.94], [818.36, 1778.53]],
                     "speed_limit_mps": 8.33, "lanes_each_direction": 1},
                ],
            },
            "vehicles": [
                {"id": "car0", "depart_s": 0, "depart_speed_mps": 5,
                 "vehicle_model": {"accel_mps2": 3.2, "length_m": 4.4},
                 "route": [{"segment": "hummelova_in", "direction": "forward"},
                           {"segment": "hummelova_out", "direction": "forward"}],
                 "technologies": ["its_g5"]},
                {"id": "car1", "depart_s": 20, "depart_speed_mps": 5,
                 "route": [{"segment": "hummelova_out", "direction": "forward"}],
                 "technologies": ["its_g5"]},
            ],
            "rsus": [],
            "flows": [{"id": "flow0", "source": "car0", "target": "car1",
                       "technology": "its_g5", "message_type": "CAM",
                       "execution": "not_implemented"}],
        }
        validate(world)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            make_inputs(world, directory)
            vehicle_types = {row.get("id"): row for row in
                             ET.parse(directory / "vehicles.rou.xml").getroot().findall("vType")}
            self.assertEqual(vehicle_types["passenger_car0"].get("accel"), "3.2")
            self.assertEqual(vehicle_types["passenger_car0"].get("length"), "4.4")
            self.assertEqual(vehicle_types["passenger_car1"].get("accel"), "2")
            self.assertEqual(vehicle_types["passenger_car1"].get("length"), "5")
            connections = ET.parse(directory / "road.con.xml").getroot()
            self.assertIn(("hummelova_in_forward", "hummelova_out_forward"),
                          {(c.get("from"), c.get("to")) for c in connections})
            subprocess.run(["netconvert", "--node-files", str(directory / "road.nod.xml"),
                            "--edge-files", str(directory / "road.edg.xml"),
                            "--connection-files", str(directory / "road.con.xml"),
                            "--output-file", str(directory / "road.net.xml"),
                            "--offset.disable-normalization", "true", "--no-warnings", "true"],
                           check=True, capture_output=True)
            verify_net_connections(directory)
            actual = {(c.get("from"), c.get("to")) for c in
                      ET.parse(directory / "road.net.xml").getroot().iter("connection")}
            self.assertIn(("hummelova_in_forward", "hummelova_out_forward"), actual)
            subprocess.run(["sumo", "--net-file", str(directory / "road.net.xml"),
                            "--route-files", str(directory / "vehicles.rou.xml"),
                            "--begin", "0", "--end", "80", "--step-length", "0.1",
                            "--fcd-output", str(directory / "fcd.xml"), "--no-step-log", "true"],
                           check=True, capture_output=True)
            driven = {v.get("lane", "").rsplit("_", 1)[0] for v in
                      ET.parse(directory / "fcd.xml").getroot().iter("vehicle") if v.get("id") == "car0"}
            self.assertIn("hummelova_in_forward", driven)
            self.assertIn("hummelova_out_forward", driven)


if __name__ == "__main__":
    unittest.main()
