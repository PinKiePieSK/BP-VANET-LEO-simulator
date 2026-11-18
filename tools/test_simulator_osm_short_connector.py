"""A short OSM way can be the only legal link between two longer roads."""

from __future__ import annotations

import math
import unittest

from simulator_osm_road_graph import graph_from_xml, local, basis, bbox_for
from simulator_sumo import validate


class OsmShortConnectorTest(unittest.TestCase):
    def test_pribinova_link_survives_import_and_sumo_validation(self):
        geo = {"frame": "WGS84_ENU", "anchor_x_m": 1000, "anchor_y_m": 1000,
               "latitude_deg": 48.1403, "longitude_deg": 17.1287, "height_m": 0}
        raw = b"""<osm version="0.6">
<node id="1" lon="17.1285358" lat="48.1403392"/>
<node id="2" lon="17.1288341" lat="48.1403122"/>
<node id="3" lon="17.1288517" lat="48.1403099"/>
<node id="4" lon="17.1290668" lat="48.1402877"/>
<way id="563753753"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
<way id="954672373"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
<way id="204438875"><nd ref="3"/><nd ref="4"/><tag k="highway" v="residential"/><tag k="oneway" v="yes"/></way>
</osm>"""
        imported = graph_from_xml([(bbox_for(geo), raw)], geo)
        by_way = {row["osm_way_id"]: row for row in imported["roads"]}
        order = ["563753753", "954672373", "204438875"]
        self.assertEqual(set(by_way), set(order))
        self.assertEqual(by_way[order[0]]["coordinates"][-1], by_way[order[1]]["coordinates"][0])
        self.assertEqual(by_way[order[1]]["coordinates"][-1], by_way[order[2]]["coordinates"][0])
        self.assertEqual(by_way[order[0]]["osm_to_node_id"], by_way[order[1]]["osm_from_node_id"])
        self.assertEqual(by_way[order[1]]["osm_to_node_id"], by_way[order[2]]["osm_from_node_id"])
        self.assertEqual(imported["source"]["import_revision"], 10)

        frame = basis(geo)
        node_ids = {}
        nodes, segments = [], []
        for way in order:
            record = by_way[way]
            shape = [[round(v, 1) for v in local(frame, *point)] for point in record["coordinates"]]
            for point in (shape[0], shape[-1]):
                key = tuple(point)
                if key not in node_ids:
                    node_ids[key] = f"node{len(nodes)}"
                    nodes.append({"id": node_ids[key], "x_m": point[0], "y_m": point[1]})
            segments.append({"id": record["id"], "from": node_ids[tuple(shape[0])],
                             "to": node_ids[tuple(shape[-1])], "shape": shape,
                             "speed_limit_mps": record["speed_limit_mps"],
                             "lanes_each_direction": record["lanes_each_direction"],
                             "oneway": record["oneway"]})
        self.assertEqual(segments[0]["to"], segments[1]["from"])
        self.assertEqual(segments[1]["to"], segments[2]["from"])
        connector_m = math.dist(*segments[1]["shape"])
        self.assertGreater(connector_m, 1)
        self.assertLess(connector_m, 2)
        world = {
            "schema_version": 2, "network_execution": "schema_only", "georeference": geo,
            "simulation": {"duration_s": 10, "step_s": 0.1, "seed": 1, "utc_origin": "2026-11-11T12:00:00Z"},
            "roads": {"nodes": nodes, "segments": segments},
            "vehicles": [
                {"id": "car0", "depart_s": 0, "depart_speed_mps": 5,
                 "route": [{"segment": row["id"], "direction": "forward"} for row in segments],
                 "technologies": ["its_g5"]},
                {"id": "car1", "depart_s": 0, "depart_speed_mps": 5,
                 "route": [{"segment": segments[2]["id"], "direction": "forward"}],
                 "technologies": ["its_g5"]},
            ],
            "rsus": [],
            "flows": [{"id": "flow0", "source": "car0", "target": "car1",
                       "technology": "its_g5", "message_type": "CAM",
                       "execution": "not_implemented"}],
        }
        validate(world)


if __name__ == "__main__":
    unittest.main()
