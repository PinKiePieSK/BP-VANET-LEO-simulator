# Premenné DCC, fázy a CAM/antén sa prenášajú zo scenára do pozemného JSON, z ktorého vznikajú
# argumenty ns-3.
"""Input path and ground configuration shared by current simulator modes."""
from __future__ import annotations

import json
from pathlib import Path

from simulator_platform import ROOT
from simulator_engine_controls import effective as engine_controls


def project_input(name: str) -> Path:
    """Resolve a saved world or demand file inside data/inputs."""
    if not isinstance(name, str):
        raise ValueError('Input path must be text')
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or relative.parts[:2] != ('data', 'inputs'):
        raise ValueError('World and demand must be under data/inputs/')
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT / 'data/inputs') or not path.is_file():
        raise ValueError(f'Input missing: {name}')
    return path


# Táto funkcia je prekladateľ medzi názvami vo formulári a schémou pozemného runnera. Dĺžka sa
# mení na počet vzoriek po 100 ms, parametre rádia a seed sa odovzdajú ďalej bez skrytého druhého
# scenára.
def ground_config(scenario: dict, world_path: Path) -> dict:
    """Bind the scenario to the ns-3 WAVE ground runner input schema."""
    config = json.loads((ROOT / 'config/ground-radio-reference.json').read_text())
    # Pôvodný referenčný súbor je základ, ale scenár nahradí prahy, časový posun a aplikačné
    # spúšťače pre konkrétny beh.
    controls = engine_controls(scenario)
    config['dcc_policy'] = {'low_cbr': controls['dcc_low_cbr'],
                            'high_cbr': controls['dcc_high_cbr'],
                            'mid_interval_ms': controls['dcc_mid_interval_ms'],
                            'high_interval_ms': controls['dcc_high_interval_ms']}
    config['phase_us'] = controls['cam_phase_cap_us']
    config['engine'] = {key: controls[key] for key in controls if key.startswith('cam_') and key!='cam_phase_cap_us' or
                        key in ('car_antenna_height_m', 'rsu_antenna_min_height_m', 'rsu_roof_clearance_m')}
    config.update(base_world=str(world_path.relative_to(ROOT)),
                  source_id=scenario['source_id'], rsu_id=scenario['rsu_id'],
                  seed=scenario['seed'], run=scenario['ns3_run'],
                  sample_count=scenario['sample_count'],
                  tx_power_dbm=scenario['radio']['tx_power_dbm'],
                  noise_figure_db=scenario['radio']['noise_figure_db'],
                  rate_mbps=scenario['radio'].get('rate_mbps',6),
                  # Táto vrstva prekladá parameter používateľského scenára do konfiguračného
                  # súboru pozemného ns-3 runnera. Predvolený kanál 180 zodpovedá 5900 MHz.
                  channel_number=scenario['radio'].get('channel_number',180),
                  tx_gain_dbi=scenario['radio'].get('tx_gain_dbi',0),
                  rx_gain_dbi=scenario['radio'].get('rx_gain_dbi',0))
    config['cases'] = [{'id': 'scenario', 'demand': scenario['demand'],
                        # Prvý polohový a komunikačný krok je v t = 0. Dĺžka zostáva tá istá pre
                        # SUMO aj ns-3; oneskorený odchod auta sa zachytí ako chyba vstupu.
                        'first_sample_s': 0, 'radio_mode': scenario['radio']['mode'],
                        # DCC už nie je odvodené len z prítomnosti udalosti DENM; každý nový
                        # scenár môže porovnať zapnutý a vypnutý výskumný regulátor.
                        'dcc': controls['dcc_enabled'], 'shadowing': scenario['radio'].get('shadowing',False)}]
    return config
