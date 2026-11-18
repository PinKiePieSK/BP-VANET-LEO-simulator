"""Join native SNS-3 layer events to DENM by the ns-3 packet UID."""
from __future__ import annotations

import csv
from collections import defaultdict
from functools import lru_cache


@lru_cache(maxsize=8)
def _joined(map_path, map_size, map_mtime, log_path, log_size, log_mtime):
    with map_path.open(newline='') as stream:
        mappings = list(csv.DictReader(stream))
    by_uid = {}
    for row in mappings:
        uid = row['packet_uid']
        if uid in by_uid and by_uid[uid] != row:
            raise ValueError('Jeden SNS-3 packet UID patrí viacerým DENM')
        if (not uid.isdecimal() or len(row['event_id']) != 16 or
                row['direction'] not in ('FWD', 'RTN') or
                row['node_type'] not in ('UT', 'GW') or
                len(row['raw_hex']) != 2 * int(row['bytes'])):
            raise ValueError('Neplatná SNS-3 väzba IP paketu na DENM')
        by_uid[uid] = row
    joined = []
    with log_path.open() as stream:
        for line in stream:
            fields = line.split()
            if (len(fields) < 8 or fields[1] not in ('SND', 'RCV', 'DRP', 'ENQ') or
                    fields[2] not in ('UT', 'SAT', 'GW') or
                    fields[5] not in ('ND', 'LLC', 'MAC', 'PHY', 'CH') or
                    fields[6] not in ('FWD', 'RTN')):
                continue
            # PacketTrace môže do jedného DVB rámca vložiť viac IP paketov.
            # Numerické tokeny za hlavičkou sú ns-3 UID; MAC adresy sa ignorujú.
            for position, uid in enumerate(fields[7:], start=7):
                if uid not in by_uid:
                    continue
                mapped = by_uid[uid]
                if fields[6] != mapped['direction']:
                    continue
                when = int(round(float(fields[0]) * 1_000_000))
                record = {'stage': f'SNS3_{fields[5]}_{fields[1]}_{fields[6]}',
                          'node': f'{fields[2]} {fields[3]}',
                          'id': mapped['event_id'], 'time_us': when,
                          'bytes': int(mapped['bytes']), 'packet_uid': int(uid),
                          'native_level': fields[5], 'native_event': fields[1],
                          'native_direction': fields[6], 'mac': fields[4],
                          'source': fields[position+1] if len(fields) > position+1 and
                                    ':' in fields[position+1] else '',
                          'destination': fields[position+2] if len(fields) > position+2 and
                                         ':' in fields[position+2] else ''}
                if (fields[5] == 'ND' and fields[1] == 'SND' and
                        fields[2] == mapped['node_type'] and fields[3] == mapped['node_id']):
                    record['raw_hex'] = mapped['raw_hex']
                joined.append(record)
    # Python stable sort keeps PacketTrace order for equal timestamps.
    joined.sort(key=lambda row: row['time_us'])
    return tuple(joined), tuple(mappings)


def load(folder):
    """Old sealed runs without an IP UID map retain their original packet view."""
    mapping = folder / 'satellite-ip-trace.csv'
    log = folder / 'PacketTrace.log'
    if not mapping.is_file() or not log.is_file():
        return (), ()
    a, b = mapping.stat(), log.stat()
    return _joined(mapping, a.st_size, a.st_mtime_ns,
                   log, b.st_size, b.st_mtime_ns)


def by_event(folder):
    groups = defaultdict(list)
    for row in load(folder)[0]:
        groups[row['id']].append(row)
    return groups
