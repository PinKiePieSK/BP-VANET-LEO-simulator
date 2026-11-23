"""Download the drivable OSM graph for a bounded simulator ENU cutout.

The OSM API is queried in bounded tiles because a complete urban cutout can
exceed its 50,000-node response limit. Successful responses are cached in the
project directory, and the editor stores selected WGS84 ways with the scenario.
"""

from __future__ import annotations

import hashlib
import gzip
import json
import math
import os
import re
import tempfile
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from simulator_platform import ROOT

API = "https://api.openstreetmap.org/api/0.6/map"
USER_AGENT = "BP-Simulator/1.0 (academic VANET simulation; local OSM road import)"
DRIVABLE = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
            "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified",
            "residential", "living_street", "service", "road"}
DENIED = {"no", "private", "agricultural", "forestry"}
MAX_BYTES = 20_000_000
MAX_TILES = 64
MAX_ROADS = 30_000
CACHE_DIR = Path(os.environ.get("BP_SIM_WORKSPACE", ROOT)) / "cache/osm"
_LOCK = threading.Lock()
_TILE_LOCKS = {}
_RATE_LIMIT_UNTIL = 0.0
_LOCAL_RESULT_LOCK = threading.Lock()


class OsmRateLimit(ValueError):
    def __init__(self, retry_after_s):
        self.retry_after_s = max(1, int(math.ceil(retry_after_s)))
        super().__init__(f"OSM dočasne obmedzil sťahovanie. Opakujem za {self.retry_after_s} s.")


def _tile_paths(bbox):
    key = hashlib.sha256(json.dumps(bbox, separators=(",", ":")).encode()).hexdigest()
    return CACHE_DIR / f"osm-v06-{key}.xml", CACHE_DIR / f"osm-v06-{key}.json"


def _cached(bbox):
    data_path, meta_path = _tile_paths(bbox)
    try:
        meta = json.loads(meta_path.read_text())
        if meta.get("bbox") != list(bbox):
            return None
        with data_path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != meta.get("sha256"):
            return None
        if ET.fromstring(raw).tag != "osm":
            return None
        return raw
    except (OSError, ValueError, ET.ParseError):
        return None


