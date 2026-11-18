"""Validate a versioned editable road graph and run its traffic in SUMO.

This is a traffic/geometry generator. The technologies field is metadata only;
this module never starts ns-3, SNS-3, Vanetza, or a network simulation.
"""

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
TECHNOLOGIES = {"its_g5", "cellular_v2x", "ip_backhaul", "satellite_terminal"}
MESSAGE_TYPES = {"CAM", "DENM", "IP_REPORT", "CUSTOM"}
CAR_MODEL_RANGES = {"accel_mps2": (.1, 10), "decel_mps2": (.1, 15),
                    "sigma": (0, 1), "length_m": (1, 20), "width_m": (.5, 3),
                    "min_gap_m": (0, 10), "speed_factor": (.1, 2)}
RSU_RADIO_RANGES = {"tx_power_dbm": (0, 33), "noise_figure_db": (0, 20),
                    "tx_gain_dbi": (-20, 20), "rx_gain_dbi": (-20, 20),
                    "antenna_height_m": (.2, 100)}
CAR_RADIO_RANGES = {**RSU_RADIO_RANGES, "antenna_height_m": (.2, 10)}


def only_keys(value, required, optional=(), label="object"):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"{label}: expected keys {sorted(required)}, optional {sorted(optional)}")


def number(value, lo, hi, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f"{label}: expected finite number in [{lo},{hi}]")
    return float(value)


def validate_car_model(model, label):
    only_keys(model, set(), CAR_MODEL_RANGES, label=label)
    if not model:
        raise ValueError(f"{label}: empty override; use the shared model")
    for key, value in model.items():
        number(value, *CAR_MODEL_RANGES[key], f"{label}.{key}")


def validate_rsu_radio(model, label):
    only_keys(model, set(), RSU_RADIO_RANGES, label=label)
    if not model:
        raise ValueError(f"{label}: empty override; use the shared radio model")
    for key, value in model.items():
        number(value, *RSU_RADIO_RANGES[key], f"{label}.{key}")


def validate_car_radio(model, label):
    only_keys(model, set(), CAR_RADIO_RANGES, label=label)
    if not model:
        raise ValueError(f"{label}: empty override; use the shared radio model")
    for key, value in model.items():
        number(value, *CAR_RADIO_RANGES[key], f"{label}.{key}")


def point(value, label, width=2000, height=None):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label}: expected [x_m,y_m]")
    return (number(value[0], 0, width, label + ".x"), number(value[1], 0, width if height is None else height, label + ".y"))


def node_id(value, label):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(f"{label}: invalid ID")
    return value


def technologies(value, label):
    if (not isinstance(value, list) or not value or
            any(not isinstance(v, str) for v in value) or
            len(value) != len(set(value)) or any(v not in TECHNOLOGIES for v in value)):
        raise ValueError(f"{label}: expected unique technologies from {sorted(TECHNOLOGIES)}")


