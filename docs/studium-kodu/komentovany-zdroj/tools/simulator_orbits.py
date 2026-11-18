# Načítanie pripnutého orbitálneho archívu, výpočet polohy družíc a kontrola geometrického
# výhľadu.
"""Pinned orbital inputs and geometric predictions used by the current simulator.

The catalogue and visibility test only select candidates; SNS-3 decides packet delivery.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import CartesianRepresentation, EarthLocation, ITRS, TEME
from astropy.time import Time
from astropy.utils import iers
from sgp4 import omm
from sgp4.api import Satrec, SatrecArray, WGS72

from simulator_platform import ROOT

EARTH_KM = 6378.137
NS3_SPHERE_RADIUS_KM = EARTH_KM


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC must end in Z")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.astimezone(timezone.utc)


def stamp(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def site(value: dict, label: str) -> tuple[float, float, float]:
    if set(value) != {"lat_deg", "lon_deg", "height_m", "status"} or value["status"] != "proxy":
        raise ValueError(f"{label}: explicit proxy WGS84 site required")
    lat, lon, height = (value[key] for key in ("lat_deg", "lon_deg", "height_m"))
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
           for x in (lat, lon, height)) or not (-90 <= lat <= 90 and -180 <= lon <= 180 and -500 <= height <= 9000):
        raise ValueError(f"{label}: invalid WGS84 range")
    return float(lat), float(lon), float(height)


# Najprv overí kontrolné súčty OMM archívu a vek elementov voči UTC pokusu. Satelity s chýbajúcim
# alebo zastaraným záznamom do výberu nevstúpia.
def load_orbits(config: dict) -> tuple[list, dict]:
    folder = ROOT / config["snapshot"]["path"]
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("schema") != 1 or manifest.get("upstream") != "CelesTrak GP":
        raise ValueError("unsupported orbit manifest")
    group = manifest["groups"][config["group"]]
    archive = folder / group["file"]
    if digest(archive) != group["gzip_sha256"]:
        raise ValueError("compressed orbit hash mismatch")
    raw = gzip.decompress(archive.read_bytes())
    if hashlib.sha256(raw).hexdigest() != group["raw_sha256"]:
        raise ValueError("raw orbit hash mismatch")
    records = json.loads(raw)
    if len(records) != group["objects"]:
        raise ValueError("orbit object count mismatch")
    origin = utc(config["utc_origin"])
    end = origin + timedelta(seconds=config["duration_s"])
    seen, eligible = set(), []
    for row in records:
        catalog = int(row["NORAD_CAT_ID"])
        if catalog in seen:
            raise ValueError(f"duplicate catalog ID {catalog}")
        seen.add(catalog)
        epoch = utc(row["EPOCH"] if row["EPOCH"].endswith("Z") else row["EPOCH"] + "Z")
        if epoch > origin or (end - epoch).total_seconds() > config["max_age_h"] * 3600:
            continue
        rec = Satrec()
        omm.initialize(rec, row, gravconst=WGS72)
        eligible.append((catalog, epoch, row, rec))
    eligible.sort(key=lambda item: item[0])
    if not eligible:
        raise ValueError("no age-eligible OMM objects")
    if config["pair"] != "auto" and not set(config["pair"]) <= {item[0] for item in eligible}:
        raise ValueError("requested catalog object missing or too old")
    return eligible, {"snapshot_manifest_sha256": digest(folder / "manifest.json"),
                      "orbit_gzip_sha256": group["gzip_sha256"],
                      "orbit_raw_sha256": group["raw_sha256"]}


def clearance(a: np.ndarray, b: np.ndarray) -> float:
    delta = b - a
    fraction = float(np.clip(-(a @ delta) / (delta @ delta), 0, 1))
    return float(np.linalg.norm(a + fraction * delta) - EARTH_KM)


# Pevné historické pokusy používajú pribalenú tabuľku orientácie Zeme aj po prekročení 30 dní od
# jej predikcie. Automatické sťahovanie je vypnuté a čas mimo rozsahu tabuľky sa odmietne; hash
# tabuľky zostáva v pôvode výsledku.
def pinned_eop(time: Time | None = None):
    """Use the archived EOP table for fixed experiment dates, even as it ages."""
    iers.conf.auto_download = False
    iers.conf.auto_max_age = None
    eop = iers.IERS_Auto.open()
    if time is not None:
        _, ut_status = eop.ut1_utc(time, return_status=True)
        _, _, pm_status = eop.pm_xy(time, return_status=True)
        if int(ut_status) not in (0, 1, 2) or int(pm_status) not in (0, 1, 2):
            raise ValueError(f"EOP unavailable at {time.isot}")
    return eop


# SGP4 vypočíta polohy pre časové vzorky. Prevod TEME → ITRS a topocentrická elevácia určí
# geometrických kandidátov pre RSU a bránu; výsledok sám nedokazuje doručenie paketu.
def sample(config: dict, objects: list) -> tuple[list[dict], str]:
    eop = pinned_eop()
    eop_hash = digest(Path(eop.meta["data_path"]))
    sats = SatrecArray([row[3] for row in objects])
    ut_station, gw_station = station_vectors(site(config["ut"], "UT")), station_vectors(site(config["gateway"], "gateway"))
    times = [utc(config["utc_origin"]) + timedelta(seconds=config["sample_s"] * n)
             for n in range(round(config["duration_s"] / config["sample_s"]) + 1)]
    out = []
    for instant in times:
        t = Time(instant, scale="utc")
        _, ustat = eop.ut1_utc(t, return_status=True)
        _, _, pstat = eop.pm_xy(t, return_status=True)
        if int(ustat) not in (0, 1, 2) or int(pstat) not in (0, 1, 2):
            raise ValueError(f"EOP unavailable at {stamp(instant)}")
        errors, positions, _ = sats.sgp4(np.array([t.jd1]), np.array([t.jd2]))
        if np.any(errors):
            raise ValueError(f"SGP4 propagation failed at {stamp(instant)}")
        xyz = TEME(CartesianRepresentation(positions[:, 0, :].T * u.km), obstime=t).transform_to(ITRS(obstime=t)).cartesian.xyz.to_value(u.km).T
        ut_e, _ = view(xyz, ut_station)
        gw_e, _ = view(xyz, gw_station)
        mask = config["mask_deg"]
        ut_ids = [objects[i][0] for i in np.flatnonzero(ut_e >= mask)]
        gw_ids = [objects[i][0] for i in np.flatnonzero(gw_e >= mask)]
        out.append({"utc": stamp(instant), "elapsed_s": round((instant - times[0]).total_seconds(), 6),
                    "ut_visible_ids": ut_ids, "gw_visible_ids": gw_ids,
                    "elevation_deg": {str(row[0]): [round(float(ut_e[i]), 6), round(float(gw_e[i]), 6)]
                                      for i, row in enumerate(objects)},
                    "xyz_km": xyz})
    return out, eop_hash


def station_vectors(location):
    lat, lon, height = location
    station = EarthLocation.from_geodetic(lon * u.deg, lat * u.deg, height * u.m)
    xyz = np.array([x.to_value(u.km) for x in station.to_geocentric()])
    phi, lam = math.radians(lat), math.radians(lon)
    up = np.array([math.cos(phi) * math.cos(lam),
                   math.cos(phi) * math.sin(lam), math.sin(phi)])
    return xyz, up


def view(xyz_sat, station):
    origin, up = station
    delta = xyz_sat - origin
    distance = np.linalg.norm(delta, axis=1)
    elevation = np.degrees(np.arcsin(np.clip(delta @ up / distance, -1, 1)))
    if not (np.all(np.isfinite(distance)) and np.all(np.isfinite(elevation))):
        raise ValueError("Non-finite topocentric geometry")
    return elevation, distance


# Táto funkcia počíta polohu jedného orbitálneho objektu v súradniciach Zeme. Používa sa pri
# priebežnej kontrole výhľadu a pri tvorbe natívneho satelitného vstupu.
def sat_ecef(sat, utc):
    t = Time(utc, scale="utc")
    pinned_eop(t)
    error, xyz, _ = sat.sgp4(t.jd1, t.jd2)
    if error:
        raise RuntimeError(f"SGP4 failed at {utc}: {error}")
    frame = TEME(CartesianRepresentation(np.array(xyz) * u.km), obstime=t)
    return np.array(frame.transform_to(ITRS(obstime=t)).cartesian.xyz.to_value(u.km))


def site_ecef(site):
    # SNS-3 3.38 GeoCoordinate(lat, lon, alt) defaults to SPHERE.
    lat, lon = math.radians(site[0]), math.radians(site[1])
    radius = NS3_SPHERE_RADIUS_KM + site[2] / 1000.0
    return radius * np.array([math.cos(lat) * math.cos(lon),
                              math.cos(lat) * math.sin(lon), math.sin(lat)])


# SNS-3 3.38 očakáva sférickú polohu GeoCoordinate. Z ECEF vektora sa preto odvodí šírka, dĺžka a
# výška nad sférickým polomerom, ktorý používa model.
def ns3_sphere_position(ecef):
    radius = float(np.linalg.norm(ecef))
    return (math.degrees(math.asin(ecef[2] / radius)),
            math.degrees(math.atan2(ecef[1], ecef[0])),
            (radius - NS3_SPHERE_RADIUS_KM) * 1000.0)
