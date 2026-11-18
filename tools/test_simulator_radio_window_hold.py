"""A short final SUMO lane must still retain its car for the CAM window."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from simulator_sumo import hold_vehicles_for_radio_window


class RadioWindowHold(unittest.TestCase):
    def test_stop_is_placed_inside_short_and_normal_final_lanes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'vehicles.rou.xml').write_text(
                '<routes><route id="short" edges="a_forward"/><route id="normal" edges="b_forward"/>'
                '<vehicle id="car0" route="short"/><vehicle id="car1" route="normal" arrivalPos="5"/></routes>')
            (root/'road.net.xml').write_text(
                '<net><edge><lane id="a_forward_0" length="0.20"/>'
                '<lane id="b_forward_0" length="20"/></edge></net>')
            hold_vehicles_for_radio_window(root,12.2)
            vehicles=ET.parse(root/'vehicles.rou.xml').getroot().findall('vehicle')
            for vehicle,length in zip(vehicles,(.2,20)):
                stop=vehicle.find('stop')
                self.assertIsNotNone(stop)
                self.assertLess(float(stop.get('endPos')),length)
                self.assertEqual(float(stop.get('until')),12.2)


if __name__=='__main__':unittest.main()
