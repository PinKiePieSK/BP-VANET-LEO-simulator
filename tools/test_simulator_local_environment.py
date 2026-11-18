import copy
import math
import unittest

import numpy as np

from simulator_local_environment import LocalObstructions, _height, impute_building_heights, validate_environment
from simulator_physical_coverage import site_ecef_km

GEO = {'frame': 'WGS84_ENU', 'anchor_x_m': 1000, 'anchor_y_m': 1000,
       'latitude_deg': 48.1486, 'longitude_deg': 17.1077, 'height_m': 0}
SITE = (GEO['latitude_deg'], GEO['longitude_deg'], 0.0)


def fixture(building=None, ridge=False):
    z = np.full((75, 75), 100.0)
    if ridge:
        z[:, 40] = 150
    return {'schema_version': 1, 'georeference': GEO,
            'uncertain_route_policy': 'optimistic_with_uncertainty_flag',
            'buildings': [building] if building else [],
            'terrain': {'origin_xy_m': [-120, -120], 'step_m': 30,
                        'width': 75, 'height': 75, 'elevation_m': z.flatten().tolist()},
            'sources': {'osm': {'sha256': 'synthetic'}, 'terrain': {'tiles': []}},
            'statistical_layers': {'vegetation': {'recommendation': 'ITU-R P.833-10', 'status': 'not_applied'},
                                   'weather': {'recommendation': 'ITU-R P.618-14', 'status': 'not_applied'}}}


def satellite(slope):
    lat, lon = map(math.radians, SITE[:2])
    east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
    return site_ecef_km(SITE) + 500 * east + 500 * slope * up


class LocalEnvironmentTest(unittest.TestCase):
    def test_height_provenance_and_rejection(self):
        self.assertEqual(_height({'height': '12 m'})[:3], (12, 12, 'osm_height_tag_unverified'))
        self.assertEqual(_height({'building:levels': '4'})[:2], (10, 16))
        self.assertEqual(_height({})[:2], (3, 30))
        env = fixture()
        validate_environment(env, GEO)
        bad = copy.deepcopy(env)
        bad['georeference']['latitude_deg'] += .01
        with self.assertRaises(ValueError):
            validate_environment(bad, GEO)

    def test_building_interval_and_clear_sight(self):
        building = {'id': 'b1', 'polygon_xy_m': [[1090, 990], [1110, 990], [1110, 1010], [1090, 1010]],
                    'height_min_m': 3, 'height_max_m': 30, 'height_source': 'unknown'}
        obs = LocalObstructions(fixture(building))
        self.assertEqual(obs.sight(SITE, satellite(.1), antenna_agl_m=1.5)[0], 'uncertain')
        building['height_min_m'] = 20
        self.assertEqual(LocalObstructions(fixture(building)).sight(SITE, satellite(.1), antenna_agl_m=1.5)[0], 'blocked')
        self.assertEqual(obs.sight(SITE, satellite(.5), antenna_agl_m=1.5)[0], 'clear')

    def test_terrain_ridge(self):
        self.assertEqual(LocalObstructions(fixture(ridge=True)).sight(SITE, satellite(.05), antenna_agl_m=1.5),
                         ('blocked', 'terrain'))
        self.assertEqual(LocalObstructions(fixture(ridge=True)).sight(SITE, satellite(.5), antenna_agl_m=1.5)[0],
                         'clear')

    def test_rectangular_working_area_terrain_grid(self):
        env = fixture()
        env['terrain'].update(width=142, height=108,
                              elevation_m=np.arange(142*108, dtype=float).tolist())
        observation = LocalObstructions(env)
        self.assertEqual(observation.z.shape, (108, 142))
        self.assertEqual(observation.height(-120 + 30*100, -120 + 30*70), 70*142+100)

    def test_local_median_and_three_sensitivity_heights(self):
        polygon = [[1090, 990], [1110, 990], [1110, 1010], [1090, 1010]]
        rows = [{'id': str(i), 'polygon_xy_m': polygon, 'height_min_m': 10 if i < 4 else 14,
                 'height_max_m': 10 if i < 4 else 14, 'height_source': 'osm_height_tag_unverified',
                 'height_reference': '', 'building_class': 'low_residential'} for i in range(8)]
        rows.append({'id': 'unknown', 'polygon_xy_m': polygon, 'height_min_m': 3,
                     'height_max_m': 30, 'height_source': 'unknown_3_to_30_m_sensitivity',
                     'height_reference': '', 'building_class': 'low_residential'})
        counts = impute_building_heights(rows)
        self.assertEqual(counts['imputed_buildings'], 1)
        self.assertEqual(rows[-1]['height_central_m'], 12)
        self.assertTrue(rows[-1]['height_min_m'] < 12 < rows[-1]['height_max_m'])
        for case, expected in [('low', 'clear'), ('central', 'blocked'), ('high', 'blocked')]:
            env = fixture(rows[-1])
            env['height_case'] = case
            validate_environment(env, GEO)
            self.assertEqual(LocalObstructions(env).sight(SITE, satellite(.1), antenna_agl_m=1.5)[0], expected)


if __name__ == '__main__':
    unittest.main()
