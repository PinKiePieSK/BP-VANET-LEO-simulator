# Preloží nastavenie rádia každého auta a RSU na presné prepínače pre natívny program. Vypnutý
# uzol tak nemôže náhodou komunikovať iba preto, že geometricky vidí druhý uzol.
"""Per-device simulator application/radio policy shared by preflight and native runners."""
from __future__ import annotations

ENV_KEYS = ('SIM_GROUND_OFF_CARS', 'SIM_CARS_ONLY', 'SIM_GROUND_OFF_RSUS',
            'SIM_SATELLITE_OFF_RSUS')


# Prepočíta individuálne politiky auta a RSU na vstupy pre natívne enginy. Práve tu sa prejaví
# vypnuté pozemné rádio alebo satelitný backhaul vybranej RSU.
def environment(policy: dict | None) -> dict[str, str]:
    if policy is None:
        return {key: '' for key in ENV_KEYS}
    return {
        'SIM_GROUND_OFF_CARS': ','.join(n for n, v in policy['cars'].items() if v['ground'] == 'off'),
        'SIM_CARS_ONLY': ','.join(n for n, v in policy['cars'].items() if v['ground'] == 'cars'),
        'SIM_GROUND_OFF_RSUS': ','.join(n for n, v in policy['rsus'].items() if not v['ground']),
        'SIM_SATELLITE_OFF_RSUS': ','.join(n for n, v in policy['rsus'].items() if not v['satellite_backhaul']),
    }
