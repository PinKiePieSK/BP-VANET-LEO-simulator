#!/usr/bin/env python3
# Technický model posiela rozhraniu aktuálne predvolené hodnoty enginu, aby sa neodvodzovali z
# popisného textu.
"""Serve the current simulator and its local scenario API."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from simulator_platform import ROOT
from simulator_inventory import VIEWER_FILES
from simulator_osm_road_graph import OsmRateLimit

UI = ROOT / "viewer"
JOBS_DIR = ROOT / "results/jobs"
RUNS_DIR = ROOT / "results/simulations"
JOBS = {}
JOB_LOCK = threading.Lock()
RUN_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
SCENARIO_ID = re.compile(r"^[a-z][a-z0-9-]{2,47}$")
STATIC = VIEWER_FILES


# Staršie URL sa mapujú na súčasné názvy API. Toto je len kompatibilita odkazov, nie ďalšia verzia
# simulačného behu.
def canonical_route(path: str) -> str:
    """Use the versionless API paths exposed by the current editor."""
    return urlparse(path).path


def running(run_id):
    child = JOBS.get(run_id)
    if child is not None:
        return child.poll() is None
    pid_path = JOBS_DIR / f"{run_id}.pid"
    if not pid_path.is_file():
        return False
    try:
        pid = int(pid_path.read_text())
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes()
        return b"simulator_cli.py" in command and run_id.encode() in command
    except (ValueError, OSError):
        return False


# Lokálne HTTP API prijíma požiadavky stránky. Pri spustení iba vytvorí úlohu pre
# simulator_cli.py; server sám nepočíta fyzikálny kanál ani nesimuluje sieť.
class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data, mime="application/json; charset=utf-8", headers=()):
        body = data if isinstance(data, bytes) else data.encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def json(self, status, payload):
        self.reply(status, json.dumps(payload, ensure_ascii=False).encode())

    def request_json(self, max_bytes):
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("Use application/json")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
            raise ValueError("Cross-origin submission is disabled")
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= max_bytes:
            raise ValueError(f"JSON request must be 1–{max_bytes} bytes")
        return json.loads(self.rfile.read(size))

    def do_POST(self):
        route = canonical_route(self.path)
        try:
            if route in {"/api/simulator/editor/save", "/api/simulator/editor/check", "/api/simulator/editor/orbits",
                         "/api/simulator/editor/orbit-motion", "/api/simulator/editor/roads"}:
                request = self.request_json(67_108_864)
                if route.endswith("/roads"):
                    from simulator_osm_road_graph import load
                    if type(request) is not dict or "georeference" not in request or set(request)-{"georeference","extent_m","width_m","height_m"} or ("width_m" in request)!=("height_m" in request):
                        raise ValueError("Expected georeference and optional working-area dimensions")
                    return self.json(200, load(request["georeference"], include_environment=True,
                                               extent=request.get("width_m",request.get("extent_m", 2000)),
                                               height=request.get("height_m")))
                if route.endswith("/orbit-motion"):
                    from simulator_constellation import motion
                    if type(request) is not dict or set(request) != {"group", "scenario", "duration_s"}:
                        raise ValueError("Expected constellation, scenario and duration")
                    return self.json(200, motion(**request))
                if route.endswith("/orbits"):
                    from simulator_constellation import preview
                    if type(request) is not dict or set(request) != {"group", "scenario", "world"}:
                        raise ValueError("Expected constellation, scenario and world")
                    return self.json(200, preview(**request))
                from simulator_editor_api import save, check
                if type(request) is not dict or set(request) != {"scenario", "world", "demand"}:
                    raise ValueError("Expected scenario, world and demand")
                return self.json(200, (save if route.endswith("/save") else check)(**request))
            if route in {"/api/simulator/preflight", "/api/simulator/runs"}:
                from simulator_cli import preflight
                request = self.request_json(8_388_608)
                if type(request) is not dict or set(request) != {"scenario"}:
                    raise ValueError("Expected one scenario")
                scenario = request["scenario"]
                plan = preflight(scenario)
                if route.endswith("/preflight"):
                    return self.json(200, plan)
                with JOB_LOCK:
                    if any(running(name) for name in JOBS) or any(running(p.stem) for p in JOBS_DIR.glob("*.pid")):
                        raise ValueError("Iná simulácia už beží")
                    run_id = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz") + uuid.uuid4().hex[:8]
                    JOBS_DIR.mkdir(parents=True, exist_ok=True)
                    RUNS_DIR.mkdir(parents=True, exist_ok=True)
                    request_path = JOBS_DIR / f"{run_id}.json"
                    with request_path.open("x") as stream:
                        json.dump(scenario, stream, indent=2, sort_keys=True)
                    with (JOBS_DIR / f"{run_id}.log").open("w") as log:
                        child = subprocess.Popen([sys.executable, str(ROOT / "tools/simulator_cli.py"), "run",
                                                  str(request_path), str(RUNS_DIR / run_id)],
                                                 cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                                 start_new_session=True)
                    JOBS[run_id] = child
                    (JOBS_DIR / f"{run_id}.pid").write_text(str(child.pid))
                return self.json(202, {"run_id": run_id, "plan": plan})
            return self.json(404, {"error": "Unknown endpoint"})
        except OsmRateLimit as exc:
            return self.json(429, {"reason": str(exc), "retry_after_s": exc.retry_after_s})
        except (ValueError, TypeError, KeyError, AssertionError, OSError, json.JSONDecodeError) as exc:
            return self.json(422, {"reason": str(exc)})

    def do_GET(self):
        route = canonical_route(self.path)
        if route in {"/", "/index.html"}:
            return self.reply(302, b"", headers=(("Location", "/simulator.html"),))
        name = route.lstrip("/")
        if name in STATIC:
            path = UI / name
            mime = ("text/html" if name.endswith(".html") else "text/css" if name.endswith(".css") else
                    "application/json" if name.endswith(".json") else "text/javascript") + "; charset=utf-8"
            try:
                return self.reply(200, path.read_bytes(), mime)
            except OSError:
                return self.json(404, {"error": "Asset not found"})
        try:
            if route == "/api/simulator/technical-model":
                from simulator_clock import EXPERIMENT_START_S as START_S
                # Jediný register predvolených hodnôt zdieľa server, preflight a runnery.
                from simulator_engine_controls import DEFAULTS as ENGINE_DEFAULTS
                from simulator_physical_coverage import PROFILES as physical
                dcc = json.loads((ROOT / "config/ground-radio-reference.json").read_text())["dcc_policy"]
                return self.json(200, {"start_offset_s": START_S, "sample_step_s": 0.1,
                                       "engine_defaults": ENGINE_DEFAULTS,
                                       "ground_rate_options_mbps": [3, 6, 12, 24],
                                       "ground_channel_options": [172, 174, 176, 178, 180, 182, 184],
                                       "ground_channel_width_mhz": 10,
                                       "dcc_policy": dcc,
                                       "sumo_vehicle": {"accel_mps2": 2.0, "decel_mps2": 4.5,
                                                        # API vracia predvolené rozmery typu vozidla, aby technická
                                                        # stránka vedela zobraziť aj staršie scenáre bez
                                                        # explicitného modelu.
                                                        "sigma": 0.0, "length_m": 5.0, "width_m": 1.8,
                                                        "min_gap_m": 2.5, "speed_factor": 1.0,
                                                        "manual_max_speed_mps": 40.0},
                                       "sumo_depart_lane_real": "best",
                                       "sumo_depart_speed_real": "max",
                                       "sumo_vehicle_hold_after_arrival": True,
                                       "physical_profiles": physical})
            if route == "/api/simulator/editor/new":
                from simulator_editor_api import new_draft
                return self.json(200, new_draft())
            if route == "/api/simulator/orbit-snapshots":
                from simulator_orbit_source import snapshots
                return self.json(200, {"snapshots": snapshots()})
            if route == "/api/simulator/rsu-reference":
                from simulator_rsu_reference import fetch
                query = parse_qs(urlparse(self.path).query)
                required = {"lat", "lon", "anchor_x", "anchor_y"}
                if not required <= set(query) or set(query) - required - {"width_m", "height_m"} or any(len(v) != 1 for v in query.values()):
                    raise ValueError("Expected lat, lon, anchor_x, anchor_y and optional width_m, height_m")
                return self.json(200, fetch(*(query[k][0] for k in ("lat", "lon", "anchor_x", "anchor_y")),
                                            query.get("width_m", [2000])[0], query.get("height_m", [2000])[0]))
            # Zoznam uložených scenárov pripúšťa aktuálnu schému 7 aj predchádzajúcu schému 6.
            # Starý scenár sa pri načítaní preverí a v editore prevedie na nový čas bez straty
            # vybraného UTC okamihu.
            if route == "/api/simulator/scenarios":
                folder = ROOT / "config/scenarios"
                return self.json(200, {"scenarios": sorted(p.stem for p in folder.glob("*.json")
                                                         if SCENARIO_ID.fullmatch(p.stem)
                                                         and json.loads(p.read_text()).get("schema_version") in (6, 7))})
            if route == "/api/simulator/editor/source":
                from simulator_editor_api import source
                query = parse_qs(urlparse(self.path).query)
                names = query.get("scenario", [])
                if len(names) != 1 or not SCENARIO_ID.fullmatch(names[0]):
                    raise ValueError("Choose one valid scenario ID")
                path = ROOT / "config/scenarios" / (names[0] + ".json")
                if not path.is_file():
                    return self.json(404, {"error": "Scenario not found"})
                return self.json(200, source(json.loads(path.read_text())))
            parts = route.strip("/").split("/")
            if len(parts) >= 4 and parts[:3] == ["api", "simulator", "runs"] and RUN_ID.fullmatch(parts[3]):
                from simulator_editor_api import verified_run
                run_id = parts[3]
                base = RUNS_DIR / run_id
                if len(parts) == 4:
                    if running(run_id):
                        return self.json(200, {"run_id": run_id, "status": "running"})
                    try:
                        checked = verified_run(base)
                        return self.json(200, {**checked, "run_id": run_id, "status": "complete"})
                    except (ValueError, TypeError, KeyError, AssertionError, OSError, json.JSONDecodeError) as exc:
                        # A finished packet run can be valid even when this long-lived
                        # server still has pre-update verifier modules in memory.
                        # Report the verification error, never the worker's PASS JSON
                        # as a false failure reason. A fresh server can recheck it.
                        # Ak beh má finálny manifest, fyzický výpočet dobehol. Chybu overenia
                        # preto server označí ako neoverený beh a uvedie skutočnú príčinu;
                        # posledný riadok úspešného worker logu sa nesmie vydávať za chybu
                        # simulácie. Po zmene zdroja počas otvoreného servera treba proces
                        # reštartovať.
                        if (base / "run-manifest.json").is_file():
                            return self.json(409, {"run_id": run_id, "status": "unverified",
                                                   "reason": f"Beh dobehol, ale overenie zlyhalo: {exc}. "
                                                             "Ak sa kód zmenil počas otvoreného okna, "
                                                             "zatvor simulátor a spusti ho znova."})
                        log = JOBS_DIR / f"{run_id}.log"
                        if log.is_file():
                            lines = [line.strip() for line in log.read_text(errors="replace").splitlines() if line.strip()]
                            return self.json(409, {"run_id": run_id, "status": "failed",
                                                   "reason": lines[-1] if lines else "Run failed; check the worker log"})
                        return self.json(409, {"run_id": run_id, "status": "failed",
                                               "reason": "Run absent or verification failed"})
                if len(parts) == 5 and parts[4] == "replay":
                    from simulator_editor_api import replay
                    return self.json(200, replay(base))
                # HTTP cesta vydáva stránkované udalosti z overenej stopy. Voliteľný časový index
                # sa posiela len pri prvom načítaní; počas prehrávania už prehliadač nepotrebuje
                # opakovať audit súborov.
                if len(parts) == 5 and parts[4] == "events":
                    from simulator_editor_api import packet_events
                    query = parse_qs(urlparse(self.path).query)
                    allowed = {"offset", "limit", "from", "to", "kind", "timeline"}
                    if set(query) - allowed or any(len(values) != 1 for values in query.values()):
                        raise ValueError("Neplatné parametre zoznamu paketov")
                    if query.get("timeline", ["0"])[0] not in ("0", "1"):
                        raise ValueError("Neplatný časový index paketov")
                    return self.json(200, packet_events(base, query.get("offset", [0])[0],
                                                        query.get("limit", [256])[0],
                                                        query.get("from", [None])[0],
                                                        query.get("to", [None])[0],
                                                        query.get("kind", [None])[0],
                                                        query.get("timeline", ["0"])[0] == "1"))
                if len(parts) == 5 and parts[4] == "physical-audit":
                    from simulator_editor_api import physical_audit
                    return self.json(200, physical_audit(base))
                if len(parts) == 6 and parts[4] == "packet":
                    from simulator_editor_api import packet
                    return self.json(200, packet(base, parts[5]))
            return self.json(404, {"error": "Unknown endpoint"})
        except OsmRateLimit as exc:
            return self.json(429, {"reason": str(exc), "retry_after_s": exc.retry_after_s})
        except (ValueError, TypeError, KeyError, AssertionError, OSError, json.JSONDecodeError) as exc:
            return self.json(409, {"reason": str(exc)})


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Python optimization disables required packet assertions")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    port = parser.parse_args().port
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    actual_port = server.server_address[1]
    print(f"Simulator: http://127.0.0.1:{actual_port}/simulator.html", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
