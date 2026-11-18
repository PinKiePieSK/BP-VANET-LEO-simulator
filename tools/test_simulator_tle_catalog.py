"""The public NORAD identity survives SNS-3's decimal TLE input limit."""
import unittest

from simulator_tle_catalog import native_ids, tle_lines


class NativeCatalogIds(unittest.TestCase):
    def test_aliases_are_deterministic_and_collision_free(self):
        catalogs = [100001, 1, 99999, 100002, 2]
        self.assertEqual(native_ids(catalogs),
                         {100001: 3, 1: 1, 99999: 99999, 100002: 4, 2: 2})
        self.assertEqual(native_ids(catalogs), native_ids(catalogs))

    def test_rejects_duplicate_or_out_of_range_public_ids(self):
        for catalogs in ([100001, 100001], [0], [1000000], [True], []):
            with self.subTest(catalogs=catalogs), self.assertRaises(ValueError):
                native_ids(catalogs)

    def test_six_digit_omm_roundtrip_retains_orbit(self):
        import json
        import math
        from datetime import datetime, timezone
        from pathlib import Path

        from astropy.time import Time
        from sgp4.api import Satrec, WGS72
        from simulator_orbit_source import newest_default
        from simulator_orbits import load_orbits
        from simulator_platform import ROOT

        pin, origin = newest_default()
        config = json.loads((ROOT/'config/orbit-starlink-reference.json').read_text())
        config.update(snapshot=pin, utc_origin=origin)
        objects, _ = load_orbits(config)
        record = next(x for x in objects if x[0] > 99999)
        line1, line2 = tle_lines(record, 1)
        restored = Satrec.twoline2rv(line1, line2, WGS72)
        self.assertEqual(restored.satnum, 1)
        instant = Time(datetime.fromisoformat(origin.replace('Z', '+00:00')),
                       scale='utc')
        err_a, pos_a, _ = record[3].sgp4(instant.jd1, instant.jd2)
        err_b, pos_b, _ = restored.sgp4(instant.jd1, instant.jd2)
        self.assertEqual((err_a, err_b), (0, 0))
        self.assertLess(math.dist(pos_a, pos_b) * 1000, 2)


if __name__ == '__main__':
    unittest.main()
