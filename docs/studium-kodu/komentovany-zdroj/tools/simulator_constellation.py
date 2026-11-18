# Počíta náhľad konštelácie a polohy pre glóbus. Prehľad môže zobraziť viac kandidátov než
# skutočný paketový beh; rozhodujúci výber pri behu robí simulator_satellite_runner.py.
"""Select an active generic-DVB satellite tree from a complete archived OMM group.

The whole age-qualified catalogue is propagated for the requested UTC window.
Only satellites that can serve the experiment site and a proxy gateway are
instantiated in SNS-3. This is geometry and generic DVB, not an operator model.
"""
from __future__ import annotations
import json
import math
from datetime import timedelta
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import CartesianRepresentation, ITRS, TEME
from astropy.time import Time
from sgp4.api import SatrecArray

from simulator_platform import ROOT
from simulator_orbits import load_orbits, sample, clearance, utc, stamp, digest, pinned_eop
from simulator_coordinates import enu_to_wgs84
from simulator_cli import GROUP_REFERENCE, full_duration
from simulator_clock import EXPERIMENT_START_S as START_S
from simulator_physical_coverage import assess, profile
from simulator_orbit_source import config_for


# Náhľad je pre glóbus a predbežnú geometriu. Zobrazuje celý archív a vhodných kandidátov, no
# aktuálny editor pri spustení znovu vyberá paketovú topológiu v simulator_satellite_runner.py.
# Preto viac bodov nad miestom ešte neznamená viac aktívnych paketových satelitov.
def preview(group: str, world: dict, scenario: dict) -> dict:
    if group not in GROUP_REFERENCE:
        raise ValueError('Neznáma konštelácia')
    if not isinstance(world, dict) or not isinstance(world.get('rsus'), list):
        raise ValueError('Konštelácia potrebuje platnú mapu')
    if not isinstance(scenario, dict) or not isinstance(scenario.get('satellite'), dict):
        raise ValueError('Satelitný náhľad potrebuje nastavenia konštelácie')
    geo = world['georeference']
    rsu = next((r for r in world['rsus'] if r['id'] == scenario.get('rsu_id')), None)
    if rsu is None and world['rsus']:
        rsu = world['rsus'][0]
    if rsu is None:
        # The local experiment covers 2 × 2 km; use its WGS84 anchor when the
        # user has only direct vehicle terminals and no RSU.
        rsu = {'x_m': geo['anchor_x_m'], 'y_m': geo['anchor_y_m']}
    site = enu_to_wgs84(rsu['x_m'], rsu['y_m'], geo['anchor_x_m'], geo['anchor_y_m'],
                        geo['latitude_deg'], geo['longitude_deg'], geo['height_m'])
    gateway = scenario['satellite']['gateway']
    if not isinstance(gateway, list) or len(gateway) != 3:
        raise ValueError('Neplatná proxy poloha brány')
    # Náhľad pre novú schému skúma zvolený interval od t = 0. Neexistuje osobitný skrytý úsek,
    # ktorý by menil fyzickú polohu satelitu na začiatku pokusu.
    end = START_S + world['simulation']['duration_s'] if full_duration(scenario) else 13
    config = config_for(group, scenario['satellite'], scenario['utc_origin'], end)
    config.update(utc_origin=scenario['utc_origin'], duration_s=end, sample_s=.5,
                  mask_deg=scenario['satellite']['mask_deg'],
                  ut=dict(zip(('lat_deg','lon_deg','height_m','status'), (*site,'proxy'))),
                  gateway=dict(zip(('lat_deg','lon_deg','height_m','status'), (*gateway,'proxy'))))
    objects, provenance = load_orbits(config)
    samples, eop_hash = sample(config, objects)
    physical = profile(group)
    window = [p for p in samples if START_S <= p['elapsed_s'] <= end]
    catalog_ids = [item[0] for item in objects]
    index = {cat: i for i, cat in enumerate(catalog_ids)}
    stable_ut = set.intersection(*(set(p['ut_visible_ids']) for p in window))
    stable_gw = set.intersection(*(set(p['gw_visible_ids']) for p in window))
    dynamic = scenario['satellite'].get('dynamic_physical') is True
    initial_window = [p for p in window if p['elapsed_s'] <= START_S+4] if dynamic else window
    target_window = [p for p in window if p['elapsed_s'] >= START_S+1] if dynamic else window
    def minimum(catalog, endpoint, points=window):
        return min(p['elevation_deg'][str(catalog)][endpoint] for p in points)
    # SNS-3 accepts five-digit native TLE IDs. The packet adapter maps larger
    # public NORAD IDs to distinct local IDs without changing the public ID.
    # The packet selector must at least respect published user-link geometry.
    # This is still no claim that the operator has illuminated the beam.
    physical_floor = max(float(config['mask_deg']), physical['minimum_elevation_deg'],
                         90.0-physical['terminal_zenith_limit_deg'])
    early = set.intersection(*(set(p['ut_visible_ids']) for p in initial_window))
    late = set.intersection(*(set(p['ut_visible_ids']) for p in target_window))
    ranked_ut = sorted((cat for cat in early if cat <= 999999 and minimum(cat, 0, initial_window) >= physical_floor),
                       key=lambda cat: (-minimum(cat, 0, initial_window), cat))
    ranked_target = sorted((cat for cat in late if cat <= 999999 and minimum(cat, 0, target_window) >= physical_floor),
                           key=lambda cat: (-minimum(cat, 0, target_window), cat))
    ranked_gw = sorted((cat for cat in stable_gw if cat <= 999999 and minimum(cat, 1) >= physical_floor),
                       key=lambda cat: (-minimum(cat, 1), cat))
    selected = None
    feeder = initial = target = None
    parents = {}
    connected_site_count = 0
    best_connected = -1
    # The native path needs a feeder-rooted ISL tree. Search every stable,
    # native-compatible gateway and site candidate, including relay nodes.
    candidates = sorted(set(ranked_ut) | set(ranked_target) | set(ranked_gw))
    visible_native = set(ranked_ut) | set(ranked_target)
    def linked(a, b):
        return all(clearance(p['xyz_km'][index[a]], p['xyz_km'][index[b]]) > 0 for p in window)
    for root in ranked_gw:
        tree = {root: None}
        queue = [root]
        for parent in queue:
            for cat in candidates:
                if cat not in tree and linked(parent, cat):
                    tree[cat] = parent
                    queue.append(cat)
            if visible_native <= tree.keys():
                break
        direct = [cat for cat in ranked_ut if cat in tree]
        future = [cat for cat in ranked_target if cat in tree]
        initial_choice = next((cat for cat in direct if cat != root), None)
        target_choice = next((cat for cat in future if cat not in (initial_choice,root)),
                             root if root in future else None)
        if initial_choice is None or target_choice is None:
            continue
        reachable = len(set(direct) | set(future))
        if selected is None or reachable > best_connected:
            feeder, parents = root, tree
            connected_site_count = best_connected = reachable
            initial = initial_choice
            target = target_choice
            selected = [initial, root] + ([target] if target != root else []) + [cat for cat in direct if cat not in (initial, root, target)]
            # Add relay ancestors needed to reach every selected site satellite.
            for cat in tuple(selected):
                ancestor = parents[cat]
                while ancestor is not None:
                    if ancestor not in selected:
                        selected.append(ancestor)
                    ancestor = parents[ancestor]
        if reachable == len(visible_native):
            break
    if selected is None:
        raise ValueError('Pre túto epochu a proxy bránu neexistuje súčasne viditeľná trasa s handoverom')
    # Only satellites on the selected gateway path need packet nodes.
    selected = [initial, feeder] + ([target] if target not in (initial, feeder) else [])
    for cat in tuple(selected):
        ancestor = parents[cat]
        while ancestor is not None:
            if ancestor not in selected:
                selected.append(ancestor)
            ancestor = parents[ancestor]
    if len(selected) > 40000:
        raise ValueError('Natívny model podporuje najviac 40 000 orbitálnych uzlov')
    # All selected satellites have a gateway path; no count is chosen by hand.
    feeder_index = selected.index(feeder)
    topology = {'catalog_ids': selected,
                'isls': [[selected.index(parents[cat]), i] for i, cat in enumerate(selected) if cat != feeder],
                'initial_serving_sat': selected.index(initial),
                'handover_target_sat': selected.index(target),
                'feeder_sat': feeder_index,
                'orbit_group': group}
    anchor = next(p for p in samples if p['elapsed_s'] == START_S)
    xyz = anchor['xyz_km']
    norm = np.linalg.norm(xyz, axis=1)
    positions = []
    physical_count = 0
    for i, cat in enumerate(catalog_ids):
        visible = cat in anchor['ut_visible_ids']
        possible = visible and assess(group, site, xyz[i])['public_envelope']
        physical_count += int(possible)
        positions.append({'id': cat, 'lat': round(math.degrees(math.asin(float(xyz[i, 2]/norm[i]))), 3),
                          'lon': round(math.degrees(math.atan2(float(xyz[i, 1]), float(xyz[i, 0]))), 3),
                          'visible_site': visible, 'physical_site': possible,
                          **({'xyz_km': np.round(xyz[i], 2).tolist()}
                             if visible or cat in selected else {})})
    snapshot = ROOT / config['snapshot']['path'] / 'manifest.json'
    archived = json.loads(snapshot.read_text())['groups'][group]['objects']
    initially_physical = {cat for cat in catalog_ids if cat in window[0]['ut_visible_ids'] and
                          window[0]['elevation_deg'][str(cat)][0] >= physical_floor}
    return {'group': group, 'utc': anchor['utc'], 'site': {'lat': site[0], 'lon': site[1], 'height_m': site[2]},
            'mask_deg': config['mask_deg'], 'archived_count': archived,
            'eligible_count': len(catalog_ids), 'native_eligible_count': sum(cat <= 999999 for cat in catalog_ids),
            'site_visible_count': len(stable_ut),
            'site_physical_count_at_start': physical_count,
            'physical_profile': physical,
            'gateway_visible_count': len(stable_gw), 'active_count': len(selected),
            'site_native_count': len(visible_native),
            'entered_during_packet_window_count': len(set(ranked_target)-initially_physical) if dynamic else 0,
            'site_connected_count': connected_site_count,
            'active_topology': topology, 'positions': positions,
            'provenance': {**provenance, 'eop_sha256': eop_hash},
            'claim_boundary': 'published physical envelope is a candidate gate only; selected active tree uses hypothetical generic DVB, not operator RF/MAC, active beams or routing'}


