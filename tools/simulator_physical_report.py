#!/usr/bin/env python3
"""F6 physical evidence audit, separate from commercial availability claims.

All layers are kept independent: horizon, published user envelope, terminal
orientation, local sight, assumed RF margin and the native packet trace.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from simulator_cli import verify as verify_run
from simulator_clock import EXPERIMENT_START_S as START_S
from simulator_platform import ROOT
from simulator_orbit_source import config_for
from simulator_physical_coverage import profile
from simulator_time_visibility import _elevation, _site, _tracks
from simulator_orbits import load_orbits, sample

STEP_US = 500_000
CSV_FIELDS = ('node_id', 'time_us', 'horizon_count', 'public_envelope_count',
              'antenna_possible_count', 'clear_sight_count', 'uncertain_sight_count',
              'blocked_count', 'serving_catalog_id', 'antenna_status', 'sight_status',
              'margin_status', 'user_uplink_margin_low_db', 'user_uplink_margin_high_db',
              'user_downlink_margin_low_db', 'user_downlink_margin_high_db',
              'feeder_uplink_margin_low_db', 'feeder_uplink_margin_high_db',
              'feeder_downlink_margin_low_db', 'feeder_downlink_margin_high_db',
              'packet_status', 'packet_offers', 'packet_gateway_rx',
              'packet_drops', 'packet_acks', 'operator_status')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def horizon_counts(scenario, waypoints):
    """Pure 0° horizon per endpoint, from the same pinned OMM and SUMO WGS84."""
    sat = scenario['satellite']
    duration = scenario['sample_count'] / 10
    config = config_for(sat['orbit_group'], sat, scenario['utc_origin'], START_S + duration)
    config.update(utc_origin=scenario['utc_origin'], duration_s=START_S + duration,
                  sample_s=.5, mask_deg=sat['mask_deg'])
    objects, _ = load_orbits(config)
    frames, _ = sample(config, objects)
    tracks = _tracks(waypoints)
    indices = {node: 0 for node in tracks}
    result = {node: {} for node in tracks}
    expected = list(range(0, int(duration * 1e6) + 1, STEP_US))
    for frame in frames:
        elapsed = float(frame['elapsed_s'])
        if elapsed < START_S - 1e-8:
            continue
        logical_us = round((elapsed - START_S) * 1e6)
        xyz = np.asarray(frame['xyz_km'], dtype=np.float64)
        if xyz.shape != (len(objects), 3) or not np.isfinite(xyz).all():
            raise ValueError('Invalid pinned orbit frame in F6 horizon audit')
        for node, track in tracks.items():
            index = indices[node]
            while index + 1 < len(track) and int(track[index + 1]['time_us']) <= round(elapsed * 1e6):
                index += 1
            indices[node] = index
            result[node][logical_us] = int(np.count_nonzero(_elevation(xyz, _site(track[index])) >= 0))
    if any(list(rows) != expected for rows in result.values()):
        raise ValueError('F6 horizon timeline does not cover the experiment')
    return result


def packet_counts(path, nodes, end_us):
    fields = ('offers', 'gateway_rx', 'drops', 'acks')
    counts = {node: {} for node in nodes}
    if not path.is_file():
        return counts
    with path.open(newline='') as stream:
        records = list(csv.DictReader(stream))
    owners = {row['event_id']: row['node_id'] for row in records
              if row['stage'] in ('DIRECT_OFFER', 'RSU_REPORT_OFFER')}
    stages = {'DIRECT_OFFER': 'offers', 'RSU_REPORT_OFFER': 'offers',
              'GATEWAY_RX': 'gateway_rx', 'DROP': 'drops', 'TERMINAL_ACK_RX': 'acks'}
    for row in records:
        stage = stages.get(row['stage'])
        owner = owners.get(row['event_id'])
        logical = int(row['time_us']) - START_S * 1_000_000
        if stage is None or owner not in counts or not 0 <= logical <= end_us:
            continue
        tick = min((logical // STEP_US) * STEP_US, end_us)
        bucket = counts[owner].setdefault(tick, {key: 0 for key in fields})
        bucket[stage] += 1
    return counts


def native_packet_counts(path, nodes, end_us):
    """Count only observed native stages, owned by the creating RSU."""
    fields = ('offers', 'gateway_rx', 'drops', 'acks')
    counts = {node: {} for node in nodes}
    with path.open(newline='') as stream:
        records = list(csv.DictReader(stream))
    owners = {row['event_id']: row['node_id'] for row in records
              if row['stage'] == 'RSU_REPORT_CREATED'}
    stages = {'UT_SAT_REPORT_TX': 'offers', 'GATEWAY_ACCEPT': 'gateway_rx',
              'RSU_GRA1_RX': 'acks'}
    for row in records:
        field = stages.get(row['stage'])
        owner = owners.get(row['event_id'])
        logical = int(row['time_us']) - START_S * 1_000_000
        if field is None or owner not in counts or not 0 <= logical <= end_us:
            continue
        tick = min((logical // STEP_US) * STEP_US, end_us)
        bucket = counts[owner].setdefault(tick, {key: 0 for key in fields})
        bucket[field] += 1
    return counts


def native_analyze(base, scenario, timeline):
    manifest = json.loads((base/'native/editor-manifest.json').read_text())
    topology = manifest['topology']
    nodes = timeline['nodes']
    horizon = horizon_counts(scenario, base/'native/baseline/waypoints.csv')
    end_us = round(scenario['sample_count'] * 100_000)
    packets = native_packet_counts(base/'native/baseline/trace.csv', nodes, end_us)
    rf_path = base/'native/baseline/satellite_rf.csv'
    rf_counts = {node: {} for node in nodes}
    if rf_path.is_file():
        with rf_path.open(newline='') as stream:
            for signal in csv.DictReader(stream):
                owner=signal['rsu_id']
                logical=int(signal['time_us'])-START_S*1_000_000
                if owner not in rf_counts or not 0<=logical<=end_us:
                    continue
                tick=min((logical//STEP_US)*STEP_US,end_us)
                bucket=rf_counts[owner].setdefault(tick,{})
                reason=signal['reason']
                bucket[reason]=bucket.get(reason,0)+1
    active = {name for name, row in scenario['node_policy']['rsus'].items()
              if row['satellite_backhaul']}
    output = {}
    for node, physical_rows in nodes.items():
        enabled = node in active
        rows = []
        for physical in physical_rows:
            tick = physical['time_us']
            if tick not in horizon[node]:
                raise ValueError('Native horizon and physical timelines are misaligned')
            record = packets[node].get(tick, {'offers': 0, 'gateway_rx': 0,
                                              'drops': 0, 'acks': 0})
            signals=rf_counts[node].get(tick,{})
            if not enabled:
                antenna_status=sight_status='terminal_disabled'
            elif not rf_path.is_file():
                antenna_status='native_mask_candidate';sight_status='not_modelled'
            else:
                antenna_status=('native_mount_pointing_gate' if
                                scenario['satellite']['orbit_group']=='starlink' else
                                'native_directional_pattern_unquantified')
                sight_status=('native_building_mixed' if signals.get('building') and
                              signals.get('accepted') else
                              'native_building_blocked' if signals.get('building') else
                              'native_building_clear' if signals and
                              scenario['satellite'].get('environment') else
                              'no_local_building_input' if signals else
                              'native_no_signal_sample')
            result = {
                'horizon_count': horizon[node][tick],
                'public_envelope_count': physical['candidate_count'],
                'antenna_possible_count': len(topology['catalog_ids']) if enabled else 0,
                'clear_sight_count': 0, 'uncertain_sight_count': 0, 'blocked_count': 0,
                'serving_catalog_id': None,
                'route_catalog_ids': topology['catalog_ids'] if enabled else [],
                'antenna_status': antenna_status,
                'sight_status': sight_status,
                'margin_status': 'unknown_no_link_budget' if enabled else 'terminal_disabled',
                'packet_status': ('gateway_received_in_interval' if record['gateway_rx'] else
                                  'offered_no_gateway_rx_in_interval' if record['offers'] else
                                  'no_packet_event_in_interval'),
                'packet_offers': record['offers'],
                'packet_gateway_rx': record['gateway_rx'],
                'packet_drops': 0, 'packet_acks': record['acks'],
                'operator_status': 'unverified',
                'native_rf_signals': sum(signals.values()),
                'native_rf_reasons': signals,
            }
            for leg in ('user_uplink', 'user_downlink', 'feeder_uplink', 'feeder_downlink'):
                result[leg+'_margin_low_db'] = None
                result[leg+'_margin_high_db'] = None
            rows.append({'node_id': node, 'time_us': tick, **result})
        output[node] = rows
    run = json.loads((base/'run-manifest.json').read_text())
    return {'schema_version': 2, 'run_id': base.name,
            'service': scenario['satellite']['orbit_group'],
            'duration_s': scenario['sample_count']/10, 'step_us': STEP_US,
            'orbit_manifest_sha256': scenario['satellite']['orbit_snapshot']['manifest_sha256'],
            'run_manifest_sha256': digest(base/'run-manifest.json'),
            'source_hashes': {key: value for key, value in run['sources'].items()
                              if key in ('tools/simulator_time_visibility.py',
                                         'tools/simulator_physical_coverage.py')},
            'layer_order': ['pure_horizon', 'published_user_envelope',
                            'native_selected_topology',
                            'native_user_link_conditions' if rf_path.is_file() else
                            'satellite_sight_not_modelled',
                            'rf_margin_not_modelled', 'recorded_native_sns3_packets'],
            'csv_fields': list(CSV_FIELDS), 'nodes': output,
            'measurement_status': 'no_same_terminal_field_measurements_supplied',
            'claim_boundary': ('raw SNS-3 generic DVB packets; declared local user-link building, mounting and Doppler gates are applied when RF trace is present; '
                               'gateway local obstruction, calibrated link budget, active operator beams, modem and commercial service remain unverified')}


def margin_status(budget):
    if budget is None:
        return 'unknown_no_link_budget'
    if not budget['route_catalog_ids']:
        return 'no_route'
    legs = [budget.get(name) for name in ('user_uplink', 'user_downlink',
                                          'feeder_uplink', 'feeder_downlink')]
    margins = [leg.get('margin_db_interval') if leg else None for leg in legs]
    if any(value is not None and value[1] < 0 for value in margins):
        return 'assumed_negative'
    if budget.get('isl_budget'):
        return 'unknown_isl_budget'
    if any(value is None for value in margins):
        return 'unknown_rf_inputs'
    if all(value[0] > 0 for value in margins):
        return 'assumed_positive'
    return 'assumed_interval_crosses_zero'


def classify(physical, service, budget, horizon_count, packets, *, group, mounted, environment):
    envelope = physical['candidate_count']
    if horizon_count < envelope:
        raise ValueError('Published envelope exceeds pure horizon')
    terminal_enabled = service is not None
    antenna_count = (service['candidate_count'] + service.get('obstruction_blocked_count', 0)
                     if service else 0)
    blocked = service.get('obstruction_blocked_count', 0) if service else 0
    uncertain = service.get('obstruction_uncertain_count', 0) if service else 0
    clear = service.get('obstruction_guaranteed_candidate_count', 0) if service else 0
    if not terminal_enabled:
        antenna = 'terminal_disabled'
    elif not envelope:
        antenna = 'outside_public_envelope'
    elif group == 'starlink' and mounted:
        antenna = 'within_declared_fov' if antenna_count else 'outside_declared_fov'
    else:
        antenna = 'possible_pattern_unquantified'
    if not terminal_enabled:
        sight = 'terminal_disabled'
    elif environment is None:
        sight = 'not_modelled'
    elif service.get('serving_obstruction_status') in ('clear', 'uncertain'):
        sight = service['serving_obstruction_status']
    elif antenna_count and blocked == antenna_count:
        sight = 'blocked_all_candidates'
    elif not antenna_count:
        sight = 'no_antenna_candidate'
    else:
        sight = 'no_proxy_route_or_eligible_serving'
    margin = margin_status(budget) if terminal_enabled else 'terminal_disabled'
    if packets['gateway_rx']:
        packet = 'gateway_received_in_interval'
    elif packets['drops']:
        packet = 'model_drop_in_interval'
    elif packets['offers']:
        packet = 'offered_no_gateway_rx_in_interval'
    else:
        packet = 'no_packet_event_in_interval'
    result = {'horizon_count': horizon_count, 'public_envelope_count': envelope,
            'antenna_possible_count': antenna_count, 'clear_sight_count': clear,
            'uncertain_sight_count': uncertain, 'blocked_count': blocked,
            'serving_catalog_id': service.get('serving_catalog_id') if service else None,
            'route_catalog_ids': service.get('route_catalog_ids', []) if service else [],
            'antenna_status': antenna, 'sight_status': sight, 'margin_status': margin,
            'packet_status': packet, 'packet_offers': packets['offers'],
            'packet_gateway_rx': packets['gateway_rx'], 'packet_drops': packets['drops'],
            'packet_acks': packets['acks'], 'operator_status': 'unverified'}
    for leg in ('user_uplink', 'user_downlink', 'feeder_uplink', 'feeder_downlink'):
        values = (budget.get(leg) or {}).get('margin_db_interval') if budget else None
        result[leg + '_margin_low_db'] = values[0] if values is not None else None
        result[leg + '_margin_high_db'] = values[1] if values is not None else None
    return result


def analyze(base, *, already_verified=False):
    base = Path(base).resolve()
    if not already_verified:
        verify_run(base)
    scenario = json.loads((base/'inputs/scenario.json').read_text())
    if not scenario.get('satellite_enabled') or not (base/'physical-timeline.json').is_file():
        raise ValueError('F6 audit requires a verified satellite run with physical timeline')
    timeline = json.loads((base/'physical-timeline.json').read_text())
    if (base/'native/editor-manifest.json').is_file():
        return native_analyze(base, scenario, timeline)
    service = timeline.get('service_routes') or {}
    budget_path = base/'service-model/link-budget.json'
    budget = json.loads(budget_path.read_text()) if budget_path.is_file() else {'nodes': {}}
    waypoint = base/'ground/scenario/waypoints.csv'
    horizon = horizon_counts(scenario, waypoint)
    end_us = round(scenario['sample_count'] * 100_000)
    packets = packet_counts(base/'service-model/service-native/service_packets.csv', timeline['nodes'], end_us)
    satellite = scenario['satellite']
    output = {}
    for node, physical_rows in timeline['nodes'].items():
        service_rows = {row['time_us']: row for row in service.get('nodes', {}).get(node, [])}
        budget_rows = {row['time_us']: row for row in budget['nodes'].get(node, [])}
        rows = []
        for physical in physical_rows:
            tick = physical['time_us']
            if tick not in horizon[node]:
                raise ValueError('F6 horizon and physical timelines are misaligned')
            result = classify(physical, service_rows.get(tick), budget_rows.get(tick),
                              horizon[node][tick], packets[node].get(tick, dict.fromkeys(
                                  ('offers', 'gateway_rx', 'drops', 'acks'), 0)),
                              group=satellite['orbit_group'],
                              mounted=node in satellite.get('terminal_mounts', {}),
                              environment=satellite.get('environment'))
            rows.append({'node_id': node, 'time_us': tick, **result})
        output[node] = rows
    manifest = json.loads((base/'run-manifest.json').read_text())
    return {'schema_version': 1, 'run_id': base.name, 'service': satellite['orbit_group'],
            'duration_s': scenario['sample_count']/10, 'step_us': STEP_US,
            'orbit_manifest_sha256': satellite['orbit_snapshot']['manifest_sha256'],
            'run_manifest_sha256': digest(base/'run-manifest.json'),
            'source_hashes': {key: value for key, value in manifest['sources'].items()
                              if key in ('tools/simulator_time_visibility.py',
                                         'tools/simulator_link_budget.py', 'tools/simulator_physical_coverage.py')},
            'layer_order': ['pure_horizon', 'published_user_envelope', 'declared_terminal_orientation',
                            'local_geometric_sight', 'assumed_bidirectional_rf_margin',
                            'recorded_packet_proxy'],
            'csv_fields': list(CSV_FIELDS),
            'nodes': output, 'measurement_status': 'no_same_terminal_field_measurements_supplied',
            'claim_boundary': 'geometric and assumed RF feasibility plus native proxy packets; active operator beams and commercial service unverified'}


def csv_text(report):
    from io import StringIO
    stream = StringIO(newline='')
    writer = csv.DictWriter(stream, CSV_FIELDS, lineterminator='\n', extrasaction='ignore')
    writer.writeheader()
    for node in sorted(report['nodes']):
        writer.writerows(report['nodes'][node])
    return stream.getvalue()


def export(base, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('F6 export destination must be new')
    report = analyze(base)
    output.mkdir(parents=True)
    (output/'audit.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    (output/'audit.csv').write_text(csv_text(report))
    meta = {'schema_version': 1, 'source_run': str(Path(base).resolve()),
            'report_source_sha256': digest(Path(__file__)),
            'run_manifest_sha256': report['run_manifest_sha256'],
            'files': {name: digest(output/name) for name in ('audit.json', 'audit.csv')}}
    (output/'manifest.json').write_text(json.dumps(meta, sort_keys=True, indent=2)+'\n')
    verify_export(output)
    return report


def verify_export(output):
    output = Path(output).resolve()
    meta = json.loads((output/'manifest.json').read_text())
    if meta.get('schema_version') != 1 or meta['report_source_sha256'] != digest(Path(__file__)):
        raise ValueError('F6 report source changed')
    report = analyze(Path(meta['source_run']))
    expected_json = (json.dumps(report, sort_keys=True, indent=2)+'\n').encode()
    expected_csv = csv_text(report).encode()
    if meta['run_manifest_sha256'] != report['run_manifest_sha256'] or \
       (output/'audit.json').read_bytes() != expected_json or \
       (output/'audit.csv').read_bytes() != expected_csv or \
       meta['files'] != {'audit.json': digest(output/'audit.json'),
                         'audit.csv': digest(output/'audit.csv')}:
        raise ValueError('F6 report differs from verified source run')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('export', 'verify'))
    parser.add_argument('path', type=Path)
    parser.add_argument('output', nargs='?', type=Path)
    args = parser.parse_args()
    result = export(args.path, args.output) if args.command == 'export' and args.output else verify_export(args.path)
    print(json.dumps({'status': 'PASS', 'run_id': result['run_id'],
                      'nodes': len(result['nodes']), 'duration_s': result['duration_s']}))
