"""Read a bounded, optional reference layer of published US V2X RSU positions.

These are registry coordinates, not evidence of live service or ITS-G5 capability.
They never enter a simulator simulation unless the user places a model RSU separately.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from simulator_osm_road_graph import basis, bbox_for, local

SOURCE = "https://geo.dot.gov/server/rest/services/hosted/V2X_Deployment_Map_ULS_RSUs___Licenses___Updated_Basemap_Sept_2025_WFL1/FeatureServer/0"
MAX_BYTES = 2_000_000


def _value(value: float, low: float, high: float, name: str) -> float:
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{name} is outside [{low}, {high}]")
    return number


@lru_cache(maxsize=32)
def fetch(lat: float, lon: float, anchor_x: float, anchor_y: float,
          width: float = 2000, height: float = 2000) -> dict:
    width = _value(width, 500, 4000, "width")
    height = _value(height, 500, 4000, "height")
    geo = {"frame": "WGS84_ENU", "latitude_deg": _value(lat, -85, 85, "latitude"),
           "longitude_deg": _value(lon, -180, 180, "longitude"),
           "anchor_x_m": _value(anchor_x, 0, width, "anchor_x"),
           "anchor_y_m": _value(anchor_y, 0, height, "anchor_y"), "height_m": 0.0}
    bbox = bbox_for(geo, int(width), int(height))
    params = {"where": "1=1", "geometry": ",".join(str(x) for x in bbox),
              "geometryType": "esriGeometryEnvelope", "inSR": "4326",
              "spatialRel": "esriSpatialRelIntersects", "outFields": "objectid,call_sign,name,location,channels,uls_url",
              "f": "geojson", "outSR": "4326", "resultRecordCount": "500"}
    request = Request(SOURCE + "/query?" + urlencode(params),
                      headers={"User-Agent": "BP-Simulator/1.0 (academic reference map)", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ValueError(f"Verejný register RSU je nedostupný: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ValueError("Odpoveď registra RSU prekročila 2 MB")
    data = json.loads(raw)
    if data.get("error") or data.get("type") != "FeatureCollection" or data.get("exceededTransferLimit") or len(data.get("features", [])) >= 500:
        raise ValueError("Register RSU nevrátil úplný GeoJSON výrez")
    records = []
    seen = set()
    frame = basis(geo)
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not isinstance(coords, list) or len(coords) != 2:
            continue
        x, y = local(frame, coords[0], coords[1])
        if not 0 <= x <= width or not 0 <= y <= height:
            continue
        key = (round(coords[0], 6), round(coords[1], 6))
        if key in seen:
            continue
        seen.add(key)
        props = feature.get("properties") or {}
        records.append({"id": str(props.get("objectid") or feature.get("id") or len(records)),
                        "longitude_deg": round(coords[0], 8), "latitude_deg": round(coords[1], 8),
                        "call_sign": str(props.get("call_sign") or "")[:40],
                        "label": str(props.get("location") or props.get("name") or "")[:100]})
    return {"records": records, "source": SOURCE, "snapshot": "2025-09",
            "meaning": "US V2X RSU registry coordinates; operating status and radio technology are not verified"}