# Vracia časový rad polôh celej konštelácie pre plynulý náhľad z pripnutej EOP tabuľky. Táto
# funkcia nepreposiela žiadny paket a nemení výsledky ns-3.
def motion(group: str, scenario: dict, duration_s: int) -> dict:
    """Bounded globe preview from the same archived OMM and pinned EOP as selection."""
    if group not in GROUP_REFERENCE:
        raise ValueError('Neznáma konštelácia')
    if not isinstance(scenario, dict) or not isinstance(scenario.get('utc_origin'), str):
        raise ValueError('Orbitálny náhľad vyžaduje UTC začiatok scenára')
    logical = full_duration(scenario)
    if type(duration_s) is not int or not (2 <= duration_s <= 120 if logical else 12 <= duration_s <= 300):
        raise ValueError('Neplatné trvanie orbitálneho náhľadu')
    config = config_for(group, scenario.get('satellite'), scenario['utc_origin'],
                        max(13, START_S + duration_s) if logical else 13)
    # Match the active-tree selection's age-qualified catalogue exactly.
    config.update(utc_origin=scenario['utc_origin'],
                  duration_s=max(13, START_S + duration_s) if logical else 13)
    objects, provenance = load_orbits(config)
    satellites = SatrecArray([row[3] for row in objects])
    eop = pinned_eop()
    eop_hash = digest(Path(eop.meta['data_path']))
    step = max(1, math.ceil(duration_s / 12))
    seconds = sorted(set([0, duration_s] + ([] if logical else [10]) + list(range(0, duration_s + 1, step))))
    origin = utc(config['utc_origin'])
    frames = []
    for elapsed in seconds:
        instant = origin + timedelta(seconds=elapsed + (START_S if logical else 0))
        time = Time(instant, scale='utc')
        _, ut_status = eop.ut1_utc(time, return_status=True)
        _, _, pm_status = eop.pm_xy(time, return_status=True)
        if int(ut_status) not in (0, 1, 2) or int(pm_status) not in (0, 1, 2):
            raise ValueError(f'EOP unavailable at {stamp(instant)}')
        errors, positions, _ = satellites.sgp4(np.array([time.jd1]), np.array([time.jd2]))
        if np.any(errors):
            raise ValueError(f'SGP4 propagation failed at {stamp(instant)}')
        xyz = TEME(CartesianRepresentation(positions[:, 0, :].T * u.km), obstime=time).transform_to(ITRS(obstime=time)).cartesian.xyz.to_value(u.km).T
        frames.append({'time_s': elapsed, 'xyz_km': np.round(xyz, 2).tolist()})
    return {'group': group, 'utc_origin': config['utc_origin'], 'duration_s': duration_s,
            'snapshot_manifest_sha256': config['snapshot']['manifest_sha256'],
            'catalog_ids': [row[0] for row in objects], 'frames': frames,
            'physical_profile': profile(group),
            'provenance': {**provenance, 'eop_sha256': eop_hash},
            'claim_boundary': 'orbit geometry preview only; visibility does not guarantee radio attachment or packet delivery'}
