"""Per-device simulator application/radio policy shared by preflight and native runners."""
from __future__ import annotations

ENV_KEYS = ('SIM_GROUND_OFF_CARS', 'SIM_CARS_ONLY', 'SIM_GROUND_OFF_RSUS',
            'SIM_SATELLITE_OFF_RSUS')


def environment(policy: dict | None) -> dict[str, str]:
    if policy is None:
        return {key: '' for key in ENV_KEYS}
    return {
        'SIM_GROUND_OFF_CARS': ','.join(n for n, v in policy['cars'].items() if v['ground'] == 'off'),
        'SIM_CARS_ONLY': ','.join(n for n, v in policy['cars'].items() if v['ground'] == 'cars'),
        'SIM_GROUND_OFF_RSUS': ','.join(n for n, v in policy['rsus'].items() if not v['ground']),
        'SIM_SATELLITE_OFF_RSUS': ','.join(n for n, v in policy['rsus'].items() if not v['satellite_backhaul']),
    }
