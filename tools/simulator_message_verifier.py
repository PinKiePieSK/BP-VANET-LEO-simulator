"""Independent byte, time and application-lifecycle check for native CAM/DENM runs."""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from simulator_packet_trace import pcap_packets
from simulator_cam_decode import decode_cam
from simulator_denm_decode import decode_denm
from simulator_satellite_trace import load as load_satellite_trace
from simulator_engine_controls import effective as engine_controls


def need(ok, why):
    if not ok:
        raise ValueError(why)


def rows(path: Path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def verify(output: Path, manifest: dict, scenario: dict) -> dict:
    folder = output / 'native/baseline'
    log = (folder / 'run.log').read_text()
    radio=scenario['radio']
    selected=re.search(r'OCB_CONFIG RATE_MBPS=(\d+) CHANNEL=(\d+) FREQUENCY_HZ=(\d+) TX_GAIN_DBI=([-\d.]+) RX_GAIN_DBI=([-\d.]+) SHADOWING=(\d+)',log)
    need(selected is not None and int(selected[1])==radio.get('rate_mbps',6) and
         int(selected[2])==radio.get('channel_number',180) and
         int(selected[3])==(5000+5*radio.get('channel_number',180))*1000000 and
         float(selected[4])==radio.get('tx_gain_dbi',0) and
         float(selected[5])==radio.get('rx_gain_dbi',0) and
         int(selected[6])==int(radio.get('shadowing',False)),
         'Natívne OCB PHY parametre sa líšia od scenára')
    need('APPLICATION_MODE=CAM_DENM' in log and
         f'DCC={int(engine_controls(scenario)["dcc_enabled"])}' in log,
         'Natívny CAM/DENM režim alebo nastavenie DCC sa líši od scenára')
    trace = rows(folder / 'trace.csv')
    by_stage = defaultdict(lambda: defaultdict(list))
    for row in trace:
        need(int(row['bytes']) == len(bytes.fromhex(row['raw_hex'])),
             'Dĺžka surového paketu sa líši od jeho hex stopy')
        by_stage[row['stage']][row['event_id']].append(row)
    old = {'RSU_REPORT_CREATED','RSU_REPORT_TX','UT_LAN_REPORT_RX','UT_SAT_REPORT_TX',
           'GATEWAY_ACCEPT','GATEWAY_GRA1_TX','UT_SAT_GRA1_RX','RSU_GRA1_RX',
           'RSU_I2V1_TX','CAR_I2V1_RX'}
    need(not old.intersection(by_stage), 'Aktívny beh vyslal starý aplikačný typ')
    waypoints = rows(folder / 'waypoints.csv')
    station_ids = {row['node_id']: int(row['station_id']) for row in waypoints if row['index']=='0'}
    cars = {row['node_id'] for row in waypoints if row['kind']=='car'}
    rsus = {row['node_id'] for row in waypoints if row['kind']=='rsu'}
    need(len(cars)>=2 and len(rsus)>=1, 'Satelitný DENM pokus potrebuje autá a RSU')
    need(all(int(row['time_us']) == 0 for row in waypoints if row['index']=='0') and
         f"READY_AT_T0 TERMINALS={len(rsus)} SATELLITES={len(manifest['topology']['catalog_ids'])}" in log,
         'Spoločný štart polôh a pripravenosť všetkých terminálov v t=0 chýba')
    cams = by_stage['CAM_UPER_TX']
    need(len(cams)>=len(cars) and all(len(items)==1 for items in cams.values()),
         'CAM vysielanie alebo identita chýba')
    for event, items in cams.items():
        row = items[0]
        decoded = decode_cam(row['raw_hex'])
        need(decoded and row['node_id'] in cars and
             decoded['station_id']==station_ids[row['node_id']] and
             len(by_stage['GN_BTP_CAM_TX'][event])==1 and
             not (bytes.fromhex(by_stage['GN_BTP_CAM_TX'][event][0]['raw_hex'])[32] & 0x80) and
             by_stage['GN_BTP_CAM_TX'][event][0]['raw_hex'].endswith(row['raw_hex']),
             'CAM UPER alebo GN/BTP bajty nesedia')
        for rx in by_stage['CAM_UPER_RX'][event]:
            need(rx['raw_hex']==row['raw_hex'] and rx['node_id']!=row['node_id'],
                 'Prijatý CAM sa líši od vyslaného alebo pochádza od seba')
    need(len(by_stage['CAM_UPER_RX'])>0, 'CAM nemá pozemný príjem')
    events = rows(folder / 'denm-events.csv')
    need(len(events)==len(by_stage['DENM_UPER_TX']),
         'DENM počet udalostí nesedí so scenárom')
    target = scenario['alert_target_rsu']
    need(not target or target in rsus and target!=scenario['rsu_id'],
         'Natívny satelitný DENM cieľ nie je iná RSU')
    origin = datetime.fromisoformat(scenario['utc_origin'].replace('Z','+00:00'))
    epoch = datetime(2004,1,1,tzinfo=timezone.utc)
    start_ms = int((origin-epoch).total_seconds()*1000)
    first_detection = {}
    event_ids=[]
    path = ('DENM_UPER_TX','CAR_DENM_GBC_TX','RSU_DENM_LAN_TX',
            'UT_DENM_LAN_RX','UT_DENM_SAT_TX','GATEWAY_DENM_RX',
            'GATEWAY_DENM_SAT_TX','UT_DENM_SAT_RX','UT_DENM_LAN_TX',
            'RSU_DENM_LAN_RX')
    for config in events:
        at=int(config['time_us']); seq=int(config['sequence']);source=config['source_id']
        matches=[(event,items[0]) for event,items in by_stage['DENM_UPER_TX'].items()
                 if len(items)==1 and int(items[0]['time_us'])==at and items[0]['node_id']==source]
        need(len(matches)==1, 'DENM udalosť sa nevyslala v určenom čase')
        event, tx = matches[0]
        event_ids.append(event)
        raw=tx['raw_hex']
        decoded=decode_denm(raw)
        first_detection.setdefault((source,seq),at)
        need(decoded and source in cars and tx['node_id']==source and
             decoded['station_id']==station_ids[source] and
             decoded['originating_station_id']==station_ids[source] and
             decoded['sequence_number']==seq and
             decoded['detection_time_ms']==start_ms+first_detection[source,seq]//1000 and
             decoded['reference_time_ms']==start_ms+at//1000 and
             decoded['validity_s']==int(config['validity_s']) and
             decoded['transmission_interval_ms']==int(config['repetition_ms']) and
             decoded['position_confidence_major_code']==4095 and
             decoded['position_confidence_minor_code']==4095 and
             decoded['information_quality_code']==0 and
             decoded['traffic_subcause']==5 and decoded['detection_paths']>=1 and
             decoded['termination']==(0 if config['operation']=='cancel' else -1),
             'DENM ASN.1 polia, identita, čas alebo príčina zápchy nesedia')
        seen_gap=False;last_time=at
        for stage in path:
            items=by_stage[stage].get(event,[])
            if stage=='CAR_DENM_GBC_TX':
                need(items, 'DENM nemá pozemné GN GBC vysielanie')
            elif not items:
                seen_gap=True
                continue
            need(not seen_gap and
                 (stage=='CAR_DENM_GBC_TX' or len(items)==1) and
                 all(item['raw_hex']==raw and int(item['time_us'])>=last_time for item in items),
                 f'DENM paketová cesta, bajty alebo spoločný čas ns-3 nesedia: {stage}')
            last_time=int(items[0]['time_us'])
        need(not by_stage['RSU_DENM_LAN_TX'].get(event) or
             by_stage['RSU_DENM_LAN_TX'][event][0]['node_id']==scenario['rsu_id'],
             'DENM zdrojová RSU nesedí')
        for stage in ('GATEWAY_DENM_SAT_TX','UT_DENM_SAT_RX','RSU_DENM_LAN_RX'):
            need(not by_stage[stage].get(event) or target and
                 by_stage[stage][event][0]['node_id']==target,
                 'DENM nešiel do vybranej vzdialenej RSU')
        regenerated=by_stage['RSU_DENM_REGENERATED'].get(event,[])
        need(bool(regenerated)==bool(by_stage['RSU_DENM_LAN_RX'].get(event)) and
             bool(regenerated)==bool(by_stage['RSU_DENM_GBC_TX'].get(event)),
             'Regenerácia DENM sa nezhoduje s príjmom a vysielaním vzdialenej RSU')
        if regenerated:
            need(len(regenerated)==1 and regenerated[0]['node_id']==target and
                 len(by_stage['RSU_DENM_GBC_TX'][event])==1 and
                 by_stage['RSU_DENM_GBC_TX'][event][0]['raw_hex']==regenerated[0]['raw_hex'],
                 'Vzdialená RSU nevyslala regenerovaný DENM cez GN/BTP')
            remote=decode_denm(regenerated[0]['raw_hex'])
            need(remote and remote['station_id']==station_ids[target] and
                 {k:v for k,v in remote.items() if k!='station_id'}==
                 {k:v for k,v in decoded.items() if k!='station_id'},
                 'Vzdialená RSU zmenila inú DENM aplikačnú položku než hlavičku stanice')
        receive=by_stage['DENM_UPER_RX'].get(event,[])
        need(all(row['node_id'] in cars|rsus and row['raw_hex'] in
                 ({raw,regenerated[0]['raw_hex']} if regenerated else {raw}) and
                 int(row['time_us'])>=at for row in receive),
             'Prijatý DENM má nesprávne bajty, uzol alebo čas')
        for repeat in by_stage['DENM_REPEAT_TX'].get(event,[]):
            need(repeat['raw_hex']==raw and at<int(repeat['time_us'])<
                 first_detection[source,seq]+int(config['validity_s'])*1000000,
                 'DENM opakovanie zmenilo obsah alebo prekročilo platnosť')
    packet_trace=(folder/'PacketTrace.log').read_text()
    if by_stage['GATEWAY_DENM_RX']:
        need(all(token in packet_trace for token in (' SND UT ',' RCV GW ')),
             'SNS-3 surová paketová stopa nemá uplink')
    if by_stage['UT_DENM_SAT_RX']:
        need(all(token in packet_trace for token in (' SND GW ',' RCV UT ')),
             'SNS-3 surová paketová stopa nemá downlink')
    native_rows, ip_mapping = load_satellite_trace(folder)
    if (folder/'satellite-ip-trace.csv').is_file():
        native_by_uid=defaultdict(list)
        for row in native_rows:
            native_by_uid[row['packet_uid']].append(row)
        mapped_paths=set()
        for row in ip_mapping:
            uid=int(row['packet_uid'])
            raw=bytes.fromhex(row['raw_hex'])
            ihl=(raw[0]&15)*4
            need(len(raw)>=ihl+8 and raw[0]>>4==4 and raw[9]==17 and
                 int.from_bytes(raw[ihl+4:ihl+6],'big')==len(raw)-ihl and
                 row['event_id'] in event_ids,
                 'SNS-3 IP/UDP väzba nemá platný DENM datagram')
            expected='UT_DENM_SAT_TX' if row['direction']=='RTN' else 'GATEWAY_DENM_SAT_TX'
            need(any(bytes.fromhex(app['raw_hex'])==raw[ihl+8:] for app in
                     by_stage[expected][row['event_id']]),
                 'SNS-3 packet UID nepatrí deklarovanému DENM')
            steps=native_by_uid[uid]
            need(any(step['native_level']=='ND' and step['native_event']=='SND' and
                     step['node']==f"{row['node_type']} {row['node_id']}" for step in steps),
                 'SNS-3 packet UID nemá pôvodný SatNetDevice odosielací krok')
            received='GATEWAY_DENM_RX' if row['direction']=='RTN' else 'UT_DENM_SAT_RX'
            if by_stage[received][row['event_id']]:
                node='GW ' if row['direction']=='RTN' else 'UT '
                need(any(step['native_level']=='ND' and step['native_event']=='RCV' and
                         step['node'].startswith(node) for step in steps),
                     'Prijatý DENM nemá natívny SNS-3 prijímací krok')
            mapped_paths.add((row['event_id'], row['direction']))
        need(all((event, direction) in mapped_paths for direction, stage in
                 (('RTN','UT_DENM_SAT_TX'),('FWD','GATEWAY_DENM_SAT_TX'))
                 for event in by_stage[stage]),
             'Odoslaný satelitný DENM nemá vlastné SNS-3 packet UID')
    pcaps=list(folder.glob('ocb-*-0.pcap'))
    need(len(pcaps)==len(station_ids), 'Pozemný PCAP chýba pre niektoré zariadenie')
    frames=[frame for path in pcaps for _,frame in pcap_packets(path,105)]
    need(all(any(bytes.fromhex(by_stage['DENM_UPER_TX'][event][0]['raw_hex']) in frame
                 for frame in frames) and
             (not by_stage['RSU_DENM_REGENERATED'].get(event) or
              any(bytes.fromhex(by_stage['RSU_DENM_REGENERATED'][event][0]['raw_hex']) in frame
                  for frame in frames)) for event in event_ids),
         'DENM originál alebo regenerovaný paket chýba v surovom OCB PCAP')
    return {'status':'PASS','packet_backend':'native_sns3_generic_dvb',
            'application_messages':['CAM','DENM'],'cars':len(cars),'rsus':len(rsus),
            'satellites':len(manifest['topology']['catalog_ids']),
            'cam_transmitted':len(cams),'denm_events':len(event_ids),
            'denm_gateway_received':len(by_stage['GATEWAY_DENM_RX']),
            'denm_remote_car_receipts':sum(1 for event in event_ids for row in
                 by_stage['DENM_UPER_RX'][event] if row['node_id'] in cars and
                 by_stage['RSU_DENM_REGENERATED'].get(event) and
                 row['raw_hex']==by_stage['RSU_DENM_REGENERATED'][event][0]['raw_hex'])}
