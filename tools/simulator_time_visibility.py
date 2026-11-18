"""Independent time series of physically possible LEO user links for every node.

This is an orbital and published-terminal envelope. It does not infer active
operator beams, capacity, modem attachment or successful packet delivery.
"""
from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from simulator_platform import ROOT
from simulator_orbit_source import config_for
from simulator_physical_coverage import profile, site_ecef_km
from simulator_orbits import load_orbits, sample
from simulator_orbits import sat_ecef
from simulator_clock import EXPERIMENT_START_S as START_S


def _tracks(path: Path) -> dict[str, list[dict]]:
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    tracks: dict[str, list[dict]] = {}
    for row in rows:
        tracks.setdefault(row['node_id'], []).append(row)
    if not tracks or any(not all(int(a['time_us']) < int(b['time_us'])
                                 for a, b in zip(track, track[1:]))
                         for track in tracks.values()):
        raise ValueError('Neplatné časové polohy terminálov')
    return tracks


def _site(row: dict) -> tuple[float, float, float]:
    return (int(row['latitude_e7']) / 1e7,
            int(row['longitude_e7']) / 1e7,
            int(row['altitude_cm']) / 100)


def _elevation(xyz: np.ndarray, position: tuple[float, float, float]) -> np.ndarray:
    ground = site_ecef_km(position)
    lat, lon = np.radians(position[:2])
    up = np.array((np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)))
    los = xyz-ground
    return np.degrees(np.arcsin(np.clip((los @ up) / np.linalg.norm(los, axis=1), -1, 1)))


def calculate(scenario: dict, waypoints: Path, *, step_s: float = 0.5) -> dict:
    """Recompute all endpoints from raw SUMO WGS84 and the pinned OMM snapshot."""
    sat = scenario['satellite']
    group = sat['orbit_group']
    duration = int(scenario['sample_count']) / 10
    if not scenario.get('satellite_enabled') or not 2 <= duration <= 120 or step_s != .5:
        raise ValueError('Časová fyzikálna kontrola vyžaduje zjednotený satelitný beh')
    spec = profile(group)
    floor = max(float(sat['mask_deg']), spec['minimum_elevation_deg'],
                90.0 - spec['terminal_zenith_limit_deg'])
    config = config_for(group, sat, scenario['utc_origin'], START_S + duration)
    config.update(utc_origin=scenario['utc_origin'], duration_s=START_S + duration,
                  sample_s=step_s, mask_deg=sat['mask_deg'])
    objects, provenance = load_orbits(config)
    points, eop = sample(config, objects)
    catalogs = np.array([item[0] for item in objects], dtype=np.int64)
    tracks = _tracks(waypoints)
    samples = {node: [] for node in tracks}
    indices = {node: 0 for node in tracks}
    previous = {node: set() for node in tracks}
    initial_candidates = {}
    for point in points:
        elapsed = float(point['elapsed_s'])
        if elapsed < START_S - 1e-8:
            continue
        time_us = round((elapsed - START_S) * 1_000_000)
        xyz = np.asarray(point['xyz_km'], dtype=np.float64)
        if xyz.shape != (len(catalogs), 3) or not np.isfinite(xyz).all():
            raise ValueError('Neplatná časová poloha v orbitálnom archíve')
        for node, track in tracks.items():
            i = indices[node]
            while i + 1 < len(track) and int(track[i + 1]['time_us']) <= round(elapsed * 1_000_000):
                i += 1
            indices[node] = i
            position = _site(track[i])
            elevations = _elevation(xyz, position)
            eligible = np.flatnonzero(elevations >= floor)
            current = {int(catalogs[j]) for j in eligible}
            if not samples[node]:
                initial_candidates[node] = sorted(current)
            entered = sorted(current - previous[node]) if samples[node] else []
            left = sorted(previous[node] - current) if samples[node] else []
            previous[node] = current
            if eligible.size:
                # Highest elevation, then lowest public NORAD ID, is deterministic.
                best = min(eligible, key=lambda j: (-float(elevations[j]), int(catalogs[j])))
                chosen = int(catalogs[best])
                angle = round(float(elevations[best]), 4)
            else:
                chosen = None
                angle = None
            samples[node].append({'time_us': time_us,
                                  'candidate_count': int(eligible.size),
                                  'entered_catalog_ids': entered,
                                  'left_catalog_ids': left,
                                  'best_catalog_id': chosen,
                                  'best_elevation_deg': angle})
    expected = [round(i * step_s * 1_000_000) for i in range(round(duration / step_s) + 1)]
    if any([row['time_us'] for row in track] != expected for track in samples.values()):
        raise ValueError('Orbitálna časová os nepokrýva celú simuláciu')
    return {'schema_version': 1, 'group': group,
            'utc_origin': scenario['utc_origin'], 'duration_s': duration,
            'sample_step_s': step_s, 'minimum_elevation_deg': floor,
            'orbit_provenance': {**provenance, 'eop_sha256': eop},
            'initial_candidates': initial_candidates,
            'nodes': samples,
            'claim_boundary': 'geometric and published-terminal envelope only; active beam and packet delivery unverified'}


