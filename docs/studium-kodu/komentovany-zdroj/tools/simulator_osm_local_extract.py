# Číta lokálny výrez OpenStreetMap zo stiahnutého PBF, keď je k dispozícii. Chráni editor pred
# limitmi verejného OSM API pri slovenských lokalitách.
"""Read bounded Slovak OSM cutouts from the pinned external Geofabrik extract."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from xml.etree import ElementTree as ET

WORKSPACE = Path(os.environ.get("BP_SIM_WORKSPACE", Path.home() / "Desktop/BP-Simulator-Workspace"))
DATA_DIR = WORKSPACE / "imports/osm"
CACHE_DIR = WORKSPACE / "cache/osm"
PBF = DATA_DIR / "slovakia-261031.osm.pbf"
MANIFEST = DATA_DIR / "slovakia-261031.manifest.json"
POLYGON = DATA_DIR / "slovakia.poly"
PINNED_SHA256 = "4af3affa32fdc294ade673b409a0dc7f5c6c908875776ff06530d7bd923a9185"
MAX_XML_BYTES = 150_000_000
_LOCK = threading.Lock()
_VERIFIED = None


def _ring(path):
    lines = path.read_text().splitlines()
    rings, ring = [], []
    for line in lines[1:]:
        value = line.strip()
        if value == "END":
            if ring:
                rings.append(ring)
                ring = []
            continue
        parts = value.split()
        if len(parts) == 1:
            continue
        if len(parts) == 2:
            ring.append((float(parts[0]), float(parts[1])))
    if len(rings) != 1 or len(rings[0]) < 4:
        raise ValueError("Unsupported Slovakia polygon format")
    return rings[0]


def _inside(point, ring):
    x, y = point
    odd = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            odd = not odd
    return odd


def _boundary_touches(bbox, ring):
    west, south, east, north = bbox
    for a, b in zip(ring, ring[1:] + ring[:1]):
        # A boundary vertex inside the requested box or a boundary edge
        # crossing it means the country extract could omit nearby features.
        if west <= a[0] <= east and south <= a[1] <= north:
            return True
        dx, dy = b[0] - a[0], b[1] - a[1]
        for x in (west, east):
            if dx:
                t = (x - a[0]) / dx
                if 0 <= t <= 1 and south <= a[1] + t * dy <= north:
                    return True
        for y in (south, north):
            if dy:
                t = (y - a[1]) / dy
                if 0 <= t <= 1 and west <= a[0] + t * dx <= east:
                    return True
    return False


# Testuje, či lokálny OSM výrez pokrýva požadovanú oblasť. Bez tejto kontroly by čiastočný súbor
# ciest mohol vyzerať ako úplná mapa.
def covers(bbox):
    if not (PBF.is_file() and MANIFEST.is_file() and POLYGON.is_file()):
        return False
    ring = _ring(POLYGON)
    west, south, east, north = bbox
    return (all(_inside(p, ring) for p in ((west, south), (west, north), (east, south), (east, north)))
            and not _boundary_touches(bbox, ring))


def _source():
    global _VERIFIED
    meta = json.loads(MANIFEST.read_text())
    expected = meta.get("sha256")
    if (meta.get("file") != PBF.name or meta.get("size_bytes") != PBF.stat().st_size or
            expected != PINNED_SHA256):
        raise ValueError("Slovak OSM PBF does not match its manifest")
    stamp = (PBF.stat().st_size, PBF.stat().st_mtime_ns, expected)
    if _VERIFIED != stamp:
        digest = hashlib.sha256()
        with PBF.open("rb") as stream:
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError("Slovak OSM PBF checksum mismatch")
        _VERIFIED = stamp
    return meta


def _osmium():
    command = shutil.which("osmium")
    if command:
        return command
    local = WORKSPACE / "tools/osmium/usr/bin/osmium"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    raise ValueError("Local Slovakia map needs osmium-tool; run the portable setup again")


# Zo slovenského lokálneho PBF vyberá len aktuálny výrez ciest a budov. Výsledný výrez sa používa
# ako vstup editora a následne SUMO/geometrie.
def extract(bbox):
    """Return one XML tile and its pinned PBF metadata; never use the network."""
    if not covers(bbox):
        return None
    with _LOCK:
        meta = _source()
        key = hashlib.sha256((PBF.name + ":" + meta["sha256"] + ":" +
                              json.dumps(bbox, separators=(",", ":"))).encode()).hexdigest()
        path = CACHE_DIR / f"slovakia-{key}.osm"
        if path.is_file() and 0 < path.stat().st_size <= MAX_XML_BYTES:
            raw = path.read_bytes()
            try:
                if ET.fromstring(raw).tag == "osm":
                    return [(bbox, raw)], meta
            except ET.ParseError:
                pass
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=CACHE_DIR, prefix=".slovakia-", suffix=".osm", delete=False) as stream:
            temporary = Path(stream.name)
        try:
            # osmium refuses to overwrite even an empty output placeholder.
            temporary.unlink()
            command = [_osmium(), "extract", "--bbox", ",".join(map(str, bbox)),
                       "--strategy", "complete_ways", "--output-format", "osm",
                       "--output", str(temporary), str(PBF)]
            run = subprocess.run(command, capture_output=True, text=True, timeout=240)
            if run.returncode:
                raise ValueError(f"Local Slovakia OSM extraction failed: {run.stderr[-300:]}")
            if not 0 < temporary.stat().st_size <= MAX_XML_BYTES:
                raise ValueError("Local Slovakia OSM cutout exceeds the 150 MB limit")
            raw = temporary.read_bytes()
            if ET.fromstring(raw).tag != "osm":
                raise ValueError("Local Slovakia OSM extract has no osm root")
            os.replace(temporary, path)
            return [(bbox, raw)], meta
        finally:
            temporary.unlink(missing_ok=True)
