"""Editor positions must survive SUMO junction trimming on imported roads."""
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from simulator_sumo import align_route_positions


class RealMapPositionAlignmentTest(unittest.TestCase):
    def test_departure_and_destination_use_trimmed_lane_distance(self):
        world = {
            'map_source': 'osm_live',
            'roads': {'segments': [{'id': 'road', 'shape': [[0, 0], [100, 0]]}]},
            'vehicles': [{'id': 'car0', 'depart_pos_m': 50, 'arrival_pos_m': 80,
                          'route': [{'segment': 'road', 'direction': 'forward'}]}],
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'road.net.xml').write_text(
                '<net><edge id="road_forward"><lane id="road_forward_0" length="80" '
                'shape="20,2 100,2"/></edge></net>')
            (root / 'vehicles.rou.xml').write_text(
                '<routes><vehicle id="car0" departPos="50" arrivalPos="80"/></routes>')
            align_route_positions(world, root)
            vehicle = ET.parse(root / 'vehicles.rou.xml').getroot().find('vehicle')
            self.assertAlmostEqual(float(vehicle.get('departPos')), 30, places=2)
            self.assertAlmostEqual(float(vehicle.get('arrivalPos')), 60, places=2)


if __name__ == '__main__':
    unittest.main()