def audit_packet_geometry(scenario: dict, folder: Path) -> dict:
    """Check every offered native user packet against its actual serving orbit."""
    sat = scenario['satellite']
    group = sat['orbit_group']
    spec = profile(group)
    floor = max(float(sat['mask_deg']), spec['minimum_elevation_deg'],
                90.0 - spec['terminal_zenith_limit_deg'])
    config = config_for(group, sat, scenario['utc_origin'], START_S + scenario['sample_count']/10)
    config['utc_origin'] = scenario['utc_origin']
    objects, _ = load_orbits(config)
    by_id = {item[0]: item[3] for item in objects}
    catalogs = sat['catalog_ids']
    tracks = _tracks(folder/'waypoints.csv')
    log = (folder/'run.log').read_text()
    primary = scenario['rsu_id']
    moves = {node: [] for node in tracks}
    for time, index in re.findall(r'^HANDOVER_MOVE_US=(\d+) SAT=(\d+)\b', log, re.M):
        moves[primary].append((int(time), int(index)))
    for time, owner, _, index in re.findall(
            r'^SIM_TERMINAL_MOVE_US=(\d+) OWNER=(\S+) INDEX=(\d+) SAT=(\d+)$', log, re.M):
        if owner in moves:
            moves[owner].append((int(time), int(index)))
    origin = datetime.fromisoformat(scenario['utc_origin'].replace('Z', '+00:00'))
    check = []

    def at(node: str, time_us: int, index: int):
        if node not in tracks or not 0 <= index < len(catalogs):
            raise ValueError('Natívny paket má neplatný terminál alebo satelit')
        position = _site(max((row for row in tracks[node]
                              if int(row['time_us']) <= time_us),
                             key=lambda row: int(row['time_us']), default=tracks[node][0]))
        moment = origin + timedelta(microseconds=time_us)
        elevation = float(_elevation(np.asarray([sat_ecef(by_id[catalogs[index]], moment)]), position)[0])
        if elevation + 0.01 < floor:
            raise ValueError(f'Paket mimo fyzikálnej obálky: {node} sat={catalogs[index]} t={time_us} elev={elevation:.3f}°')
        check.append(elevation)

    with (folder/'trace.csv').open(newline='') as stream:
        reports = list(csv.DictReader(stream))
    source = {row['event_id']: row['node_id'] for row in reports if row['stage']=='RSU_REPORT_TX'}
    report_count = 0
    for row in reports:
        if row['stage'] != 'UT_SAT_REPORT_TX':
            continue
        node = source.get(row['event_id'])
        if node is None:
            raise ValueError('Satelitný paket nemá pôvodnú RSU')
        time_us = int(row['time_us'])
        index = sat['initial_serving_sat']
        for move_time, target in sorted(moves[node]):
            if move_time > time_us:
                break
            index = target
        at(node, time_us, index)
        report_count += 1
    direct_count = 0
    with (folder/'direct_link.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            if row['accepted'] == '1':
                at(row['car'], int(row['time_us']), int(row['sat_id']))
                direct_count += 1
    return {'status': 'PASS', 'rsu_packet_offers': report_count,
            'direct_packet_offers': direct_count,
            'minimum_packet_elevation_deg': round(min(check), 4) if check else None,
            'minimum_required_deg': floor,
            'claim_boundary': 'native packet sends checked against archived orbit and terminal envelope; operator beam unknown'}
