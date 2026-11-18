# Inventár povoľuje nový RSU panel cez server a prenosný balík; bez toho by sa v pracovnej ikone
# nenačítal.
"""Files exposed by the current editor and shipped in the portable package."""

# Whitelisting bráni serveru sprístupniť staré stránky a balíku pribaliť neaktívne UI. Pri pridaní
# nového skriptu alebo štýlu sa mení tento zoznam.
VIEWER_FILES = frozenset({
    "simulator.html", "simulator.css", "simulator.js",
    "technical-parameters.html", "technical-parameters.css",
    "technical-parameters.js", "technical-parameters-bridge.js",
    "route-planner.js", "traffic-spawner.js", "globe.js",
    # Nový panel je aktívny súbor aplikácie a musí byť v zdroji, runtime aj ZIPe.
    "manual-buildings.js", "rsu-inputs.js", "packet-inspector.js", "earth-map.js",
    "physical-audit.js", "globe-land.json",
    "lib/d3-array-3.2.4.min.js", "lib/d3-geo-3.1.1.min.js",
    "lib/maplibre-gl-5.24.0.js", "lib/maplibre-gl-5.24.0.css",
})

STUDY_UI_FILES = {name for name in VIEWER_FILES if "/" not in name and
                  name.endswith((".html", ".css", ".js"))}
