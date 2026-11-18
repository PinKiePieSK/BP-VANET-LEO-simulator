"""Pinned local terrain/building inputs and line-of-sight sensitivity for LEO.

Terrain is bare-earth HGT from AWS Terrain Tiles (source varies by region).
OSM building heights are community tags, not surveyed ground truth.  The
unknown-height interval is deliberately retained in route results.
"""
from __future__ import annotations

import gzip
import hashlib
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import numpy as np

from simulator_platform import ROOT
from simulator_osm_road_graph import basis, local

HGT_BASE = 'https://s3.amazonaws.com/elevation-tiles-prod/skadi'
HGT_CACHE = ROOT / 'data/derived/terrain-cache'
MAX_BUILDINGS = 50_000
STEP_M = 30
TERRAIN_SIDE = 75  # -120 .. 2100 m, inclusive


def terrain_side(extent):
    if type(extent) is not int or not 500 <= extent <= 4000:
        raise ValueError('Local environment dimension must be 500..4000 m')
    return TERRAIN_SIDE + math.ceil((extent - 2000) / STEP_M)


def _height(tags):
    raw = tags.get('height', '').strip().lower()
    m = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*(m|meter|metre|meters|metres)?', raw)
    if m and 0 < float(m[1]) <= 500:
        value = float(m[1])
        return value, value, 'osm_height_tag_unverified', tags.get('source:height', '')[:100]
    raw = tags.get('building:levels', '').strip()
    if re.fullmatch(r'[1-9][0-9]{0,2}', raw) and int(raw) <= 100:
        count = int(raw)
        return 2.5 * count, 4.0 * count, 'levels_2.5_to_4_m_assumption', ''
    return 3.0, 30.0, 'unknown_3_to_30_m_sensitivity', ''


def _building_class(value):
    """Small, declared OSM-type groups; footprint size is not a height proxy."""
    groups = {
        'house': 'low_residential', 'detached': 'low_residential',
        'semidetached_house': 'low_residential', 'terrace': 'low_residential',
        'residential': 'low_residential', 'apartments': 'multi_residential',
        'dormitory': 'multi_residential', 'hotel': 'multi_residential',
        'office': 'commercial', 'commercial': 'commercial', 'retail': 'commercial',
        'supermarket': 'commercial', 'industrial': 'industrial',
        'warehouse': 'industrial', 'factory': 'industrial',
        'garage': 'accessory', 'garages': 'accessory', 'carport': 'accessory',
        'shed': 'accessory', 'school': 'institutional',
        'university': 'institutional', 'hospital': 'institutional',
        'civic': 'institutional',
    }
    return groups.get(value, 'unspecified')


