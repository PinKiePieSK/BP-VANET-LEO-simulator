"""Read raw PCAP frames and verify IPv4/UDP packets on SNS-3 ISL hops."""
from __future__ import annotations

import re
import struct
from collections import defaultdict
from pathlib import Path


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def pcap_packets(path: Path, linktype: int) -> list[tuple[int, bytes]]:
    raw = path.read_bytes()
    require(len(raw) >= 24 and raw[:4] == b"\xd4\xc3\xb2\xa1" and
            struct.unpack_from("<I", raw, 20)[0] == linktype,
            f"invalid PCAP header: {path.name}")
    packets = []
    offset = 24
    while offset < len(raw):
        require(len(raw) >= offset + 16, "truncated PCAP packet header")
        sec, usec, length, original = struct.unpack_from("<IIII", raw, offset)
        offset += 16
        require(length == original and length <= len(raw) - offset and usec < 1000000,
                "truncated PCAP frame or timestamp")
        packets.append((sec * 1000000 + usec, raw[offset:offset + length]))
        offset += length
    return packets


def ones_complement_valid(data: bytes) -> bool:
    if len(data) % 2:
        data += b"\x00"
    total = sum(int.from_bytes(data[index:index + 2], "big")
                for index in range(0, len(data), 2))
    while total >> 16:
        total = (total & 0xffff) + (total >> 16)
    return total == 0xffff


def decode_isl(raw: bytes, size: int, destination_port: int) -> bytes:
    require(len(raw) == size + 28 and raw[0] == 0x45 and
            int.from_bytes(raw[2:4], "big") == len(raw) and raw[9] == 17 and
            ones_complement_valid(raw[:20]), "ISL IPv4 header or checksum invalid")
    udp = raw[20:]
    require(len(udp) == size + 8 and int.from_bytes(udp[4:6], "big") == len(udp) and
            int.from_bytes(udp[2:4], "big") == destination_port,
            "ISL UDP length or destination invalid")
    pseudo = raw[12:20] + b"\x00\x11" + len(udp).to_bytes(2, "big")
    require(ones_complement_valid(pseudo + udp), "ISL UDP checksum invalid")
    return udp[8:]


def hops(log: str, kind: str) -> dict[str, list[tuple[int, tuple[int, int], bytes]]]:
    """Pair each logged ISL hop with its complete checked application payload."""
    require(kind in {"report", "ack"}, "unknown ISL packet kind")
    label = "REPORT" if kind == "report" else "ACK"
    hex_label = "ISL_IP_PACKET_HEX" if kind == "report" else "ISL_ACK_IP_PACKET_HEX"
    pattern = (rf"^HANDOVER_ISL_{label}_HOP=(\d+),(\d+),(\d+)\n"
               rf"ISL_{label}_RX_US=(\d+),sat_node=(\d+),protocol=2048,bytes=(\d+)\n"
               rf"{hex_label}=([0-9a-f]+)$")
    result = defaultdict(list)
    for match in re.finditer(pattern, log, re.M):
        a, b, when, rx, node, size = map(int, match.groups()[:6])
        raw = bytes.fromhex(match.group(7))
        require(a == node and when == rx and len(raw) == size,
                "ISL hop metadata/size changed")
        packet = decode_isl(raw, size - 28, 45000 if kind == "report" else 45001)
        require(packet[:5] == (b"ICB1\x01" if kind == "report" else b"GRA1\x01"),
                "ISL application framing invalid")
        result[packet[5:13].hex()].append((when, (a, b), packet))
    require(log.count(f"HANDOVER_ISL_{label}_HOP=") == sum(map(len, result.values())),
            "ISL hop log unparsed")
    return result
