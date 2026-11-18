# Prevod lokálnych metrov editora na WGS84 pomocou tečnej roviny ENU a knižnice Astropy.
"""Convert the editor's local east/north metres to WGS84 positions."""
from __future__ import annotations

import math
import astropy.units as u
from astropy.coordinates import EarthLocation


# Rozdiel polohy od kotevného bodu sa rozloží na východ a sever, prevedie do zemských súradníc a
# späť na zemepisnú šírku, dĺžku a výšku. Toto je väzba medzi mapou, SUMO a správami CAM.
def enu_to_wgs84(x_m: float, y_m: float, anchor_x_m: float, anchor_y_m: float,
                  anchor_lat_deg: float, anchor_lon_deg: float,
                  anchor_height_m: float) -> tuple[float, float, float]:
    """Apply a local WGS84 tangent-frame displacement at fixed ENU up=0 m."""
    origin = EarthLocation.from_geodetic(anchor_lon_deg * u.deg,
                                          anchor_lat_deg * u.deg,
                                          anchor_height_m * u.m)
    ox, oy, oz = (component.to_value(u.m) for component in origin.to_geocentric())
    east, north = x_m - anchor_x_m, y_m - anchor_y_m
    phi, lam = math.radians(anchor_lat_deg), math.radians(anchor_lon_deg)
    dx = -math.sin(lam) * east - math.sin(phi) * math.cos(lam) * north
    dy = math.cos(lam) * east - math.sin(phi) * math.sin(lam) * north
    dz = math.cos(phi) * north
    point = EarthLocation.from_geocentric((ox + dx) * u.m,
                                            (oy + dy) * u.m,
                                            (oz + dz) * u.m)
    lon, lat, height = point.to_geodetic()
    return lat.to_value(u.deg), lon.to_value(u.deg), height.to_value(u.m)
