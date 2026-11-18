# Mapuje verejné orbitálne ID na identifikátory a TLE formát, ktorý prijíma SNS-3 3.38. Pôvodné
# verejné ID sa zachováva v manifeste.
"""Map public NORAD catalogue IDs to collision-free five-digit SNS-3 TLE IDs.

SNS-3 3.38's SGP4 reader parses the five-character TLE field as decimal. The
public ID remains the sole external identity; the native TLE ID is local to a
single selected topology and is recorded separately in its model manifest.
"""
from __future__ import annotations

from sgp4 import exporter, omm
from sgp4.api import Satrec, WGS72


def native_ids(catalogs: list[int]) -> dict[int, int]:
    if (type(catalogs) is not list or not 1 <= len(catalogs) <= 40000 or
            any(type(cat) is not int or not 1 <= cat <= 999999 for cat in catalogs) or
            len(set(catalogs)) != len(catalogs)):
        raise ValueError('NORAD katalóg musí mať jedinečné kladné ID do 999999')
    used = {cat for cat in catalogs if cat <= 99999}
    mapping = {}
    next_free = 1
    for cat in catalogs:
        if cat <= 99999:
            mapping[cat] = cat
            continue
        while next_free in used:
            next_free += 1
        if next_free > 99999:
            raise ValueError('Nedostatok voľných interných TLE ID')
        mapping[cat] = next_free
        used.add(next_free)
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Kolízia interných TLE ID')
    return mapping


# Číta dvojriadkové elementy orbity a ich identitu. Tá istá pripnutá sada sa musí použiť v
# predpovedi aj v simulačnom behu.
def tle_lines(record: tuple, native_id: int) -> tuple[str, str]:
    catalog, _, omm_row, original = record
    if type(native_id) is not int or not 1 <= native_id <= 99999:
        raise ValueError('Interné TLE ID musí byť päťmiestne desiatkové číslo')
    if native_id == catalog:
        satellite = original
    else:
        aliased = dict(omm_row)
        aliased['NORAD_CAT_ID'] = native_id
        satellite = Satrec()
        omm.initialize(satellite, aliased, gravconst=WGS72)
    line1, line2 = exporter.export_tle(satellite)
    parsed = Satrec.twoline2rv(line1, line2, WGS72)
    if (len(line1) != 69 or len(line2) != 69 or
            parsed.satnum != native_id or line1[2:7] != line2[2:7]):
        raise ValueError(f'Neplatná rekonštrukcia TLE identity {catalog}')
    return line1, line2


# Mapuje katalógové ID na súbory a orbitálnu epochu. Tým sa predchádza zámene satelitov pri
# zobrazení a pri tvorbe SNS-3 topológie.
def manifest_mapping(catalogs: list[int]) -> dict[str, int]:
    mapping = native_ids(catalogs)
    return {str(cat): mapping[cat] for cat in catalogs if mapping[cat] != cat}


def expected_tle(catalogs: list[int], objects: list[tuple]) -> tuple[str, dict[str, int]]:
    records = {record[0]: record for record in objects}
    mapping = native_ids(catalogs)
    if not set(catalogs) <= set(records):
        raise ValueError('NORAD ID v pripnutom archíve chýba')
    lines = [str(len(catalogs))]
    for index, catalog in enumerate(catalogs):
        line1, line2 = tle_lines(records[catalog], mapping[catalog])
        lines.extend((f'{index} CATALOG {catalog}', line1, line2))
    return '\n'.join(lines) + '\n', manifest_mapping(catalogs)