def _store(bbox, raw):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data_path, meta_path = _tile_paths(bbox)
    meta = {"bbox": list(bbox), "sha256": hashlib.sha256(raw).hexdigest(),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
    for path, data in ((data_path, raw), (meta_path, (json.dumps(meta, sort_keys=True) + "\n").encode())):
        with tempfile.NamedTemporaryFile(dir=CACHE_DIR, prefix=".osm-", delete=False) as stream:
            temp = Path(stream.name)
            stream.write(data)
        os.replace(temp, path)


def _tile_lock(bbox):
    with _LOCK:
        return _TILE_LOCKS.setdefault(tuple(bbox), threading.Lock())


def _retry_seconds(exc, detail):
    header = exc.headers.get("Retry-After", "")
    match = re.search(r"(\d+)\s+seconds?", detail, re.I)
    seconds = int(header) if header.isdigit() else int(match.group(1)) if match else 30
    return min(3600, max(30, seconds))


def finite(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} is outside [{low}, {high}]")
    return float(value)


def basis(geo):
    if type(geo) is not dict or set(geo) != {"frame", "anchor_x_m", "anchor_y_m", "latitude_deg", "longitude_deg", "height_m"} or geo["frame"] != "WGS84_ENU":
        raise ValueError("Expected a WGS84_ENU georeference")
    lat = math.radians(finite(geo["latitude_deg"], -89.9, 89.9, "latitude"))
    lon = math.radians(finite(geo["longitude_deg"], -180, 180, "longitude"))
    height = finite(geo["height_m"], -500, 9000, "height")
    ax = finite(geo["anchor_x_m"], 0, 4000, "anchor_x")
    ay = finite(geo["anchor_y_m"], 0, 4000, "anchor_y")
    a, e2 = 6378137.0, 6.69437999014e-3
    sl, cl, so, co = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
    n = a / math.sqrt(1 - e2 * sl * sl)
    return ((n + height) * cl * co, (n + height) * cl * so, (n * (1 - e2) + height) * sl,
            (-so, co, 0), (-sl * co, -sl * so, cl), ax, ay, a, e2)


def local(geo_basis, lon_deg, lat_deg):
    ox, oy, oz, east, north, ax, ay, a, e2 = geo_basis
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    sl, cl, so, co = math.sin(lat), math.cos(lat), math.sin(lon), math.cos(lon)
    n = a / math.sqrt(1 - e2 * sl * sl)
    # OSM roads are placed on the reference ellipsoid for horizontal ENU.
    d = ((n * cl * co) - ox, (n * cl * so) - oy, (n * (1 - e2) * sl) - oz)
    return ax + sum(d[i] * east[i] for i in range(3)), ay + sum(d[i] * north[i] for i in range(3))


def dimensions(extent=2000, height=None):
    width = extent
    height = width if height is None else height
    if any(type(v) is not int or not 500 <= v <= 4000 for v in (width, height)):
        raise ValueError('OSM cutout dimensions must be 500..4000 m')
    return width, height


def bbox_for(geo, extent=2000, height=None):
    width, height = dimensions(extent, height)
    lat = geo["latitude_deg"]
    if abs(lat) >= 89:
        raise ValueError("The road importer does not support polar sites")
    lon = geo["longitude_deg"]
    pad = 120.0
    west = lon + (-geo["anchor_x_m"] - pad) / (111320 * math.cos(math.radians(lat)))
    east = lon + (width - geo["anchor_x_m"] + pad) / (111320 * math.cos(math.radians(lat)))
    south = lat + (-geo["anchor_y_m"] - pad) / 110574
    north = lat + (height - geo["anchor_y_m"] + pad) / 110574
    return tuple(round(v, 8) for v in (west, south, east, north))


def download(bbox, depth=0):
    global _RATE_LIMIT_UNTIL
    if depth > 5:
        raise ValueError("OSM cutout is too dense for a bounded download")
    def split():
        west, south, east, north = bbox
        mid_lon, mid_lat = (west + east) / 2, (south + north) / 2
        result = []
        for tile in ((west, south, mid_lon, mid_lat), (mid_lon, south, east, mid_lat),
                     (west, mid_lat, mid_lon, north), (mid_lon, mid_lat, east, north)):
            result.extend(download(tile, depth + 1))
            if len(result) > MAX_TILES:
                raise ValueError("OSM cutout required too many tiles")
        return result
    with _tile_lock(bbox):
        cached = _cached(bbox)
        if cached is not None:
            return [(bbox, cached)]
        with _LOCK:
            remaining = _RATE_LIMIT_UNTIL - time.monotonic()
        if remaining > 0:
            raise OsmRateLimit(remaining)
        query = urlencode({"bbox": ",".join(str(x) for x in bbox)})
        request = Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT, "Accept": "application/xml"})
        try:
            with urlopen(request, timeout=35) as response:
                raw = response.read(MAX_BYTES + 1)
        except HTTPError as exc:
            detail = exc.read(300).decode("utf-8", "replace")
            if exc.code == 400 and "too many nodes" in detail.lower():
                return split()
            if exc.code == 509:
                seconds = _retry_seconds(exc, detail)
                with _LOCK:
                    _RATE_LIMIT_UNTIL = max(_RATE_LIMIT_UNTIL, time.monotonic() + seconds)
                raise OsmRateLimit(seconds) from exc
            raise ValueError(f"OSM road download failed ({exc.code}): {detail[:120]}") from exc
        except OSError as exc:
            raise ValueError(f"OSM road download failed: {exc}") from exc
        if len(raw) > MAX_BYTES:
            return split()
        try:
            if ET.fromstring(raw).tag != "osm":
                raise ValueError("OSM response has no osm root")
        except ET.ParseError as exc:
            raise ValueError("OSM returned incomplete XML") from exc
        try:
            _store(bbox, raw)
        except OSError:
            pass
        return [(bbox, raw)]


