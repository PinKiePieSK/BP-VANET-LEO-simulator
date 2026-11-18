# Verejne doložené minimálne elevácie a ďalšie fyzikálne profily Starlinku, Iridia a Globalstaru.
# Výsledkom je kandidátska geometrická obálka, nie potvrdená dostupnosť služby operátora.
"""Public-evidence physical *possibility* envelopes for simulator satellite terminals.

This module never infers an active operator beam, receive threshold or service.
The return values distinguish horizon, published terminal/beam constraints and
the unknown satellite beam assignment. Frequencies yield free-space loss only.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

LIGHT_M_S = 299_792_458.0
WGS84_A_KM = 6378.137
WGS84_E2 = 6.69437999014e-3

# Each profile is tied to one named user terminal. A zero minimum means only
# that no defensible product-specific lower bound was found, not that a link
# works at zero elevation. The Starlink 25-degree bound is the published Gen2
# Ku user-link design condition below 62 degrees latitude in FCC 22-91.
PROFILES = {
    "iridium-NEXT": {
        "terminal": "Iridium Certus 9770 / Certus 100",
        "user_uplink_hz": 1.62125e9, "user_downlink_hz": 1.62125e9,
        "minimum_elevation_deg": 0.0, "terminal_zenith_limit_deg": 90.0,
        "satellite_beam_model": "48-beam published layout; current activation unknown",
        "evidence_level": "geometric envelope only; satellite gain contour unquantified",
        "sources": ["https://www.iridium.com/products/iridium-certus-9770",
                    "https://docs.fcc.gov/public/attachments/DA-16-875A1.pdf"],
    },
    "globalstar": {
        "terminal": "Globalstar RM200M",
        "user_uplink_hz": 1.615e9, "user_downlink_hz": 2.49175e9,
        "minimum_elevation_deg": 0.0, "terminal_zenith_limit_deg": 90.0,
        "satellite_beam_model": "generation-specific multi-beam; current contour unknown",
        "evidence_level": "geometric envelope only; patch gain and beam contour unquantified",
        "sources": ["https://www.globalstar.com/getmedia/a4613a3c-9086-4cdf-b2c2-12cc2c3df169/rm200m-eu-type-certification.pdf",
                    "https://investors.globalstar.com/static-files/ca62cad1-878b-4328-9b4a-91c4f68b8c8b"],
    },
    "starlink": {
        "terminal": "Starlink Flat High Performance / Performance Gen 2",
        "user_uplink_hz": 14.25e9, "user_downlink_hz": 11.7e9,
        "minimum_elevation_deg": 25.0, "terminal_zenith_limit_deg": 70.0,
        "satellite_beam_model": "electronically steerable Gen2 Ku user-beam envelope",
        "evidence_level": "published Gen2/FHP bounds; active beam and satellite generation unverified",
        "sources": ["https://starlink.com/public-files/specification_sheet_flat_high_performance.pdf",
                    "https://docs.fcc.gov/public/attachments/FCC-22-91A1.pdf"],
    },
}


# Každá pomenovaná služba má verejný fyzikálny profil terminálu a minimálnej elevácie. Tieto čísla
# určujú kandidátsku obálku; komerčný aktívny lúč a prijatie služby z nich nemožno vyvodiť.
def profile(group: str) -> dict:
    """Serializable profile metadata, including its limitations and sources."""
    if group not in PROFILES:
        raise ValueError(f"Unsupported physical coverage group: {group}")
    return dict(PROFILES[group])


def direct_link_policy(group: str, generic: dict) -> dict:
    """Use the named terminal band and public field of view in the native gate.

    Doppler compensation and steering speed remain declared research values.
    An omni/unknown patch pattern has no invented narrow pointing penalty.
    """
    spec = profile(group)
    result = dict(generic)
    result["rf_hz"] = spec["user_uplink_hz"]
    result["zenith_cone_deg"] = min(90.0-spec["minimum_elevation_deg"],
                                     spec["terminal_zenith_limit_deg"])
    result["beam_half_angle_deg"] = 5.0 if group == "starlink" else 90.0
    return result


# Prevádza WGS84 šírku, dĺžku a výšku pozemného bodu na ECEF v kilometroch. Rovnaké jednotky musí
# mať vektor družice; inak by vzdialenosť a uhol boli nesprávne.
def site_ecef_km(site: Sequence[float]) -> np.ndarray:
    if len(site) != 3 or not all(math.isfinite(float(x)) for x in site):
        raise ValueError("Physical coverage site needs finite WGS84 lat/lon/height")
    lat, lon, height = map(float, site)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and -500 <= height <= 9000):
        raise ValueError("Physical coverage site outside WGS84 bounds")
    phi, lam = math.radians(lat), math.radians(lon)
    s, c = math.sin(phi), math.cos(phi)
    n = WGS84_A_KM / math.sqrt(1-WGS84_E2*s*s)
    h = height/1000.0
    return np.array([(n+h)*c*math.cos(lam), (n+h)*c*math.sin(lam),
                     (n*(1-WGS84_E2)+h)*s], dtype=float)


# Z geometrie terminál–družica vypočíta eleváciu a porovná ju s verejnou obálkou. Výsledok je
# fyzikálny kandidát, nie potvrdený IP prenos.
def assess(group: str, site: Sequence[float], satellite_xyz_km: Sequence[float]) -> dict:
    """LOS and public envelope at one endpoint; no proprietary beam inference."""
    spec = profile(group)
    sat = np.asarray(satellite_xyz_km, dtype=float)
    if sat.shape != (3,) or not np.isfinite(sat).all() or np.linalg.norm(sat) < 6400:
        raise ValueError("Invalid satellite ECEF position")
    ground = site_ecef_km(site)
    lat, lon = map(math.radians, site[:2])
    up = np.array([math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat)])
    sight = sat-ground
    distance = float(np.linalg.norm(sight))
    elevation = math.degrees(math.asin(float(np.clip(np.dot(sight, up)/distance, -1, 1))))
    zenith = 90.0-elevation
    to_ground = ground-sat
    to_nadir = -sat
    off_nadir = math.degrees(math.acos(float(np.clip(np.dot(to_ground, to_nadir)/
                                                  (np.linalg.norm(to_ground)*np.linalg.norm(to_nadir)), -1, 1))))
    horizon = elevation >= 0.0
    envelope = (horizon and elevation >= spec["minimum_elevation_deg"] and
                zenith <= spec["terminal_zenith_limit_deg"])
    loss = lambda frequency: 20*math.log10(4*math.pi*distance*1000*frequency/LIGHT_M_S)
    return {
        "horizon": horizon, "public_envelope": envelope,
        "classification": "potential_unverified_beam" if envelope else
                          "below_horizon" if not horizon else "outside_published_envelope",
        "elevation_deg": round(elevation, 4), "off_nadir_deg": round(off_nadir, 4),
        "terminal_zenith_deg": round(zenith, 4), "range_km": round(distance, 4),
        "free_space_loss_uplink_db": round(loss(spec["user_uplink_hz"]), 4),
        "free_space_loss_downlink_db": round(loss(spec["user_downlink_hz"]), 4),
        "link_margin_known": False,
    }


# Kontroluje súčasný výhľad terminálu aj brány na tú istú družicu. Pre dvojbodovú službu nestačí,
# že satelit vidí iba RSU; brána musí mať použiteľnú geometriu tiež.
def assess_pair(group: str, terminal: Sequence[float], gateway: Sequence[float],
                satellite_xyz_km: Sequence[float]) -> dict:
    """Keep the two physical legs separate, especially for bent-pipe Globalstar."""
    user = assess(group, terminal, satellite_xyz_km)
    # The feeder dish, band and elevation mask are not the user terminal's.
    # Reuse only the independently valid geometric quantities here.
    geometry = assess(group, gateway, satellite_xyz_km)
    feeder = {key: geometry[key] for key in
              ('horizon', 'elevation_deg', 'off_nadir_deg', 'range_km')}
    return {"user": user, "feeder_geometry": feeder,
            "same_satellite_two_leg_possible": user["public_envelope"] and feeder["horizon"],
            "claim_boundary": "gateway is only a geometric endpoint; its identity, dish and band are unverified"}
