# Diagnostický výpočet orientačného link budgetu. Je oddelený od natívneho paketového kanála;
# číslo z tohto súboru samo nepredpovedá doručenie.
"""Auditable bidirectional RF sensitivity overlay for pinned simulator route frames.

P.525 free-space loss is geometric. Operator EIRP, G/T, beam state, modem
threshold and gateway feeder parameters are unknown unless a scenario supplies
explicit assumptions. A positive assumed margin is never commercial service.
"""
from __future__ import annotations

import math

from simulator_physical_coverage import LIGHT_M_S, profile

K_DB = 228.6  # -10 log10(k_B), dB(W/K/Hz), rounded
LEGS = ('user_uplink', 'user_downlink', 'feeder_uplink', 'feeder_downlink')


def _interval(value, key, lower=-200.0, upper=200.0):
    if (type(value) is not list or len(value) != 2 or
        any(type(v) not in (int, float) or not math.isfinite(v) or
            not lower <= v <= upper for v in value) or value[0] > value[1]):
        raise ValueError(f'Invalid link budget interval: {key}')
    return [float(value[0]), float(value[1])]


# `validate_assumptions()` kontroluje platnosť vstupu a pri chybe zastaví ďalší postup.
def validate_assumptions(config):
    if config is None:
        return
    if type(config) is not dict or set(config) - set(LEGS):
        raise ValueError('Unknown link budget leg')
    required = {'eirp_dbw_interval', 'rx_gt_db_per_k_interval',
                'required_cn0_dbhz_interval', 'other_loss_db_interval'}
    for leg, fields in config.items():
        if type(fields) is not dict or set(fields) - (required | {
            'frequency_hz', 'pointing_loss_db_at_70deg_interval',
            'environment_loss_db_interval'}):
            raise ValueError(f'Invalid link budget assumptions for {leg}')
        if leg.startswith('feeder') and ('frequency_hz' not in fields or
            type(fields['frequency_hz']) not in (int, float) or
            not math.isfinite(fields['frequency_hz']) or
            not 1e8 <= fields['frequency_hz'] <= 1e11):
            raise ValueError('Feeder frequency needs an explicit scenario assumption')
        if leg.startswith('user') and 'frequency_hz' in fields:
            raise ValueError('Published user-band frequency is selected by service')
        for key in required & set(fields):
            _interval(fields[key], key, 0, 100) if key == 'other_loss_db_interval' else _interval(fields[key], key)
        if 'pointing_loss_db_at_70deg_interval' in fields:
            _interval(fields['pointing_loss_db_at_70deg_interval'], 'pointing loss', 0, 100)
        if 'environment_loss_db_interval' in fields:
            _interval(fields['environment_loss_db_interval'], 'environment loss', 0, 100)


# Voľnopriestorová strata rastie s frekvenciou aj vzdialenosťou. Jednotky vstupu musia byť hertz a
# metre; výsledok je v dB. Ide o analytický odhad, nie o úspech natívneho paketu.
def fspl_db(range_m, frequency_hz):
    if not range_m > 0 or not frequency_hz > 0:
        raise ValueError('Positive range and frequency required')
    return 20 * math.log10(4 * math.pi * range_m * frequency_hz / LIGHT_M_S)


def _radial_speed(rows, index, *, feeder=False):
    row = rows[index]
    sat = row['serving_catalog_id']
    if sat is None:
        return None
    before = rows[index - 1] if index else None
    after = rows[index + 1] if index + 1 < len(rows) else None
    # Central difference when possible; one-sided at the experiment bounds.
    points = [x for x in (before, row, after)
              if x and x['serving_catalog_id'] == sat and x['path_ranges_m'] and
              (not feeder or x['route_catalog_ids'][-1] == row['route_catalog_ids'][-1])]
    if len(points) < 2:
        return None
    a, b = points[0], points[-1]
    dt = (b['time_us'] - a['time_us']) / 1e6
    path_index = -1 if feeder else 0
    return (b['path_ranges_m'][path_index] - a['path_ranges_m'][path_index]) / dt if dt > 0 else None