def impute_building_heights(buildings):
    """Deterministic local median with an empirical + floor-height interval.

    Donors are only OSM height tags or level counts.  Their availability is
    selective, not a random survey, so the interval remains a sensitivity
    envelope rather than a statistical confidence interval.
    """
    donors, grid = [], {}
    for index, b in enumerate(buildings):
        poly = b['polygon_xy_m']
        b['height_central_m'] = (float(b['height_min_m']) if
            b['height_source'] == 'osm_height_tag_unverified' else
            round(float(b['height_min_m']) / 2.5 * 3, 2) if
            b['height_source'] == 'levels_2.5_to_4_m_assumption' else None)
        if b['height_central_m'] is None:
            continue
        x = sum(p[0] for p in poly) / len(poly)
        y = sum(p[1] for p in poly) / len(poly)
        donors.append((x, y, b['building_class'], b))
        grid.setdefault((math.floor(x / 100), math.floor(y / 100)), []).append(len(donors) - 1)
    for b in buildings:
        if b['height_central_m'] is not None:
            continue
        poly = b['polygon_xy_m']
        x = sum(p[0] for p in poly) / len(poly)
        y = sum(p[1] for p in poly) / len(poly)
        kind = b['building_class']
        def nearby(radius, same_class):
            cx, cy = math.floor(x / 100), math.floor(y / 100)
            side = math.ceil(radius / 100)
            ids = (i for gx in range(cx - side, cx + side + 1)
                   for gy in range(cy - side, cy + side + 1)
                   for i in grid.get((gx, gy), ()))
            return [donors[i][3] for i in ids
                    if (not same_class or donors[i][2] == kind)
                    and (donors[i][0] - x) ** 2 + (donors[i][1] - y) ** 2 <= radius ** 2]
        selected, scope = [], ''
        for radius, same_class, minimum, label in (
            (300, kind != 'unspecified', 8, 'same_type_300m'),
            (250, False, 12, 'all_types_250m'),
            (500, kind != 'unspecified', 12, 'same_type_500m'),
            (500, False, 12, 'all_types_500m')):
            if label.startswith('same_type') and kind == 'unspecified':
                continue
            found = nearby(radius, same_class)
            if len(found) >= minimum:
                selected, scope = found, label
                break
        if not selected and kind != 'unspecified':
            found = [d[3] for d in donors if d[2] == kind]
            if len(found) >= 20:
                selected, scope = found, 'same_type_whole_cutout'
        if not selected and len(donors) >= 20:
            selected, scope = [d[3] for d in donors], 'whole_cutout'
        if not selected:
            b['height_central_m'] = 9.0
            b['height_reference'] = 'fallback_9m_no_donors'
            continue
        centers = [row['height_central_m'] for row in selected]
        central = float(np.median(centers))
        low = min(float(np.quantile([row['height_min_m'] for row in selected], .1)), central * .6)
        high = max(float(np.quantile([row['height_max_m'] for row in selected], .9)), central * 1.6)
        b['height_min_m'] = round(max(3, min(central, low)), 2)
        b['height_central_m'] = round(central, 2)
        b['height_max_m'] = round(min(100, max(central, high)), 2)
        b['height_source'] = 'imputed_local_median_not_measured'
        b['height_reference'] = f'{scope};n={len(selected)};OSM_height_or_levels'
    return {'donor_buildings': len(donors),
            'imputed_buildings': sum(b['height_source'] == 'imputed_local_median_not_measured'
                                     for b in buildings),
            'fallback_buildings': sum(b['height_reference'] == 'fallback_9m_no_donors'
                                      for b in buildings)}


def buildings_from_xml(tiles, geo, extent=2000, height=None):
    width = extent
    height = width if height is None else height
    """Closed building ways only; incomplete/multipolygon relations are counted."""
    nodes, ways, relation_count = {}, {}, 0
    for _, raw in tiles:
        root = ET.fromstring(raw)
        for node in root.iter('node'):
            nodes[node.attrib['id']] = (float(node.attrib['lon']), float(node.attrib['lat']))
        relation_count += sum(1 for rel in root.iter('relation')
                              if any(t.attrib.get('k') == 'building' for t in rel.findall('tag')))
        for way in root.iter('way'):
            tags = {t.attrib['k']: t.attrib['v'] for t in way.findall('tag')}
            if tags.get('building') in (None, 'no'):
                continue
            refs = [n.attrib['ref'] for n in way.findall('nd')]
            if len(refs) >= 4 and refs[0] == refs[-1]:
                ways[way.attrib['id']] = (refs, tags)
    frame = basis(geo)
    rows = []
    incomplete = 0
    for wid, (refs, tags) in sorted(ways.items(), key=lambda x: int(x[0])):
        if len(refs) > 150 or any(ref not in nodes for ref in refs):
            incomplete += 1
            continue
        polygon = [local(frame, *nodes[ref]) for ref in refs[:-1]]
        if len(polygon) < 3 or not any(-120 <= x <= width + 120 and -120 <= y <= height + 120 for x, y in polygon):
            continue
        if not (-120 <= min(x for x, _ in polygon) <= width + 120 or
                -120 <= max(x for x, _ in polygon) <= width + 120):
            continue
        lo, hi, source, height_ref = _height(tags)
        rows.append({'id': 'osm-building-' + wid,
                     'polygon_xy_m': [[round(x, 2), round(y, 2)] for x, y in polygon],
                     'height_min_m': lo, 'height_max_m': hi,
                     'height_source': source, 'height_reference': height_ref,
                     'building_class': _building_class(tags['building'])})
        if len(rows) > MAX_BUILDINGS:
            raise ValueError('More than 50,000 closed OSM buildings in local cutout')
    estimates = impute_building_heights(rows)
    return rows, {'closed_ways': len(rows), 'incomplete_closed_ways': incomplete,
                  'building_relations_not_imported': relation_count, **estimates}


