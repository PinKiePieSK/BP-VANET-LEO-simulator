"""Export pinned OSM footprints for the native ITS-G5 LOS/NLOS condition.

The selected building height is a scenario sensitivity, not a measured wall
loss. Ground antenna heights remain the declared ns-3 mounting assumptions.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from simulator_local_environment import validate_environment


def export_bytes(environment: dict) -> bytes:
    validate_environment(environment, environment['georeference'])
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('id', 'height_m', 'polygon_xy_m'))
    case = environment.get('height_case', 'interval')
    for building in environment['buildings']:
        height = (building['height_min_m'] if case == 'low' else
                  building['height_max_m'] if case == 'high' else
                  building.get('height_central_m',
                               (building['height_min_m'] + building['height_max_m']) / 2))
        polygon = ';'.join(f'{x:.2f}:{y:.2f}' for x, y in building['polygon_xy_m'])
        writer.writerow((building['id'], f'{height:.2f}', polygon))
    return output.getvalue().encode('utf-8')


def write(environment: dict, path: Path) -> int:
    raw = export_bytes(environment)
    if len(environment['buildings']) == 0:
        raise ValueError('Ground obstruction model requires at least one building')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return len(environment['buildings'])
