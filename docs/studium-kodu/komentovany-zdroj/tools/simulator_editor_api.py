# Nový návrh ukladá úplný profil enginu, aby boli aj pôvodne pevné vedecké predpoklady súčasťou
# reprodukovateľného scenára.
"""Validate editor inputs and expose only verified run traces to the UI."""
from __future__ import annotations
import copy
import base64
import csv
import hashlib
import json
import math
import re
import shutil
import tempfile
import threading
from functools import lru_cache
from datetime import datetime, timedelta
from pathlib import Path

from simulator_platform import ROOT
from simulator_cli import preflight, project_input, verify, full_duration
from simulator_clock import EXPERIMENT_START_S as START_S
from simulator_sumo import validate as validate_world
from simulator_cam_decode import enrich as enrich_cam
from simulator_denm_decode import decode_denm
from simulator_satellite_trace import load as load_satellite_trace

IDENT = re.compile(r'^[a-z][a-z0-9-]{2,47}$')
EVENT = re.compile(r'^[A-Za-z0-9_-]{1,80}$')
_verified = {}
_verify_lock = threading.Lock()


def _file_state(path):
    try:
        state = path.lstat()
        return state.st_mode, state.st_size, state.st_mtime_ns, state.st_ctime_ns
    except OSError:
        return None


# `_run_state()` riadi vykonanie jedného kroku alebo celého behu.
def _run_state(base):
    """Cheap invalidation key for checked outputs and their recorded sources."""
    manifest = base / 'run-manifest.json'
    raw = manifest.read_bytes() if manifest.is_file() else b''
    try:
        sources = json.loads(raw).get('sources', {})
    except (ValueError, TypeError):
        sources = {}
    source_paths = []
    for name in sources:
        relative = Path(name)
        if not relative.is_absolute() and '..' not in relative.parts:
            source_paths.append((name, _file_state(ROOT / relative)))
    # The manifest names every source needed by this run. Historical snapshots
    # are checked by the verifier when they are relevant to an older result.
    outputs = tuple((str(p.relative_to(base)), _file_state(p)) for p in sorted(base.rglob('*')))
    return hashlib.sha256(raw).hexdigest(), tuple(sorted(source_paths)), outputs


# Pred vydaním replay najprv opakuje `verify(base)`. Cache platí len kým sa nezmení manifest,
# zdrojový súbor ani niektorý výsledný súbor. Zamknutie bráni dvom HTTP vláknam overovať súčasne
# ten istý meniaci sa beh.
def verified_run(base):
    """Reuse a complete audit only while its files and source snapshots stay unchanged."""
    base = Path(base).resolve()
    with _verify_lock:
        before = _run_state(base)
        cached = _verified.get(base)
        if cached and cached[0] == before:
            return cached[1]
        result = verify(base)
        after = _run_state(base)
        if before != after:
            raise ValueError('Výsledky sa počas overovania zmenili; skús znova')
        if len(_verified) >= 8:
            _verified.pop(next(iter(_verified)))
        _verified[base] = (after, result)
        return result


def read(path):
    return json.loads(path.read_text())


