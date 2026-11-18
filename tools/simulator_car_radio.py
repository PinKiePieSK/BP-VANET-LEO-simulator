"""Pin the effective ground PHY and antenna height of every car."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from simulator_sumo import validate_car_radio

FIELDS = ('id', 'tx_power_dbm', 'noise_figure_db', 'tx_gain_dbi',
          'rx_gain_dbi', 'antenna_height_m')


def render(world: dict, radio: dict, car_height_m: float) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(FIELDS)
    for car in world['vehicles']:
        override = car.get('radio_model', {})
        if override:
            validate_car_radio(override, f"{car['id']}.radio_model")
        writer.writerow((car['id'],
                         override.get('tx_power_dbm', radio['tx_power_dbm']),
                         override.get('noise_figure_db', radio['noise_figure_db']),
                         override.get('tx_gain_dbi', radio.get('tx_gain_dbi', 0)),
                         override.get('rx_gain_dbi', radio.get('rx_gain_dbi', 0)),
                         override.get('antenna_height_m', car_height_m)))
    return stream.getvalue().encode('utf-8')


def write(world: dict, radio: dict, car_height_m: float, path: Path) -> None:
    path.write_bytes(render(world, radio, car_height_m))