def _tile_key(lat, lon):
    south, west = math.floor(lat), math.floor(lon)
    if not (-89 <= south <= 89 and -180 <= west <= 179):
        raise ValueError('HGT tile outside supported latitude/longitude')
    name = f'{"N" if south >= 0 else "S"}{abs(south):02d}{"E" if west >= 0 else "W"}{abs(west):03d}'
    folder = f'{"N" if south >= 0 else "S"}{abs(south):02d}'
    return south, west, name, f'{HGT_BASE}/{folder}/{name}.hgt.gz'


def _hgt(lat, lon, cache):
    south, west, name, url = _tile_key(lat, lon)
    if name not in cache:
        HGT_CACHE.mkdir(parents=True, exist_ok=True)
        path = HGT_CACHE / (name + '.hgt.gz')
        if not path.is_file():
            request = Request(url, headers={'User-Agent': 'BP-Simulator/1.0 academic terrain import'})
            with urlopen(request, timeout=60) as response:
                raw = response.read(15_000_001)
            if not 1_000_000 <= len(raw) <= 15_000_000:
                raise ValueError('HGT download has unexpected size')
            path.write_bytes(raw)
        raw = path.read_bytes()
        decoded = gzip.decompress(raw)
        side = math.isqrt(len(decoded) // 2)
        if side not in (1201, 3601) or side * side * 2 != len(decoded):
            raise ValueError('HGT tile resolution or size is invalid')
        matrix = np.frombuffer(decoded, dtype='>i2').reshape(side, side)
        cache[name] = (matrix, {'url': url, 'sha256': hashlib.sha256(raw).hexdigest(),
                                'resolution': side, 'tile': name})
    matrix, meta = cache[name]
    n = len(matrix) - 1
    col = (lon - west) * n
    row = (south + 1 - lat) * n
    i, j = max(0, min(n - 1, int(row))), max(0, min(n - 1, int(col)))
    fy, fx = row - i, col - j
    z = matrix[i:i + 2, j:j + 2].astype(float)
    if np.any(z <= -32000):
        raise ValueError(f'HGT contains a void near {lat},{lon}')
    return float((1 - fy) * ((1 - fx) * z[0, 0] + fx * z[0, 1]) +
                 fy * ((1 - fx) * z[1, 0] + fx * z[1, 1])), meta


def _xy_to_geo(geo, x, y):
    lat0 = math.radians(geo['latitude_deg'])
    lat = geo['latitude_deg'] + (y - geo['anchor_y_m']) / 110574.0
    lon = geo['longitude_deg'] + (x - geo['anchor_x_m']) / (111320.0 * math.cos(lat0))
    return lat, lon


def terrain_for(geo, extent=2000, height=None):
    cache, values, sources = {}, [], {}
    width = terrain_side(extent)
    height = terrain_side(extent if height is None else height)
    for iy in range(height):
        y = -120 + iy * STEP_M
        for ix in range(width):
            x = -120 + ix * STEP_M
            z, source = _hgt(*_xy_to_geo(geo, x, y), cache)
            values.append(round(z, 2))
            sources[source['tile']] = source
    return {'origin_xy_m': [-120, -120], 'step_m': STEP_M,
            'width': width, 'height': height,
            'elevation_m': values}, list(sources.values())


def import_environment(tiles, geo, extent=2000, height=None, provider='openstreetmap-api-v0.6'):
    width = extent
    height = width if height is None else height
    buildings, counts = buildings_from_xml(tiles, geo, width, height)
    terrain, hgt = terrain_for(geo, width, height)
    osm_hash = hashlib.sha256(''.join(f'{box}:{hashlib.sha256(raw).hexdigest()}'
                                     for box, raw in sorted(tiles)).encode()).hexdigest()
    result = {'schema_version': 1, 'georeference': geo, 'buildings': buildings,
            'terrain': terrain, 'height_policy': 'local_robust_median_v1',
            'height_case': 'central',
            'uncertain_route_policy': 'optimistic_with_uncertainty_flag',
            'statistical_layers': {
                'vegetation': {'recommendation': 'ITU-R P.833-10',
                               'status': 'unknown_without_canopy_depth_species_and_frequency',
                               'assumed_loss_db_interval': None},
                'weather': {'recommendation': 'ITU-R P.618-14',
                            'status': 'unknown_without_rain_climate_and_link_frequency',
                            'assumed_loss_db_interval': None}},
            'sources': {'osm': {'provider': provider, 'sha256': osm_hash, **counts},
                        'terrain': {'provider': 'AWS Terrain Tiles Skadi HGT', 'tiles': hgt,
                                    'vertical_datum': 'source_dependent_relative_heights_only'},
                        'retrieved_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}}
    if width == height and width in (2000, 4000):
        result['extent_m'] = width
    else:
        result.update(width_m=width, height_m=height)
    return result


def validate_environment(env, geo):
    if type(env) is not dict or env.get('schema_version') != 1 or env.get('georeference') != geo:
        raise ValueError('Local environment georeference does not match scenario')
    extent = env.get('extent_m', 2000)
    width, height = env.get('width_m', extent), env.get('height_m', extent)
    if ('width_m' in env) != ('height_m' in env):
        raise ValueError('Local environment width and height must be supplied together')
    cols, rows = terrain_side(width), terrain_side(height)
    if env.get('uncertain_route_policy') != 'optimistic_with_uncertainty_flag':
        raise ValueError('Unknown local obstruction policy')
    buildings = env.get('buildings')
    if type(buildings) is not list or len(buildings) > MAX_BUILDINGS:
        raise ValueError('Invalid building list')
    for b in buildings:
        poly = b.get('polygon_xy_m')
        if (type(poly) is not list or not 3 <= len(poly) <= 150 or
            not all(type(p) is list and len(p) == 2 and all(type(v) in (int, float)
                and math.isfinite(v) and -500 <= v <= (width if i == 0 else height) + 500
                for i, v in enumerate(p)) for p in poly) or
            not all(type(b.get(k)) in (int, float) and math.isfinite(b[k]) for k in ('height_min_m', 'height_max_m')) or
            not 0 <= b['height_min_m'] <= b['height_max_m'] <= 500 or
            type(b.get('height_source')) is not str):
            raise ValueError('Invalid local building polygon or height interval')
        if 'height_central_m' in b and (type(b['height_central_m']) not in (int, float) or
            not math.isfinite(b['height_central_m']) or
            not b['height_min_m'] <= b['height_central_m'] <= b['height_max_m']):
            raise ValueError('Central building height must be inside sensitivity interval')
    if env.get('height_case', 'interval') not in ('interval', 'low', 'central', 'high'):
        raise ValueError('Unknown building-height sensitivity case')
    if env.get('height_case') in ('low', 'central', 'high') and any(
        'height_central_m' not in b for b in buildings):
        raise ValueError('Height sensitivity needs central estimates for all buildings')
    t = env.get('terrain')
    if type(t) is not dict or t.get('origin_xy_m') != [-120, -120] or t.get('step_m') != STEP_M or \
            t.get('width') != cols or t.get('height') != rows or \
            type(t.get('elevation_m')) is not list or len(t['elevation_m']) != cols * rows or \
            not all(type(z) in (int, float) and math.isfinite(z) and -500 <= z <= 9000 for z in t['elevation_m']):
        raise ValueError('Invalid terrain grid')
    sources = env.get('sources')
    if type(sources) is not dict or 'osm' not in sources or 'terrain' not in sources:
        raise ValueError('Environment provenance is required')
    layers = env.get('statistical_layers')
    expected = {'vegetation': 'ITU-R P.833-10', 'weather': 'ITU-R P.618-14'}
    if type(layers) is not dict or set(layers) != set(expected):
        raise ValueError('Vegetation and weather must be separate statistical layers')
    for name, rec in expected.items():
        layer = layers[name]
        if type(layer) is not dict or layer.get('recommendation') != rec or \
                type(layer.get('status')) is not str:
            raise ValueError('Invalid statistical layer provenance')
        interval = layer.get('assumed_loss_db_interval')
        if interval is not None and (type(interval) is not list or len(interval) != 2 or
            not all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 100 for x in interval) or
            interval[0] > interval[1] or layer['status'] != 'scenario_assumption_not_ITU_prediction'):
            raise ValueError('Loss interval requires explicit scenario-assumption status')


class LocalObstructions:
    def __init__(self, env):
        self.env = env
        self.geo = env['georeference']
        self.height_case = env.get('height_case', 'interval')
        self.frame = basis(self.geo)
        self.rows = env['terrain']['height']
        self.cols = env['terrain']['width']
        self.z = np.asarray(env['terrain']['elevation_m'], dtype=float).reshape(self.rows, self.cols)
        self.buildings = []
        self.grid = {}
        terrain_peak = float(self.z.max())
        self.max_roof_m = terrain_peak
        for index, b in enumerate(env['buildings']):
            poly = [tuple(p) for p in b['polygon_xy_m']]
            box = (min(p[0] for p in poly), min(p[1] for p in poly),
                   max(p[0] for p in poly), max(p[1] for p in poly))
            self.buildings.append((poly, box, b))
            self.max_roof_m = max(self.max_roof_m, terrain_peak + b['height_max_m'])
            for gx in range(math.floor(box[0] / 100), math.floor(box[2] / 100) + 1):
                for gy in range(math.floor(box[1] / 100), math.floor(box[3] / 100) + 1):
                    self.grid.setdefault((gx, gy), set()).add(index)

    def height(self, x, y):
        col, row = (x + 120) / STEP_M, (y + 120) / STEP_M
        if not (0 <= col < self.cols - 1 and 0 <= row < self.rows - 1):
            return None
        i, j = int(row), int(col)
        u, v = col - j, row - i
        return float((1 - v) * ((1 - u) * self.z[i, j] + u * self.z[i, j + 1]) +
                     v * ((1 - u) * self.z[i + 1, j] + u * self.z[i + 1, j + 1]))

    @staticmethod
    def _inside(poly, x, y):
        inside = False
        for a, b in zip(poly, poly[-1:] + poly[:-1]):
            if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                inside = not inside
        return inside

    def sight(self, site, sat_xyz_km, *, antenna_agl_m):
        """Return clear/uncertain/blocked in a 2 km local cutout.

        The orbital vector uses ECEF; only terrain *differences* are compared,
        so uncertain HGT vertical datum never shifts orbital positions.
        """
        x0, y0 = local(self.frame, site[1], site[0])
        z0 = self.height(x0, y0)
        if z0 is None:
            raise ValueError('Terminal outside pinned local terrain grid')
        lat, lon = math.radians(site[0]), math.radians(site[1])
        sl, cl, so, co = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
        from simulator_physical_coverage import site_ecef_km
        d = np.asarray(sat_xyz_km) - site_ecef_km(site)
        dx = (-so * d[0] + co * d[1]) * 1000
        dy = (-sl * co * d[0] - sl * so * d[1] + cl * d[2]) * 1000
        dz = (cl * co * d[0] + cl * so * d[1] + sl * d[2]) * 1000
        horizontal = math.hypot(dx, dy)
        if horizontal < 1 or dz <= 0:
            return 'clear', None
        ux, uy, slope = dx / horizontal, dy / horizontal, dz / horizontal
        limit = min([d for d in ((-120 - x0) / ux if ux < 0 else (2100 - x0) / ux if ux > 0 else math.inf,
                                 (-120 - y0) / uy if uy < 0 else (2100 - y0) / uy if uy > 0 else math.inf)
                     if d >= 0] or [0])
        limit = min(limit, 2200)
        if slope > 0:
            limit = min(limit, max(0, (self.max_roof_m - z0 - antenna_agl_m) / slope + STEP_M))
        # DEM is bare earth. A 30 m pixel and 30 m ray step cannot resolve
        # small berms; this is a geometric sensitivity model, not a survey.
        distances = np.arange(STEP_M, limit, STEP_M)
        xs, ys = x0 + ux * distances, y0 + uy * distances
        cols, rows = (xs + 120) / STEP_M, (ys + 120) / STEP_M
        ii, jj = np.floor(rows).astype(int), np.floor(cols).astype(int)
        good = (ii >= 0) & (jj >= 0) & (ii < TERRAIN_SIDE - 1) & (jj < TERRAIN_SIDE - 1)
        ii, jj, cols, rows, distances = ii[good], jj[good], cols[good], rows[good], distances[good]
        elevations = ((1 - (rows - ii)) * ((1 - (cols - jj)) * self.z[ii, jj] + (cols - jj) * self.z[ii, jj + 1]) +
                      (rows - ii) * ((1 - (cols - jj)) * self.z[ii + 1, jj] + (cols - jj) * self.z[ii + 1, jj + 1]))
        if np.any(elevations > z0 + antenna_agl_m + slope * distances):
            return 'blocked', 'terrain'
        nearby = set()
        gx, gy = math.floor(x0 / 100), math.floor(y0 / 100)
        sx, sy = (1 if ux > 0 else -1), (1 if uy > 0 else -1)
        next_x = ((gx + (1 if sx > 0 else 0)) * 100 - x0) / ux if abs(ux) > 1e-12 else math.inf
        next_y = ((gy + (1 if sy > 0 else 0)) * 100 - y0) / uy if abs(uy) > 1e-12 else math.inf
        step_x = 100 / abs(ux) if abs(ux) > 1e-12 else math.inf
        step_y = 100 / abs(uy) if abs(uy) > 1e-12 else math.inf
        while min(next_x, next_y) <= limit + max(step_x if math.isfinite(step_x) else 0,
                                                  step_y if math.isfinite(step_y) else 0):
            nearby.update(self.grid.get((gx, gy), ()))
            if min(next_x, next_y) > limit:
                break
            if next_x <= next_y:
                gx += sx
                next_x += step_x
            else:
                gy += sy
                next_y += step_y
        uncertain = None
        for index in nearby:
            poly, box, b = self.buildings[index]
            # Find all intersections of the 2D ray and footprint boundary.
            cuts = []
            for a, c in zip(poly, poly[1:] + poly[:1]):
                vx, vy = c[0] - a[0], c[1] - a[1]
                denominator = ux * vy - uy * vx
                if abs(denominator) < 1e-9:
                    continue
                rx, ry = a[0] - x0, a[1] - y0
                along = (rx * vy - ry * vx) / denominator
                edge = (rx * uy - ry * ux) / denominator
                if 0 <= along <= limit and 0 <= edge <= 1:
                    cuts.append(along)
            if self._inside(poly, x0, y0):
                cuts.append(0.0)
            if not cuts:
                continue
            near = min(cuts)
            if near < 0.5:
                continue  # do not let the terminal's own enclosing footprint mask it
            roof_ground = self.height(x0 + ux * near, y0 + uy * near)
            if roof_ground is None:
                continue
            ray_z = z0 + antenna_agl_m + slope * near
            selected_height = (b['height_min_m'] if self.height_case in ('low', 'interval') else
                               b['height_max_m'] if self.height_case == 'high' else
                               b['height_central_m'])
            if roof_ground + selected_height > ray_z:
                return 'blocked', b['id']
            if self.height_case == 'interval' and roof_ground + b['height_max_m'] > ray_z:
                uncertain = b['id']
        return ('uncertain', uncertain) if uncertain else ('clear', None)