# Vytvorí predvolený scenár, prázdny svet a dopyt vozidiel. Číselné hodnoty tu sú prednastavenia
# editora, nie namerané vlastnosti Starlinku či Iridia. Skutočný beh musí prejsť preflightom.
def new_draft():
    """Return an empty editor state, independent of demonstration scenarios."""
    from simulator_link_policy_defaults import LINK_POLICY
    from simulator_physical_coverage import direct_link_policy
    from simulator_orbit_source import newest_default
    # Predvolené hodnoty sa kopírujú do nového scenára; staršie uložené scenáre zostávajú
    # čitateľné vďaka dedeniu v engine_controls.
    from simulator_engine_controls import DEFAULTS as ENGINE_DEFAULTS
    pin, fetched = newest_default()
    origin = (datetime.fromisoformat(fetched.replace('Z', '+00:00')) - timedelta(seconds=START_S)).strftime('%Y-%m-%dT%H:%M:%SZ')
    scenario = {
        'schema_version': 7, 'time_policy': 'ready_at_t0_full_duration', 'scenario_id': 'novy-scenar',
        'world_template': '', 'demand': '', 'source_id': '', 'rsu_id': '',
        'alert_target_rsu': '', 'seed': 314161, 'ns3_run': 1,
        # Nový návrh nezačína vymyslenou výstrahou. Používateľ pridáva udalosti jednotlivo pri
        # autách v editore.
        'denm_events': [],
        'engine': dict(ENGINE_DEFAULTS),
        'utc_origin': origin, 'sample_count': 20,
        'radio': {'mode': 'urban_los', 'tx_power_dbm': 20, 'noise_figure_db': 7,
                  'rate_mbps': 6, 'channel_number': 180, 'tx_gain_dbi': 0,
                  'rx_gain_dbi': 0, 'shadowing': False},
        'mode': 'unified', 'satellite_enabled': False,
        'node_policy': {'cars': {}, 'rsus': {}},
        'link_policy_override': False,
        'link_policy': direct_link_policy('iridium-NEXT', LINK_POLICY),
        'satellite': {
            'catalog_ids': [], 'isls': [], 'initial_serving_sat': 0,
            'handover_target_sat': 0, 'feeder_sat': 0,
            'gateway': [37.8167, 22.6667, 0.0], 'mask_deg': 0.5,
            'beam_gain_dbi': 17.0, 'ut_power_dbw': 4.0,
            'forward_isl_bps': 1000000000, 'reverse_isl_bps': 1000000000,
            'forward_queue_packets': 100, 'reverse_queue_packets': 100,
            'orbit_group': 'iridium-NEXT',
            'orbit_snapshot': pin,
            'dynamic_physical': True,
            'antenna_model': 'public-v1',
            'terminal_mounts': {},
        },
    }
    world = {
        'schema_version': 2, 'network_execution': 'schema_only',
        'map_source': 'manual', 'width_m': 4000, 'height_m': 4000, 'roads': {'nodes': [], 'segments': []},
        'rsus': [], 'vehicles': [],
        'georeference': {'frame': 'WGS84_ENU', 'latitude_deg': 48.1486,
                         'longitude_deg': 17.1077, 'height_m': 0,
                         'anchor_x_m': 2000, 'anchor_y_m': 2000},
        'simulation': {'duration_s': 2, 'seed': scenario['seed'],
                       'step_s': .1, 'utc_origin': origin,
                       # Nový scenár obsahuje explicitné predvolené parametre SUMO vozidla.
                       # Technická stránka ich môže upravovať a uložený svet ich prenesie do
                       # každého nového behu.
                       'vehicle_model': {'accel_mps2': 2, 'decel_mps2': 4.5, 'sigma': 0,
                                         'length_m': 5, 'width_m': 1.8, 'min_gap_m': 2.5,
                                         'speed_factor': 1, 'manual_max_speed_mps': 40}},
        'flows': [{'id': 'cam_broadcast', 'source': '', 'target': 'broadcast',
                   'message_type': 'CAM', 'technology': 'its_g5',
                   'execution': 'not_implemented'}],
    }
    demand = {'schema_version': 1, 'kind': 'synthetic_trips',
              'provenance': 'Routes created in the simulator editor; synthetic demand, not measured traffic',
              'vehicles': []}
    return {'scenario': scenario, 'world': world, 'demand': demand}


