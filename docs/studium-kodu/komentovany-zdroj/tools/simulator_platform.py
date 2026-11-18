# Spoločné cesty k projektu a runtime, kontrolné súčty súborov, bezpečný zápis generovaných
# vstupov a poloha terminálu RSU.
"""Shared paths, file integrity and station input for the current simulator."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = ROOT / "vendor/ns-3.38-ocb-eval"
VANETZA = ROOT / "build/vanetza-v26.06"
VANETZA_BUILD = ROOT / "build/vanetza-v26.06-cmake"
OPENSSL = ROOT / "build/openssl-dev-local/usr/include"

# Toto je jednotná hlavička waypoint CSV medzi SUMO adaptérom a oboma ns-3 enginmi. Jednotky v
# názvoch polí bránia tichej zámene stupňov, centimetrov a pevnej desatinnej reprezentácie ETSI.
CAM_FIELDS = ("node_id", "station_id", "kind", "index", "time_us", "utc", "x_m", "y_m",
              "latitude_e7", "longitude_e7", "altitude_cm", "speed_cmps",
              "heading_decideg", "generation_delta_ms", "acceleration_dmps2",
              "yaw_rate_cdegps", "curvature_1e4", "vehicle_length_dm",
              "vehicle_width_dm", "exterior_lights_bits")


# Hash sa počíta po blokoch, aby aj veľké vstupy a výsledky bolo možné overiť bez načítania celého
# súboru do pamäte.
def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# Vstup vytvorený pre SNS-3 sa nesmie potichu nahradiť inými bajtmi. Ak sa zmení fyzikálna poloha
# alebo iný obsah, generátor má vytvoriť novú identitu vstupu.
def put_exact(path: Path, contents: str) -> None:
    """Do not silently replace a generated SNS-3 input with different bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != contents:
        raise RuntimeError(f"existing generated input differs: {path}")
    path.write_text(contents)


# Každý satelitný terminál preberá polohu svojej RSU z waypointov. Kontrola vyžaduje rovnaké WGS84
# súradnice vo všetkých vzorkách.
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
