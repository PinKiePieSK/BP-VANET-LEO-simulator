# Overí integrovaný ns-3/SNS-3 beh: zdrojovú binárku, satelitnú knižnicu, raw stopy, bajty a cestu
# DENM do brány a vzdialených áut. Neakceptuje náhradný servisný model.
"""Independent raw-byte and provenance check of an editor SNS-3 packet run."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from simulator_platform import ROOT, sha
from simulator_packet_trace import hops, pcap_packets
from simulator_satellite_runner import SOURCE, SATELLITE_LIBRARY
from simulator_physical_coverage import profile as physical_profile
from simulator_rsu_radio import render as render_rsu_radio
from simulator_car_radio import render as render_car_radio
from simulator_engine_controls import effective as engine_controls


def _rows(path: Path) -> list[dict]:
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


# Integrovaný verifier kontroluje zdroj, skompilovanú binárku, knižnicu SNS-3, konfiguráciu a
# stopy. Zvlášť musí sedieť cesta DENM cez natívny satelitný paketový beh; starý servisný model
# nemôže nahradiť jeho neúspech.
def verify(output: Path) -> dict:
    output = output.resolve()
    manifest = json.loads((output / 'native/editor-manifest.json').read_text())
    folder = output / 'native/baseline'
    _need(manifest['schema_version'] == 1 and
          manifest['execution_state'] == 'single_ns3_sns3_packet_process' and
          manifest['source_sha256'] == sha(SOURCE) and
          manifest['satellite_library_sha256'] == sha(SATELLITE_LIBRARY) and
          manifest['binary_sha256'] == sha(output / 'native/simulator-packet-engine') and
          manifest['orbit_reference_sha256'] == sha(folder / 'orbit-reference.json'),
          'Natívny binárny kód, SNS-3 alebo orbitálny vstup sa zmenil')
    _need(manifest['runner_sha256'] == sha(ROOT / 'tools/simulator_satellite_runner.py'),
          'Natívny generátor vstupov sa zmenil')
    for name, digest in manifest['raw_sha256'].items():
        _need(sha(output / name) == digest, f'Surový vstup alebo stopa sa zmenili: {name}')
    original = {name for name in manifest['raw_sha256'] if name.startswith('native/baseline/')}
    present = {str(path.relative_to(output)) for path in folder.rglob('*') if path.is_file()}
    _need(original == present, 'Sada natívnych surových stôp sa zmenila')
    _need(not (output / 'service-model').exists(), 'Servisný fallback sa nesmie nachádzať v natívnom behu')
    scenario = json.loads((output / 'inputs/scenario.json').read_text())
    world = json.loads((output / 'inputs/world.json').read_text())
    _need((folder / 'rsu-radio.csv').read_bytes() == render_rsu_radio(world, scenario['radio']),
          'RSU radio PHY differs from scenario and world')
    # Overovač satelitného behu kontroluje pozemný profil každého auta v surovom CSV aj v hlásení
    # konkrétneho ns-3 PHY.
    car_radio = folder / 'car-radio.csv'
    if car_radio.is_file():
        _need(car_radio.read_bytes() == render_car_radio(
            world, scenario['radio'], engine_controls(scenario)['car_antenna_height_m']),
            'car radio PHY differs from scenario and world')
        car_applied = {match[0]: [float(value) for value in match[1:]] for match in re.findall(
            r'^CAR_RADIO_PROFILE ID=(\w+) TX=([-+\deE.]+) NOISE=([-+\deE.]+) TX_GAIN=([-+\deE.]+) RX_GAIN=([-+\deE.]+) HEIGHT=([-+\deE.]+)$',
            (folder / 'run.log').read_text(), re.M)}
        car_declared = _rows(car_radio)
        _need(set(car_applied) == {row['id'] for row in car_declared} and all(
            all(abs(a-float(row[key])) < 1e-6 for a, key in zip(car_applied[row['id']],
                ('tx_power_dbm', 'noise_figure_db', 'tx_gain_dbi', 'rx_gain_dbi', 'antenna_height_m')))
            for row in car_declared), 'car PHY actually applied by ns-3 differs from CSV')
    applied = {match[0]: [float(value) for value in match[1:]] for match in re.findall(
        r'^RSU_RADIO_PROFILE ID=(\w+) TX=([-+\deE.]+) NOISE=([-+\deE.]+) TX_GAIN=([-+\deE.]+) RX_GAIN=([-+\deE.]+) HEIGHT=([-+\deE.]+)$',
        (folder / 'run.log').read_text(), re.M)}
    # Kontroluje, že integrovaný ns-3 proces použil účinný profil každého pozemného RSU; satelitný
    # model tým nezískava operátorskú kalibráciu.
    declared = _rows(folder / 'rsu-radio.csv')
    _need(set(applied) == {row['id'] for row in declared} and all(
        all(abs(a-float(row[key])) < 1e-6 for a, key in zip(applied[row['id']],
            ('tx_power_dbm', 'noise_figure_db', 'tx_gain_dbi', 'rx_gain_dbi', 'antenna_height_m')))
        for row in declared), 'RSU PHY actually applied by ns-3 differs from CSV')
    controls = engine_controls(scenario)
    # Checker porovná natívne hlásené časy s účinným scenárom; zároveň kontroluje účinný zorný
    # uhol každého satelitného terminálu.
    times = re.search(r'^NATIVE_CONTROL_TIMES HANDOVER=(\d+) APPLY=(\d+) RELEASE=(\d+)$',
                      (folder / 'run.log').read_text(), re.M)
    _need(times is not None and [int(value) for value in times.groups()] ==
          [controls['satellite_handover_request_us'], controls['satellite_apply_us'],
           controls['satellite_burst_release_us']], 'Natívne časy sa líšia od scenára')
    terminal = _rows(folder / 'satellite-terminal-config.csv')
    _need({row['rsu_id'] for row in terminal} == {row['id'] for row in world['rsus']} and
          all(abs(float(row['half_fov_deg']) -
                  (controls['satellite_terminal_fov_deg'] if scenario['satellite']['orbit_group']=='starlink' else 180)) < 1e-6
              for row in terminal), 'Zorný uhol terminálu sa líši od scenára')
    if (folder/'denm-events.csv').is_file():
        from simulator_message_verifier import verify as verify_cam_denm
        return verify_cam_denm(output,manifest,scenario)
    top = manifest['topology']
    _need(scenario['satellite_enabled'] and top['catalog_ids'] and
          top['selection'] in ('explicit', 'best_full_window_single_satellite'),
          'Natívna orbitálna topológia chýba')
    if (folder/'satellite-terminal-config.csv').is_file():
        policy=scenario['link_policy']; sat=scenario['satellite']
        profiles={row['rsu_id']:row for row in _rows(folder/'satellite-terminal-config.csv')}
        for row in profiles.values():
            owner=row['rsu_id']; mount=sat['terminal_mounts'].get(owner,{'tilt_deg':0,'azimuth_deg':0})
            directional=sat['orbit_group']=='starlink'
            expected={'tilt_deg':mount['tilt_deg'],'azimuth_deg':mount['azimuth_deg'],
                      'half_fov_deg':engine_controls(scenario)['satellite_terminal_fov_deg'] if directional else 180,'rf_hz':policy['rf_hz'],
                      'compensation':policy['compensation'],
                      'doppler_tolerance_hz':policy['doppler_tolerance_hz'],
                      'zenith_cone_deg':policy['zenith_cone_deg'] if directional else 180,
                      'steering_rate_deg_s':policy['steering_rate_deg_s'] if directional else 360,
                      'beam_half_angle_deg':policy['beam_half_angle_deg'] if directional else 180}
            _need(owner in scenario['node_policy']['rsus'] and
                  all(abs(float(row[key])-value)<1e-6 for key,value in expected.items()),
                  'Natívne RF parametre terminálu sa líšia od scenára')
        rf_rows=_rows(folder/'satellite_rf.csv')
        _need(bool(rf_rows), 'SNS-3 nevytvoril RF rozhodnutia na používateľskom kanáli')
        for row in rf_rows:
            owner=row['rsu_id']; reason=row['reason']
            profile=profiles.get(owner)
            _need(profile is not None and row['channel'] in ('return_user','forward_user') and
                  0<=int(row['sat_id'])<len(top['catalog_ids']),
                  'RF stopa odkazuje na neznámy terminál alebo družicu')
            expected_reason=('building' if int(row['building_blocked']) else
                             'mount_fov' if float(row['off_axis_deg'])>float(profile['half_fov_deg'])+1e-9 else
                             'doppler' if float(row['residual_hz'])>float(profile['doppler_tolerance_hz'])+1e-9 else
                             'pointing' if float(row['pointing_error_deg'])>float(profile['beam_half_angle_deg'])+1e-9 else
                             'accepted')
            _need(reason==expected_reason and
                  abs(float(row['residual_hz'])-abs(float(row['doppler_hz']))*
                      (1-float(profile['compensation'])))<.1 and
                  ('carrier_hz' not in row or
                   abs(float(row['doppler_hz'])+
                       float(row['carrier_hz'])*float(row['range_rate_mps'])/299792458.0)<.1) and
                  ('carrier_hz' not in row or row['channel']!='return_user' or
                   float(profile['rf_hz'])<=float(row['carrier_hz'])<=float(profile['rf_hz'])+1e9) and
                  ('carrier_hz' not in row or row['channel']!='forward_user' or
                   physical_profile(sat['orbit_group'])['user_downlink_hz']<=
                   float(row['carrier_hz'])<=physical_profile(sat['orbit_group'])['user_downlink_hz']+1e9),
                  'Natívne RF rozhodnutie nezodpovedá surovej geometrii a parametrom')
    for rel, digest in manifest['model']['sha256'].items():
        _need(sha(folder / 'inputs' / rel) == digest, 'SNS-3 modelový vstup sa zmenil')
    log = (folder / 'run.log').read_text()
    radio=scenario['radio']
    # Aj natívny beh bez udalosti DENM musí zodpovedať deklarovanému kanálu, frekvencii, rýchlosti
    # a anténnym parametrom.
    selected=re.search(r'OCB_CONFIG RATE_MBPS=(\d+) CHANNEL=(\d+) FREQUENCY_HZ=(\d+) TX_GAIN_DBI=([-\d.]+) RX_GAIN_DBI=([-\d.]+) SHADOWING=(\d+)',log)
    _need(selected is not None and int(selected[1])==radio.get('rate_mbps',6) and
          int(selected[2])==radio.get('channel_number',180) and
          int(selected[3])==(5000+5*radio.get('channel_number',180))*1000000 and
          float(selected[4])==radio.get('tx_gain_dbi',0) and
          float(selected[5])==radio.get('rx_gain_dbi',0) and
          int(selected[6])==int(radio.get('shadowing',False)),
          'Natívne OCB PHY parametre sa líšia od scenára')
    count = len(top['catalog_ids'])
    attach = {int(sat): (int(gw), int(ut)) for sat, gw, ut in re.findall(
        r'^HANDOVER_INITIAL_ATTACH_SAT=(\d+) GW=(\d+) UT=(\d+)$', log, re.M)}
    _need(set(attach) == set(range(count)) and attach[top['feeder_sat']][0] > 0,
          'Deklarovaný feeder nemá natívne SNS-3 pripojenie brány')
    _need(re.search(r'^SATELLITE_COUNT=' + str(count) + r'\b', log, re.M) is not None and
          'SIM_NATIVE_SAT_CHANNELS=' in log, 'Natívny SNS-3 kanál alebo topológia chýba')
    packet_trace = (folder / 'PacketTrace.log').read_text()
    _need(' SND UT ' in packet_trace and ' RCV GW ' in packet_trace and
          ' SND GW ' in packet_trace and ' RCV UT ' in packet_trace,
          'SNS-3 nemá obojsmernú surovú paketovú stopu')
    waypoints = _rows(folder / 'waypoints.csv')
    node_order = list(dict.fromkeys(row['node_id'] for row in waypoints))
    _need(node_order[0] == scenario['source_id'] and
          node_order[-1] == scenario['rsu_id'], 'Natívne polohy majú iné poradie uzlov')
    stations = {int(row['station_id']): row['node_id'] for row in waypoints if row['index'] == '0'}
    rsus = {row['node_id'] for row in waypoints if row['kind'] == 'rsu'}
    cars = {row['node_id'] for row in waypoints if row['kind'] == 'car'}
    _need(len(stations) == len(node_order) and len(rsus) >= 1 and len(cars) >= 2,
          'Poloha alebo identita uzla chýba')
    expected_samples = scenario['sample_count']
    _need(all(sum(row['node_id'] == node for row in waypoints) == expected_samples
              for node in node_order), 'Natívny čas polôh nepokrýva celú simuláciu')
    trace = defaultdict(lambda: defaultdict(list))
    for row in _rows(folder / 'trace.csv'):
        trace[row['stage']][row['event_id']].append(row)
    if top['handover_target_sat'] is not None and (folder/'satellite-terminal-config.csv').is_file():
        moves=re.findall(r'^HANDOVER_MOVE_US=(\d+) SAT=(\d+) RSU=(\S+) UT_IP=(\S+) UT_MAC=(\S+)$',log,re.M)
        confirms=re.findall(r'^HANDOVER_ATTACH_CONFIRMED_US=(\d+) RSU=(\S+)$',log,re.M)
        gateways=re.findall(r'^HANDOVER_PROBE_GATEWAY_RX_US=(\d+) RSU=(\S+)$',log,re.M)
        _need(len(moves)==len(rsus) and len(confirms)==len(rsus) and len(gateways)==len(rsus) and
              {row[2] for row in moves}==rsus and {row[1] for row in confirms}==rsus and
              {row[1] for row in gateways}==rsus and
              all(int(row[1])==top['handover_target_sat'] for row in moves) and
              len({row[3] for row in moves})==len(rsus) and len({row[4] for row in moves})==len(rsus),
              'Každý RSU terminál musí mať vlastný natívny presun, probe a potvrdenie')
        for owner in rsus:
            moved=next(int(row[0]) for row in moves if row[2]==owner)
            gateway=next(int(row[0]) for row in gateways if row[1]==owner)
            confirmed=next(int(row[0]) for row in confirms if row[1]==owner)
            _need(moved<gateway<confirmed and
                  any(int(item['time_us'])>confirmed
                      for event,items in trace['GATEWAY_ACCEPT'].items()
                      for item in items
                      if trace['RSU_REPORT_CREATED'][event][0]['node_id']==owner)
                  if scenario['node_policy']['rsus'][owner]['satellite_backhaul'] else
                  moved<gateway<confirmed,
                  'Po prepnutí RSU chýba spätný natívny paketový tok')
    cam_rows = _rows(folder / 'cam.csv')
    cams = {(int(row['station_id']), int(row['gdt_ms'])): bytes.fromhex(row['raw_hex'])
            for row in cam_rows if row['stage'] == 'CAM_UPER_TX'}
    _need(bool(cams) and len(cams) == len([row for row in cam_rows if row['stage'] == 'CAM_UPER_TX']),
          'CAM identita alebo bajty chýbajú')
    policy=scenario['node_policy']
    _need(all(stations[key[0]] in cars and policy['cars'][stations[key[0]]]['ground']!='off'
              for key in cams),'Vypnuté pozemné rádio vytvorilo CAM')
    identity = _rows(folder / 'identity.csv')
    cam_ids = {row['event_id']: (int(row['station_id']), int(row['gdt_ms']))
               for row in identity if row['kind'] == 'cam'}
    report_ids = {row['event_id']: row for row in identity if row['kind'] == 'report'}
    _need(len(cam_ids) == len(cams) and len(report_ids) == len(trace['RSU_REPORT_CREATED']),
          'Počet CAM alebo RSU reportov nesedí s identitou')
    for event, key in cam_ids.items():
        rows = trace['CAM_UPER_TX'][event]
        _need(len(rows) == 1 and bytes.fromhex(rows[0]['raw_hex']) == cams[key] and
              rows[0]['node_id'] == stations[key[0]], 'CAM raw bajty alebo stanica nesedia')
    accepted = set(trace['GATEWAY_ACCEPT'])
    sent = set(trace['UT_SAT_REPORT_TX'])
    returned = set(trace['CAR_I2V1_RX'])
    _need(accepted and accepted <= sent <= set(report_ids) and returned <= accepted,
          'Natívny paketový prenos nemá úspešný report a návrat')
    for event, row in report_ids.items():
        parent = row['parent_event_id']
        _need(parent in cam_ids and row['station_id'] == str(cam_ids[parent][0]),
              'RSU report nemá správny CAM pôvod')
        created = trace['RSU_REPORT_CREATED'][event]
        _need(len(created) == 1 and created[0]['node_id'] in rsus,
              'RSU report vznikol v nesprávnom uzle')
        _need(policy['rsus'][created[0]['node_id']]['satellite_backhaul'] and
              policy['cars'][stations[cam_ids[parent][0]]]['ground']=='all',
              'RSU alebo auto vytvorilo satelitný report proti svojej politike')
        packet = bytes.fromhex(created[0]['raw_hex'])
        cam = cams[cam_ids[parent]]
        _need(packet[:5] == b'ICB1\x01' and packet[5:13] == int(event, 16).to_bytes(8, 'big') and
              packet[23:55] == hashlib.sha256(cam).digest() and packet[55:] == cam,
              'ICB1 neobsahuje presné pôvodné CAM bajty')
        for stage in ('RSU_REPORT_TX', 'UT_LAN_REPORT_RX', 'UT_SAT_REPORT_TX',
                      'GATEWAY_ACCEPT'):
            rows = trace[stage].get(event, [])
            _need(len(rows) == (1 if stage in ('RSU_REPORT_TX', 'UT_LAN_REPORT_RX') or
                                   event in (sent if stage == 'UT_SAT_REPORT_TX' else accepted) else 0) and
                  all(bytes.fromhex(item['raw_hex']) == packet for item in rows),
                  f'ICB1 bajty alebo časová cesta nesedia: {stage}')
        if event in accepted:
            ack = b'GRA1\x01' + int(event, 16).to_bytes(8, 'big') + hashlib.sha256(packet).digest() + b'\x00'
            _need(len(trace['GATEWAY_GRA1_TX'][event]) == 1 and
                  bytes.fromhex(trace['GATEWAY_GRA1_TX'][event][0]['raw_hex']) == ack,
                  'Brána nevytvorila správnu odpoveď GRA1')
            _need(int(created[0]['time_us']) <
                  int(trace['UT_SAT_REPORT_TX'][event][0]['time_us']) <
                  int(trace['GATEWAY_ACCEPT'][event][0]['time_us']) <=
                  int(trace['GATEWAY_GRA1_TX'][event][0]['time_us']),
                  'Natívne poradie reportu a odpovede je neplatné')
            for stage in ('UT_SAT_GRA1_RX', 'RSU_GRA1_RX'):
                for item in trace[stage].get(event, []):
                    _need(bytes.fromhex(item['raw_hex']) == ack,
                          f'GRA1 bajty sa zmenili v {stage}')
            if event in returned:
                response = trace['CAR_I2V1_RX'][event]
                _need(len(response) == 1 and response[0]['node_id'] == stations[cam_ids[parent][0]],
                      'Upozornenie prišlo nesprávnemu autu')
                expected = (b'I2V1\x01' + int(event, 16).to_bytes(8, 'big') +
                            cam_ids[parent][0].to_bytes(4, 'big') +
                            hashlib.sha256(packet).digest() + b'\x00')
                _need(bytes.fromhex(response[0]['raw_hex']) == expected and
                      bytes.fromhex(trace['RSU_I2V1_TX'][event][0]['raw_hex']) == expected,
                      'I2V1 surové bajty alebo príjemca nesedia')
    mapping = re.findall(r'^SIM_RSU_TERMINAL=(\S+) UT_NODE=(\d+) USER_NODE=(\d+) IP=(\S+) LAT=(\S+) LON=(\S+)$',
                         log, re.M)
    _need({row[0] for row in mapping} == rsus and len({row[1] for row in mapping}) == len(rsus),
          'Každá RSU nemá vlastný natívny terminál')
    pcaps = list(folder.glob('ocb-*-0.pcap'))
    _need(len(pcaps) == len(node_order) and
          all(path.stat().st_size >= 24 and next(iter(pcap_packets(path, 105)), None) is not None
              for path in pcaps),
          'Pozemné raw PCAP stopy chýbajú')
    if count == 1:
        _need('ISL_RX_DEVICE_COUNT=0' in log and 'HANDOVER_ISL_REPORT_HOP=' not in log,
              'Jednosatelitná cesta nesmie používať ISL')
    else:
        edges={tuple(sorted(edge)) for edge in top['isls']}
        forward=hops(log,'report');reverse=hops(log,'ack')
        _need(bool(forward) and bool(reverse),'Viacdružicový beh nemá natívne ISL IP/UDP bajty')
        for collection,kind in ((forward,'report'),(reverse,'ack')):
            for event,records in collection.items():
                _need(event in report_ids,'ISL obsahuje neznámy paket')
                report=bytes.fromhex(trace['RSU_REPORT_CREATED'][event][0]['raw_hex'])
                expected=(report if kind=='report' else b'GRA1\x01'+
                          int(event,16).to_bytes(8,'big')+hashlib.sha256(report).digest()+b'\x00')
                _need(all(tuple(sorted(pair)) in edges and payload==expected
                          for _,pair,payload in records),
                      'ISL IP/UDP bajty, identita alebo hrana nesedia')
    return {'status': 'PASS', 'cars': len(cars), 'rsus': len(rsus),
            'satellites': count, 'cam_transmitted': len(cams),
            'reports_created': len(report_ids), 'reports_sent': len(sent),
            'gateway_received': len(accepted), 'car_replies': len(returned),
            'packet_backend': 'native_sns3_generic_dvb'}
