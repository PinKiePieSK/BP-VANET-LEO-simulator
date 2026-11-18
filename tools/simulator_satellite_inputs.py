#!/usr/bin/env python3
"""Prepare pinned SNS-3 orbit, ISL and diagnostic antenna input files."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

from astropy.time import Time
from sgp4.api import Satrec

from simulator_platform import put_exact, sha
from simulator_orbits import load_orbits, ns3_sphere_position, sat_ecef
from simulator_tle_catalog import native_ids, tle_lines, manifest_mapping

PATTERN = "BpTwoLeoIslPinned20261022"


def generate(checkout: Path, stage: Path, topology: dict, gain_dbi: float) -> dict:
    if (type(gain_dbi) not in (int, float) or not math.isfinite(gain_dbi) or
            not -10 <= gain_dbi <= 50):
        raise ValueError("unsupported: satellite transport diagnostic beam gain outside sensitivity range")
    catalogs = topology["catalog_ids"]
    edges = topology["isls"]
    serving = topology.get("initial_serving_sat", 0)
    if (not isinstance(catalogs, list) or not catalogs or len(catalogs) != len(set(catalogs)) or
            any(type(x) is not int or x <= 0 or x > 999999 for x in catalogs) or
            not isinstance(edges, list) or
            any(not isinstance(x, list) or len(x) != 2 or
                any(type(v) is not int or not 0 <= v < len(catalogs) for v in x) or
                x[0] == x[1] for x in edges) or
            len({tuple(sorted(x)) for x in edges}) != len(edges) or
            type(serving) is not int or not 0 <= serving < len(catalogs)):
        raise ValueError("invalid handover SNS-3 orbit pool/ISL graph")
    adjacency = [set() for _ in catalogs]
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    reached, pending = {serving}, [serving]
    while pending:
        for neighbor in adjacency[pending.pop()] - reached:
            reached.add(neighbor)
            pending.append(neighbor)
    if len(reached) != len(catalogs):
        raise ValueError("unsupported: disconnected handover SNS-3 satellite pool")
    utc = topology["utc_origin"]
    moment = datetime.fromisoformat(utc.replace("Z", "+00:00"))
    if moment.tzinfo is None or moment.utcoffset().total_seconds() != 0:
        raise ValueError("handover UTC origin must be explicit UTC")
    orbit_config = json.loads((stage / "orbit-reference.json").read_text())
    orbit_config["utc_origin"] = utc
    objects, provenance = load_orbits(orbit_config)
    by_id = {x[0]: x for x in objects}
    if not set(catalogs) <= set(by_id):
        raise ValueError("handover orbit object absent or too old at UTC origin")
    tle = [str(len(catalogs))]
    reconstruction = {}
    native = native_ids(catalogs)
    for index, catalog in enumerate(catalogs):
        record = by_id[catalog]
        sat = record[3]
        line1, line2 = tle_lines(record, native[catalog])
        restored = Satrec.twoline2rv(line1, line2)
        t = Time(moment, scale="utc")
        e1, p1, _ = sat.sgp4(t.jd1, t.jd2)
        e2, p2, _ = restored.sgp4(t.jd1, t.jd2)
        difference = math.dist(p1, p2) * 1000
        if e1 or e2 or difference >= 2:
            raise ValueError(f"handover OMM/TLE reconstruction failed for {catalog}")
        reconstruction[str(catalog)] = difference
        tle.extend((f"{index} CATALOG {catalog}", line1, line2))
    aliases = manifest_mapping(catalogs)
    position = ns3_sphere_position(sat_ecef(by_id[catalogs[serving]][3], utc.removesuffix("Z")))
    key = hashlib.sha256(json.dumps({"topology": topology, "gain_dbi": gain_dbi,
                                     "reference_position": position},
                                    sort_keys=True).encode()).hexdigest()[:16]
    name = "bp-u4-" + key
    files = {
        "tles.txt": "\n".join(tle) + "\n",
        "isls.txt": str(len(edges)) + "\n" + "".join(f"{a} {b}\n" for a, b in edges),
        "ut_positions.txt": "{:.7f} {:.7f} {:.2f}\n".format(*topology["ut"]),
        "gw_positions.txt": "{:.7f} {:.7f} {:.2f}\n".format(*topology["gateway"]),
        "ut_sat_ids.txt": f"{serving}\n",
    }
    archive = stage / "inputs" / name
    archive.mkdir(parents=True)
    for filename, contents in files.items():
        put_exact(checkout / "contrib/satellite/data/constellations" / name / filename, contents)
        (archive / filename).write_text(contents)
    pattern_name = "BpU4" + key
    pattern = checkout / "contrib/satellite/data/antennapatterns" / pattern_name
    put_exact(pattern / "GeoPos.in", "{:.12f} {:.12f} {:.6f}\n".format(*position))
    source_pattern = checkout / "contrib/satellite/data/antennapatterns" / PATTERN / "BpIridiumTwoSat_30.txt"
    original = source_pattern.read_text()
    if original.count("17.00000000") != 11011:
        raise ValueError("satellite transport diagnostic pattern shape changed")
    put_exact(pattern / "BpIridiumTwoSat_30.txt",
              original.replace("17.00000000", f"{gain_dbi:.8f}"))
    pattern_archive = stage / "inputs" / pattern_name
    pattern_archive.mkdir(parents=True)
    shutil.copy2(pattern / "GeoPos.in", pattern_archive / "GeoPos.in")
    shutil.copy2(pattern / "BpIridiumTwoSat_30.txt", pattern_archive / "BpIridiumTwoSat_30.txt")
    hashes = {str(p.relative_to(stage / "inputs")): sha(p) for p in sorted((stage / "inputs").rglob("*")) if p.is_file()}
    return {"scenario": name, "pattern": pattern_name, "sha256": hashes,
            "orbit_provenance": provenance, "tle_reconstruction_m": reconstruction,
            "catalog_ids": catalogs, "isls": edges, "gain_dbi": gain_dbi,
            **({"native_tle_aliases": aliases} if aliases else {})}