def validate_map_objects(data):
    only_keys(data, {"schema_version", "roads", "cars", "rsus"}, {"sources", "manual_joins", "turn_restrictions"}, label="map_objects")
    if data["schema_version"] != 1:
        raise ValueError("map_objects schema_version must be 1")
    for kind in ("roads", "cars", "rsus"):
        rows = data[kind]
        if not isinstance(rows, list) or len(rows) > (100000 if kind == "roads" else 10000):
            raise ValueError(f"map_objects.{kind} exceeds its bounded capacity")
        ids = set()
        for row in rows:
            if kind == "roads":
                only_keys(row, {"id", "coordinates", "speed_limit_mps", "lanes_each_direction"}, {"oneway", "osm_way_id", "osm_from_node_id", "osm_to_node_id", "name", "road_class", "speed_forward_mps", "speed_reverse_mps", "lanes_forward", "lanes_reverse", "speed_forward_source", "speed_reverse_source", "lanes_forward_source", "lanes_reverse_source", "service", "bridge", "tunnel", "layer", "access_rules", "conditional_rules"}, label="global road")
                coords = row["coordinates"]
                if not isinstance(coords, list) or not 2 <= len(coords) <= 30:
                    raise ValueError("global road needs 2..30 WGS84 points")
                for pair in coords:
                    if not isinstance(pair, list) or len(pair) != 2:
                        raise ValueError("global road coordinate must be [longitude,latitude]")
                    number(pair[0], -180, 180, "global road longitude")
                    number(pair[1], -90, 90, "global road latitude")
                number(row["speed_limit_mps"], 1, 40, "global road speed")
                if type(row["lanes_each_direction"]) is not int or not 1 <= row["lanes_each_direction"] <= 3:
                    raise ValueError("global road lanes must be 1..3")
                if "oneway" in row and type(row["oneway"]) is not bool:
                    raise ValueError("global road oneway must be boolean")
                if "osm_way_id" in row and (type(row["osm_way_id"]) is not str or not row["osm_way_id"].isdigit()):
                    raise ValueError("global road osm_way_id must be decimal text")
                for endpoint in ("osm_from_node_id", "osm_to_node_id"):
                    if endpoint in row and (type(row[endpoint]) is not str or not row[endpoint].isdigit()):
                        raise ValueError(f"global road {endpoint} must be decimal text")
                if "name" in row and (type(row["name"]) is not str or len(row["name"]) > 120):
                    raise ValueError("global road name must be text up to 120 characters")
                if "road_class" in row and (type(row["road_class"]) is not str or len(row["road_class"]) > 40):
                    raise ValueError("global road class must be text up to 40 characters")
                for field in ("speed_forward_mps", "speed_reverse_mps"):
                    if field in row:
                        number(row[field], 1, 40, f"global road {field}")
                for field in ("lanes_forward", "lanes_reverse"):
                    if field in row and (type(row[field]) is not int or not 1 <= row[field] <= 6):
                        raise ValueError(f"global road {field} must be 1..6")
                for field in ("speed_forward_source", "speed_reverse_source", "lanes_forward_source", "lanes_reverse_source"):
                    if field in row and (type(row[field]) is not str or len(row[field]) > 40):
                        raise ValueError(f"global road {field} must be short text")
                if "service" in row and (type(row["service"]) is not str or len(row["service"]) > 40):
                    raise ValueError("global road service must be short text")
                if any(field in row and type(row[field]) is not bool for field in ("bridge", "tunnel")):
                    raise ValueError("global road bridge/tunnel must be boolean")
                if "layer" in row and (type(row["layer"]) is not int or not -99 <= row["layer"] <= 99):
                    raise ValueError("global road layer must be an integer")
                for field in ("access_rules", "conditional_rules"):
                    if field in row and (not isinstance(row[field], dict) or
                            any(type(k) is not str or len(k) > 60 or type(v) is not str or len(v) > 120
                                for k, v in row[field].items())):
                        raise ValueError(f"global road {field} must be bounded text")
            elif kind == "cars":
                only_keys(row, {"id", "longitude_deg", "latitude_deg", "road_id", "depart_s", "depart_speed_mps", "direction", "technologies", "ground_mode", "source"}, {"route", "arrival_pos_m", "max_speed_mps", "depart_speed_mode", "vehicle_model", "radio_model"}, label="global car")
                node_id(row["road_id"], "global car road_id")
                number(row["depart_s"], 0, 300, "global car depart_s")
                number(row["depart_speed_mps"], 0, 40, "global car speed")
                if "max_speed_mps" in row:
                    number(row["max_speed_mps"], .1, 40, "global car maximum speed")
                if "depart_speed_mode" in row and row["depart_speed_mode"] not in ("max", "fixed"):
                    raise ValueError("invalid global car departure speed mode")
                if "vehicle_model" in row:
                    validate_car_model(row["vehicle_model"], "global car vehicle_model")
                if "radio_model" in row:
                    validate_car_radio(row["radio_model"], "global car radio_model")
                if "arrival_pos_m" in row:
                    number(row["arrival_pos_m"], 0, 20000, "global car arrival_pos_m")
                technologies(row["technologies"], "global car technologies")
                if "satellite_terminal" in row["technologies"]:
                    raise ValueError("Vehicle satellite terminals are retired")
                if row["direction"] not in ("forward", "reverse") or row["ground_mode"] not in ("all", "cars", "off") or type(row["source"]) is not bool:
                    raise ValueError("invalid global car policy")
            else:
                only_keys(row, {"id", "longitude_deg", "latitude_deg", "technologies", "ground", "satellite_backhaul", "primary", "alert_target"}, {"radio_model"}, label="global RSU")
                if "radio_model" in row:
                    validate_rsu_radio(row["radio_model"], "global RSU radio_model")
                technologies(row["technologies"], "global RSU technologies")
                if any(type(row[key]) is not bool for key in ("ground", "satellite_backhaul", "primary", "alert_target")):
                    raise ValueError("invalid global RSU policy")
            rid = node_id(row["id"], f"global {kind} ID")
            if rid in ids:
                raise ValueError(f"duplicate global {kind} ID {rid}")
            ids.add(rid)
            if kind != "roads":
                number(row["longitude_deg"], -180, 180, f"global {kind} longitude")
                number(row["latitude_deg"], -90, 90, f"global {kind} latitude")
    road_ids = {road["id"] for road in data["roads"]}
    if any(car["road_id"] not in road_ids for car in data["cars"]):
        raise ValueError("global car references a missing global road")
    for car in data["cars"]:
        if "route" in car:
            route = car["route"]
            if not isinstance(route, list) or not 1 <= len(route) <= 200 or route[0] != {"segment": car["road_id"], "direction": car["direction"]}:
                raise ValueError("global car route is invalid")
            for hop in route:
                only_keys(hop, {"segment", "direction"}, label="global car route hop")
                if hop["segment"] not in road_ids or hop["direction"] not in ("forward", "reverse"):
                    raise ValueError("global car route references an invalid road")
    if "sources" in data:
        if not isinstance(data["sources"], list) or len(data["sources"]) > 100:
            raise ValueError("map_objects.sources must contain at most 100 entries")
        for source in data["sources"]:
            only_keys(source, {"bbox", "retrieved_at", "sha256", "provider", "tiles", "ways", "roads"},
                      {"dataset_sha256", "import_revision", "access_excluded_ways", "conditional_ways", "boundary_splits"}, label="road source")
            if (not isinstance(source["bbox"], list) or len(source["bbox"]) != 4 or
                    any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in source["bbox"]) or
                    source["provider"] not in ("openstreetmap-api-v0.6", "geofabrik-slovakia-pbf") or
                    not isinstance(source["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) or
                    not isinstance(source["retrieved_at"], str) or
                    ("dataset_sha256" in source and
                     (not isinstance(source["dataset_sha256"], str) or
                      not re.fullmatch(r"[0-9a-f]{64}", source["dataset_sha256"]))) or
                    any(type(source[key]) is not int or source[key] < 0 for key in ("tiles", "ways", "roads")) or
                    any(key in source and (type(source[key]) is not int or source[key] < 0)
                        for key in ("access_excluded_ways", "conditional_ways", "boundary_splits")) or
                    ("import_revision" in source and source["import_revision"] not in (3, 4, 5, 6, 7, 8, 9, 10))):
                raise ValueError("invalid road source provenance")
    if "turn_restrictions" in data:
        restrictions = data["turn_restrictions"]
        if not isinstance(restrictions, list) or len(restrictions) > 30000:
            raise ValueError("map_objects.turn_restrictions must be bounded")
        for row in restrictions:
            only_keys(row, {"id", "kind", "from_way_id", "to_way_id", "via_node_id", "via_way_id", "except"}, {"conditional"}, label="OSM restriction")
            if any(type(row[key]) is not str or len(row[key]) > 120 for key in row):
                raise ValueError("OSM restriction values must be short text")
    if "manual_joins" in data:
        joins = data["manual_joins"]
        if not isinstance(joins, list) or len(joins) > 1000:
            raise ValueError("map_objects.manual_joins must contain at most 1000 entries")
        for join in joins:
            only_keys(join, {"road_id", "end", "target_id", "longitude_deg", "latitude_deg", "distance_m"},
                      {"new_part_id"}, label="manual road join")
            node_id(join["road_id"], "manual join road")
            node_id(join["target_id"], "manual join target")
            if "new_part_id" in join:
                node_id(join["new_part_id"], "manual join new part")
            if join["end"] not in ("from", "to"):
                raise ValueError("manual join end must be from or to")
            number(join["longitude_deg"], -180, 180, "manual join longitude")
            number(join["latitude_deg"], -90, 90, "manual join latitude")
            number(join["distance_m"], 0, 50, "manual join distance")


def validate(data):
    only_keys(data, {"schema_version", "simulation", "georeference", "roads", "vehicles", "rsus", "flows", "network_execution"}, {"map_source", "map_objects", "extent_m", "width_m", "height_m", "osm_import_status"}, label="scenario")
    extent = data.get("extent_m", 2000)
    if type(extent) is not int or extent not in (2000, 4000):
        raise ValueError("extent_m must be 2000 or 4000 m")
    if ("width_m" in data) != ("height_m" in data):
        raise ValueError("width_m and height_m must be supplied together")
    width, height = data.get("width_m", extent), data.get("height_m", extent)
    if any(type(v) is not int or not 500 <= v <= 4000 for v in (width, height)):
        raise ValueError("working area width_m and height_m must be 500..4000 m")
    if type(data["schema_version"]) is not int or data["schema_version"] != 2:
        raise ValueError("schema_version must be 2")
    if data["network_execution"] != "schema_only":
        raise ValueError("network_execution must be schema_only: no ns-3 binding exists")
    if data.get("map_source", "manual") not in ("manual", "osm_live"):
        raise ValueError("map_source must be manual or osm_live")
    if "map_objects" in data:
        validate_map_objects(data["map_objects"])
    if "osm_import_status" in data:
        status = data["osm_import_status"]
        only_keys(status, {"applied_restrictions", "unresolved_restrictions"}, label="OSM import status")
        if any(type(value) is not int or value < 0 for value in status.values()):
            raise ValueError("OSM import status counts must be nonnegative integers")
    sim = data["simulation"]
    only_keys(sim, {"duration_s", "step_s", "seed", "utc_origin"}, {"vehicle_model"}, label="simulation")
    if "vehicle_model" in sim:
        vehicle_model = sim["vehicle_model"]
        only_keys(vehicle_model, {"accel_mps2", "decel_mps2", "sigma", "length_m", "width_m", "min_gap_m", "speed_factor", "manual_max_speed_mps"}, label="vehicle_model")
        for key, low, high in (("accel_mps2", .1, 10), ("decel_mps2", .1, 15),
                               ("sigma", 0, 1), ("length_m", 1, 20), ("width_m", .5, 3),
                               ("min_gap_m", 0, 10), ("speed_factor", .1, 2),
                               ("manual_max_speed_mps", .1, 60)):
            number(vehicle_model[key], low, high, "vehicle_model." + key)
    duration = number(sim["duration_s"], 1, 300, "duration_s")
    step = number(sim["step_s"], 0.1, 1, "step_s")
    if abs(duration / step - round(duration / step)) > 1e-8:
        raise ValueError("duration_s must be an integer multiple of step_s")
    if type(sim["seed"]) is not int or not 0 <= sim["seed"] <= 2**31 - 1:
        raise ValueError("seed must be a nonnegative 31-bit integer")
    from datetime import datetime
    if not isinstance(sim["utc_origin"], str):
        raise ValueError("utc_origin must be ISO 8601 UTC")
    try:
        utc = datetime.fromisoformat(sim["utc_origin"].replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("utc_origin must be ISO 8601 UTC") from exc
    if utc.tzinfo is None or utc.utcoffset().total_seconds() != 0:
        raise ValueError("utc_origin must carry UTC timezone")
    geo = data["georeference"]
    only_keys(geo, {"frame", "anchor_x_m", "anchor_y_m", "latitude_deg", "longitude_deg", "height_m"}, label="georeference")
    if geo["frame"] != "WGS84_ENU":
        raise ValueError("georeference.frame must be WGS84_ENU (+x east, +y north)")
    number(geo["anchor_x_m"], 0, width, "georeference.anchor_x_m")
    number(geo["anchor_y_m"], 0, height, "georeference.anchor_y_m")
    number(geo["latitude_deg"], -90, 90, "georeference.latitude_deg")
    number(geo["longitude_deg"], -180, 180, "georeference.longitude_deg")
    number(geo["height_m"], -500, 9000, "georeference.height_m")
    roads = data["roads"]
    only_keys(roads, {"nodes", "segments"}, {"turn_rules"}, label="roads")
    if not isinstance(roads["nodes"], list) or not 2 <= len(roads["nodes"]) <= 30000:
        raise ValueError("roads.nodes needs 2..30000 nodes")
    nodes = {}
    for entry in roads["nodes"]:
        only_keys(entry, {"id", "x_m", "y_m"}, label="road node")
        nid = node_id(entry["id"], "road node")
        if nid in nodes:
            raise ValueError(f"duplicate node {nid}")
        nodes[nid] = (number(entry["x_m"], 0, width, "x_m"), number(entry["y_m"], 0, height, "y_m"))
    if not isinstance(roads["segments"], list) or not 1 <= len(roads["segments"]) <= 30000:
        raise ValueError("roads.segments needs 1..30000 segments")
    segments = {}
    for entry in roads["segments"]:
        only_keys(entry, {"id", "from", "to", "shape", "speed_limit_mps", "lanes_each_direction"}, {"oneway", "osm_way_id", "osm_from_node_id", "osm_to_node_id", "name", "road_class", "speed_forward_mps", "speed_reverse_mps", "lanes_forward", "lanes_reverse", "speed_forward_source", "speed_reverse_source", "lanes_forward_source", "lanes_reverse_source", "service", "bridge", "tunnel", "layer", "access_rules", "conditional_rules"}, label="road segment")
        sid = node_id(entry["id"], "segment ID")
        start_id = node_id(entry["from"], f"segment {sid} from")
        end_id = node_id(entry["to"], f"segment {sid} to")
        if sid in segments or sid in nodes or start_id not in nodes or end_id not in nodes or start_id == end_id:
            raise ValueError(f"segment {sid}: duplicate or invalid endpoints")
        if type(entry["lanes_each_direction"]) is not int or not 1 <= entry["lanes_each_direction"] <= 3:
            raise ValueError(f"segment {sid}: lanes_each_direction must be 1..3")
        if "oneway" in entry and type(entry["oneway"]) is not bool:
            raise ValueError(f"segment {sid}: oneway must be boolean")
        if "osm_way_id" in entry and (type(entry["osm_way_id"]) is not str or not entry["osm_way_id"].isdigit()):
            raise ValueError(f"segment {sid}: invalid OSM way ID")
        if "name" in entry and (type(entry["name"]) is not str or len(entry["name"]) > 120):
            raise ValueError(f"segment {sid}: invalid road name")
        if "road_class" in entry and (type(entry["road_class"]) is not str or len(entry["road_class"]) > 40):
            raise ValueError(f"segment {sid}: invalid road class")
        for field in ("osm_from_node_id", "osm_to_node_id"):
            if field in entry and (type(entry[field]) is not str or not entry[field].isdigit()):
                raise ValueError(f"segment {sid}: invalid {field}")
        if "service" in entry and (type(entry["service"]) is not str or len(entry["service"]) > 40):
            raise ValueError(f"segment {sid}: invalid service type")
        if any(field in entry and type(entry[field]) is not bool for field in ("bridge", "tunnel")):
            raise ValueError(f"segment {sid}: bridge/tunnel must be boolean")
        if "layer" in entry and (type(entry["layer"]) is not int or not -99 <= entry["layer"] <= 99):
            raise ValueError(f"segment {sid}: invalid OSM layer")
        for field in ("access_rules", "conditional_rules"):
            if field in entry and (not isinstance(entry[field], dict) or
                    any(type(k) is not str or len(k) > 60 or type(v) is not str or len(v) > 120
                        for k, v in entry[field].items())):
                raise ValueError(f"segment {sid}: invalid {field}")
        number(entry["speed_limit_mps"], 1, 40, f"segment {sid} speed_limit_mps")
        for field in ("speed_forward_mps", "speed_reverse_mps"):
            if field in entry:
                number(entry[field], 1, 40, f"segment {sid} {field}")
        for field in ("lanes_forward", "lanes_reverse"):
            if field in entry and (type(entry[field]) is not int or not 1 <= entry[field] <= 6):
                raise ValueError(f"segment {sid}: {field} must be 1..6")
        for field in ("speed_forward_source", "speed_reverse_source", "lanes_forward_source", "lanes_reverse_source"):
            if field in entry and (type(entry[field]) is not str or len(entry[field]) > 40):
                raise ValueError(f"segment {sid}: {field} must be short text")
        shape = entry["shape"]
        if not isinstance(shape, list) or not 2 <= len(shape) <= 30:
            raise ValueError(f"segment {sid}: shape needs 2..30 points")
        coords = [point(p, f"segment {sid} shape", width, height) for p in shape]
        if math.dist(coords[0], nodes[entry["from"]]) > 0.01 or math.dist(coords[-1], nodes[entry["to"]]) > 0.01:
            raise ValueError(f"segment {sid}: shape endpoints must match graph nodes (0.01 m tolerance)")
        pieces = [math.dist(a, b) for a, b in zip(coords, coords[1:])]
        if min(pieces) < 0.5:
            raise ValueError(f"segment {sid}: consecutive points must be >=0.5 m")
        segments[sid] = entry
    turn_rules = roads.get("turn_rules", [])
    if not isinstance(turn_rules, list) or len(turn_rules) > 30000:
        raise ValueError("roads.turn_rules must be a bounded list")
    forbidden = set()
    for rule in turn_rules:
        only_keys(rule, {"from", "to"}, label="turn rule")
        for edge in ("from", "to"):
            if not isinstance(rule[edge], str) or not rule[edge].endswith(("_forward", "_reverse")):
                raise ValueError("turn rule needs directed edge IDs")
            road_id, direction = rule[edge].rsplit("_", 1)
            if road_id not in segments or direction == "reverse" and segments[road_id].get("oneway"):
                raise ValueError("turn rule references missing edge")
        forbidden.add((rule["from"], rule["to"]))
    vehicles = data["vehicles"]
    if not isinstance(vehicles, list) or not 1 <= len(vehicles):
        raise ValueError("vehicles requires at least one entry")
    vehicle_ids = set()
    for car in vehicles:
        only_keys(car, {"id", "depart_s", "depart_speed_mps", "route", "technologies"}, {"depart_pos_m", "arrival_pos_m", "max_speed_mps", "depart_speed_mode", "vehicle_model", "radio_model"}, "vehicle")
        cid = node_id(car["id"], "vehicle ID")
        if cid in vehicle_ids or cid in nodes or cid in segments:
            raise ValueError(f"duplicate vehicle ID {cid}")
        vehicle_ids.add(cid)
        number(car["depart_s"], 0, duration - step, f"{cid}.depart_s")
        number(car["depart_speed_mps"], 0, 40, f"{cid}.depart_speed_mps")
        if "max_speed_mps" in car:
            number(car["max_speed_mps"], .1, 40, f"{cid}.max_speed_mps")
        if "depart_speed_mode" in car and car["depart_speed_mode"] not in ("max", "fixed"):
            raise ValueError(f"{cid}: invalid departure speed mode")
        if "vehicle_model" in car:
            validate_car_model(car["vehicle_model"], f"{cid}.vehicle_model")
        if "radio_model" in car:
            validate_car_radio(car["radio_model"], f"{cid}.radio_model")
        maximum = car.get("max_speed_mps", car["depart_speed_mps"] if data.get("map_source") == "osm_live" else sim.get("vehicle_model", {}).get("manual_max_speed_mps", 40))
        mode = car.get("depart_speed_mode", "max" if data.get("map_source") == "osm_live" else "fixed")
        if mode == "fixed" and car["depart_speed_mps"] > maximum:
            raise ValueError(f"{cid}: departure speed exceeds maximum speed")
        technologies(car["technologies"], f"{cid}.technologies")
        if "satellite_terminal" in car["technologies"]:
            raise ValueError(f"{cid}: vehicle satellite terminals are retired")
        route = car["route"]
        if not isinstance(route, list) or not 1 <= len(route) <= 200:
            raise ValueError(f"{cid}: route needs 1..200 directed segments")
        previous_end = None
        previous_edge = None
        for hop in route:
            only_keys(hop, {"segment", "direction"}, label=f"{cid} route hop")
            hop_id = node_id(hop["segment"], f"{cid} route segment")
            if hop_id not in segments or hop["direction"] not in ("forward", "reverse"):
                raise ValueError(f"{cid}: invalid route hop")
            segment = segments[hop["segment"]]
            if segment.get("oneway", False) and hop["direction"] == "reverse":
                raise ValueError(f"{cid}: reverse travel on one-way segment {hop_id}")
            start, end = (segment["from"], segment["to"]) if hop["direction"] == "forward" else (segment["to"], segment["from"])
            if previous_end is not None and previous_end != start:
                raise ValueError(f"{cid}: disconnected route at {previous_end} -> {start}")
            this_edge = f"{hop_id}_{hop['direction']}"
            if previous_edge is not None and previous_edge.rsplit("_", 1)[0] == hop_id and previous_edge != this_edge:
                raise ValueError(f"{cid}: immediate U-turn on segment {hop_id}")
            if previous_edge is not None and (previous_edge, this_edge) in forbidden:
                raise ValueError(f"{cid}: prohibited OSM turn {previous_edge} -> {this_edge}")
            previous_edge = this_edge
            previous_end = end
        first = segments[route[0]["segment"]]
        length = sum(math.dist(point(a, "shape", width, height), point(b, "shape", width, height)) for a, b in zip(first["shape"], first["shape"][1:]))
        number(car.get("depart_pos_m", 0), 0, max(0, length - 20), f"{cid}.depart_pos_m")
        if "arrival_pos_m" in car:
            last = segments[route[-1]["segment"]]
            final_length = sum(math.dist(point(a, "shape", width, height), point(b, "shape", width, height)) for a, b in zip(last["shape"], last["shape"][1:]))
            arrival = number(car["arrival_pos_m"], 0, final_length, f"{cid}.arrival_pos_m")
            if len(route) == 1 and arrival <= car.get("depart_pos_m", 0) + 1:
                raise ValueError(f"{cid}: clicked destination must be ahead of departure")
    rsus = data["rsus"]
    if not isinstance(rsus, list):
        raise ValueError("rsus must be a list")
    all_ids = set(nodes) | vehicle_ids | set(segments)
    for rsu in rsus:
        only_keys(rsu, {"id", "x_m", "y_m", "technologies"}, {"radio_model"}, label="RSU")
        rid = node_id(rsu["id"], "RSU ID")
        if rid in all_ids:
            raise ValueError(f"duplicate RSU ID {rid}")
        all_ids.add(rid)
        number(rsu["x_m"], 0, width, f"{rid}.x_m")
        number(rsu["y_m"], 0, height, f"{rid}.y_m")
        technologies(rsu["technologies"], f"{rid}.technologies")
        if "radio_model" in rsu:
            validate_rsu_radio(rsu["radio_model"], f"{rid}.radio_model")
    capabilities = {n["id"]: set(n["technologies"]) for n in vehicles + rsus}
    flows = data["flows"]
    if not isinstance(flows, list) or not 1 <= len(flows) <= 100:
        raise ValueError("flows needs 1..100 entries")
    flow_ids = set()
    for flow in flows:
        only_keys(flow, {"id", "source", "target", "technology", "message_type", "execution"}, label="flow")
        fid = node_id(flow["id"], "flow ID")
        if fid in flow_ids or fid in all_ids:
            raise ValueError(f"duplicate flow ID {fid}")
        flow_ids.add(fid)
        source, target, tech = flow["source"], flow["target"], flow["technology"]
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError(f"flow {fid}: invalid source/target ID")
        if source not in capabilities or (target not in capabilities and target != "broadcast") or target == source:
            raise ValueError(f"flow {fid}: invalid source/target ID")
        if not isinstance(tech, str) or tech not in TECHNOLOGIES or tech not in capabilities[source]:
            raise ValueError(f"flow {fid}: source lacks declared technology {tech}")
        if target == "broadcast":
            if not any(tech in caps for nid, caps in capabilities.items() if nid != source):
                raise ValueError(f"flow {fid}: broadcast has no capable peer")
        elif tech not in capabilities[target]:
            raise ValueError(f"flow {fid}: target lacks declared technology {tech}")
        if not isinstance(flow["message_type"], str) or flow["message_type"] not in MESSAGE_TYPES:
            raise ValueError(f"flow {fid}: unsupported message_type")
        if flow["message_type"] in ("CAM", "DENM") and tech not in ("its_g5", "cellular_v2x"):
            raise ValueError(f"flow {fid}: CAM/DENM needs terrestrial V2X technology")
        if flow["execution"] != "not_implemented":
            raise ValueError(f"flow {fid}: execution must be not_implemented")
    return data


def write_xml(path, root):
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def make_inputs(data, directory):
    directory.mkdir(parents=True, exist_ok=True)
    nodes = ET.Element("nodes")
    for n in data["roads"]["nodes"]:
        ET.SubElement(nodes, "node", id=n["id"], x=str(n["x_m"]), y=str(n["y_m"]))
    write_xml(directory / "road.nod.xml", nodes)
    edges = ET.Element("edges")
    for segment in data["roads"]["segments"]:
        for direction, start, end, shape in (
            ("forward", segment["from"], segment["to"], segment["shape"]),
            ("reverse", segment["to"], segment["from"], segment["shape"][::-1]),
        ):
            if segment.get("oneway", False) and direction == "reverse":
                continue
            ET.SubElement(edges, "edge", id=f"{segment['id']}_{direction}",
                          **{"from": start}, to=end,
                          numLanes=str(segment.get(f"lanes_{direction}", segment["lanes_each_direction"])),
                          speed=str(segment.get(f"speed_{direction}_mps", segment["speed_limit_mps"])),
                          shape=" ".join(f"{p[0]},{p[1]}" for p in shape))
    write_xml(directory / "road.edg.xml", edges)
    # Export every graph transition. Otherwise netconvert may guess away a
    # legal sharp turn between distinct OSM ways at a shared junction node.
    outgoing = {}
    for edge in edges.findall("edge"):
        outgoing.setdefault(edge.get("from"), []).append(edge.get("id"))
    denied = {(rule["from"], rule["to"]) for rule in data["roads"].get("turn_rules", [])}
    connections = ET.Element("connections")
    for edge in edges.findall("edge"):
        source = edge.get("id")
        allowed = [target for target in outgoing.get(edge.get("to"), [])
                   if (source, target) not in denied and
                   not (source.rsplit("_", 1)[0] == target.rsplit("_", 1)[0] and source != target)]
        for target in allowed:
            ET.SubElement(connections, "connection", **{"from": source, "to": target})
        if not allowed:
            ET.SubElement(connections, "connection", **{"from": source})
    write_xml(directory / "road.con.xml", connections)
    routes = ET.Element("routes")
    real_map = data.get("map_source") == "osm_live"
    model = data["simulation"].get("vehicle_model", {
        "accel_mps2": 2, "decel_mps2": 4.5, "sigma": 0, "length_m": 5,
        "width_m": 1.8, "min_gap_m": 2.5, "speed_factor": 1,
        "manual_max_speed_mps": 40,
    })
    # SUMO requires departure-time order. On a shared lane, insert the front
    # vehicles first; otherwise a rear vehicle can delay a valid front spawn.
    for car in sorted(data["vehicles"],
                      key=lambda row: (row["depart_s"], -row.get("depart_pos_m", 0), row["id"])):
        # New scenarios expose both speeds. Legacy scenarios retain their old
        # map-specific interpretation until the user edits the car.
        maximum = car.get("max_speed_mps", car["depart_speed_mps"] if real_map else model["manual_max_speed_mps"])
        mode = car.get("depart_speed_mode", "max" if real_map else "fixed")
        car_model = {**model, **car.get("vehicle_model", {})}
        car_type = dict(accel=str(car_model["accel_mps2"]), decel=str(car_model["decel_mps2"]),
                        sigma=str(car_model["sigma"]), length=str(car_model["length_m"]),
                        width=str(car_model["width_m"]), minGap=str(car_model["min_gap_m"]),
                        speedFactor=str(car_model["speed_factor"]))
        vehicle_type = f"passenger_{car['id']}"
        ET.SubElement(routes, "vType", id=vehicle_type,
                      maxSpeed=str(maximum), **car_type)
        edge_ids = " ".join(f"{h['segment']}_{h['direction']}" for h in car["route"])
        ET.SubElement(routes, "route", id=f"route_{car['id']}", edges=edge_ids)
        vehicle_args={"id":car["id"],"type":vehicle_type,"route":f"route_{car['id']}",
                      "depart":str(car["depart_s"]),
                      "departSpeed":"max" if mode == "max" else str(car["depart_speed_mps"]),
                      "departPos":str(car.get("depart_pos_m", 0)),
                      "departLane":"best"}
        if "arrival_pos_m" in car:
            vehicle_args["arrivalPos"]=str(car["arrival_pos_m"])
        ET.SubElement(routes, "vehicle", **vehicle_args)
    write_xml(directory / "vehicles.rou.xml", routes)
    pois = ET.Element("additional")
    for rsu in data["rsus"]:
        ET.SubElement(pois, "poi", id=rsu["id"], x=str(rsu["x_m"]), y=str(rsu["y_m"]),
                      color="0,0,255", type="rsu_position_only")
    write_xml(directory / "rsus.add.xml", pois)


def verify_net_connections(directory):
    """Reject a netconvert network whose usable turns differ from our input graph."""
    declared = {(row.get("from"), row.get("to")) for row in
                ET.parse(directory / "road.con.xml").getroot() if row.get("to")}
    actual = {(row.get("from"), row.get("to")) for row in
              ET.parse(directory / "road.net.xml").getroot().iter("connection")
              if not row.get("from", "").startswith(":") and not row.get("to", "").startswith(":")}
    if declared != actual:
        missing = sorted(declared - actual)
        unexpected = sorted(actual - declared)
        raise RuntimeError(f"SUMO junction connections differ: missing={missing[:4]}, unexpected={unexpected[:4]}")


def hold_vehicles_for_radio_window(directory, until_s):
    """Keep cars that finish early physically stopped until the CAM window ends."""
    routes_path = directory / "vehicles.rou.xml"
    routes = ET.parse(routes_path)
    root = routes.getroot()
    edges = {item.get("id"): item.get("edges").split() for item in root.findall("route")}
    lengths = {lane.get("id"): float(lane.get("length"))
               for lane in ET.parse(directory / "road.net.xml").getroot().iter("lane")
               if lane.get("length") is not None}
    for vehicle in root.findall("vehicle"):
        lane = edges[vehicle.get("route")][-1] + "_0"
        length = lengths[lane]
        if length <= .02:
            raise ValueError(f"Final edge too short for radio-window hold: {vehicle.get('id')}")
        arrival = float(vehicle.get("arrivalPos", length))
        position = max(.01, min(length / 2 if length < 1 else length - .1, arrival - .1))
        ET.SubElement(vehicle, "stop", lane=lane, endPos=f"{position:.2f}", until=f"{until_s:.2f}")
    write_xml(routes_path, root)


def align_route_positions(data, directory):
    """Map editor distances onto SUMO's junction-trimmed lane geometry."""
    if data.get("map_source") != "osm_live":
        return
    roads = {row["id"]: row for row in data["roads"]["segments"]}
    net = ET.parse(directory / "road.net.xml").getroot()
    lanes = {edge.get("id"): edge.find("lane") for edge in net.findall("edge")
             if edge.get("id") and not edge.get("id").startswith(":")}
    routes_path = directory / "vehicles.rou.xml"
    routes = ET.parse(routes_path)
    vehicles = {row["id"]: row for row in data["vehicles"]}

    def point_on_shape(shape, distance):
        for a, b in zip(shape, shape[1:]):
            length = math.dist(a, b)
            if length and distance <= length:
                fraction = distance / length
                return (a[0] + (b[0] - a[0]) * fraction,
                        a[1] + (b[1] - a[1]) * fraction)
            distance -= length
        return tuple(shape[-1])

    def project(position, hop, label):
        road = roads[hop["segment"]]
        shape = road["shape"] if hop["direction"] == "forward" else road["shape"][::-1]
        target = point_on_shape(shape, position)
        lane = lanes.get(f"{hop['segment']}_{hop['direction']}")
        if lane is None:
            raise ValueError(f"{label}: SUMO edge is missing")
        lane_shape = [tuple(float(x) for x in pair.split(","))
                      for pair in lane.get("shape", "").split()]
        lane_length = float(lane.get("length"))
        if len(lane_shape) < 2 or lane_length <= .02:
            raise ValueError(f"{label}: SUMO lane is too short")
        best = (float("inf"), 0.0)
        walked = 0.0
        for a, b in zip(lane_shape, lane_shape[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if not length:
                continue
            fraction = max(0.0, min(1.0, ((target[0] - a[0]) * dx + (target[1] - a[1]) * dy) / length**2))
            closest = (a[0] + fraction * dx, a[1] + fraction * dy)
            candidate = (math.dist(target, closest), walked + fraction * length)
            if candidate[0] < best[0]:
                best = candidate
            walked += length
        if not walked:
            raise ValueError(f"{label}: SUMO lane has no geometry")
        margin = min(.1, lane_length / 4)
        return max(margin, min(lane_length - margin, best[1] * lane_length / walked))

    for vehicle in routes.getroot().findall("vehicle"):
        car = vehicles[vehicle.get("id")]
        vehicle.set("departPos", f"{project(car.get('depart_pos_m', 0), car['route'][0], car['id']):.2f}")
        if "arrival_pos_m" in car:
            vehicle.set("arrivalPos", f"{project(car['arrival_pos_m'], car['route'][-1], car['id']):.2f}")
    write_xml(routes_path, routes.getroot())


def run(data, source, directory, hold_until_s=None):
    validate(data)
    if hold_until_s is not None and (not isinstance(hold_until_s, (int, float)) or
                                     not 0 < hold_until_s < data["simulation"]["duration_s"]):
        raise ValueError("Radio-window hold must end inside the SUMO duration")
    make_inputs(data, directory)
    net_log = directory / "netconvert.log"
    sumo_log = directory / "sumo.log"
    commands = [
        ["netconvert", "--node-files", str(directory / "road.nod.xml"),
         "--edge-files", str(directory / "road.edg.xml"),
         "--connection-files", str(directory / "road.con.xml"),
         "--output-file", str(directory / "road.net.xml"),
         "--offset.disable-normalization", "true", "--no-warnings", "true"],
        ["sumo", "--net-file", str(directory / "road.net.xml"), "--route-files", str(directory / "vehicles.rou.xml"),
         "--additional-files", str(directory / "rsus.add.xml"), "--begin", "0", "--end", str(data["simulation"]["duration_s"]),
         "--step-length", str(data["simulation"]["step_s"]), "--seed", str(data["simulation"]["seed"]),
         "--fcd-output", str(directory / "fcd.xml"), "--fcd-output.acceleration", "true",
         "--fcd-output.signals", "true", "--summary-output", str(directory / "summary.xml"),
         "--no-step-log", "true", "--no-warnings", "true"],
    ]
    for index, (command, log) in enumerate(zip(commands, (net_log, sumo_log))):
        if index == 1:
            align_route_positions(data, directory)
        if index == 1 and hold_until_s is not None:
            hold_vehicles_for_radio_window(directory, hold_until_s)
        with log.open("w") as handle:
            subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=True)
        if index == 0:
            verify_net_connections(directory)
    summary = ET.parse(directory / "summary.xml").getroot()[-1].attrib
    fcd_ids = sorted({v.get("id") for v in ET.parse(directory / "fcd.xml").getroot().iter("vehicle")})
    if set(fcd_ids) != {car["id"] for car in data["vehicles"]}:
        raise RuntimeError("FCD does not contain every configured vehicle")
    if int(summary["inserted"]) != len(data["vehicles"]):
        raise RuntimeError("SUMO did not insert every configured vehicle")
    files = ["road.nod.xml", "road.edg.xml",
             "road.con.xml",
             "vehicles.rou.xml", "rsus.add.xml",
             "road.net.xml", "fcd.xml", "summary.xml", "netconvert.log", "sumo.log"]
    metadata = {
        "schema_version": 2,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "network_execution": "schema_only",
        "traffic_execution": "SUMO",
        **({"radio_window_hold_until_s": hold_until_s} if hold_until_s is not None else {}),
        "simulation": data["simulation"],
        "georeference": data["georeference"],
        "rsus": data["rsus"],
        "node_technologies_declarative_only": {n["id"]: n["technologies"] for n in data["vehicles"] + data["rsus"]},
        "flows_declarative_only": data["flows"],
        "commands": commands,
        "tool_versions": {name: subprocess.check_output([name, "--version"], text=True).splitlines()[0]
                          for name in ("netconvert", "sumo")},
        "traffic_summary_last_step": summary,
        "fcd_observed_vehicle_ids": fcd_ids,
        "output_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in files},
    }
    (directory / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--output", type=Path, help="Generate XML and run traffic; omit for validation only")
    args = parser.parse_args()
    scenario = args.scenario.resolve()
    data = validate(json.loads(scenario.read_text()))
    if args.output:
        run(data, scenario, args.output.resolve())
        print(f"PASS SUMO traffic: {args.output.resolve()}")
    else:
        print(f"PASS schema v2: {len(data['roads']['segments'])} road segments, "
              f"{len(data['vehicles'])} vehicles, {len(data['rsus'])} RSUs, "
              f"{len(data['flows'])} unimplemented flows; network schema only")