# Spojí vysielací výkon, anténne zisky, straty, teplotu a šírku pásma do hrubého link budgetu.
# Porovnanie s prahom je analýza citlivosti; skutočný generický DVB paket hodnotí SNS-3.
def _budget(leg, range_m, frequency_hz, fields, *, radial_mps=None,
            off_axis_deg=None, environmental_loss=None):
    result = {'frequency_hz': frequency_hz, 'range_m': range_m,
              'fspl_db': round(fspl_db(range_m, frequency_hz), 4),
              'doppler_hz': (round(-radial_mps * frequency_hz / LIGHT_M_S, 3)
                             if radial_mps is not None else None),
              'radial_speed_mps': round(radial_mps, 3) if radial_mps is not None else None,
              'off_axis_deg': off_axis_deg, 'cn0_dbhz_interval': None,
              'margin_db_interval': None, 'assessment': 'unknown_missing_rf_assumptions'}
    if fields is None:
        return result
    required = ('eirp_dbw_interval', 'rx_gt_db_per_k_interval',
                'required_cn0_dbhz_interval', 'other_loss_db_interval')
    missing = [key for key in required if key not in fields]
    if environmental_loss is None:
        missing.append('environmental_loss')
    if 'pointing_loss_db_at_70deg_interval' in fields and off_axis_deg is None:
        missing.append('off_axis')
    if missing:
        result['assessment'] = 'unknown_missing_' + '_'.join(missing)
        return result
    pointing = fields.get('pointing_loss_db_at_70deg_interval', [0, 0])
    scale = min(1.0, (off_axis_deg or 0) / 70) ** 2
    losses = [fields['other_loss_db_interval'][0] + environmental_loss[0] + pointing[0] * scale,
              fields['other_loss_db_interval'][1] + environmental_loss[1] + pointing[1] * scale]
    eirp, gt, threshold = (fields[key] for key in required[:3])
    cn0 = [eirp[0] + gt[0] + K_DB - result['fspl_db'] - losses[1],
           eirp[1] + gt[1] + K_DB - result['fspl_db'] - losses[0]]
    margin = [cn0[0] - threshold[1], cn0[1] - threshold[0]]
    result['cn0_dbhz_interval'] = [round(x, 4) for x in cn0]
    result['margin_db_interval'] = [round(x, 4) for x in margin]
    result['assessment'] = ('assumed_margin_positive' if margin[0] > 0 else
                            'assumed_margin_negative' if margin[1] < 0 else
                            'assumed_margin_straddles_zero')
    return result


# Vyhodnotí link budget vo vybraných časoch a pre vybrané geometrické dvojice. Výsledky ukladaj
# oddelene od raw RX udalostí, lebo analytická dostupnosť nemusí znamenať doručenie paketu.
def evaluate(scenario, routes):
    sat = scenario['satellite']
    group = sat['orbit_group']
    spec = profile(group)
    assumptions = sat.get('link_budget')
    validate_assumptions(assumptions)
    assumptions = assumptions or {}
    environment = sat.get('environment')
    losses = None
    if environment is None:
        losses = [0, 0]  # No F4 loss layer was selected.
    else:
        layers = environment['statistical_layers']
        values = [layers[k]['assumed_loss_db_interval'] for k in ('weather', 'vegetation')]
        if all(value is not None for value in values):
            losses = [sum(value[0] for value in values),
                      sum(value[1] for value in values)]
    output = {}
    for node, rows in routes['nodes'].items():
        series = []
        for index, row in enumerate(rows):
            path = row['path_ranges_m']
            item = {'time_us': row['time_us'], 'serving_catalog_id': row['serving_catalog_id'],
                    'route_catalog_ids': row['route_catalog_ids'], 'user_uplink': None,
                    'user_downlink': None, 'feeder_uplink': None, 'feeder_downlink': None,
                    'isl_budget': 'unknown_unverified_crosslink_rf_or_optical_parameters' if
                    len(row['route_catalog_ids']) > 1 else None}
            if path:
                radial = _radial_speed(rows, index)
                feeder_radial = _radial_speed(rows, index, feeder=True)
                off_axis = row.get('antenna_off_axis_deg')
                for leg, frequency in (('user_uplink', spec['user_uplink_hz']),
                                       ('user_downlink', spec['user_downlink_hz'])):
                    fields = assumptions.get(leg)
                    link_losses = fields.get('environment_loss_db_interval', losses) if fields else losses
                    item[leg] = _budget(leg, path[0], frequency, fields,
                                        radial_mps=radial, off_axis_deg=off_axis,
                                        environmental_loss=link_losses)
                for leg in ('feeder_uplink', 'feeder_downlink'):
                    fields = assumptions.get(leg)
                    if fields is None:
                        item[leg] = {'range_m': path[-1], 'frequency_hz': None,
                                     'fspl_db': None, 'assessment': 'unknown_feeder_band_and_rf'}
                    else:
                        # A weather/vegetation layer at the vehicle cannot
                        # describe the remote gateway; feeder loss is separate.
                        feeder_losses = fields.get('environment_loss_db_interval')
                        if feeder_losses is None and environment is None:
                            feeder_losses = [0, 0]
                        item[leg] = _budget(leg, path[-1], fields['frequency_hz'], fields,
                                            radial_mps=feeder_radial,
                                            environmental_loss=feeder_losses)
            series.append(item)
        output[node] = series
    return {'schema_version': 1, 'service': group, 'step_us': routes['step_us'],
            'assumption_status': 'explicit_scenario_assumption_not_operator_measurement' if assumptions else
                                 'no_rf_assumptions',
            'environmental_loss_status': 'explicit_scenario_assumption' if environment and losses is not None else
                                         'unknown_weather_vegetation' if environment else 'no_environment_layer_selected',
            'user_band_source': spec['sources'], 'model_source':
                'https://www.itu.int/rec/R-REC-P.525-5-202411-I/en',
            'nodes': output,
            'claim_boundary': 'P.525 free-space physics and optional assumed C/N0; no active beam, real modem threshold, verified feeder or commercial availability'}
