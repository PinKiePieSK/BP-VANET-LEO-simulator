"""Check that a native control frame never inherits a DENM identity."""
import tempfile
import unittest
from pathlib import Path

from simulator_satellite_trace import load


class SatelliteTraceTest(unittest.TestCase):
    def test_ground_run_has_no_native_steps(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(load(Path(temporary)), ((), ()))

    def test_uid_join_and_layer_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'satellite-ip-trace.csv').write_text(
                'packet_uid,event_id,node_type,node_id,direction,time_us,bytes,raw_hex\n'
                '977,d319516eb46351c4,UT,2,RTN,5000000,2,4500\n')
            (folder / 'PacketTrace.log').write_text(
                '5 SND UT 2 aa ND RTN 977\n'
                '5.1 SND UT 2 aa PHY RTN 977 bb cc 978 bb cc\n'
                '5.2 RCV SAT 0 bb PHY RTN 977 bb cc\n'
                '5.3 RCV GW 1 cc ND RTN 977\n'
                '5.4 SND GW 1 cc ND FWD 977\n'
                '5.5 SND GW 1 cc ND FWD 978\n')
            rows, mapping = load(folder)
            self.assertEqual(len(mapping), 1)
            self.assertEqual(len(rows), 4)
            self.assertEqual([row['node'] for row in rows],
                             ['UT 2', 'UT 2', 'SAT 0', 'GW 1'])
            self.assertEqual([row.get('raw_hex') for row in rows],
                             ['4500', None, None, None])


if __name__ == '__main__':
    unittest.main()