def point_near_square(a, b, extent=2000, height=None):
    width, height = dimensions(extent, height)
    if any(0 <= p[0] <= width and 0 <= p[1] <= height for p in (a, b)):
        return True
    lo, hi = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for p, q in ((-dx, a[0]), (dx, width - a[0]), (-dy, a[1]), (dy, height - a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            lo = max(lo, t)
        else:
            hi = min(hi, t)
        if lo > hi:
            return False
    return True


def speed(tags):
    raw = tags.get("maxspeed", "").strip().lower()
    try:
        number = float(raw.split()[0])
        if "mph" in raw:
            number *= 1.609344
        if 5 <= number <= 140:
            return round(number / 3.6, 3)
    except (ValueError, IndexError):
        pass
    kind = tags["highway"]
    return {"motorway": 25.0, "trunk": 22.22, "living_street": 5.56,
            "service": 5.56, "residential": 8.33}.get(kind, 13.89)


def directional_speed(tags, direction):
    raw = tags.get(f"maxspeed:{direction}")
    if not raw:
        return speed(tags)
    return speed({**tags, "maxspeed": raw})


def speed_source(tags, direction):
    if tags.get(f"maxspeed:{direction}"):
        return f"maxspeed:{direction}"
    return "maxspeed" if tags.get("maxspeed") else "fallback_highway"


def directional_lanes(tags, direction, oneway):
    raw = tags.get(f"lanes:{direction}")
    if raw and raw.isdigit():
        return max(1, min(6, int(raw)))
    total = tags.get("lanes", "")
    if total.isdigit():
        return max(1, min(6, int(total) if oneway else math.ceil(int(total) / 2)))
    return 1


def lanes_source(tags, direction):
    if tags.get(f"lanes:{direction}"):
        return f"lanes:{direction}"
    return "lanes" if tags.get("lanes") else "fallback_1"


def passenger_access(tags):
    # Specific vehicle tags override a broad access tag.
    value = next((tags[key] for key in ("motorcar", "motor_vehicle", "vehicle", "access") if key in tags), "yes")
    return value not in DENIED


def graph_from_xml(tiles, geo, extent=2000, height=None, provider="openstreetmap-api-v0.6"):
    width, height = dimensions(extent, height)
    points, ways, relations = {}, {}, {}
    access_excluded = set()
    hashes = []
    for bbox, raw in tiles:
        hashes.append((bbox, hashlib.sha256(raw).hexdigest()))
        root = ET.fromstring(raw)
        for node in root.iter("node"):
            points[node.attrib["id"]] = (float(node.attrib["lon"]), float(node.attrib["lat"]))
        for way in root.iter("way"):
            tags = {row.attrib["k"]: row.attrib["v"] for row in way.findall("tag")}
            if tags.get("highway") not in DRIVABLE or tags.get("area") == "yes":
                continue
            if not passenger_access(tags):
                access_excluded.add(way.attrib["id"])
                continue
            refs = [row.attrib["ref"] for row in way.findall("nd")]
            if len(refs) >= 2:
                if tags.get("oneway") == "-1":
                    refs.reverse()
                ways[way.attrib["id"]] = (refs, tags)
        for relation in root.iter("relation"):
            tags = {row.attrib["k"]: row.attrib["v"] for row in relation.findall("tag")}
            if tags.get("type") != "restriction":
                continue
            members = [{"type": row.attrib.get("type"), "ref": row.attrib.get("ref"),
                        "role": row.attrib.get("role")} for row in relation.findall("member")]
            relations[relation.attrib["id"]] = (members, tags)
    degree = Counter(ref for refs, _ in ways.values() for ref in set(refs))
    frame = basis(geo)
    rows = []
    boundary_splits = 0
    for way_id, (refs, tags) in sorted(ways.items(), key=lambda item: int(item[0])):
        local_points = [local(frame, *points[ref]) if ref in points else None for ref in refs]
        crossing = [bool(a and b and point_near_square(a, b, width, height))
                    for a, b in zip(local_points, local_points[1:])]
        start = 0
        for index in range(1, len(refs)):
            boundary_break = index < len(refs) - 1 and (
                crossing[index - 1] != crossing[index] or
                (crossing[index - 1] and crossing[index] and
                 local_points[index] is not None and
                 not (0 <= local_points[index][0] <= width and 0 <= local_points[index][1] <= height)))
            if index != len(refs) - 1 and degree[refs[index]] < 2 and index - start < 29 and not boundary_break:
                continue
            boundary_splits += boundary_break
            part = refs[start:index + 1]
            start = index
            coords = [points[ref] for ref in part if ref in points]
            if len(coords) < 2:
                continue
            xy = [local(frame, *coord) for coord in coords]
            if not any(point_near_square(a, b, width, height) for a, b in zip(xy, xy[1:])):
                continue
            length = sum(math.dist(a, b) for a, b in zip(xy, xy[1:]))
            if length < 0.5:
                continue
            key = f"{way_id}:{part[0]}:{part[-1]}:{index}"
            rid = "osm" + hashlib.blake2s(key.encode(), digest_size=10).hexdigest()
            oneway = tags.get("oneway") in ("yes", "true", "1", "-1") or tags.get("junction") == "roundabout" or (tags["highway"] == "motorway" and tags.get("oneway") not in ("no", "false", "0"))
            forward_tag = "backward" if tags.get("oneway") == "-1" else "forward"
            backward_tag = "forward" if tags.get("oneway") == "-1" else "backward"
            forward_lanes = directional_lanes(tags, forward_tag, oneway)
            lanes = min(3, forward_lanes)
            forward_speed = directional_speed(tags, forward_tag)
            reverse_speed = directional_speed(tags, backward_tag)
            try:
                legacy_lanes = max(1, min(3, math.ceil(int(tags.get("lanes", "")) /
                                                     (1 if tags.get("oneway") in ("yes", "true", "1", "-1") else 2))))
            except ValueError:
                legacy_lanes = 1
            rows.append({"id": rid, "coordinates": [list(c) for c in coords],
                         "speed_limit_mps": forward_speed, "lanes_each_direction": lanes,
                         "legacy_speed_mps": speed(tags), "legacy_lanes_each_direction": legacy_lanes,
                         "speed_forward_mps": forward_speed, "speed_reverse_mps": reverse_speed,
                         "lanes_forward": forward_lanes, "lanes_reverse": directional_lanes(tags, backward_tag, oneway),
                         "speed_forward_source": speed_source(tags, forward_tag),
                         "speed_reverse_source": speed_source(tags, backward_tag),
                         "lanes_forward_source": lanes_source(tags, forward_tag),
                         "lanes_reverse_source": lanes_source(tags, backward_tag),
                         "oneway": oneway,
                         "osm_way_id": way_id, "osm_from_node_id": part[0], "osm_to_node_id": part[-1],
                         "name": (tags.get("name") or tags.get("ref") or "")[:120],
                         "road_class": tags["highway"], "service": tags.get("service", "")[:40],
                         "bridge": tags.get("bridge", "") not in ("", "no"),
                         "tunnel": tags.get("tunnel", "") not in ("", "no"),
                         "layer": int(tags.get("layer", "0")) if re.fullmatch(r"-?\d{1,2}", tags.get("layer", "0")) else 0,
                         "access_rules": {key: tags[key][:120] for key in ("access", "vehicle", "motor_vehicle", "motorcar") if key in tags}})
            if len(rows) > MAX_ROADS:
                raise ValueError("The OSM graph exceeds the 30,000-road bound")
    restrictions = []
    for relation_id, (members, tags) in relations.items():
        from_way = next((m["ref"] for m in members if m["role"] == "from" and m["type"] == "way"), None)
        to_way = next((m["ref"] for m in members if m["role"] == "to" and m["type"] == "way"), None)
        via = next((m for m in members if m["role"] == "via"), None)
        if (from_way in ways and to_way in ways and via and
                not tags.get("restriction:conditional") and
                tags.get("restriction", "").startswith(("no_", "only_"))):
            restrictions.append({"id": relation_id, "kind": tags["restriction"], "from_way_id": from_way,
                                 "to_way_id": to_way, "via_node_id": via["ref"] if via["type"] == "node" else "",
                                 "via_way_id": via["ref"] if via["type"] == "way" else "",
                                 "except": tags.get("except", "")[:120]})
    digest = hashlib.sha256("".join(f"{box}:{value}" for box, value in sorted(hashes)).encode()).hexdigest()
    return {"roads": rows, "turn_restrictions": restrictions, "source": {"bbox": list(bbox_for(geo, width, height)),
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "sha256": digest, "provider": provider, "import_revision": 10, "tiles": len(tiles),
            "ways": len(ways), "roads": len(rows), "access_excluded_ways": len(access_excluded),
            "boundary_splits": boundary_splits}}


def _build(geo, width, height, include_environment, bbox):
    from simulator_osm_local_extract import extract
    local = extract(bbox)
    tiles, metadata = local if local is not None else (download(bbox), None)
    provider = "geofabrik-slovakia-pbf" if metadata is not None else "openstreetmap-api-v0.6"
    result = graph_from_xml(tiles, geo, width, height, provider)
    if metadata is not None:
        result["source"]["retrieved_at"] = metadata["source_data_utc"]
        result["source"]["dataset_sha256"] = metadata["sha256"]
    fetched = []
    if metadata is None:
        for box, _ in tiles:
            try:
                fetched.append(json.loads(_tile_paths(box)[1].read_text())["fetched_at"])
            except (OSError, ValueError, KeyError):
                pass
    if fetched:
        result["source"]["retrieved_at"] = min(fetched)
    if include_environment:
        from simulator_local_environment import import_environment
        result['environment'] = import_environment(tiles, geo, width, height, provider=provider)
        if metadata is not None:
            result['environment']['sources']['osm']['dataset_sha256'] = metadata['sha256']
    return result


def load(geo, *, include_environment=False, extent=2000, height=None):
    width, height = dimensions(extent, height)
    bbox = bbox_for(geo, width, height)
    from simulator_osm_local_extract import PINNED_SHA256, _source, covers
    if not covers(bbox):
        return _build(geo, width, height, include_environment, bbox)

    # Cache the complete derived cutout, including the building/terrain model.
    # The source PBF is still verified before accepting a cached derivative.
    _source()
    code = b''.join(Path(__file__).with_name(name).read_bytes() for name in
                    ('simulator_osm_road_graph.py', 'simulator_osm_local_extract.py', 'simulator_local_environment.py'))
    key = hashlib.sha256(json.dumps({'geo': geo, 'width': width, 'height': height,
                                     'environment': include_environment, 'pbf': PINNED_SHA256},
                                    sort_keys=True, separators=(',', ':')).encode() + code).hexdigest()
    path = CACHE_DIR / f'graph-{key}.json.gz'
    with _LOCAL_RESULT_LOCK:
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as stream:
                cached = json.load(stream)
            if (cached['source']['provider'] == 'geofabrik-slovakia-pbf' and
                    cached['source']['dataset_sha256'] == PINNED_SHA256 and
                    cached['source'].get('import_revision') == 10 and
                    ('environment' in cached) == include_environment):
                return cached
        except (OSError, ValueError, KeyError, EOFError):
            pass
        result = _build(geo, width, height, include_environment, bbox)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=CACHE_DIR, prefix='.graph-', suffix='.gz', delete=False) as stream:
            temporary = Path(stream.name)
            try:
                with gzip.open(stream, 'wt', encoding='utf-8', compresslevel=3) as packed:
                    json.dump(result, packed, separators=(',', ':'))
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        return result
