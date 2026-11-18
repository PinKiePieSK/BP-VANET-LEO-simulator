"""OSM import keeps road semantics and all visible boundary components."""

import math
import unittest

from simulator_osm_road_graph import bbox_for, graph_from_xml


GEO = {"frame": "WGS84_ENU", "anchor_x_m": 1000, "anchor_y_m": 1000,
       "latitude_deg": 48.0, "longitude_deg": 17.0, "height_m": 0}


def node(index, x, y=1000):
    lon = 17 + (x - 1000) / (111320 * math.cos(math.radians(48)))
    lat = 48 + (y - 1000) / 110574
    return f'<node id="{index}" lon="{lon}" lat="{lat}"/>'


class OsmRulesTest(unittest.TestCase):
    def test_directional_values_and_via_node_restriction(self):
        raw = (f'<osm>{node(1, 900)}{node(2, 1000)}{node(3, 1100)}'
               '<way id="10"><nd ref="1"/><nd ref="2"/>'
               '<tag k="highway" v="residential"/><tag k="maxspeed:forward" v="60"/>'
               '<tag k="maxspeed:backward" v="30"/><tag k="lanes:forward" v="2"/>'
               '<tag k="lanes:backward" v="1"/><tag k="bridge" v="yes"/>'
               '<tag k="layer" v="1"/><tag k="access:conditional" v="no @ (Mo-Fr 08:00-09:00)"/></way>'
               '<way id="11"><nd ref="2"/><nd ref="3"/><tag k="highway" v="residential"/></way>'
               '<relation id="20"><member type="way" ref="10" role="from"/>'
               '<member type="node" ref="2" role="via"/>'
               '<member type="way" ref="11" role="to"/>'
               '<tag k="type" v="restriction"/><tag k="restriction" v="no_left_turn"/></relation></osm>').encode()
        graph = graph_from_xml([(bbox_for(GEO), raw)], GEO)
        road = next(row for row in graph["roads"] if row["osm_way_id"] == "10")
        self.assertEqual((road["lanes_forward"], road["lanes_reverse"]), (2, 1))
        self.assertAlmostEqual(road["speed_forward_mps"], 60 / 3.6, places=2)
        self.assertAlmostEqual(road["speed_reverse_mps"], 30 / 3.6, places=2)
        self.assertEqual(road["speed_forward_source"], "maxspeed:forward")
        self.assertEqual((road["bridge"], road["layer"]), (True, 1))
        self.assertNotIn("conditional_rules", road)
        self.assertEqual(graph["turn_restrictions"][0]["via_node_id"], "2")

    def test_reentering_work_area_keeps_both_road_pieces(self):
        raw = (f'<osm>{node(1, -100)}{node(2, 100)}{node(3, -100)}'
               f'{node(4, -200)}{node(5, 100)}'
               '<way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/>'
               '<nd ref="4"/><nd ref="5"/><tag k="highway" v="residential"/></way></osm>').encode()
        graph = graph_from_xml([(bbox_for(GEO), raw)], GEO)
        self.assertEqual(len(graph["roads"]), 2)
        self.assertGreater(graph["source"]["boundary_splits"], 0)


if __name__ == "__main__":
    unittest.main()
