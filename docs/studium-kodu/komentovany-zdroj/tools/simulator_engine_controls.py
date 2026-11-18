# Spoločný register scenárových premenných pre natívny engine. Staršie scenáre dedia pôvodné
# hodnoty; hranice bránia neplatným kombináciám prahov, frontov a RF predpokladov.
"""Editable scenario inputs shared by the editor, preflight and native runners."""
from __future__ import annotations

import math

DEFAULTS = {
    'dcc_enabled': False,
    'dcc_low_cbr': 0.004, 'dcc_high_cbr': 0.012,
    'dcc_mid_interval_ms': 250, 'dcc_high_interval_ms': 500,
    'cam_distance_m': 4.0, 'cam_speed_mps': 0.5, 'cam_heading_deg': 4.0,
    'cam_low_frequency_ms': 500, 'cam_tgen_max_ms': 1000,
    'cam_periodic_repeat': 3,
    'cam_phase_cap_us': 1000,
    'car_antenna_height_m': 1.5, 'rsu_antenna_min_height_m': 5.0,
    'rsu_roof_clearance_m': 2.0,
    'backhaul_forward_queue_packets': 512, 'backhaul_reverse_queue_packets': 512,
    'backhaul_forward_service_us': 1, 'backhaul_reverse_service_us': 1,
    'satellite_rtn_feeder_freq_hz': 17_700_000_000,
    'satellite_ut_rx_temp_dbk': 24.6,
    'satellite_sat_user_rx_temp_dbk': 28.4,
    'satellite_gw_rx_temp_dbk': 24.62,
    'satellite_sat_queue_max_packets': 10000,
    'satellite_control_slot_ms': 100,
    'satellite_rtn_arq': False, 'satellite_fwd_acm': True,
    'satellite_rtn_acm': True,
    'satellite_default_fwd_modcod': 'QPSK_1_TO_2',
    'satellite_isl_speed_mps': 299792458.0,
    'satellite_terminal_fov_deg': 70.0,
    # Súbežné satelitné časy majú jednotku mikrosekunda a povinné poradie. Staršie scenáre preberú
    # pôvodné hodnoty, nový editor ich zapisuje výslovne.
    'satellite_handover_request_us': 1000000,
    'satellite_apply_us': 2500000,
    'satellite_burst_release_us': 3500000,
}

BOUNDS = {
    'dcc_low_cbr': (0, 1), 'dcc_high_cbr': (0, 1),
    'dcc_mid_interval_ms': (100, 1000), 'dcc_high_interval_ms': (100, 1000),
    'cam_distance_m': (0, 100), 'cam_speed_mps': (0, 20),
    'cam_heading_deg': (0, 180), 'cam_low_frequency_ms': (100, 1000),
    'cam_tgen_max_ms': (100, 1000), 'cam_periodic_repeat': (1, 20),
    'cam_phase_cap_us': (0, 1000),
    'car_antenna_height_m': (0.2, 10), 'rsu_antenna_min_height_m': (0.2, 100),
    'rsu_roof_clearance_m': (0, 50),
    'backhaul_forward_queue_packets': (1, 1000),
    'backhaul_reverse_queue_packets': (1, 1000),
    'backhaul_forward_service_us': (1, 1000000),
    'backhaul_reverse_service_us': (1, 1000000),
    'satellite_rtn_feeder_freq_hz': (1e9, 5e10),
    'satellite_ut_rx_temp_dbk': (0, 60),
    'satellite_sat_user_rx_temp_dbk': (0, 60),
    'satellite_gw_rx_temp_dbk': (0, 60),
    'satellite_sat_queue_max_packets': (1, 100000),
    'satellite_control_slot_ms': (10, 1000),
    'satellite_isl_speed_mps': (1e8, 299792458),
    'satellite_terminal_fov_deg': (1, 180),
    'satellite_handover_request_us': (1000000, 10000000),
    'satellite_apply_us': (2000001, 14000000),
    'satellite_burst_release_us': (3000000, 15000000),
}


# Validácia vracia úplný účinný profil. Tento istý profil používajú runner aj technické rozhranie,
# preto zmena položky skutočne zmení argumenty behu.
def effective(scenario: dict) -> dict:
    """Older scenarios inherit defaults; a new scenario stores its complete profile."""
    supplied = scenario.get('engine', {})
    if not isinstance(supplied, dict) or set(supplied) - set(DEFAULTS):
        raise ValueError('Neplatná konfigurácia enginu')
    result = {**DEFAULTS, **supplied}
    if 'dcc_enabled' not in supplied:
        result['dcc_enabled'] = bool(scenario.get('denm_events'))
    for key, (minimum, maximum) in BOUNDS.items():
        value = result[key]
        if (type(value) not in (int, float) or not math.isfinite(value) or
                not minimum <= value <= maximum or
                type(DEFAULTS[key]) is int and type(value) is not int):
            raise ValueError(f'Neplatná hodnota enginu: {key}')
    for key in ('dcc_enabled', 'satellite_rtn_arq', 'satellite_fwd_acm', 'satellite_rtn_acm'):
        if type(result[key]) is not bool:
            raise ValueError(f'Neplatná hodnota enginu: {key}')
    if result['satellite_default_fwd_modcod'] not in ('QPSK_1_TO_2', 'QPSK_1_TO_4'):
        raise ValueError('Neplatná modulácia satelitného kanála')
    if not (result['dcc_low_cbr'] < result['dcc_high_cbr'] and
            result['dcc_mid_interval_ms'] <= result['dcc_high_interval_ms'] and
            result['cam_low_frequency_ms'] <= result['cam_tgen_max_ms']):
        raise ValueError('Prahy DCC a CAM musia byť vzostupné')
    if not (result['satellite_apply_us'] > result['satellite_handover_request_us'] + 1000000 and
            result['satellite_burst_release_us'] > result['satellite_apply_us'] + 100000):
        raise ValueError('Satelitné časy musia nasledovať: prepnutie, aplikácia, uvoľnenie')
    return result
