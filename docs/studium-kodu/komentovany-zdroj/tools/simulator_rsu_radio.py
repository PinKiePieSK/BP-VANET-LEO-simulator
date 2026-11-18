# Vytvorí presný účinný rádiový profil každej RSU zo spoločného nastavenia scenára a
# individuálnych prepísaní. Rovnaké bajty kontrolujú nezávislé verifiery.
"""Pin per-RSU ground PHY overrides used by both native packet backends."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from simulator_sumo import validate_rsu_radio

FIELDS = ('id', 'tx_power_dbm', 'noise_figure_db', 'tx_gain_dbi',
          'rx_gain_dbi', 'antenna_height_m')


# Pri každej RSU sa prepíšu iba nastavené polia. Nezadaná výška je −1 a natívny engine ju počíta z
# budovy alebo minima; ostatné polia dedia spoločný profil.
def render(world: dict, radio: dict) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(FIELDS)
    for rsu in world['rsus']:
        override = rsu.get('radio_model', {})
        if override:
            validate_rsu_radio(override, f"{rsu['id']}.radio_model")
        writer.writerow((rsu['id'],
                         override.get('tx_power_dbm', radio['tx_power_dbm']),
                         override.get('noise_figure_db', radio['noise_figure_db']),
                         override.get('tx_gain_dbi', radio.get('tx_gain_dbi', 0)),
                         override.get('rx_gain_dbi', radio.get('rx_gain_dbi', 0)),
                         override.get('antenna_height_m', -1)))
    return stream.getvalue().encode('utf-8')


def write(world: dict, radio: dict, path: Path) -> None:
    path.write_bytes(render(world, radio))
