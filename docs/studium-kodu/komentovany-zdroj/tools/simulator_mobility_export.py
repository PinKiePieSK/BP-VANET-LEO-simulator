#!/usr/bin/env python3
# Spojí SUMO FCD polohy s identitou staníc a vytvorí waypoints.csv pre C++ paketový engine.
# Dôležitý most medzi pohybom vozidiel a časmi odoslania CAM.
"""Produce 100 ms motion samples for ground model; native CAM timing is decided at runtime."""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import astropy.units as u
from astropy.time import Time

from simulator_sumo import validate as validate_v2
from simulator_platform import CAM_FIELDS as FIELDS, sha
from simulator_coordinates import enu_to_wgs84


# Číta časové polohy z FCD a zapisuje ich vo formáte, ktorý číta natívny paketový engine. Každý
# riadok spája identitu auta alebo RSU, čas, zemepisnú polohu a pohybové údaje. Na tejto hranici
# sa SUMO mobilita stretáva s rádiovou simuláciou.
def prepare(world_path: Path, fcd_path: Path, normalized: dict, output: Path) -> dict:
    world = json.loads(world_path.read_text())
    validate_v2(world)
    agents = normalized["agents"]
    cam = normalized["applications"]["cam"]
    source_id, rsu_id = agents["cam_source_id"], agents["rsu_id"]
    cars = {item["id"]: item for item in world["vehicles"] if "its_g5" in item["technologies"]}
    rsus = {item["id"]: item for item in world["rsus"] if "its_g5" in item["technologies"]}
    v2v_only = rsu_id == "" and not rsus
    if source_id not in cars or (not v2v_only and rsu_id not in rsus):
        raise ValueError("scenario selected CAM source or RSU missing in staged world")
    participants = ([cars[source_id]] + [item for name, item in cars.items() if name != source_id] +
                    ([] if v2v_only else [item for name, item in rsus.items() if name != rsu_id] + [rsus[rsu_id]]))
    if len(participants) < 2 or len(cars) < 2:
        raise ValueError("simulator requires at least 2 radio cars")
    count = cam["count"]
    if not 1 <= count <= 1200:
        raise ValueError("Native engine supports 1–1200 CAM samples per case")
    times = [round(cam["first_tx_s"] + index * cam["interval_s"], 6) for index in range(count)]
    if any(abs(round(value * 1_000_000) - value * 1_000_000) > 1e-5 for value in times):
        raise ValueError("CAM times must resolve to microseconds")
    fcd_by_time = {}
    for tick in ET.parse(fcd_path).getroot().findall("timestep"):
        value = round(float(tick.get("time")), 6)
        if value in times:
            fcd_by_time[value] = {vehicle.get("id"): vehicle for vehicle in tick.findall("vehicle")}
    if set(fcd_by_time) != set(times):
        raise ValueError("SUMO FCD misses a declared CAM time")
    anchor = world["georeference"]
    # Rozmery prenášané v CAM musia zodpovedať individuálnemu typu vozidla v SUMO. Pri každom aute
    # sa preto k spoločnému modelu pridajú jeho vlastné zmeny ešte pred kódovaním dĺžky a šírky.
    model = world["simulation"].get("vehicle_model", {"length_m": 5, "width_m": 1.8})
    origin = datetime.fromisoformat(world["simulation"]["utc_origin"].replace("Z", "+00:00"))
    epoch = Time(datetime(2004, 1, 1, tzinfo=timezone.utc), scale="utc")
    gdts = []
    for value in times:
        moment = origin + timedelta(seconds=value)
        elapsed_tai_ms = round((Time(moment, scale="utc").tai - epoch.tai).to_value(u.ms))
        gdts.append(elapsed_tai_ms % 65536)
    if len(set(gdts)) != len(gdts):
        raise ValueError("CAM generationDeltaTime wraps/collides in one native case")
    rows = []
    prior_heading: dict[str, tuple[float, float]] = {}
    for node_index, participant in enumerate(participants):
        node_id = participant["id"]
        kind = "car" if node_id in cars else "rsu"
        station_id = 1001 + node_index
        car_model = {**model, **participant.get("vehicle_model", {})} if kind == "car" else model
        length_dm = round(car_model["length_m"] * 10)
        width_dm = round(car_model["width_m"] * 10)
        for index, value in enumerate(times):
            if kind == "car":
                vehicle = fcd_by_time[value].get(node_id)
                if vehicle is None:
                    raise ValueError(f"{node_id} absent in FCD at t={value}")
                x, y = float(vehicle.get("x")), float(vehicle.get("y"))
                speed = float(vehicle.get("speed"))
                heading = float(vehicle.get("angle")) % 360.0
                # SUMO's FCD acceleration and signalling are sampled at the same instant as position.
                accel = float(vehicle.get("acceleration"))
                signals = int(vehicle.get("signals"))
                if not math.isfinite(accel):
                    raise ValueError(f"non-finite FCD acceleration for {node_id}")
                accel_code = -160 if accel <= -16 else 160 if accel >= 16 else round(accel * 10)
                # Zmena smeru medzi dvoma vzorkami poskytne uhlovú rýchlosť; pri dostatočnej
                # rýchlosti z nej vyplýva zakrivenie. Prvý bod nemá minulú vzorku, preto používa
                # ETSI kód unavailable. Bity svetiel sa mapujú z presných bitov SUMO.
                previous = prior_heading.get(node_id)
                yaw_code, curvature_code = 32767, 1023
                if previous is not None:
                    old_heading, old_time = previous
                    dt = value - old_time
                    # ETSI yaw is positive counterclockwise; SUMO heading grows clockwise from north.
                    delta = (heading - old_heading + 180) % 360 - 180
                    yaw = -delta / dt
                    yaw_code = max(-32766, min(32766, round(yaw * 100)))
                    if speed >= 1.0:
                        curvature_code = max(-1023, min(1022, round(math.radians(yaw) / speed * 10000)))
                prior_heading[node_id] = (heading, value)
                # ETSI ExteriorLights bit order: low/high/left/right/day/reverse/fog/parking.
                lights = (0x80 if signals & 16 else 0) | (0x40 if signals & 64 else 0)
                lights |= (0x20 if signals & 2 else 0) | (0x10 if signals & 1 else 0)
                lights |= (0x04 if signals & 128 else 0) | (0x02 if signals & 32 else 0)
            else:
                x, y = float(participant["x_m"]), float(participant["y_m"])
                speed, heading = 0.0, 0.0
                accel_code, yaw_code, curvature_code, lights = 161, 32767, 1023, 0
            lat, lon, height = enu_to_wgs84(x, y, anchor["anchor_x_m"], anchor["anchor_y_m"],
                                             anchor["latitude_deg"], anchor["longitude_deg"],
                                             anchor["height_m"])
            moment = origin + timedelta(seconds=value)
            rows.append({"node_id": node_id, "station_id": station_id, "kind": kind,
                         "index": index, "time_us": round(value * 1_000_000),
                         "utc": moment.isoformat().replace("+00:00", "Z"),
                         "x_m": f"{x:.2f}", "y_m": f"{y:.2f}",
                         "latitude_e7": round(lat * 1e7), "longitude_e7": round(lon * 1e7),
                         "altitude_cm": round(height * 100), "speed_cmps": round(speed * 100),
                         "heading_decideg": round(heading * 10) % 3600,
                         "generation_delta_ms": gdts[index],
                         "acceleration_dmps2": accel_code,
                         "yaw_rate_cdegps": yaw_code,
                         "curvature_1e4": curvature_code,
                         "vehicle_length_dm": length_dm if kind == "car" else 1023,
                         "vehicle_width_dm": width_dm if kind == "car" else 62,
                         "exterior_lights_bits": lights})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    metadata = {"world_sha256": sha(world_path), "fcd_sha256": sha(fcd_path),
                "waypoints_sha256": sha(output), "source_id": source_id, "rsu_id": rsu_id,
                "participants": [item["id"] for item in participants],
                "sample_times_s": times, "generation_delta_ms": gdts,
                "station_ids": {item["id"]: 1001 + index for index, item in enumerate(participants)}}
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata
