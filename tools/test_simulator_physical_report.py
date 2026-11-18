import csv
import tempfile
import unittest
from pathlib import Path

from simulator_physical_report import classify, margin_status, packet_counts


ZERO = {'offers': 0, 'gateway_rx': 0, 'drops': 0, 'acks': 0}


class PhysicalReportTest(unittest.TestCase):
    def test_layers_do_not_turn_geometry_into_service(self):
        physical = {'candidate_count': 0}
        row = classify(physical, None, None, 0, ZERO, group='starlink',
                       mounted=False, environment=None)
        self.assertEqual(row['horizon_count'], 0)
        self.assertEqual(row['operator_status'], 'unverified')
        self.assertEqual(row['antenna_status'], 'terminal_disabled')
        physical['candidate_count'] = 1
        row = classify(physical, {'candidate_count': 0, 'obstruction_blocked_count': 0,
                                  'route_catalog_ids': [], 'serving_catalog_id': None},
                       None, 2, ZERO, group='starlink', mounted=True, environment={})
        self.assertEqual(row['horizon_count'], 2)
        self.assertEqual(row['public_envelope_count'], 1)
        self.assertEqual(row['antenna_status'], 'outside_declared_fov')
        self.assertEqual(row['operator_status'], 'unverified')
        with self.assertRaises(ValueError):
            classify(physical, None, None, 0, ZERO, group='starlink',
                     mounted=False, environment=None)

    def test_obstruction_rf_and_packet_are_independent(self):
        service = {'candidate_count': 0, 'obstruction_blocked_count': 2,
                   'obstruction_uncertain_count': 0,
                   'obstruction_guaranteed_candidate_count': 0,
                   'route_catalog_ids': [], 'serving_catalog_id': None}
        row = classify({'candidate_count': 2}, service, None, 3,
                       {**ZERO, 'gateway_rx': 1}, group='globalstar', mounted=False,
                       environment={})
        self.assertEqual(row['sight_status'], 'blocked_all_candidates')
        self.assertEqual(row['packet_status'], 'gateway_received_in_interval')
        self.assertEqual(row['operator_status'], 'unverified')
        positive = {'route_catalog_ids': [1], 'isl_budget': None}
        for key in ('user_uplink', 'user_downlink', 'feeder_uplink', 'feeder_downlink'):
            positive[key] = {'margin_db_interval': [1, 5]}
        self.assertEqual(margin_status(positive), 'assumed_positive')
        positive['isl_budget'] = 'unknown'
        self.assertEqual(margin_status(positive), 'unknown_isl_budget')
        positive['isl_budget'] = None
        positive['user_downlink']['margin_db_interval'] = [-3, -1]
        self.assertEqual(margin_status(positive), 'assumed_negative')

    def test_packet_stage_counts_use_original_offer_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'service_packets.csv'
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, ['stage', 'time_us', 'event_id', 'node_id'])
                writer.writeheader()
                writer.writerows([
                    {'stage': 'DIRECT_OFFER', 'time_us': 1000, 'event_id': 'x', 'node_id': 'car0'},
                    {'stage': 'GATEWAY_RX', 'time_us': 200000, 'event_id': 'x', 'node_id': 'gateway'},
                    {'stage': 'TERMINAL_ACK_RX', 'time_us': 600000, 'event_id': 'x', 'node_id': 'car0'}])
            counts = packet_counts(path, ['car0'], 2_000_000)
            self.assertEqual(counts['car0'][0]['offers'], 1)
            self.assertEqual(counts['car0'][0]['gateway_rx'], 1)
            self.assertEqual(counts['car0'][500000]['acks'], 1)


if __name__ == '__main__':
    unittest.main()
