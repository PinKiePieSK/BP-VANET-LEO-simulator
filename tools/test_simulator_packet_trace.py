"""Raw packet checks must reject altered bytes even when the log text looks valid."""
import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from simulator_packet_trace import decode_isl, hops, pcap_packets


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    total = sum(int.from_bytes(data[i:i + 2], "big") for i in range(0, len(data), 2))
    while total >> 16:
        total = (total & 0xffff) + (total >> 16)
    return ~total & 0xffff


def ipv4_udp(payload: bytes) -> bytes:
    source, target = bytes((10, 0, 0, 1)), bytes((10, 0, 0, 2))
    udp = bytearray(struct.pack("!HHHH", 12345, 45000, len(payload) + 8, 0) + payload)
    pseudo = source + target + b"\0\x11" + len(udp).to_bytes(2, "big")
    struct.pack_into("!H", udp, 6, checksum(pseudo + udp))
    ip = bytearray(b"\x45\0" + (len(udp) + 20).to_bytes(2, "big") +
                   b"\0\0\0\0\x40\x11\0\0" + source + target)
    struct.pack_into("!H", ip, 10, checksum(ip))
    return bytes(ip + udp)


class PacketTraceTest(unittest.TestCase):
    def test_island_hop_requires_complete_checked_packet(self):
        payload = b"ICB1\x01" + bytes.fromhex("0102030405060708") + b"DENM"
        raw = ipv4_udp(payload)
        self.assertEqual(decode_isl(raw, len(payload), 45000), payload)
        log = (f"HANDOVER_ISL_REPORT_HOP=1,0,100\n"
               f"ISL_REPORT_RX_US=100,sat_node=1,protocol=2048,bytes={len(raw)}\n"
               f"ISL_IP_PACKET_HEX={raw.hex()}\n")
        self.assertEqual(hops(log, "report")["0102030405060708"],
                         [(100, (1, 0), payload)])
        corrupted = bytearray(raw)
        corrupted[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            decode_isl(bytes(corrupted), len(payload), 45000)
        with self.assertRaises(ValueError):
            hops(log.replace("sat_node=1", "sat_node=2"), "report")

    def test_pcap_rejects_truncated_frame(self):
        frame = b"abc"
        header = struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 105)
        record = struct.pack("<IIII", 1, 500, len(frame), len(frame)) + frame
        with TemporaryDirectory() as directory:
            path = Path(directory) / "capture.pcap"
            path.write_bytes(header + record)
            self.assertEqual(pcap_packets(path, 105), [(1_000_500, frame)])
            path.write_bytes((header + record)[:-1])
            with self.assertRaisesRegex(ValueError, "truncated"):
                pcap_packets(path, 105)
