# Validuje náklon a azimut terminálu proti zvolenému fyzikálnemu profilu. Tieto predpoklady
# opisujú výskumný model, nie skutočnú anténu operátora.
"""Published terminal field of view with an explicit, assumed mounting direction.

Only Starlink Flat High Performance has a quantified field of view here. The
Iridium Certus 9770 uses an external passive omni antenna; the Globalstar
RM200M has a ceramic patch but no public installed gain contour. Neither is
given an invented orientation cutoff. Satellite beam assignment is unknown.
"""
from __future__ import annotations

import math
import numpy as np

from simulator_physical_coverage import site_ecef_km

STARLINK_HALF_FOV_DEG = 70.0
EVIDENCE = {
    'starlink': {
        'terminal': 'Flat High Performance / Performance Gen 2',
        'antenna': 'electronically steered phased array',
        'public_fov_deg': 140.0,
        'installed_boresight': 'scenario assumption; not inferred from orbit or vehicle heading alone',
        'source': 'https://starlink.com/public-files/specification_sheet_flat_high_performance.pdf',
    },
    'iridium-NEXT': {
        'terminal': 'Certus 9770',
        'antenna': 'external passive omnidirectional antenna',
        'public_fov_deg': None,
        'installed_boresight': 'no directional cutoff applied; installed gain pattern unknown',
        'source': 'https://www.iridium.com/products/iridium-certus-9770',
    },
    'globalstar': {
        'terminal': 'RM200M',
        'antenna': 'ceramic patch',
        'public_fov_deg': None,
        'installed_boresight': 'no directional cutoff applied; installed gain pattern unknown',
        'source': 'https://www.globalstar.com/getmedia/a4613a3c-9086-4cdf-b2c2-12cc2c3df169/rm200m-eu-type-certification.pdf',
    },
}


# Kontroluje rozsah deklarovanej montáže antény pre každú RSU. Nesprávna orientácia alebo mimo
# rozsahu zadaný uhol sa odmieta pred behom.
def validate_mounts(group: str, mounts: object, kinds: dict[str, str]) -> dict:
    """Validate mount angles; an omitted mount points toward zenith."""
    if group not in EVIDENCE or type(mounts) is not dict:
        raise ValueError('Neplatný anténny profil alebo zoznam montáží')
    if mounts and group != 'starlink':
        raise ValueError('Smerový limit montáže je doložený iba pre terminál Starlink FHP')
    if not set(mounts) <= set(kinds):
        raise ValueError('Anténna montáž odkazuje na neznámy uzol')
    for node, mount in mounts.items():
        if type(mount) is not dict or set(mount) != {'tilt_deg', 'azimuth_deg', 'frame'}:
            raise ValueError(f'{node}: montáž potrebuje náklon, azimut a referenčný rámec')
        tilt, azimuth = mount['tilt_deg'], mount['azimuth_deg']
        if (type(tilt) not in (int, float) or type(azimuth) not in (int, float) or
                not math.isfinite(tilt) or not math.isfinite(azimuth) or
                not 0 <= tilt <= 180 or not 0 <= azimuth < 360):
            raise ValueError(f'{node}: neplatný náklon alebo azimut antény')
        if mount['frame'] not in ('north', 'vehicle') or \
                mount['frame'] == 'vehicle' and kinds[node] != 'car':
            raise ValueError(f'{node}: rámec vehicle patrí iba autu')
    return mounts


def angles_deg(site: tuple[float, float, float], satellites_xyz: np.ndarray,
               mount: dict, heading_deg: float = 0.0) -> np.ndarray:
    """Angle between installed panel normal and each satellite line of sight."""
    xyz = np.asarray(satellites_xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError('Neplatné ECEF súradnice satelitov')
    if not math.isfinite(heading_deg):
        raise ValueError('Neplatný smer jazdy')
    lat, lon = np.radians(site[:2])
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    north = np.array([-np.sin(lat)*np.cos(lon), -np.sin(lat)*np.sin(lon), np.cos(lat)])
    up = np.array([np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)])
    tilt = np.deg2rad(mount['tilt_deg'])
    azimuth = np.deg2rad(mount['azimuth_deg'] +
                        (heading_deg if mount['frame'] == 'vehicle' else 0.0))
    boresight = (np.cos(tilt)*up +
                 np.sin(tilt)*(np.sin(azimuth)*east + np.cos(azimuth)*north))
    sight = xyz - site_ecef_km(site)
    norm = np.linalg.norm(sight, axis=1)
    if np.any(norm <= 0):
        raise ValueError('Satelit je na mieste terminálu')
    return np.rad2deg(np.arccos(np.clip((sight/norm[:, None])@boresight, -1, 1)))


# Odvádza viditeľnú oblasť zo zorného poľa a minimálnej elevácie ako scenárový predpoklad. Tento
# profil nie je potvrdená mapa lúčov alebo kapacity služby Starlink.
def starlink_fov_mask(site: tuple[float, float, float], satellites_xyz: np.ndarray,
                      mount: dict, heading_deg: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    angles = angles_deg(site, satellites_xyz, mount, heading_deg)
    return angles <= STARLINK_HALF_FOV_DEG + 1e-9, angles
