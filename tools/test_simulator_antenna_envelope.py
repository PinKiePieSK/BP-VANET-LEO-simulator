import unittest

import numpy as np

from simulator_antenna_envelope import starlink_fov_mask, validate_mounts
from simulator_physical_coverage import site_ecef_km


class AntennaEnvelopeTest(unittest.TestCase):
    def test_starlink_panel_direction_and_car_heading(self):
        site = (0.0, 0.0, 0.0)
        ground = site_ecef_km(site)
        overhead = ground + np.array([600.0, 0.0, 0.0])
        northeast = ground + np.array([500.0, 0.0, 500.0])
        upright = {'tilt_deg': 0, 'azimuth_deg': 0, 'frame': 'north'}
        inverted = {'tilt_deg': 180, 'azimuth_deg': 0, 'frame': 'north'}
        vehicle = {'tilt_deg': 90, 'azimuth_deg': 0, 'frame': 'vehicle'}
        self.assertEqual(starlink_fov_mask(site, np.array([overhead]), upright)[0].tolist(), [True])
        self.assertEqual(starlink_fov_mask(site, np.array([overhead]), inverted)[0].tolist(), [False])
        self.assertEqual(starlink_fov_mask(site, np.array([northeast]), vehicle, 0)[0].tolist(), [True])
        self.assertEqual(starlink_fov_mask(site, np.array([northeast]), vehicle, 180)[0].tolist(), [False])

    def test_unknown_antenna_pattern_cannot_be_hard_gated(self):
        mount = {'car0': {'tilt_deg': 8, 'azimuth_deg': 0, 'frame': 'vehicle'}}
        for group in ('iridium-NEXT', 'globalstar'):
            with self.assertRaisesRegex(ValueError, 'iba pre terminál Starlink'):
                validate_mounts(group, mount, {'car0': 'car'})
        with self.assertRaisesRegex(ValueError, 'vehicle patrí iba autu'):
            validate_mounts('starlink', {'rsu0': mount['car0']}, {'rsu0': 'rsu'})


if __name__ == '__main__':
    unittest.main()
