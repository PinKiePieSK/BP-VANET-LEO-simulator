#!/usr/bin/env python3
"""Check ground CAM/DENM traces, CBR decisions, radio events and PCAP bytes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from simulator_packet_trace import pcap_packets
from simulator_platform import ROOT
from simulator_ground_runner import CHECKOUT, VANETZA, DEPENDENCIES, NS3_LIBRARIES
from simulator_denm_decode import decode_denm
from simulator_cam_decode import decode_cam
from simulator_rsu_radio import render as render_rsu_radio
from simulator_car_radio import render as render_car_radio
from simulator_engine_controls import effective as engine_controls


def require(test: bool, message: str) -> None:
    if not test:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def segment_hits_box(a: tuple, b: tuple, box: dict) -> bool:
    lo, hi = 0.0, 1.0
    for axis, name in enumerate(("x", "y", "z")):
        start, end = a[axis], b[axis]
        lower, upper = box[f"{name}_min"], box[f"{name}_max"]
        if abs(end-start) < 1e-12:
            if not lower <= start <= upper:
                return False
        else:
            first, second = sorted(((lower-start)/(end-start), (upper-start)/(end-start)))
            lo, hi = max(lo, first), min(hi, second)
            if lo > hi:
                return False
    return True


def load_case(folder: Path, case: dict, config: dict) -> dict:
    participants = case["participants"]
    station_ids = case["station_ids"]
    require(len(participants) == case["traffic"]["configured_vehicles"] + len(case["traffic"]["rsu_positions"]),
            "radio participants differ from SUMO demand and RSU count")
    waypoint = rows(folder / "waypoints.csv")
    tracks = defaultdict(list)
    for row in waypoint:
        tracks[row["node_id"]].append(row)
    count = config["sample_count"]
    require(set(tracks) == set(participants) and all(len(t) == count for t in tracks.values()),
            "FCD-derived waypoint coverage differs")
    for node in participants:
        for index, row in enumerate(tracks[node]):
            require(int(row["index"]) == index and int(row["station_id"]) == station_ids[node] and
                    int(row["time_us"]) == round(case["sample_times_s"][index] * 1e6),
                    "waypoint time/identity mismatch")
    traffic = case["traffic"]
    world = json.loads((folder / "world.json").read_text())
    demand = json.loads((ROOT / case["config"]["demand"]).read_text())
    expected_world = json.loads((ROOT / config["base_world"]).read_text())
    expected_world["vehicles"] = demand["vehicles"]
    expected_world["simulation"]["step_s"] = 0.1
    require(world == expected_world,
            "map/demand combination changed")
    require((folder / "rsu-radio.csv").read_bytes() == render_rsu_radio(world, config),
            "RSU radio PHY differs from the selected world and shared model")
    car_radio = folder / "car-radio.csv"
    if car_radio.is_file():
        require(car_radio.read_bytes() == render_car_radio(
            world, config, engine_controls({'engine': config.get('engine', {})})['car_antenna_height_m']),
            "car radio PHY differs from the selected world and shared model")
        car_applied = {match[0]: [float(value) for value in match[1:]] for match in re.findall(
            r'^CAR_RADIO_PROFILE ID=(\w+) TX=([-+\deE.]+) NOISE=([-+\deE.]+) TX_GAIN=([-+\deE.]+) RX_GAIN=([-+\deE.]+) HEIGHT=([-+\deE.]+)$',
            (folder / "run.log").read_text(), re.M)}
        car_declared = rows(car_radio)
        require(set(car_applied) == {row['id'] for row in car_declared} and all(
            all(math.isclose(a, float(row[key]), abs_tol=1e-6) for a, key in zip(car_applied[row['id']],
                ('tx_power_dbm', 'noise_figure_db', 'tx_gain_dbi', 'rx_gain_dbi', 'antenna_height_m')))
            for row in car_declared), "car PHY actually applied by ns-3 differs from the CSV")
    applied = {match[0]: [float(value) for value in match[1:]] for match in re.findall(
        r'^RSU_RADIO_PROFILE ID=(\w+) TX=([-+\deE.]+) NOISE=([-+\deE.]+) TX_GAIN=([-+\deE.]+) RX_GAIN=([-+\deE.]+) HEIGHT=([-+\deE.]+)$',
        (folder / "run.log").read_text(), re.M)}
    declared = rows(folder / "rsu-radio.csv")
    require(set(applied) == {row['id'] for row in declared} and all(
        all(math.isclose(a, float(row[key]), abs_tol=1e-6) for a, key in zip(applied[row['id']],
            ('tx_power_dbm', 'noise_figure_db', 'tx_gain_dbi', 'rx_gain_dbi', 'antenna_height_m')))
        for row in declared), "RSU PHY actually applied by ns-3 differs from the CSV")
    for rsu in world["rsus"]:
        for sample in tracks[rsu["id"]]:
            require(math.isclose(float(sample["x_m"]), rsu["x_m"], abs_tol=0.01) and
                    math.isclose(float(sample["y_m"]), rsu["y_m"], abs_tol=0.01),
                    "RSU coordinate differs from declared world")
    fcd = ET.parse(folder / "sumo/fcd.xml").getroot()
    times = set(case["sample_times_s"])
    sumo_manifest = json.loads((folder / "sumo/manifest.json").read_text())
    hold_until = sumo_manifest.get("radio_window_hold_until_s")
    if hold_until is not None:
        require(hold_until > max(times), "SUMO radio hold ends before the CAM window")
        routes = ET.parse(folder / "sumo/vehicles.rou.xml").getroot()
        route_edges = {row.get("id"): row.get("edges").split() for row in routes.findall("route")}
        vehicles = routes.findall("vehicle")
        require({row.get("id") for row in vehicles} == {v["id"] for v in world["vehicles"]},
                "radio hold vehicle set changed")
        for vehicle in vehicles:
            stops = vehicle.findall("stop")
            require(len(stops) == 1 and stops[0].get("lane") == route_edges[vehicle.get("route")][-1] + "_0" and
                    math.isclose(float(stops[0].get("until")), hold_until, abs_tol=.011),
                    "SUMO radio hold route or time changed")
    observed = [step for step in fcd.findall("timestep") if round(float(step.get("time")), 6) in times]
    require(len(observed) == count, "FCD time coverage changed")
    speeds = []
    for step in observed:
        vehicles = step.findall("vehicle")
        require({v.get("id") for v in vehicles} == {v["id"] for v in world["vehicles"]},
                "realized density differs from configured demand")
        speeds.extend(float(v.get("speed")) for v in vehicles)
    summary = ET.parse(folder / "sumo/summary.xml").getroot().findall("step")
    require(max(int(s.get("teleports", "0")) for s in summary) == traffic["sumo_teleports_total"] and
            max(int(s.get("collisions", "0")) for s in summary) == traffic["sumo_collisions_total"] and
            math.isclose(sum(speeds)/len(speeds), traffic["mean_speed_mps"], abs_tol=1e-9),
            "SUMO traffic diagnostics changed")
    blocked_pairs = None
    if "buildings" in case["config"]:
        source = ROOT / case["config"]["buildings"]
        require(digest(source) == case["building_sha256"], "building source changed")
        boxes = json.loads(source.read_text())["boxes"]
        require(rows(folder / "buildings.csv") == [{k: str(v) for k,v in box.items()} for box in boxes],
                "native building boxes differ from source")
        observations = rows(folder / "building_los.csv")
        require(len(observations) == count*len(world["vehicles"])*len(world["rsus"]),
                "building LOS trace count differs")
        seen, blocked_pairs = set(), 0
        times_us = {int(s["time_us"]): index for index,s in enumerate(tracks[participants[0]])}
        for row in observations:
            when = int(row["time_us"])
            key = (when, row["node_id"], row["rsu_id"])
            require(key not in seen and when in times_us and row["node_id"] in {v["id"] for v in world["vehicles"]},
                    "building LOS identity/time invalid")
            seen.add(key)
            car = tracks[row["node_id"]][times_us[when]]
            rsu = tracks[row["rsu_id"]][times_us[when]]
            a = (float(car["x_m"]),float(car["y_m"]),1.5)
            b = (float(rsu["x_m"]),float(rsu["y_m"]),5.0)
            blocked = any(segment_hits_box(a,b,box) for box in boxes)
            require(int(row["blocked"]) == int(blocked), "ns-3 building LOS differs from independent box geometry")
            blocked_pairs += int(blocked)
        require(blocked_pairs > 0, "building obstacle did not intersect a measured radio link")
    elif "obstructions" in case["config"]:
        source = ROOT / case["config"]["obstructions"]
        require(digest(source) == case["obstruction_sha256"] and
                (folder / "osm-buildings.csv").read_bytes() == source.read_bytes(),
                "OSM ground footprints differ from pinned source")
        require(case["building_sha256"] is None and not (folder / "building_los.csv").exists(),
                "legacy box trace leaked into OSM ground case")
    else:
        require(case["building_sha256"] is None and not (folder / "building_los.csv").exists(),
                "building trace leaked into non-building case")

    cam = rows(folder / "cam.csv")
    node_policy=config.get('node_policy')
    car_mode=lambda node: node_policy['cars'][node]['ground'] if node_policy else 'all'
    rsu_active=lambda node: node_policy['rsus'][node]['ground'] if node_policy else True
    tx, gn = {}, {}
    for row in cam:
        key = (int(row["station_id"]), int(row["gdt_ms"]))
        target = tx if row["stage"] == "CAM_UPER_TX" else gn if row["stage"] == "GN_BTP_CAM_TX" else None
        require(target is not None and key not in target, "duplicate or unexpected CAM stage")
        require(row["node_id"] in participants and station_ids[row["node_id"]] == key[0], "CAM station mismatch")
        target[key] = row
    require(tx and set(gn)=={key for key,row in tx.items() if car_mode(row['node_id'])!='off'},
            "CAM/GN offer identity mismatch with per-node radio policy")
    engine = engine_controls({'engine': config.get('engine', {})})
    last_low = {}
    for key, row in sorted(tx.items(), key=lambda item: (item[1]["node_id"], int(item[1]["time_us"]))):
        raw = bytes.fromhex(row["raw_hex"])
        wire = bytes.fromhex(gn[key]["raw_hex"]) if key in gn else None
        node, now = row["node_id"], int(row["time_us"])
        low = node not in last_low or now-last_low[node] >= engine['cam_low_frequency_ms']*1000
        require(41 <= len(raw) <= 80 and
                (wire is None or (len(wire) == len(raw)+44 and wire.endswith(raw) and
                                  ('acceleration_dmps2' not in tracks[node][0] or not (wire[32] & 0x80)) and
                                  int(row["time_us"]) == int(gn[key]["time_us"]))), "CAM/GN raw bytes differ")
        if low:
            last_low[node] = now
    # Decode representative raw CAMs independently of the sender's trace fields.
    for node in (item for item in participants if item in {v['id'] for v in world['vehicles']}):
        track = tracks[node]
        if 'acceleration_dmps2' not in track[0]:
            continue  # Older waypoint rows do not contain the fields checked below.
        chosen = {0, min(5, count-1), count-1}
        chosen.add(next((i for i, w in enumerate(track) if int(w['acceleration_dmps2']) != 0), 0))
        for i in sorted(chosen):
            w = track[i]
            key = (int(w['station_id']), int(w['generation_delta_ms']))
            if key not in tx:
                continue
            decoded = decode_cam(tx[key]['raw_hex'])
            require(decoded is not None and decoded['latitude_code'] == int(w['latitude_e7']) and
                    decoded['longitude_code'] == int(w['longitude_e7']) and
                    decoded['speed_code'] == int(w['speed_cmps']) and
                    decoded['heading_code'] == int(w['heading_decideg']) and
                    decoded['longitudinal_acceleration_code'] == int(w['acceleration_dmps2']) and
                    decoded['yaw_rate_code'] == int(w['yaw_rate_cdegps']) and
                    decoded['curvature_code'] == int(w['curvature_1e4']) and
                    decoded['vehicle_length_code'] == int(w['vehicle_length_dm']) and
                    decoded['vehicle_width_code'] == int(w['vehicle_width_dm']) and
                    decoded['position_confidence_major_code'] == 4095 and
                    decoded['position_confidence_minor_code'] == 4095,
                    'decoded CAM differs from SUMO waypoint')
            if decoded['low_frequency_present']:
                require(decoded['exterior_lights_hex'] == f"{int(w['exterior_lights_bits']):02x}" and
                        decoded['path_history_count'] == (1 if i >= 5 else 0),
                        'decoded CAM lights or history differ')
    got = set()
    rx_count = 0
    car_set = {v['id'] for v in world['vehicles']}
    rsu_set = {r['id'] for r in world['rsus']}
    with (folder / "rx.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            key = (int(row["station_id"]), int(row["gdt_ms"]))
            pair = (key, row["rx_node_id"])
            receiver=row['rx_node_id'];sender=tx[key]['node_id'] if key in tx else ''
            allowed=key in gn and (receiver in car_set and car_mode(receiver)!='off' or
                                 receiver in rsu_set and rsu_active(receiver) and car_mode(sender)=='all')
            require(allowed and pair not in got and receiver != sender and
                    row["cam_hex"] == tx[key]["raw_hex"] and row["gn_hex"] == gn[key]["raw_hex"],
                    "RX CAM/GN bytes, receiver or duplicate differs")
            require(int(row["time_us"]) >= int(tx[key]["time_us"]), "RX precedes TX")
            got.add(pair)
            rx_count += 1
    pcap_paths = sorted(folder.glob("ocb-*-0.pcap"), key=lambda p: int(p.name.split("-")[1]))
    require(len(pcap_paths) == len(participants), "one OCB PCAP per station required")
    # ns-3 OCB frames have a 34-byte 802.11/LLC prefix and a 4-byte FCS.
    # Index the exact GN payload once: scanning every frame for every received
    # packet makes large fleets quadratic in the number of receptions.
    frames = {}
    for node, path in zip(participants, pcap_paths):
        packets = pcap_packets(path, 105)
        # Short control frames have no GN payload; pcap_packets already
        # validates their record length and we audit CAM payloads below.
        frames[node] = Counter(frame[34:-4] for _, frame in packets if len(frame) >= 38)
    for key, row in gn.items():
        wire = bytes.fromhex(row["raw_hex"])
        require(frames[row["node_id"]][wire] == 1,
                "transmitted GN wire absent/duplicated in source PCAP")
    for key, node in got:
        wire = bytes.fromhex(gn[key]["raw_hex"])
        require(frames[node][wire] == 1,
                "received GN wire absent/duplicated in receiver PCAP")

    states = defaultdict(list)
    with (folder / "phy_state.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            require(row["node_id"] in participants and 0 <= int(row["state"]) <= 6,
                    "PHY state invalid")
            if int(row["state"]) in (1, 2, 3):
                states[row["node_id"]].append((int(row["seq"]), int(row["start_us"]),
                                               int(row["end_us"])))
    decisions = rows(folder / "dcc_decisions.csv")
    by_node = defaultdict(list)
    for d in decisions:
        by_node[d["node_id"]].append(d)
    car_ids = {v["id"] for v in world["vehicles"]}
    participant_index = {node: i for i, node in enumerate(participants)}
    require(set(by_node) == car_ids and all(len(by_node[id]) == count for id in car_ids),
            "CAM trigger decision count differs from moving cars")
    for node in car_ids:
        last = None
        tgen, periodic_count = engine['cam_tgen_max_ms'], 0
        busy = states[node]
        require(all(start <= end and
                    (i == 0 or (seq > busy[i-1][0] and start >= busy[i-1][1]))
                    for i, (seq, start, end) in enumerate(busy)),
                "PHY busy intervals are not chronological")
        busy_cursor = 0
        union_start, union_end, union_total = [], [], []
        def occupied_before(boundary):
            pos = bisect_right(union_start, boundary) - 1
            if pos < 0:
                return 0
            earlier = union_total[pos-1] if pos else 0
            return earlier + min(max(boundary-union_start[pos], 0),
                                 union_end[pos]-union_start[pos])
        for index, d in enumerate(by_node[node]):
            sample = tracks[node][index]
            now, seq = int(d["time_us"]), int(d["seq"])
            phase = case["config"].get("phase_us", config["phase_us"])
            require(now == int(sample["time_us"]) + phase * (participant_index[node]+1),
                    "CAM check not aligned to 100ms motion sample")
            while busy_cursor < len(busy) and busy[busy_cursor][0] < seq:
                _, start, end = busy[busy_cursor]
                if union_end and start <= union_end[-1]:
                    if end > union_end[-1]:
                        union_total[-1] += end-union_end[-1]
                        union_end[-1] = end
                else:
                    union_start.append(start)
                    union_end.append(end)
                    union_total.append((union_total[-1] if union_total else 0) + end-start)
                busy_cursor += 1
            occupied = occupied_before(now) - occupied_before(now-1000000)
            denominator = max(1, min(1000000, now-int(tracks[node][0]["time_us"])))
            load = occupied/denominator
            require(math.isclose(load, float(d["cbr_1s"]), abs_tol=1e-8),
                    "CBR decision is not recomputable from observed PHY states")
            policy = config["dcc_policy"]
            minimum = (policy["high_interval_ms"] if load >= policy["high_cbr"] else
                       policy["mid_interval_ms"] if load >= policy["low_cbr"] else 100) if case["config"]["dcc"] else 100
            require(minimum == int(d["dcc_min_ms"]) and tgen == int(d["t_gen_cam_ms"]),
                    "DCC interval or T_GenCam state does not follow trace")
            if last is None:
                motion, periodic, trigger = False, True, 0
            else:
                distance = math.hypot(float(sample["x_m"])-float(last["x_m"]),
                                      float(sample["y_m"])-float(last["y_m"]))
                speed = abs(int(sample["speed_cmps"])-int(last["speed_cmps"]))/100
                angle = abs(int(sample["heading_decideg"])-int(last["heading_decideg"]))/10
                heading = min(angle, 360-angle)
                motion = (distance > engine['cam_distance_m'] or
                          speed > engine['cam_speed_mps'] or
                          heading > engine['cam_heading_deg'])
                elapsed = now - last_time
                periodic = elapsed >= tgen*1000
                trigger = 1 if elapsed >= minimum*1000 and motion else (
                          2 if elapsed >= minimum*1000 and periodic else -1)
            send = trigger >= 0
            require(int(d["motion_trigger"]) == int(motion) and
                    int(d["periodic_trigger"]) == int(periodic) and
                    int(d["trigger_condition"]) == trigger and
                    int(d["send"]) == int(send), "CAM movement/periodic trigger changed")
            if send:
                gdt = int(sample["generation_delta_ms"])
                key = (station_ids[node], gdt)
                require(key in tx and int(tx[key]["time_us"]) == now, "trigger has no exact CAM packet")
                if trigger == 1:
                    tgen, periodic_count = min(engine['cam_tgen_max_ms'], max(100, elapsed//1000)), 0
                elif trigger == 2:
                    periodic_count += 1
                    if periodic_count >= engine['cam_periodic_repeat']:
                        tgen, periodic_count = engine['cam_tgen_max_ms'], 0
                last, last_time = sample, now
    require(sum(int(d["send"]) for d in decisions) == len(tx), "CAM trigger total differs from packets")
    log = (folder / "run.log").read_text()
    radio_config = re.search(r'OCB_CONFIG RATE_MBPS=(\d+) CHANNEL=(\d+) FREQUENCY_HZ=(\d+) TX_GAIN_DBI=([-\d.]+) RX_GAIN_DBI=([-\d.]+) SHADOWING=(\d+)',log)
    require(radio_config is not None and int(radio_config[1])==config.get('rate_mbps',6) and
            int(radio_config[2])==config.get('channel_number',180) and
            int(radio_config[3])==(5000+5*config.get('channel_number',180))*1000000 and
            float(radio_config[4])==config.get('tx_gain_dbi',0) and
            float(radio_config[5])==config.get('rx_gain_dbi',0) and
            int(radio_config[6])==int(case['config'].get('shadowing',False)),
            'OCB PHY parameter log differs from the scenario')
    match = re.search(r"GROUND_NODES=(\d+) CAM_TX=(\d+) CAM_RX=(\d+) PHY_DROPS=(\d+) GN_DROPS=(\d+) DCC=(\d+) RADIO=(\w+) SHADOWING=(\d+) TX_POWER_DBM=([0-9.]+) RX_NOISE_FIGURE_DB=([0-9.]+) PHASE_US=(\d+) SEED=(\d+) RUN=(\d+) DCC_LOW_CBR=([0-9.]+) DCC_HIGH_CBR=([0-9.]+) DCC_MID_MS=(\d+) DCC_HIGH_MS=(\d+)", log)
    require(match is not None and (int(match[1]), int(match[2]), int(match[3])) ==
            (len(participants), len(gn), rx_count) and int(match[5]) == 0 and
            int(match[6]) == int(case["config"]["dcc"]) and match[7] == case["config"]["radio_mode"] and
            int(match[8]) == int(case["config"].get("shadowing",False)) and
            float(match[9]) == config["tx_power_dbm"] and float(match[10]) == config["noise_figure_db"] and
            int(match[11]) == case["config"].get("phase_us",config["phase_us"]) and
            int(match[12]) == config["seed"] and int(match[13]) == config["run"] and
            float(match[14]) == config["dcc_policy"]["low_cbr"] and
            float(match[15]) == config["dcc_policy"]["high_cbr"] and
            int(match[16]) == config["dcc_policy"]["mid_interval_ms"] and
            int(match[17]) == config["dcc_policy"]["high_interval_ms"],
            "native log counters/policy differ")
    drop_rows = rows(folder / "phy_drop.csv")
    require(len(drop_rows) == int(match[4]) and
            all(row["node_id"] in participants and 0 <= int(row["time_us"]) for row in drop_rows),
            "PHY drop reasons differ from native counter")
    reasons = dict(Counter(row["reason"] for row in drop_rows))
    offered_pairs=sum(1 for key,row in gn.items() for receiver in participants
                      if receiver!=row['node_id'] and
                      (receiver in {v['id'] for v in world['vehicles']} and car_mode(receiver)!='off' or
                       receiver in {r['id'] for r in world['rsus']} and rsu_active(receiver) and car_mode(row['node_id'])=='all'))
    result={"vehicles": len(car_ids), "rsus": len(participants)-len(car_ids),
            "cam_tx": len(gn),
            "cam_rx": rx_count, "offered_receiver_pairs": offered_pairs,
            "local_pdr": rx_count/offered_pairs, "phy_rx_drops": int(match[4]),
            "phy_drop_reasons": reasons,
            "mean_speed_mps": traffic["mean_speed_mps"],
            "teleports": traffic["sumo_teleports_total"],
            "mean_cbr": sum(float(d["cbr_1s"]) for d in decisions)/len(decisions),
            "peak_cbr": max(float(d["cbr_1s"]) for d in decisions),
            "dcc_limited_checks": sum(int(d["dcc_min_ms"]) > 100 for d in decisions),
            "building_blocked_car_rsu_samples": blocked_pairs}
    if config.get('denm_events'):
        native_events=rows(folder/'denm-events.csv')
        require(len(native_events)==len(config['denm_events']),
                'Ground DENM event input count changed')
        trace=rows(folder/'trace.csv')
        stages=defaultdict(lambda:defaultdict(list))
        for row in trace:
            require(int(row['bytes'])==len(bytes.fromhex(row['raw_hex'])),
                    'Ground raw trace byte count differs')
            stages[row['stage']][row['event_id']].append(row)
        require(len(stages['DENM_UPER_TX'])==len(native_events),
                'Ground DENM source event count differs')
        origin=datetime.fromisoformat(config['utc_origin'].replace('Z','+00:00'))
        start_ms=int((origin-datetime(2004,1,1,tzinfo=timezone.utc)).total_seconds()*1000)
        detection={}
        for setting in native_events:
            at=int(setting['time_us']);seq=int(setting['sequence']);source=setting['source_id']
            rows_at=[(event,items[0]) for event,items in stages['DENM_UPER_TX'].items()
                     if len(items)==1 and int(items[0]['time_us'])==at and items[0]['node_id']==source]
            require(len(rows_at)==1,'Ground DENM did not start at declared time')
            event,row=rows_at[0];raw=row['raw_hex'];decoded=decode_denm(raw)
            detection.setdefault((source,seq),at)
            require(decoded and source in station_ids and row['node_id']==source and
                    decoded['station_id']==station_ids[source] and
                    decoded['originating_station_id']==station_ids[source] and
                    decoded['sequence_number']==seq and
                    decoded['detection_time_ms']==start_ms+detection[source,seq]//1000 and
                    decoded['reference_time_ms']==start_ms+at//1000 and
                    decoded['validity_s']==int(setting['validity_s']) and
                    decoded['transmission_interval_ms']==int(setting['repetition_ms']) and
                    decoded['traffic_subcause']==5 and decoded['detection_paths']>=1 and
                    decoded['termination']==(0 if setting['operation']=='cancel' else -1),
                    'Ground DENM ASN.1 identity, event or lifecycle differs')
            emits=stages['CAR_DENM_GBC_TX'].get(event,[])
            require(emits and all(item['node_id']==source and
                                  item['raw_hex']==raw for item in emits),
                    'Ground DENM GBC source bytes differ')
            wire=[item for item in stages['GN_BTP_DENM_TX'].get(event,[])
                  if item['node_id']==source]
            require(wire and all(item['raw_hex'].endswith(raw) for item in wire),
                    'Ground DENM GN/BTP source payload differs')
            require(any(bytes.fromhex(item['raw_hex']) in frame
                        for _,frame in pcap_packets(pcap_paths[participant_index[source]],105)
                        for item in wire),
                    'Ground DENM GBC absent in source OCB PCAP')
            for received in stages['DENM_UPER_RX'].get(event,[]):
                require(received['node_id']!=source and
                        received['raw_hex']==raw and int(received['time_us'])>at,
                        'Ground DENM receiver bytes, identity or time changed')
        result['denm_events']=len(native_events)
        result['denm_receipts']=sum(len(items) for items in stages['DENM_UPER_RX'].values())
    if node_policy:result['cam_generated']=len(tx)
    return result


def verify(out: Path) -> dict:
    out = out.resolve()
    manifest = json.loads((out / "run-manifest.json").read_text())
    require(manifest["schema_version"] == 1 and manifest["execution_state"] == "native_ground_packets",
            "wrong ground model manifest state")
    config_path = ROOT / manifest["config_path"]
    config = json.loads(config_path.read_text())
    require(config["cam_sender_policy"] == "all_its_g5_vehicles" and
            config["cam_receiver_policy"] == "all_other_radio_nodes", "ground model CAM role policy changed")
    for key, path in (("config_sha256", config_path), ("base_world_sha256", ROOT / config["base_world"]),
                      ("source_sha256", ROOT / "src/vanet-ground-network.cc"),
                      ("runner_sha256", ROOT / "tools/simulator_ground_runner.py"),
                      ("generator_sha256", ROOT / "tools/simulator_mobility_export.py"),
                      ("checker_sha256", Path(__file__)),
                      ("binary_sha256", out / "ground-packet-engine")):
        require(manifest[key] == digest(path), f"Ground provenance changed: {key}")
    dependencies = {name: digest(ROOT / name) for name in DEPENDENCIES + (("tools/simulator_node_policy.py",) if "node_policy" in config else ()) +
                    (("src/ground-building-condition.h", "tools/simulator_ground_obstructions.py") if
                     any("obstructions" in case for case in config["cases"]) else ())}
    require(manifest["dependency_sha256"] == dependencies,
            "ground model dependency source changed")
    for name, commit in manifest["ns3_commits"].items():
        require(subprocess.check_output(["git", "-C", str(CHECKOUT / name), "rev-parse", "HEAD"],
                                        text=True).strip() == commit,
                "ground model ns-3/SNS-3 checkout commit changed")
    require(subprocess.check_output(["git", "-C", str(VANETZA), "rev-parse", "HEAD"],
                                    text=True).strip() == manifest["vanetza_commit"],
            "ground model Vanetza commit changed")
    require(manifest["ns3_library_sha256"] ==
            {name: digest(CHECKOUT / f"build/lib/libns3.38-{name}-debug.so") for name in NS3_LIBRARIES},
            "ground model linked ns-3.38 library changed")
    require(manifest["tool_versions"] ==
            {name: subprocess.check_output([name, "--version"], text=True).splitlines()[0]
             for name in ("sumo", "netconvert", "g++")},
            "ground model toolchain version changed")
    require(set(manifest["cases"]) == {c["id"] for c in config["cases"]}, "case set changed")
    for name, case in manifest["cases"].items():
        require(digest(ROOT / case["config"]["demand"]) == case["demand_sha256"],
                "demand source changed")
        if "buildings" in case["config"]:
            require(digest(ROOT / case["config"]["buildings"]) == case["building_sha256"],
                    "building provenance changed")
        if "obstructions" in case["config"]:
            require(digest(ROOT / case["config"]["obstructions"]) == case["obstruction_sha256"],
                    "OSM ground building provenance changed")
    for relative, sha in manifest["raw_sha256"].items():
        require(digest(out / relative) == sha, f"raw artifact changed: {relative}")
    stats = {name: load_case(out / name, case, config) for name, case in manifest["cases"].items()}
    if set(stats) >= {"sparse_los", "medium_los", "dense_los", "dense_los_dcc", "dense_nlos", "dense_los_late", "dense_collision", "dense_building", "dense_building_shadow"}:
        require([stats[x]["vehicles"] for x in ("sparse_los", "medium_los", "dense_los")] == [3,12,24],
                "density ladder changed")
        require(stats["dense_los_dcc"]["cam_tx"] < stats["dense_los"]["cam_tx"] and
                stats["dense_los_dcc"]["dcc_limited_checks"] > 0,
                "measured-CBR feedback did not reduce CAM load")
        require(stats["dense_nlos"]["local_pdr"] < stats["dense_los"]["local_pdr"] and
                stats["dense_nlos"]["phy_rx_drops"] > 0,
                "LOS/NLOS radio contrast absent")
        require(stats["dense_collision"]["local_pdr"] < stats["dense_los"]["local_pdr"] and
                stats["dense_collision"]["phy_rx_drops"] > stats["dense_los"]["phy_rx_drops"],
                "synchronized collision control absent")
        require(stats["dense_collision"]["phy_drop_reasons"].get("RXING", 0) +
                stats["dense_collision"]["phy_drop_reasons"].get("BUSY_DECODING_PREAMBLE", 0) > 0,
                "collision control lacks overlapping reception evidence")
        require(stats["dense_building"]["building_blocked_car_rsu_samples"] ==
                stats["dense_building_shadow"]["building_blocked_car_rsu_samples"] and
                stats["dense_building"]["local_pdr"] != stats["dense_building_shadow"]["local_pdr"],
                "shadowing sensitivity effect absent or building pair changed")
        require(all(stats[x]["teleports"] == 0 for x in stats), "SUMO teleport invalidates traffic window")
    return stats


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    print(json.dumps(verify(args.output), sort_keys=True, indent=2))