# Pri otvorení starého uloženého scenára sa technická epocha posunie o jeho pôvodných 10 s.
# Používateľom vybraný fyzický okamih zostane rovnaký; nový beh sa ukladá v schéme 7.
def source(scenario):
    """Validate a saved scenario, including the previous 10 s clock format."""
    current = copy.deepcopy(scenario)
    if current.get('schema_version') == 6 and current.get('time_policy') == 'warmup_then_full_duration':
        origin = datetime.fromisoformat(current['utc_origin'].replace('Z', '+00:00'))
        current['utc_origin'] = (origin + timedelta(seconds=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
        current['schema_version'] = 7
        current['time_policy'] = 'ready_at_t0_full_duration'
    preflight(current)
    return {'scenario': scenario, 'world': read(project_input(scenario['world_template'])),
            'demand': read(project_input(scenario['demand']))}


# Uloží scenár, mapu a dopravu ako súvisiacu trojicu. Tieto súbory sú skutočným vstupom
# neskoršieho behu; grafické nastavenie bez uloženia ešte nie je dôkazový scenár.
def save(scenario, world, demand):
    if not isinstance(scenario, dict) or not IDENT.fullmatch(str(scenario.get('scenario_id', ''))):
        raise ValueError('Neplatné ID scenára')
    sid = scenario['scenario_id']
    if not isinstance(demand, dict) or not isinstance(demand.get('vehicles'), list):
        raise ValueError('Neplatný dopyt vozidiel')
    applied = copy.deepcopy(world)
    applied['vehicles'] = demand['vehicles']
    applied['simulation'].update(seed=scenario['seed'], utc_origin=scenario['utc_origin'], step_s=.1)
    validate_world(applied)
    folder = ROOT / 'data/inputs/user' / sid
    folder.mkdir(parents=True, exist_ok=False)
    try:
        (folder / 'world.json').write_text(json.dumps(applied, indent=2, sort_keys=True) + '\n')
        (folder / 'demand.json').write_text(json.dumps(demand, indent=2, sort_keys=True) + '\n')
        saved = copy.deepcopy(scenario)
        saved['world_template'] = str((folder / 'world.json').relative_to(ROOT))
        saved['demand'] = str((folder / 'demand.json').relative_to(ROOT))
        plan = preflight(saved)
        target = ROOT / 'config/scenarios' / (sid + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x') as stream:
            json.dump(saved, stream, indent=2, sort_keys=True)
        return {'scenario': saved, 'plan': plan, 'path': str(target.relative_to(ROOT))}
    except Exception:
        shutil.rmtree(folder)
        raise


# Vykoná validáciu rozpracovaného návrhu bez spustenia drahého paketového modelu. Je to spätná
# väzba editora, nie výsledok experimentu.
def check(scenario, world, demand):
    """Validate an unsaved map using the exact runner preflight, without retaining inputs."""
    if not isinstance(scenario, dict) or not IDENT.fullmatch(str(scenario.get('scenario_id', ''))):
        raise ValueError('Neplatné ID scenára')
    parent = ROOT / 'data/inputs/user'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='check-', dir=parent) as tmp:
        folder = Path(tmp)
        applied=copy.deepcopy(world)
        applied['vehicles']=demand['vehicles']
        (folder / 'world.json').write_text(json.dumps(applied))
        (folder / 'demand.json').write_text(json.dumps(demand))
        current = copy.deepcopy(scenario)
        current['world_template'] = str((folder / 'world.json').relative_to(ROOT))
        current['demand'] = str((folder / 'demand.json').relative_to(ROOT))
        return {'plan': preflight(current)}


def _rows(path):
    if not path.is_file():
        return []
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def _folder(base):
    for candidate in (base / 'native/baseline', base / 'ground/scenario'):
        if (candidate / 'waypoints.csv').is_file():
            return candidate
    raise ValueError('Beh nemá stopy polôh pre prehrávanie')


# Pre replay znovu vypočíta polohy satelitov z uložených TLE pre časy konkrétneho behu. Nesmie
# použiť čerstvo stiahnutý archív, lebo by sa satelity posunuli oproti raw paketovým stopám.
def _satellites(base, folder, origin, times):
    editor_manifest = base / 'native/editor-manifest.json'
    if not editor_manifest.is_file():
        return []
    record = read(editor_manifest)
    ids = record['topology']['catalog_ids']
    tle = folder / 'inputs' / record['model']['scenario'] / 'tles.txt'
    if not tle.is_file():
        return []
    from sgp4.api import Satrec
    from simulator_orbits import sat_ecef
    lines = tle.read_text().splitlines()
    if int(lines[0]) != len(ids) or len(lines) != 1 + 3 * len(ids):
        raise ValueError('Nesúlad TLE a konštelácie')
    sats = [Satrec.twoline2rv(lines[2 + 3*i], lines[3 + 3*i]) for i in range(len(ids))]
    epoch = datetime.fromisoformat(origin.replace('Z', '+00:00'))
    answer = []
    for t in times:
        instant = epoch + timedelta(microseconds=t)
        for index, sat in enumerate(sats):
            x, y, z = sat_ecef(sat, instant)
            answer.append({'id': f'sat{index}', 'catalog_id': ids[index], 'time_us': t,
                           'xyz_km': [float(x), float(y), float(z)],
                           'lat': math.degrees(math.atan2(z, math.hypot(x, y))),
                           'lon': math.degrees(math.atan2(y, x))})
    return answer


VISIBLE = {'CAM_UPER_TX', 'CAM_UPER_RX', 'GN_BTP_CAM_TX',
           'DENM_UPER_TX','DENM_UPER_RX','DENM_REPEAT_TX','CAR_DENM_GBC_TX',
           'RSU_DENM_LAN_TX','UT_DENM_LAN_RX','UT_DENM_SAT_TX','GATEWAY_DENM_RX',
           'GATEWAY_DENM_SAT_TX','UT_DENM_SAT_RX','UT_DENM_LAN_TX',
           'RSU_DENM_LAN_RX','RSU_DENM_REGENERATED','RSU_DENM_GBC_TX'}


# `_packet_event_index()` pracuje s paketom a jeho bajtmi alebo stopami.
@lru_cache(maxsize=6)
# Z overeného CSV vytvorí chronologický index dvojíc čas a bajtová pozícia. Obsah paketov zostáva
# na disku; index slúži pre stránkovanie aj presné zobrazenie okamihu udalosti v replay.
def _packet_event_index(path, size, mtime_ns, start_us, end_us, link):
    """Index byte offsets once; pages then read the verified CSV without copying it."""
    indexed = []
    origins, report_rsu = {}, {}
    with path.open('rb') as stream:
        names = next(csv.reader([stream.readline().decode('utf-8')]))
        columns = {name: names.index(name) for name in
                   ('stage', 'event_id', 'node_id', 'time_us')}
        while True:
            offset = stream.tell()
            line = stream.readline()
            if not line:
                break
            fields = next(csv.reader([line.decode('utf-8')]))
            stage = fields[columns['stage']]
            event = fields[columns['event_id']]
            if not event or event == '0000000000000000':
                continue
            node = fields[columns['node_id']]
            if link:
                pair = None
                if stage in ('CAM_UPER_TX', 'DENM_UPER_TX', 'RSU_DENM_GBC_TX'):
                    origins[event] = node
                elif stage == 'RSU_DENM_LAN_TX':
                    report_rsu[event] = node
                elif stage in ('CAM_UPER_RX', 'DENM_UPER_RX'):
                    pair = (origins.get(event), node, 'its-g5')
                elif stage == 'GATEWAY_DENM_RX':
                    pair = (report_rsu.get(event), 'sat0', 'satellite-native')
                elif stage == 'UT_DENM_SAT_RX':
                    pair = ('sat0', node, 'satellite-native')
                if pair != link:
                    continue
            when = int(fields[columns['time_us']]) - start_us
            if when >= 0 and (end_us is None or when <= end_us):
                indexed.append((when, offset))
    indexed.sort()
    return tuple(indexed)


# Z chronologických časov vytvorí rozdiely v mikrosekundách a zakóduje ich malým premenlivým
# počtom bajtov. Prenesú sa iba časy, nie celý CSV obsah ani bajty paketov.
def _packet_timeline(index):
    """Encode ordered microsecond gaps for one browser-side replay clock."""
    encoded = bytearray()
    previous = 0
    for item in index:
        when = item[0]
        gap = when - previous
        previous = when
        while gap >= 128:
            encoded.append((gap & 0x7f) | 0x80)
            gap >>= 7
        encoded.append(gap)
    return base64.b64encode(encoded).decode('ascii')


# Overí beh a vráti požadovanú stránku surovej stopy. Na prvú požiadavku môže pridať kompaktný
# časový index všetkých udalostí, aby prehliadač pri prehrávaní odhaľoval len už nastalé pakety.
# Časový zoznam spája aplikáčnú CSV stopu s natívnymi SNS-3 vrstvovými udalosťami podľa UID mapy.
# Stránkovanie zostáva nad celým časom behu; udalosti bez preukázanej DENM identity, napríklad
# riadiace rámce, sa neprezentujú ako súčasť výstrahy.
def packet_events(base, offset=0, limit=256, from_node=None, to_node=None, kind=None,
                  timeline=False):
    """Return a random-access page covering the whole checked simulation clock."""
    offset, limit = int(offset), int(limit)
    if offset < 0 or not 1 <= limit <= 512:
        raise ValueError('Neplatný rozsah paketových udalostí')
    requested = (from_node, to_node, kind)
    if any(value is not None for value in requested):
        if (any(value is None or not EVENT.fullmatch(value) for value in requested) or
                kind not in ('its-g5', 'satellite-native', 'isl-model')):
            raise ValueError('Neplatný filter paketového spojenia')
        link = requested
    else:
        link = None
    verified_run(base)
    scenario = read(base / 'inputs/scenario.json')
    start_us = START_S * 1_000_000 if full_duration(scenario) else 0
    end_us = int(scenario['sample_count']) * 100_000 if full_duration(scenario) else None
    path = _folder(base) / 'trace.csv'
    stat = path.stat()
    app_index = _packet_event_index(path, stat.st_size, stat.st_mtime_ns,
                                    start_us, end_us, link)
    native, _ = load_satellite_trace(_folder(base))
    linked_ids = None
    if link:
        linked_ids = set()
        with path.open('rb') as stream:
            names = next(csv.reader([stream.readline().decode('utf-8')]))
            event_column = names.index('event_id')
            for _, position in app_index:
                stream.seek(position)
                linked_ids.add(next(csv.reader([stream.readline().decode('utf-8')]))[event_column])
    index = [(when, 0, position) for when, position in app_index]
    index.extend((row['time_us'] - start_us, 1, row) for row in native
                 if row['time_us'] >= start_us and
                 (end_us is None or row['time_us'] - start_us <= end_us) and
                 (linked_ids is None or row['id'] in linked_ids))
    index.sort(key=lambda item: item[0])
    selected = index[offset:offset + limit]
    events = []
    with path.open('rb') as stream:
        names = next(csv.reader([stream.readline().decode('utf-8')]))
        for _, source, item in selected:
            if source:
                events.append({**item, 'time_us': item['time_us'] - start_us,
                               'raw_hex': ''})
            else:
                stream.seek(item)
                fields = next(csv.reader([stream.readline().decode('utf-8')]))
                row = dict(zip(names, fields))
                events.append({'stage': row['stage'], 'node': row['node_id'],
                               'id': row['event_id'], 'time_us': int(row['time_us']) - start_us,
                               'bytes': int(row['bytes'])})
    answer = {'offset': offset, 'limit': limit, 'total': len(index), 'events': events}
    if timeline:
        answer['time_deltas_us_b64'] = _packet_timeline(index)
        answer['timeline_encoding'] = 'uvarint-delta-us-v1'
    return answer


def _visible_trace_events(trace_rows):
    """Bound replay size while keeping application events ahead of routine CAMs."""
    important, ground = [], []
    total = omitted_receives = 0
    for row in trace_rows:
        if row['stage'] not in VISIBLE or row['event_id'] in ('', '0000000000000000'):
            continue
        total += 1
        if row['stage'] == 'CAM_UPER_RX':
            omitted_receives += 1
            continue
        target = ground if row['stage'] in ('CAM_UPER_TX', 'GN_BTP_CAM_TX') else important
        if len(target) < 30000:
            target.append({'stage': row['stage'], 'node': row['node_id'],
                           'id': row['event_id'], 'time_us': int(row['time_us']),
                           'bytes': int(row['bytes'])})
    events = important[:30000] + ground[:max(0, 30000-len(important))]
    return sorted(events, key=lambda r: r['time_us']), total, omitted_receives


# Zo zaznamenaných etap paketu skladá časované spojenia medzi uzlami. Linka sa vykreslí len na
# základe stopy; nie je to nový výpočet pravdepodobnosti príjmu. Limit chráni UI pred príliš
# veľkým počtom grafických prvkov.
def _replay_links(trace_rows, limit=120000):
    """Observed end-to-end receptions and explicit ISL queue transfers for the UI.

    The UI may sample very dense traces. Only confirmed receiver stages create
    ground links; a PHY drop never creates a line.
    """
    from random import Random
    rng = Random(388)
    origins = {}
    report_rsu = {}
    chosen, satellite = [], []
    total = 0
    ground_total = satellite_total = 0

    def add(source, target, row, kind):
        nonlocal total, ground_total, satellite_total
        if not source or not target or source == target:
            return
        total += 1
        if kind == 'its-g5': ground_total += 1
        else: satellite_total += 1
        link = {'from': source, 'to': target, 'id': row['event_id'],
                'time_us': int(row['time_us']), 'kind': kind}
        pool, capacity, seen = (chosen, limit, ground_total) if kind == 'its-g5' else (satellite, 30000, satellite_total)
        if len(pool) < capacity:
            pool.append(link)
        else:
            index = rng.randrange(seen)
            if index < capacity:
                pool[index] = link

    for row in trace_rows:
        event = row['event_id']
        if not event or event == '0000000000000000':
            continue
        stage, node = row['stage'], row['node_id']
        if stage == 'CAM_UPER_TX':
            origins[event] = node
        elif stage == 'CAM_UPER_RX':
            add(origins.get(event), node, row, 'its-g5')
        elif stage == 'DENM_UPER_TX':
            origins[event] = node
        elif stage == 'RSU_DENM_GBC_TX':
            origins[event] = node
        elif stage == 'DENM_UPER_RX':
            add(origins.get(event), node, row, 'its-g5')
        elif stage == 'RSU_DENM_LAN_TX':
            report_rsu[event] = node
        elif stage == 'GATEWAY_DENM_RX':
            add(report_rsu.get(event), 'sat0', row, 'satellite-native')
        elif stage == 'UT_DENM_SAT_RX':
            add('sat0', node, row, 'satellite-native')
    links = chosen + satellite
    links.sort(key=lambda item: item['time_us'])
    return links, total


# Po overení behu poskladá časové polohy, pakety a udalosti pre prehrávač. Replay neprepočítava
# komunikáciu; iba číta a zobrazuje uložené stopy.
def replay(base):
    verified_run(base)
    folder = _folder(base)
    rows = _rows(folder / 'waypoints.csv')
    if len(rows) > 50000:
        stride = math.ceil(len(rows) / 48000)
        last_index = max(int(r['index']) for r in rows)
        rows = [r for r in rows if int(r['index']) % stride == 0 or int(r['index']) == last_index]
    points = [{'id': r['node_id'], 'kind': r['kind'], 'time_us': int(r['time_us']),
               'x': float(r['x_m']), 'y': float(r['y_m'])} for r in rows]
    path = folder / 'trace.csv'
    if not path.is_file():
        raise ValueError('Beh nemá paketovú stopu pre prehrávanie')
    with path.open(newline='') as stream:
        events, event_total, omitted_receives = _visible_trace_events(csv.DictReader(stream))
    with path.open(newline='') as stream:
        packet_links, link_total = _replay_links(csv.DictReader(stream))
    scenario = read(base / 'inputs/scenario.json')
    # The run input is the geometry template. Ground's checked world contains
    # the applied demand and therefore every car actually used by the run.
    world = read(base / 'ground/scenario/world.json')
    if full_duration(scenario):
        # Read the saved editor geometry; the native world includes SUMO's tail.
        world = read(ROOT / scenario['world_template'])
        world['vehicles'] = read(ROOT / scenario['demand'])['vehicles']
        offset = START_S * 1_000_000
        for row in points: row['time_us'] -= offset
        for row in events: row['time_us'] -= offset
        for row in packet_links: row['time_us'] -= offset
        end_us = world['simulation']['duration_s'] * 1_000_000
        events = [row for row in events if 0 <= row['time_us'] <= end_us]
        packet_links = [row for row in packet_links if 0 <= row['time_us'] <= end_us]
    times = sorted({p['time_us'] for p in points if p['kind'] == 'car'})
    sat_times = times[::max(1, len(times)//80)]
    if full_duration(scenario):
        sat_times = sorted(set(sat_times + [world['simulation']['duration_s'] * 1_000_000]))
        sat_times = [time_us + START_S * 1_000_000 for time_us in sat_times]
    gateway = scenario['satellite']['gateway'] if scenario['satellite'] else None
    links = scenario['satellite'].get('isls',[]) if scenario['satellite'] else []
    satellites = _satellites(base, folder, scenario['utc_origin'], sat_times)
    if full_duration(scenario):
        for row in satellites: row['time_us'] -= START_S * 1_000_000
    physical = read(base/'physical-timeline.json') if (base/'physical-timeline.json').is_file() else None
    return {'world': world, 'scenario': scenario, 'points': points,
            'events': events, 'event_total': event_total,
            'events_omitted': event_total-len(events), 'cam_receives_on_demand': omitted_receives,
            'satellites': satellites,
            'packet_links': packet_links, 'packet_link_total': link_total,
            'gateway': gateway, 'orbit_links': links,
            'physical_timeline': physical,
            'trace_kind': str(folder.relative_to(base))}


# Vydá audit fyzikálneho výhľadu pre overený beh. Ak sa zmenia vstupy alebo výsledky,
# `verified_run` ich musí najprv odmietnuť.
def physical_audit(base):
    """Read-only F6 evidence; the sealed source run is verified before analysis."""
    verified_run(base)
    from simulator_physical_report import analyze
    return analyze(base, already_verified=True)


# Podľa identity udalosti vyberie reálne raw bajty a potvrdené dekódované polia. Detail paketu
# musí vychádzať zo stopy, nie zo šablóny v prehliadači.
def packet(base, event_id):
    if not EVENT.fullmatch(event_id):
        raise ValueError('Neplatné ID paketu')
    verified_run(base)
    logical = full_duration(read(base / 'inputs/scenario.json'))
    end_us = read(base / 'inputs/scenario.json')['sample_count'] * 100000 if logical else None
    folder = _folder(base)
    path = folder / 'trace.csv'
    if not path.is_file():
        raise ValueError('Beh nemá paketovú stopu')
    stages = []
    with path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            if row['event_id'] == event_id:
                stages.append({'stage': row['stage'], 'node': row['node_id'],
                               'time_us': int(row['time_us']), 'bytes': int(row['bytes']),
                               'raw_hex': row['raw_hex']})
                if len(stages) >= 2000:
                    break
    native, _ = load_satellite_trace(folder)
    stages.extend({**row, 'time_us': row['time_us']} for row in native
                  if row['id'] == event_id)
    stages.sort(key=lambda row: row['time_us'])
    if logical:
        for row in stages: row['time_us'] -= START_S * 1_000_000
        stages = [row for row in stages if 0 <= row['time_us'] <= end_us]
    for stage in enrich_cam(stages):
        raw=stage.get('raw_hex','').lower()
        if raw.startswith('0201'):
            stage['decoded_denm']=decode_denm(raw)
        elif '07d200000201' in raw:
            stage['decoded_denm']=decode_denm(raw.split('07d20000',1)[1])
        elif stage.get('native_level') and raw.startswith('4'):
            data = bytes.fromhex(raw)
            ip_header = (data[0] & 15) * 4
            if len(data) >= ip_header + 8 and data[9] == 17:
                stage['decoded_denm'] = decode_denm(data[ip_header + 8:].hex())
    return {'event_id': event_id, 'stages': stages,
            'raw_hex_limit': None, 'truncated_stages': len(stages) >= 2000}
