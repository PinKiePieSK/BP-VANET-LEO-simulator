"""A satellite entering the user envelope must appear in the temporal record."""
import csv
import tempfile
import unittest
from pathlib import Path

from simulator_orbit_source import newest_default
from simulator_time_visibility import calculate, audit_packet_geometry


class TimeVisibility(unittest.TestCase):
    def test_packet_below_published_envelope_is_rejected(self):
        pin, origin = newest_default()
        scenario = {'satellite_enabled': True, 'sample_count': 60,
                    'utc_origin': origin, 'rsu_id': 'rsu-a',
                    'satellite': {'orbit_group': 'starlink', 'orbit_snapshot': pin,
                                  'mask_deg': 0.5, 'catalog_ids': [46063],
                                  'initial_serving_sat': 0}}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with (folder/'waypoints.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=('node_id', 'time_us',
                                                            'latitude_e7', 'longitude_e7',
                                                            'altitude_cm'))
                writer.writeheader()
                writer.writerow({'node_id': 'car0', 'time_us': 10_000_000,
                                 'latitude_e7': 481448785, 'longitude_e7': 171050084,
                                 'altitude_cm': 0})
            with (folder/'trace.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=('stage', 'event_id', 'node_id', 'time_us'))
                writer.writeheader()
            with (folder/'direct_link.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=('car', 'time_us', 'sat_id', 'accepted'))
                writer.writeheader()
                writer.writerow({'car': 'car0', 'time_us': 11_002_000,
                                 'sat_id': 0, 'accepted': 1})
            (folder/'run.log').write_text('')
            with self.assertRaisesRegex(ValueError, 'Paket mimo fyzikálnej obálky'):
                audit_packet_geometry(scenario, folder)

    def test_each_terminal_has_independent_timed_candidates(self):
        pin, origin = newest_default()
        scenario = {'satellite_enabled': True, 'sample_count': 60,
                    'utc_origin': origin,
                    'satellite': {'orbit_group': 'starlink', 'orbit_snapshot': pin,
                                  'mask_deg': 0.5}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'waypoints.csv'
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=('node_id', 'time_us',
                                                            'latitude_e7', 'longitude_e7',
                                                            'altitude_cm'))
                writer.writeheader()
                for node, lat, lon in [('rsu-a', 48.1448785, 17.1050084),
                                       ('rsu-b', 48.6448785, 17.6050084)]:
                    for t in (10_000_000, 16_000_000):
                        writer.writerow({'node_id': node, 'time_us': t,
                                         'latitude_e7': round(lat*1e7),
                                         'longitude_e7': round(lon*1e7),
                                         'altitude_cm': 0})
            result = calculate(scenario, path)
        self.assertEqual(len(result['nodes']['rsu-a']), 13)
        self.assertEqual(result['nodes']['rsu-a'][0]['time_us'], 0)
        self.assertEqual(result['nodes']['rsu-a'][-1]['time_us'], 6_000_000)
        self.assertNotEqual(result['initial_candidates']['rsu-a'],
                            result['initial_candidates']['rsu-b'])
        entered = {catalog for row in result['nodes']['rsu-a']
                   for catalog in row['entered_catalog_ids']}
        self.assertTrue(entered)
        self.assertFalse(entered & set(result['initial_candidates']['rsu-a']))
        self.assertTrue(all(row['candidate_count'] > 0 and row['best_catalog_id']
                            for row in result['nodes']['rsu-a']))


if __name__ == '__main__':
    unittest.main()
