"""Files exposed by the current editor and shipped in the portable package."""

VIEWER_FILES = frozenset({
    "simulator.html", "simulator.css", "simulator.js",
    "technical-parameters.html", "technical-parameters.css",
    "technical-parameters.js", "technical-parameters-bridge.js",
    "route-planner.js", "traffic-spawner.js", "globe.js",
    "manual-buildings.js", "rsu-inputs.js", "packet-inspector.js", "earth-map.js",
    "physical-audit.js", "globe-land.json",
    "lib/d3-array-3.2.4.min.js", "lib/d3-geo-3.1.1.min.js",
    "lib/maplibre-gl-5.24.0.js", "lib/maplibre-gl-5.24.0.css",
})

STUDY_UI_FILES = {name for name in VIEWER_FILES if "/" not in name and
                  name.endswith((".html", ".css", ".js"))}
