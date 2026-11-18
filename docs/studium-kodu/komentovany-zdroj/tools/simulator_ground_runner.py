#!/usr/bin/env python3
# Pozemný runner odovzdáva účinné CAM a anténne parametre natívnemu ns-3 programu a zaznamenáva
# zdroj ich validácie.
"""Prepare SUMO mobility and run ground VANET packets in ns-3."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

from simulator_sumo import run as run_sumo, validate as validate_world
from simulator_mobility_export import prepare
from simulator_platform import VANETZA, VANETZA_BUILD, OPENSSL, CHECKOUT, ROOT
from simulator_node_policy import environment as node_policy_environment
from simulator_rsu_radio import write as write_rsu_radio
from simulator_car_radio import write as write_car_radio
from simulator_engine_controls import effective as engine_controls

SOURCE = ROOT / "src/vanet-ground-network.cc"
CHECKER = ROOT / "tools/simulator_ground_verifier.py"
GENERATOR = ROOT / "tools/simulator_mobility_export.py"
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
DEPENDENCIES = ("tools/simulator_sumo.py", "tools/simulator_mobility_export.py",
                "tools/simulator_platform.py", "tools/simulator_coordinates.py",
                "tools/simulator_engine_controls.py", "tools/simulator_rsu_radio.py", "tools/simulator_car_radio.py",
                "src/rsu-radio-config.h")
NS3_LIBRARIES = ("buildings", "wave", "wifi", "mobility", "propagation", "network", "core")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_file(name: str) -> Path:
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"input is absent/outside project: {name}")
    return path


# Pozemný C++ model sa zostaví proti pripnutým knižniciam ns-3.38 a Vanetza. Cesta k binárke je vo
# výsledku konkrétneho behu, aby bolo možné spätne dokázať, ktorý spustiteľný súbor vytvoril
# stopy.
def compile_source(out: Path) -> Path:
    libs = sorted((VANETZA_BUILD / "lib/static").glob("*.a"))
    if not libs:
        raise RuntimeError("pinned Vanetza static libraries absent")
    includes = [CHECKOUT / "build/include", VANETZA, OPENSSL,
                OPENSSL / "x86_64-linux-gnu", VANETZA / "vanetza/asn1/support",
                VANETZA / "vanetza/asn1/its", VANETZA / "vanetza/asn1/its/r2"]
    binary = out / "ground-packet-engine"
    command = ["g++", "-std=c++17", "-O0", "-g0", *[f"-I{p}" for p in includes],
               str(SOURCE), "-Wl,--start-group", *map(str, libs), "-Wl,--end-group",
               f"-L{CHECKOUT / 'build/lib'}", f"-Wl,-rpath,{CHECKOUT / 'build/lib'}",
               "-lns3.38-buildings-debug", "-lns3.38-wave-debug", "-lns3.38-wifi-debug",
               "-lns3.38-mobility-debug", "-lns3.38-propagation-debug",
               "-lns3.38-network-debug", "-lns3.38-core-debug", "-lboost_date_time",
               "/lib/x86_64-linux-gnu/libcrypto.so.3", "-pthread", "-o", str(binary)]
    with (out / "build.log").open("w") as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    return binary


# Overí nízkoúrovňovú konfiguráciu, ktorá už vznikla z používateľského scenára. Prísne polia a
# intervaly bránia tomu, aby iný experimentálny runner podsúval skryté alebo neznáme nastavenia.
def validate_config(config: dict) -> None:
    required = {"schema_version", "base_world", "source_id", "rsu_id", "cam_sender_policy", "cam_receiver_policy", "sample_step_s",
                "sample_count", "seed", "run", "tx_power_dbm", "noise_figure_db", "phase_us", "cases"}
    required.add("dcc_policy")
    optional={"node_policy","denm_events","utc_origin","rate_mbps","channel_number","tx_gain_dbi","rx_gain_dbi","engine"}
    if not isinstance(config, dict) or not required<=set(config) or not set(config)<=required|optional or config["schema_version"] != 1:
        raise ValueError("invalid ground model configuration schema")
    if ('denm_events' in config) != ('utc_origin' in config):
        raise ValueError('DENM requires the scenario UTC origin')
    if "node_policy" in config and (type(config["node_policy"]) is not dict or
                                    set(config["node_policy"]) != {"cars", "rsus"}):
        raise ValueError("invalid per-node communication policy")
    if (config["cam_sender_policy"] != "all_its_g5_vehicles" or
            config["cam_receiver_policy"] != "all_other_radio_nodes"):
        raise ValueError("ground model supports all ITS-G5 vehicles sending CAM to all other radio nodes")
    # Priamy pozemný beh kontroluje aj voliteľný profil, aby sa nedal obísť preflight editora.
    if 'engine' in config:
        from simulator_engine_controls import effective as engine_controls
        engine_controls({'engine': config['engine']})
    if config["sample_step_s"] != 0.1 or not 20 <= config["sample_count"] <= 1200:
        raise ValueError("ground model requires 20..1200 samples at exact 100 ms")
    if not 0 <= config["seed"] < 2**31 or not 1 <= config["run"] < 2**31:
        raise ValueError("invalid ns-3 seed/run")
    if not 0 <= config["tx_power_dbm"] <= 33 or not 0 <= config["noise_figure_db"] <= 20:
        raise ValueError("radio parameters outside supported range")
    if type(config.get('rate_mbps',6)) is not int or config.get('rate_mbps',6) not in (3,6,12,24):
        raise ValueError('unsupported 10 MHz OCB data rate')
    # Pozemný runner kontroluje prípustné 10 MHz kanály a odovzdáva do ns-3 rovnaký kanál, PHY
    # rýchlosť, anténne zisky a zapnutie tieňovania ako spoločný runner.
    if type(config.get('channel_number',180)) is not int or config.get('channel_number',180) not in (172,174,176,178,180,182,184):
        raise ValueError('unsupported 10 MHz OCB channel')
    for gain in ('tx_gain_dbi','rx_gain_dbi'):
        value=config.get(gain,0)
        if type(value) not in (int,float) or not math.isfinite(value) or not -20<=value<=20:
            raise ValueError(f'invalid {gain}')
    if type(config["phase_us"]) is not int or not 0 <= config["phase_us"] <= 1000:
        raise ValueError("phase_us outside 0..1000")
    policy = config["dcc_policy"]
    if (not isinstance(policy, dict) or set(policy) != {"low_cbr", "high_cbr", "mid_interval_ms", "high_interval_ms"} or
            not all(type(policy[k]) in (int,float) for k in ("low_cbr","high_cbr")) or
            not 0 <= policy["low_cbr"] < policy["high_cbr"] <= 1 or
            any(type(policy[k]) is not int for k in ("mid_interval_ms","high_interval_ms")) or
            not 100 <= policy["mid_interval_ms"] <= policy["high_interval_ms"] <= 1000):
        raise ValueError("invalid configurable ground model DCC research policy")
    if not isinstance(config["cases"], list) or not 1 <= len(config["cases"]) <= 20:
        raise ValueError("ground model needs 1..20 cases")
    ids = []
    for case in config["cases"]:
        if (set(case) - {"id", "demand", "first_sample_s", "radio_mode", "dcc", "phase_us", "buildings", "obstructions", "shadowing"} or
                not {"id", "demand", "first_sample_s", "radio_mode", "dcc"} <= set(case) or
                not ID.fullmatch(case["id"])):
            raise ValueError("invalid ground model case")
        if "phase_us" in case and (type(case["phase_us"]) is not int or not 0 <= case["phase_us"] <= 1000):
            raise ValueError("case phase_us outside 0..1000")
        if case["radio_mode"] not in {"friis", "urban_los", "urban_nlos", "urban_building", "urban_osm_building"} or type(case["dcc"]) is not bool:
            raise ValueError("invalid ground model radio/DCC case")
        if ("shadowing" in case and type(case["shadowing"]) is not bool) or (
                case["radio_mode"] == "friis" and case.get("shadowing", False)):
            raise ValueError("invalid ground model shadowing selection")
        if (case["radio_mode"] == "urban_building") != ("buildings" in case):
            raise ValueError("building model needs an explicit box source")
        if (case["radio_mode"] == "urban_osm_building") != ("obstructions" in case):
            raise ValueError("OSM ground building mode needs pinned polygon input")
        if "obstructions" in case and "buildings" in case:
            raise ValueError("ground obstruction input types cannot be mixed")
        # Pozemný runner teraz prijíma prvú vzorku už v nule. Kontrola úplnosti FCD ďalej vyžaduje
        # každé auto v každom časovom kroku.
        if not 0 <= case["first_sample_s"] <= 250:
            raise ValueError("invalid ground model first sample")
        ids.append(case["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ground model case id")


# Z FCD vypočíta skutočnú dopravnú situáciu počas komunikačného okna. Počet áut a časové vzorky sa
# nesmú stratiť; inak by sme porovnávali rádio s inou dopravou, než sme zadali.
def traffic_metrics(world: dict, sumo_dir: Path, first: float, count: int) -> dict:
    steps = ET.parse(sumo_dir / "fcd.xml").getroot().findall("timestep")
    observed = [s for s in steps if first <= float(s.get("time")) < first + count * 0.1 - 1e-7]
    if len(observed) != count:
        raise ValueError("FCD sample window incomplete")
    vehicles = {v["id"] for v in world["vehicles"]}
    speeds = []
    for step in observed:
        rows = step.findall("vehicle")
        observed_ids = {v.get("id") for v in rows}
        if observed_ids != vehicles:
            missing = sorted(vehicles - observed_ids)
            extra = sorted(observed_ids - vehicles)
            raise ValueError(f"FCD at {step.get('time')} s differs from the scenario: "
                             f"{len(missing)} missing cars {missing[:8]}, {len(extra)} unexpected {extra[:8]}. "
                             "Check departures and routes ending before the communication window.")
        speeds += [float(v.get("speed")) for v in rows]
    summaries = ET.parse(sumo_dir / "summary.xml").getroot().findall("step")
    teleports = max(int(s.get("teleports", "0")) for s in summaries)
    collisions = max(int(s.get("collisions", "0")) for s in summaries)
    return {"configured_vehicles": len(vehicles), "realized_vehicles_per_sample": len(vehicles),
            "fcd_samples": len(observed), "mean_speed_mps": sum(speeds)/len(speeds),
            "min_speed_mps": min(speeds), "max_speed_mps": max(speeds),
            "sumo_teleports_total": teleports, "sumo_collisions_total": collisions,
            "rsu_positions": {x["id"]: [x["x_m"], x["y_m"]] for x in world["rsus"]}}


# Po príprave SUMO a waypointov sa zostaví a spustí pozemný C++ program. Smeruje doň rádio, DCC,
# DENM a politiku každého uzla. Nakoniec uloží surové PCAP a CSV stopy spolu s manifestom.
def run(config_path: Path, out: Path) -> dict:
    config_path, out = config_path.resolve(), out.resolve()
    if out.exists():
        raise ValueError(f"refusing to overwrite ground model results: {out}")
    if not out.is_relative_to(ROOT / "results"):
        raise ValueError("ground model results must be inside project results/")
    config = json.loads(config_path.read_text())
    validate_config(config)
    base_path = root_file(config["base_world"])
    base = json.loads(base_path.read_text())
    validate_world(base)
    out.mkdir(parents=True)
    binary = None
    cases = {}
    for case in config["cases"]:
        name = case["id"]
        folder = out / name
        folder.mkdir()
        demand_path = root_file(case["demand"])
        demand = json.loads(demand_path.read_text())
        if (set(demand) != {"schema_version", "kind", "provenance", "vehicles"} or
                demand["schema_version"] != 1 or demand["kind"] not in {"synthetic_trips", "measured_trips"} or
                not isinstance(demand["provenance"], str) or not demand["provenance"].strip()):
            raise ValueError(f"invalid demand provenance: {name}")
        if demand["kind"] == "measured_trips" and not demand["provenance"].startswith("https://"):
            raise ValueError("measured trips require a traceable source URL")
        world = copy.deepcopy(base)
        world["vehicles"] = demand["vehicles"]
        world["simulation"]["step_s"] = 0.1
        validate_world(world)
        if (not 2 <= len(world["vehicles"]) or not all("its_g5" in v["technologies"] for v in world["vehicles"]) or
                not all("its_g5" in r["technologies"] for r in world["rsus"])):
            raise ValueError("simulator requires at least two ITS-G5 cars and ITS-G5 RSUs")
        v2v_only = config["rsu_id"] == "" and not world["rsus"]
        if config["source_id"] not in {v["id"] for v in world["vehicles"]} or (not v2v_only and config["rsu_id"] not in {r["id"] for r in world["rsus"]}):
            raise ValueError("CAM source/RSU absent from selected demand/world")
        world_path = folder / "world.json"
        world_path.write_text(json.dumps(world, sort_keys=True, indent=2) + "\n")
        # Pred ns-3 behom sa uloží úplný profil RSU z efektívnych vstupov. Súbor je v raw
        # manifeste a jeho obsah checker nezávisle znovu zostaví.
        write_rsu_radio(world, config, folder / "rsu-radio.csv")
        # Runner ukladá účinný profil áut pri surových vstupoch a odovzdá jeho cestu natívnemu
        # procesu. Výška bez prepísania pochádza zo spoločného profilu enginu.
        write_car_radio(world, config,
                        engine_controls({'engine': config.get('engine', {})})['car_antenna_height_m'],
                        folder / "car-radio.csv")
        # Short roads may end before the fixed packet window. A real SUMO stop
        # keeps the car in FCD as a stationary radio participant until it ends.
        hold_until = min(world["simulation"]["duration_s"] - .01,
                         case["first_sample_s"] + config["sample_count"] * .1 + .2)
        run_sumo(world, world_path, folder / "sumo", hold_until_s=hold_until)
        metric = traffic_metrics(world, folder / "sumo", case["first_sample_s"], config["sample_count"])
        if binary is None:
            binary = compile_source(out)
        normalized = {"agents": {"cam_source_id": config["source_id"], "rsu_id": config["rsu_id"]},
                      "applications": {"cam": {"count": config["sample_count"],
                                               "first_tx_s": case["first_sample_s"], "interval_s": 0.1}}}
        waypoint = folder / "waypoints.csv"
        meta = prepare(world_path, folder / "sumo/fcd.xml", normalized, waypoint)
        if config.get('denm_events'):
            with (folder / 'denm-events.csv').open('w', newline='') as stream:
                writer=csv.writer(stream,lineterminator='\n')
                writer.writerow(('time_us','source_id','sequence','operation','validity_s','radius_m','repetition_ms'))
                # Pozemný proces dostáva časovo zoradený plán DENM. Každý riadok nesie konkrétne
                # auto a čas v mikrosekundách pre ns-3 plánovač.
                for event in sorted(config['denm_events'],key=lambda row:(row['at_s'],row.get('source_id',config['source_id']))):
                    writer.writerow((int(round((case['first_sample_s']+event['at_s'])*1_000_000)),
                        event.get('source_id',config['source_id']),event['sequence'],event['operation'],event['validity_s'],
                        event['radius_m'],event['repetition_ms']))
        building_sha = None
        obstruction_sha = None
        if "buildings" in case:
            building_path = root_file(case["buildings"])
            building = json.loads(building_path.read_text())
            if (set(building) != {"schema_version", "kind", "provenance", "boxes"} or
                    building["schema_version"] != 1 or building["kind"] not in {"synthetic_boxes", "surveyed_boxes"} or
                    not building["provenance"] or not 1 <= len(building["boxes"]) <= 100):
                raise ValueError("invalid building-box source/provenance")
            if building["kind"] == "surveyed_boxes" and not building["provenance"].startswith("https://"):
                raise ValueError("surveyed building boxes require a traceable source URL")
            building_csv = folder / "buildings.csv"
            fields = ["id", "x_min", "x_max", "y_min", "y_max", "z_min", "z_max"]
            with building_csv.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                for box in building["boxes"]:
                    if (set(box) != set(fields) or not ID.fullmatch(box["id"]) or
                            not 0 <= box["x_min"] < box["x_max"] <= 2000 or
                            not 0 <= box["y_min"] < box["y_max"] <= 2000 or
                            not 0 <= box["z_min"] < box["z_max"] <= 100):
                        raise ValueError("building box outside validated local ENU frame")
                    writer.writerow(box)
            building_sha = digest(building_path)
        if "obstructions" in case:
            obstruction_path = root_file(case["obstructions"])
            # The parent simulator runner has already bound this CSV to the validated
            # scenario environment; keep the exact bytes in this native case.
            raw = obstruction_path.read_bytes()
            if not raw.startswith(b"id,height_m,polygon_xy_m\n") or len(raw.splitlines()) < 2:
                raise ValueError("invalid OSM ground building CSV")
            (folder / "osm-buildings.csv").write_bytes(raw)
            obstruction_sha = digest(obstruction_path)
        # ns-3 CommandLine splits values at spaces inside one argv item.
        with tempfile.TemporaryDirectory(prefix="bp-ground-run-") as temporary:
            alias = Path(temporary) / "out"
            alias.symlink_to(out, target_is_directory=True)
            short = alias / name
            command = [str(binary), f"--waypoints={short / 'waypoints.csv'}", f"--output={short}",
                       f"--rsu_radio_config={short / 'rsu-radio.csv'}",
                       f"--car_radio_config={short / 'car-radio.csv'}",
                       f"--radio_mode={case['radio_mode']}", f"--dcc={int(case['dcc'])}",
                       f"--seed={config['seed']}", f"--run={config['run']}",
                       f"--phase_us={case.get('phase_us', config['phase_us'])}", f"--tx_power_dbm={config['tx_power_dbm']}",
                       f"--noise_figure_db={config['noise_figure_db']}",
                       f"--rate_mbps={config.get('rate_mbps',6)}",
                       f"--channel_number={config.get('channel_number',180)}",
                       f"--tx_gain_dbi={config.get('tx_gain_dbi',0)}",
                       f"--rx_gain_dbi={config.get('rx_gain_dbi',0)}",
                       f"--dcc_low_cbr={config['dcc_policy']['low_cbr']}",
                       f"--dcc_high_cbr={config['dcc_policy']['high_cbr']}",
                       f"--dcc_mid_ms={config['dcc_policy']['mid_interval_ms']}",
                       f"--dcc_high_ms={config['dcc_policy']['high_interval_ms']}",
                       f"--shadowing={int(case.get('shadowing', False))}"]
            command += [f'--{key}={value}' for key, value in config.get('engine', {}).items()]
            if config.get('denm_events'):
                command += [f"--denm_events={short / 'denm-events.csv'}",
                            f"--utcOrigin={config['utc_origin'][:19]}"]
            if "buildings" in case:
                command.append(f"--buildings={short / 'buildings.csv'}")
            if "obstructions" in case:
                command.append(f"--osm_buildings={short / 'osm-buildings.csv'}")
            with (folder / "run.log").open("w") as log:
                child_env=os.environ.copy()
                child_env.update(node_policy_environment(config.get('node_policy')))
                subprocess.run(command, cwd=ROOT, env=child_env, stdout=log, stderr=subprocess.STDOUT, check=True)
        cases[name] = {"config": case, "demand_kind": demand["kind"],
                       "demand_sha256": digest(demand_path), "demand_provenance": demand["provenance"],
                       "traffic": metric, "participants": meta["participants"],
                       "station_ids": meta["station_ids"], "building_sha256": building_sha,
                       "obstruction_sha256": obstruction_sha,
                       "sample_times_s": meta["sample_times_s"]}
    raw = {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name != "run-manifest.json"}
    git_rev = lambda directory: subprocess.check_output(
        ["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
    manifest = {"schema_version": 1, "execution_state": "native_ground_packets",
                "config_path": str(config_path.relative_to(ROOT)), "config_sha256": digest(config_path),
                "base_world_sha256": digest(base_path), "source_sha256": digest(SOURCE),
                "runner_sha256": digest(Path(__file__)), "generator_sha256": digest(GENERATOR),
                "checker_sha256": digest(CHECKER), "binary_sha256": digest(binary),
                "dependency_sha256": {name: digest(ROOT / name) for name in DEPENDENCIES + (("tools/simulator_node_policy.py",) if "node_policy" in config else ()) +
                                      (("src/ground-building-condition.h", "tools/simulator_ground_obstructions.py") if
                                       any("obstructions" in case for case in config["cases"]) else ())},
                "ns3_checkout": str(CHECKOUT),
                "ns3_commits": {".": git_rev(CHECKOUT), "contrib/satellite": git_rev(CHECKOUT / "contrib/satellite")},
                "vanetza_commit": git_rev(VANETZA),
                "ns3_library_sha256": {name: digest(CHECKOUT / f"build/lib/libns3.38-{name}-debug.so")
                                       for name in NS3_LIBRARIES},
                "tool_versions": {name: subprocess.check_output([name, "--version"], text=True).splitlines()[0]
                                  for name in ("sumo", "netconvert", "g++")},
                "cases": cases, "raw_sha256": raw}
    (out / "run-manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=ROOT / "config/ground-experiment.json")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = run(args.config, args.output)
        print(f"PASS ground model native ground run: {args.output.resolve()} ({len(result['cases'])} cases)")
    except Exception as exc:
        print(f"ground model run failed: {exc}", file=sys.stderr)
        raise
