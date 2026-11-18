"""Physical possibility bounds must not become a false active-service claim."""
import math
import unittest

from simulator_physical_coverage import assess, assess_pair, direct_link_policy, profile, site_ecef_km


class PhysicalCoverage(unittest.TestCase):
    def test_product_bands_and_native_direct_gate(self):
        base = dict(rf_hz=29.5e9, zenith_cone_deg=85, beam_half_angle_deg=5)
        expected = {'iridium-NEXT': (1.62125e9, 90, 90),
                    'globalstar': (1.615e9, 90, 90),
                    'starlink': (14.25e9, 65, 5)}
        for group, fields in expected.items():
            with self.subTest(group=group):
                self.assertEqual(tuple(direct_link_policy(group, base)[key] for key in
                                       ('rf_hz', 'zenith_cone_deg', 'beam_half_angle_deg')), fields)
                self.assertTrue(profile(group)['evidence_level'])

    def test_starlink_published_elevation_changes_candidate_set(self):
        earth = site_ecef_km((0, 0, 0))
        for elevation, expected in ((20, False), (30, True)):
            angle = math.radians(elevation)
            satellite = earth + [1000*math.sin(angle), 1000*math.cos(angle), 0]
            sl = assess('starlink', (0, 0, 0), satellite)
            self.assertAlmostEqual(sl['elevation_deg'], elevation, places=3)
            self.assertEqual(sl['public_envelope'], expected)
            self.assertTrue(assess('iridium-NEXT', (0, 0, 0), satellite)['public_envelope'])
        self.assertGreater(assess('starlink', (0, 0, 0), satellite)['free_space_loss_uplink_db'],
                           assess('iridium-NEXT', (0, 0, 0), satellite)['free_space_loss_uplink_db'])

    def test_globalstar_bent_pipe_needs_separate_feeder_sight(self):
        sat = site_ecef_km((0, 0, 0)) + [1400, 0, 0]
        same = assess_pair('globalstar', (0, 0, 0), (0, 1, 0), sat)
        opposite = assess_pair('globalstar', (0, 0, 0), (0, 180, 0), sat)
        self.assertTrue(same['same_satellite_two_leg_possible'])
        self.assertFalse(opposite['same_satellite_two_leg_possible'])
        self.assertFalse(opposite['feeder_geometry']['horizon'])
        self.assertNotIn('free_space_loss_uplink_db', same['feeder_geometry'])
        self.assertNotIn('public_envelope', same['feeder_geometry'])

    def test_invalid_satellite_rejected(self):
        with self.assertRaises(ValueError):
            assess('starlink', (0, 0, 0), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
