"""Shared paths, file integrity and station input for the current simulator."""
from __future__ import annotations

import csv
import hashlib
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = ROOT / "vendor/ns-3.38-ocb-eval"
VANETZA = ROOT / "build/vanetza-v26.06"
VANETZA_BUILD = ROOT / "build/vanetza-v26.06-cmake"
OPENSSL = ROOT / "build/openssl-dev-local/usr/include"


def repair_generated_ns3_headers() -> int:
    """Relocate generated ns-3 include wrappers after a portable runtime is moved."""
    folder = CHECKOUT / "build/include/ns3"
    if not folder.is_dir():
        raise RuntimeError(f"ns-3 generated headers absent: {folder}")
    marker = f"/vendor/{CHECKOUT.name}/"
    repaired = 0
    for wrapper in folder.glob("*.h"):
        contents = wrapper.read_text()
        match = re.match(r'^#include "(/[^"\n]+)"', contents)
        if not match or Path(match.group(1)).is_file():
            continue
        old = match.group(1)
        if marker not in old:
            raise RuntimeError(f"Unknown generated ns-3 header path: {wrapper}: {old}")
        candidate = CHECKOUT / old.split(marker, 1)[1]
        if not candidate.is_file() or not candidate.resolve().is_relative_to(CHECKOUT.resolve()):
            raise RuntimeError(f"Missing ns-3 source for generated header {wrapper}: {candidate}")
        wrapper.write_text(contents.replace(old, str(candidate), 1))
        repaired += 1
    return repaired


def native_library_environment() -> dict[str, str]:
    """Locate ns-3 shared libraries in the active runtime after relocation."""
    environment = os.environ.copy()
    active = str(CHECKOUT / "build/lib")
    previous = environment.get("LD_LIBRARY_PATH")
    environment["LD_LIBRARY_PATH"] = active + (f":{previous}" if previous else "")
    return environment

CAM_FIELDS = ("node_id", "station_id", "kind", "index", "time_us", "utc", "x_m", "y_m",
              "latitude_e7", "longitude_e7", "altitude_cm", "speed_cmps",
              "heading_decideg", "generation_delta_ms", "acceleration_dmps2",
              "yaw_rate_cdegps", "curvature_1e4", "vehicle_length_dm",
              "vehicle_width_dm", "exterior_lights_bits")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def put_exact(path: Path, contents: str) -> None:
    """Do not silently replace a generated SNS-3 input with different bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != contents:
        raise RuntimeError(f"existing generated input differs: {path}")
    path.write_text(contents)


def ut_site(waypoint: Path, rsu_id: str) -> tuple[float, float, float]:
    """Read the stationary WGS84 position assigned to one RSU terminal."""
    with waypoint.open(newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row["node_id"] == rsu_id]
    if not rows or len({(row["latitude_e7"], row["longitude_e7"], row["altitude_cm"])
                        for row in rows}) != 1:
        raise ValueError("selected RSU/UT must be stationary in every CAM sample")
    return (int(rows[0]["latitude_e7"]) / 1e7,
            int(rows[0]["longitude_e7"]) / 1e7,
            int(rows[0]["altitude_cm"]) / 100)
