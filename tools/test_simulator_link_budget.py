import copy
import math
import unittest

from simulator_link_budget import evaluate, fspl_db, validate_assumptions


def fixture():
    scenario = {'satellite': {'orbit_group': 'globalstar'}}
    rows = []
    for time_us, distance in ((0, 1_000_000), (500_000, 999_500), (1_000_000, 999_000)):
        rows.append({'time_us': time_us, 'serving_catalog_id': 123,
                     'route_catalog_ids': [123], 'path_ranges_m': [distance, 1_100_000],
                     'antenna_off_axis_deg': 35})
    routes = {'step_us': 500_000, 'nodes': {'car-1': rows}}
    return scenario, routes


class LinkBudgetTest(unittest.TestCase):
    def test_public_geometry_never_claims_margin(self):
        scenario, routes = fixture()
        result = evaluate(scenario, routes)
        up = result['nodes']['car-1'][1]['user_uplink']
        down = result['nodes']['car-1'][1]['user_downlink']
        self.assertAlmostEqual(up['fspl_db'], fspl_db(999500, 1.615e9), places=4)
        self.assertGreater(up['doppler_hz'], 0)  # closing range -> positive Doppler
        self.assertNotEqual(up['frequency_hz'], down['frequency_hz'])
        self.assertIsNone(up['margin_db_interval'])
        self.assertEqual(result['nodes']['car-1'][1]['feeder_uplink']['assessment'],
                         'unknown_feeder_band_and_rf')

    def test_assumed_margin_interval_and_pointing_loss(self):
        scenario, routes = fixture()
        fields = {'eirp_dbw_interval': [20, 20], 'rx_gt_db_per_k_interval': [10, 10],
                  'required_cn0_dbhz_interval': [100, 100], 'other_loss_db_interval': [1, 3],
                  'pointing_loss_db_at_70deg_interval': [4, 8]}
        scenario['satellite']['link_budget'] = {'user_uplink': fields}
        output = evaluate(scenario, routes)['nodes']['car-1'][1]['user_uplink']
        loss = output['fspl_db']
        self.assertEqual(output['cn0_dbhz_interval'],
                         [round(20 + 10 + 228.6 - loss - 5, 4),
                          round(20 + 10 + 228.6 - loss - 2, 4)])
        self.assertEqual(output['assessment'], 'assumed_margin_negative')
        higher = copy.deepcopy(scenario)
        higher['satellite']['link_budget']['user_uplink']['eirp_dbw_interval'] = [80, 80]
        self.assertEqual(evaluate(higher, routes)['nodes']['car-1'][1]['user_uplink']['assessment'],
                         'assumed_margin_positive')

    def test_unknown_weather_and_invalid_feeder_are_explicit(self):
        scenario, routes = fixture()
        scenario['satellite']['link_budget'] = {'user_uplink': {
            'eirp_dbw_interval': [20, 20], 'rx_gt_db_per_k_interval': [10, 10],
            'required_cn0_dbhz_interval': [70, 70], 'other_loss_db_interval': [0, 0]}}
        scenario['satellite']['environment'] = {'statistical_layers': {
            'weather': {'assumed_loss_db_interval': None},
            'vegetation': {'assumed_loss_db_interval': None}}}
        item = evaluate(scenario, routes)['nodes']['car-1'][0]['user_uplink']
        self.assertIsNone(item['margin_db_interval'])
        self.assertIn('environmental_loss', item['assessment'])
        with self.assertRaises(ValueError):
            validate_assumptions({'feeder_uplink': {'eirp_dbw_interval': [10, 20]}})

    def test_feeder_needs_its_own_environment_assumption(self):
        scenario, routes = fixture()
        scenario['satellite']['environment'] = {'statistical_layers': {
            'weather': {'assumed_loss_db_interval': [1, 2]},
            'vegetation': {'assumed_loss_db_interval': [0, 1]}}}
        feeder = {'frequency_hz': 7e9, 'eirp_dbw_interval': [40, 40],
                  'rx_gt_db_per_k_interval': [15, 15],
                  'required_cn0_dbhz_interval': [60, 60],
                  'other_loss_db_interval': [1, 1]}
        scenario['satellite']['link_budget'] = {'feeder_downlink': feeder}
        item = evaluate(scenario, routes)['nodes']['car-1'][0]['feeder_downlink']
        self.assertIn('environmental_loss', item['assessment'])
        feeder['environment_loss_db_interval'] = [0, 3]
        item = evaluate(scenario, routes)['nodes']['car-1'][0]['feeder_downlink']
        self.assertIsNotNone(item['margin_db_interval'])


if __name__ == '__main__':
    unittest.main()
