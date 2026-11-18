"""Prepare SUMO positions and run simulator ground and SNS-3 packets in one ns-3 process.

The orbital catalogue is only an input.  A successful native packet trace is
required before an editor run is accepted; no service-model fallback exists.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from astropy import units as u
from astropy.coordinates import CartesianRepresentation, ITRS, TEME
from astropy.time import Time
from sgp4.api import SatrecArray

from simulator_platform import ROOT, CHECKOUT, sha, put_exact, ut_site
from simulator_engine_controls import effective as engine_controls
from simulator_satellite_inputs import generate
from simulator_build import compile_packet_engine
from simulator_sumo import run as run_sumo
from simulator_mobility_export import prepare
from simulator_ground_runner import traffic_metrics
from simulator_node_policy import environment as policy_environment
from simulator_rsu_radio import write as write_rsu_radio
from simulator_car_radio import write as write_car_radio
from simulator_orbit_source import config_for
from simulator_physical_coverage import profile
from simulator_time_visibility import _elevation
from simulator_orbits import sat_ecef, load_orbits, pinned_eop

SOURCE = ROOT / 'src/vanet-leo-network.cc'
SATELLITE_LIBRARY = CHECKOUT / 'build/lib/libns3.38-satellite-debug.so'


def _orbit_positions(objects: list, when: datetime) -> np.ndarray:
    time = Time(when, scale='utc')
    pinned_eop(time)
    errors, positions, _ = SatrecArray([row[3] for row in objects]).sgp4(
        np.array([time.jd1]), np.array([time.jd2]))
    if np.any(errors):
        raise ValueError('SGP4 zlyhal pri výbere natívnej konštelácie')
    return TEME(CartesianRepresentation(positions[:, 0, :].T * u.km),
                obstime=time).transform_to(ITRS(obstime=time)).cartesian.xyz.to_value(u.km).T


def _select_topology(scenario: dict, waypoints: Path, reference: dict) -> dict:
    sat = scenario['satellite']
    config = dict(reference, utc_origin=scenario['utc_origin'])
    objects, _ = load_orbits(config)
    by_id = {row[0]: row for row in objects}
    with waypoints.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    rsus = [row for row in rows if row['kind'] == 'rsu' and row['index'] == '0' and
            scenario['node_policy']['rsus'][row['node_id']]['satellite_backhaul']]
    if not rsus:
        raise ValueError('Natívny SNS-3 beh potrebuje RSU terminál')
    sites = [(int(row['latitude_e7']) / 1e7, int(row['longitude_e7']) / 1e7,
              int(row['altitude_cm']) / 100) for row in rsus]
    sites.append(tuple(sat['gateway']))
    specification=profile(sat['orbit_group'])
    floor = max(float(sat['mask_deg']), float(specification['minimum_elevation_deg']),
                90.0-float(specification['terminal_zenith_limit_deg']))
    origin = datetime.fromisoformat(scenario['utc_origin'].replace('Z', '+00:00'))
    duration = scenario['sample_count'] / 10
    times = [origin + timedelta(seconds=duration * part) for part in (0, .5, 1)]
    minimum = np.full(len(objects), 90.0)
    for when in times:
        xyz = _orbit_positions(objects, when)
        for site in sites:
            minimum = np.minimum(minimum, _elevation(xyz, site))
    full_minimum = {}
    def full_window_minimum(catalog: int) -> float:
        if catalog not in full_minimum:
            orbit=by_id[catalog][3]
            worst=90.0
            for half_second in range(round(duration*2)+1):
                xyz=np.asarray([sat_ecef(orbit,origin+timedelta(seconds=half_second*.5))])
                for site in sites:
                    worst=min(worst,float(_elevation(xyz,site)[0]))
            full_minimum[catalog]=worst
        return full_minimum[catalog]
    declared = sat.get('catalog_ids') or []
    if declared:
        if any(catalog not in by_id for catalog in declared):
            raise ValueError('Zvolený satelit chýba v pripnutom OMM archíve')
        catalogs = list(declared)
        isls = sat['isls']
        initial = sat['initial_serving_sat']
        feeder = sat['feeder_sat']
        target = sat['handover_target_sat']
        if target != initial and duration < 5:
            raise ValueError('Natívny RSU handover potrebuje aspoň 5 s')
        if sat['orbit_group'] == 'globalstar' and isls:
            raise ValueError('Globalstar nemá verejne doložené ISL; natívny beh ich nezavedie')
    else:
        eligible = sorted(np.flatnonzero(minimum >= floor),
                          key=lambda index: (-float(minimum[index]), objects[index][0]))
        if not len(eligible):
            raise ValueError('Žiadna jediná družica nedrží všetky RSU a bránu nad výškovou maskou počas behu; natívny viacdružicový handover treba zvoliť explicitne')
        selected = next((index for index in eligible if full_window_minimum(objects[index][0]) >= floor),None)
        if selected is None:
            raise ValueError('Žiadna natívna družica nemá výhľad na všetky aktívne RSU a bránu počas celého behu')
        catalogs = [objects[selected][0]]
        isls = []
        initial = feeder = target = 0
    if any(minimum[next(index for index, row in enumerate(objects) if row[0] == catalog)] < floor
           for catalog in catalogs):
        raise ValueError('Deklarovaná natívna topológia stráca fyzikálny výhľad počas behu')
    if any(full_window_minimum(catalog) < floor for catalog in catalogs):
        raise ValueError('Natívna družica klesá pod výškovú masku počas behu')
    if not (0 <= initial < len(catalogs) and 0 <= feeder < len(catalogs) and
            0 <= target < len(catalogs)):
        raise ValueError('Index natívnej družice je mimo topológie')
    if len(catalogs) > 1 and len(isls) != len(catalogs) - 1:
        raise ValueError('SNS-3 simulator aktuálne vyžaduje spojitý strom ISL')
    return {'catalog_ids': catalogs, 'isls': isls, 'gateway': sat['gateway'],
            'initial_serving_sat': initial, 'feeder_sat': feeder,
            'handover_target_sat': target if target != initial else None,
            'mask_deg': floor, 'utc_origin': scenario['utc_origin'],
            'ut': list(ut_site(waypoints, scenario['rsu_id'])),
            'minimum_elevation_deg': {str(catalog): round(full_window_minimum(catalog), 3)
                                      for catalog in catalogs},
            'selection': 'explicit' if declared else 'best_full_window_single_satellite'}


def _model(folder: Path, topology: dict, gain: float, waypoints: Path) -> dict:
    base = generate(CHECKOUT, folder, topology, gain)
    with waypoints.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    primary = next(row['node_id'] for row in rows if row['kind'] == 'rsu' and
                   row['node_id'] == topology['primary_rsu'])
    rsus = [primary] + [row['node_id'] for row in rows if row['kind'] == 'rsu' and
             row['index'] == '0' and row['node_id'] != primary]
    name = 'bp-satellite-' + hashlib.sha256(json.dumps(
        [base['scenario'], rsus, topology], sort_keys=True).encode()).hexdigest()[:16]
    source = folder / 'inputs' / base['scenario']
    target = folder / 'inputs' / name
    target.mkdir()
    for path in source.iterdir():
        value = path.read_text()
        if path.name == 'ut_positions.txt':
            value += ''.join('{:.7f} {:.7f} {:.2f}\n'.format(*ut_site(waypoints, rsu))
                             for rsu in rsus[1:])
        elif path.name == 'ut_sat_ids.txt':
            value += f"{topology['initial_serving_sat']}\n" * (len(rsus) - 1)
        (target / path.name).write_text(value)
        put_exact(CHECKOUT / 'contrib/satellite/data/constellations' / name / path.name,
                  value)
    base['scenario'] = name
    base['sha256'] = {str(p.relative_to(folder / 'inputs')): sha(p)
                      for p in (folder / 'inputs').rglob('*') if p.is_file()}
    return base


def run(scenario: dict, output: Path, ground_config: dict, orbit_reference: dict) -> dict:
    controls = engine_controls(scenario)
    output = output.resolve()
    folder = output / 'native/baseline'
    prepared = output / 'ground/scenario'
    if folder.exists() or prepared.exists():
        raise ValueError('Natívny editorový výstup už existuje')
    folder.mkdir(parents=True)
    prepared.mkdir(parents=True)
    world = json.loads((output / 'inputs/world.json').read_text())
    world_path = prepared / 'world.json'
    world_path.write_text(json.dumps(world, indent=2, sort_keys=True) + '\n')
    case = ground_config['cases'][0]
    hold_until = min(world['simulation']['duration_s'] - .01,
                     case['first_sample_s'] + ground_config['sample_count'] * .1 + .2)
    run_sumo(world, world_path, prepared / 'sumo', hold_until_s=hold_until)
    traffic_metrics(world, prepared / 'sumo', case['first_sample_s'],
                    ground_config['sample_count'])
    normalized = {'agents': {'cam_source_id': scenario['source_id'],
                             'rsu_id': scenario['rsu_id']},
                  'applications': {'cam': {'count': scenario['sample_count'],
                                           'first_tx_s': case['first_sample_s'],
                                           'interval_s': .1}}}
    prepare(world_path, prepared / 'sumo/fcd.xml', normalized,
            prepared / 'waypoints.csv')
    shutil.copy2(prepared / 'waypoints.csv', folder / 'waypoints.csv')
    shutil.copy2(world_path, folder / 'world.json')
    write_rsu_radio(world, scenario['radio'], folder / 'rsu-radio.csv')
    write_car_radio(world, scenario['radio'], engine_controls(scenario)['car_antenna_height_m'],
                    folder / 'car-radio.csv')
    shutil.copytree(prepared / 'sumo', folder / 'sumo')
    obstruction = output / 'inputs/ground-obstructions.csv'
    if obstruction.is_file():
        shutil.copy2(obstruction, folder / 'osm-buildings.csv')
    (folder / 'orbit-reference.json').write_text(
        json.dumps(orbit_reference, indent=2, sort_keys=True) + '\n')
    topology = _select_topology(scenario, folder / 'waypoints.csv', orbit_reference)
    topology['primary_rsu'] = scenario['rsu_id']
    rf = scenario['link_policy']
    sat = scenario['satellite']
    with (folder / 'satellite-terminal-config.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(('rsu_id', 'tilt_deg', 'azimuth_deg', 'half_fov_deg',
                         'rf_hz', 'compensation', 'doppler_tolerance_hz',
                         'zenith_cone_deg', 'steering_rate_deg_s', 'beam_half_angle_deg'))
        with (folder / 'waypoints.csv').open(newline='') as positions:
            owners = [row['node_id'] for row in csv.DictReader(positions)
                      if row['kind'] == 'rsu' and row['index'] == '0']
        for owner in owners:
            mount = sat['terminal_mounts'].get(owner, {'tilt_deg': 0, 'azimuth_deg': 0})
            directional = sat['orbit_group'] == 'starlink'
            writer.writerow((owner, mount['tilt_deg'], mount['azimuth_deg'],
                             controls['satellite_terminal_fov_deg'] if directional else 180, rf['rf_hz'], rf['compensation'],
                             rf['doppler_tolerance_hz'],
                             rf['zenith_cone_deg'] if directional else 180,
                             rf['steering_rate_deg_s'] if directional else 360,
                             rf['beam_half_angle_deg'] if directional else 180))
    model = _model(folder, topology, scenario['satellite']['beam_gain_dbi'],
                   folder / 'waypoints.csv')
    native = output / 'native'
    binary = compile_packet_engine(native, SOURCE)
    sat = scenario['satellite']
    end_us = scenario['sample_count'] * 100_000
    if end_us != int(end_us):
        raise ValueError('Dĺžka natívneho behu musí byť násobkom 100 ms')
    events = sorted(scenario['denm_events'],
                    key=lambda event: (event['at_s'], event.get('source_id', scenario['source_id'])))
    with (folder / 'denm-events.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(('time_us', 'source_id', 'sequence', 'operation', 'validity_s',
                         'radius_m', 'repetition_ms'))
        for event in events:
            writer.writerow((int(round(event['at_s'] * 1_000_000)),
                             event.get('source_id', scenario['source_id']),
                             event['sequence'], event['operation'], event['validity_s'],
                             event['radius_m'], event['repetition_ms']))
    with tempfile.TemporaryDirectory(prefix='bp-satellite-run-') as temp:
        alias = Path(temp) / 'run'
        alias.symlink_to(folder, target_is_directory=True)
        args = [str(binary), f'--waypoints={alias / "waypoints.csv"}',
                f'--rsu_radio_config={alias / "rsu-radio.csv"}',
                f'--car_radio_config={alias / "car-radio.csv"}',
                f'--source={scenario["source_id"]}', f'--rsu={scenario["rsu_id"]}',
                f'--scenario_id={scenario["scenario_id"]}',
                f'--run_id={output.name}', '--backhaul_mode=satellite',
                '--cam_denm_mode=1', f'--denm_events={alias / "denm-events.csv"}',
                f'--denm_target_rsu={scenario["alert_target_rsu"]}',
                f'--forward_queue_capacity={controls["backhaul_forward_queue_packets"]}',
                f'--reverse_queue_capacity={controls["backhaul_reverse_queue_packets"]}',
                f'--forward_service_us={controls["backhaul_forward_service_us"]}',
                f'--reverse_service_us={controls["backhaul_reverse_service_us"]}',
                f'--trace={alias / "trace.csv"}',
                f'--delivery={alias / "delivery.csv"}',
                f'--pcap_prefix={alias / "ocb"}', f'--output_path={alias}',
                f'--simulation_end_us={int(end_us)}',
                f'--seed={scenario["seed"]}', f'--run={scenario["ns3_run"]}',
                f'--radio_mode={"urban_osm_building" if obstruction.is_file() else scenario["radio"]["mode"]}',
                f'--dcc={int(controls["dcc_enabled"])}', f'--phase_us={ground_config["phase_us"]}',
                f'--tx_power_dbm={scenario["radio"]["tx_power_dbm"]}',
                f'--noise_figure_db={scenario["radio"]["noise_figure_db"]}',
                f'--rate_mbps={scenario["radio"].get("rate_mbps",6)}',
                f'--channel_number={scenario["radio"].get("channel_number",180)}',
                f'--tx_gain_dbi={scenario["radio"].get("tx_gain_dbi",0)}',
                f'--rx_gain_dbi={scenario["radio"].get("rx_gain_dbi",0)}',
                f'--shadowing={int(scenario["radio"].get("shadowing",False))}',
                f'--dcc_low_cbr={ground_config["dcc_policy"]["low_cbr"]}',
                f'--dcc_high_cbr={ground_config["dcc_policy"]["high_cbr"]}',
                f'--dcc_mid_ms={ground_config["dcc_policy"]["mid_interval_ms"]}',
                f'--dcc_high_ms={ground_config["dcc_policy"]["high_interval_ms"]}',
                '--block_satellite=0', '--no_return_route=0', '--leo_reference=1',
                '--two_sat_isl=1', f'--expected_satellites={len(topology["catalog_ids"])}',
                f'--initial_serving_sat={topology["initial_serving_sat"]}',
                f'--return_route_old_sat={topology["initial_serving_sat"]}',
                f'--return_route_new_sat={topology["feeder_sat"]}',
                f'--initial_return_route_update={int(len(topology["catalog_ids"])>1)}',
                f'--handover_case={"switch" if topology["handover_target_sat"] is not None else "stay"}',
                f'--handover_target_sat={topology["handover_target_sat"] or 0}',
                f'--handover_request_us={controls["satellite_handover_request_us"]}',
                f'--utcOrigin={scenario["utc_origin"][:19]}',
                f'--scenarioFolder={model["scenario"]}',
                f'--patternFolder={model["pattern"]}',
                f'--utLat={topology["ut"][0]:.7f}',
                f'--utLon={topology["ut"][1]:.7f}',
                f'--utAlt={topology["ut"][2]:.2f}',
                f'--gwLat={topology["gateway"][0]}',
                f'--gwLon={topology["gateway"][1]}',
                f'--gwAlt={topology["gateway"][2]}',
                f'--satellite_ut_power_dbw={sat["ut_power_dbw"]}',
                f'--satellite_rtn_user_freq_hz={rf["rf_hz"]}',
                f'--satellite_fwd_user_freq_hz={profile(sat["orbit_group"])["user_downlink_hz"]}',
                f'--satellite_forward_bps={sat["forward_isl_bps"]}',
                f'--satellite_reverse_bps={sat["reverse_isl_bps"]}',
                f'--satellite_forward_queue_packets={sat["forward_queue_packets"]}',
                f'--satellite_reverse_queue_packets={sat["reverse_queue_packets"]}',
                '--satellite_burst=0',
                f'--satellite_apply_us={controls["satellite_apply_us"]}',
                f'--satellite_burst_release_us={controls["satellite_burst_release_us"]}',
                f'--sat_mask_deg={topology["mask_deg"]}']
        args.append(f'--sat_terminal_config={alias / "satellite-terminal-config.csv"}')
        for key in ('cam_distance_m', 'cam_speed_mps', 'cam_heading_deg',
                    'cam_low_frequency_ms', 'cam_tgen_max_ms', 'cam_periodic_repeat',
                    'car_antenna_height_m', 'rsu_antenna_min_height_m', 'rsu_roof_clearance_m',
                    'satellite_rtn_feeder_freq_hz', 'satellite_ut_rx_temp_dbk',
                    'satellite_sat_user_rx_temp_dbk', 'satellite_gw_rx_temp_dbk',
                    'satellite_sat_queue_max_packets', 'satellite_control_slot_ms',
                    'satellite_rtn_arq', 'satellite_fwd_acm', 'satellite_rtn_acm',
                    'satellite_default_fwd_modcod', 'satellite_isl_speed_mps'):
            value = controls[key]
            args.append(f'--{key}={int(value) if isinstance(value, bool) else value}')
        if obstruction.is_file():
            args.append(f'--osm_buildings={alias / "osm-buildings.csv"}')
        env = dict(os.environ, NS_LOG='', **policy_environment(scenario['node_policy']))
        timeout = max(180, min(21600, 60 + 2 * len(world['vehicles']) *
                                scenario['sample_count'] / 10))
        with (folder / 'run.log').open('w') as stdout,\
             (folder / 'run.stderr.log').open('w') as stderr:
            result = subprocess.run(args, cwd=CHECKOUT, env=env,
                                    stdout=stdout, stderr=stderr, timeout=timeout)
        if result.returncode:
            raise RuntimeError(f'Natívny SNS-3 beh zlyhal ({result.returncode}); pozri {folder / "run.log"}')
    raw = {str(path.relative_to(output)): sha(path) for path in output.rglob('*')
           if path.is_file() and path != output / 'run-manifest.json'}
    manifest = {'schema_version': 1, 'execution_state': 'single_ns3_sns3_packet_process',
                'topology': topology, 'model': model,
                'source_sha256': sha(SOURCE), 'runner_sha256': sha(Path(__file__)),
                'binary_sha256': sha(binary),
                'satellite_library_sha256': sha(SATELLITE_LIBRARY),
                'orbit_reference_sha256': sha(folder / 'orbit-reference.json'),
                'raw_sha256': raw}
    (native / 'editor-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return {'native': str(folder.relative_to(output)), 'topology': topology,
            'execution': manifest['execution_state']}
