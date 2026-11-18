"""Check inherited and per-node PHY inputs before native packet execution."""
import csv
import io
import unittest

from simulator_rsu_radio import render
from simulator_car_radio import render as render_car_radio
from simulator_sumo import validate_car_radio
from simulator_engine_controls import effective


class RsuRadioTest(unittest.TestCase):
    def test_individual_override_and_shared_fallback(self):
        world = {'rsus': [
            {'id': 'rsu0', 'radio_model': {'tx_power_dbm': 26, 'antenna_height_m': 12}},
            {'id': 'rsu1'}]}
        shared = {'tx_power_dbm': 20, 'noise_figure_db': 7,
                  'tx_gain_dbi': 1, 'rx_gain_dbi': 2}
        rows = list(csv.DictReader(io.StringIO(render(world, shared).decode())))
        self.assertEqual(rows[0], {'id': 'rsu0', 'tx_power_dbm': '26',
                                   'noise_figure_db': '7', 'tx_gain_dbi': '1',
                                   'rx_gain_dbi': '2', 'antenna_height_m': '12'})
        self.assertEqual(rows[1]['tx_power_dbm'], '20')
        self.assertEqual(rows[1]['antenna_height_m'], '-1')

    def test_invalid_override_rejected(self):
        world = {'rsus': [{'id': 'rsu0', 'radio_model': {'tx_power_dbm': 40}}]}
        with self.assertRaises(ValueError):
            render(world, {'tx_power_dbm': 20, 'noise_figure_db': 7})

    def test_car_radio_override_and_inherited_height(self):
        world = {'vehicles': [
            {'id': 'car0', 'radio_model': {'tx_power_dbm': 26, 'antenna_height_m': 2.2}},
            {'id': 'car1'}]}
        shared = {'tx_power_dbm': 20, 'noise_figure_db': 7,
                  'tx_gain_dbi': 1, 'rx_gain_dbi': 2}
        rows = list(csv.DictReader(io.StringIO(render_car_radio(world, shared, 1.5).decode())))
        self.assertEqual(rows[0], {'id': 'car0', 'tx_power_dbm': '26',
                                   'noise_figure_db': '7', 'tx_gain_dbi': '1',
                                   'rx_gain_dbi': '2', 'antenna_height_m': '2.2'})
        self.assertEqual(rows[1]['tx_power_dbm'], '20')
        self.assertEqual(rows[1]['antenna_height_m'], '1.5')
        with self.assertRaises(ValueError):
            validate_car_radio({'antenna_height_m': 12}, 'car0.radio_model')

    def test_dcc_legacy_fallback_and_explicit_switch(self):
        self.assertFalse(effective({'denm_events': []})['dcc_enabled'])
        self.assertTrue(effective({'denm_events': [{'operation': 'new'}]})['dcc_enabled'])
        self.assertFalse(effective({'denm_events': [{'operation': 'new'}],
                                    'engine': {'dcc_enabled': False}})['dcc_enabled'])

    def test_satellite_control_time_order(self):
        with self.assertRaisesRegex(ValueError, 'Satelitné časy'):
            effective({'engine': {'satellite_apply_us': 2000001,
                                  'satellite_handover_request_us': 2000000}})
        self.assertEqual(effective({'engine': {'satellite_terminal_fov_deg': 55}})
                         ['satellite_terminal_fov_deg'], 55)


if __name__ == '__main__':
    unittest.main()
