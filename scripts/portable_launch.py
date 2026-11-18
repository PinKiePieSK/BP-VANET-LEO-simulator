#!/usr/bin/env python3
"""Own one local simulator server and its browser window."""
from __future__ import annotations

import fcntl
import hashlib
import argparse
import json
import os
import re
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlencode
from datetime import datetime, timezone
from pathlib import Path


PACKAGE = Path(__file__).resolve().parent
URL_LINE = re.compile(r"^Simulator: (http://127\.0\.0\.1:\d+/simulator\.html)$")


class Stopped(Exception):
    pass


def desktop() -> Path:
    try:
        value = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True,
                                        stderr=subprocess.DEVNULL).strip()
        if value:
            return Path(value).expanduser()
    except (OSError, subprocess.CalledProcessError):
        pass
    return Path.home() / "Desktop"


def tell(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
    notifier = shutil.which("notify-send")
    if notifier:
        subprocess.run([notifier, "BP Simulátor", message], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def on_signal(_number, _frame) -> None:
    raise Stopped()


def stop(child: subprocess.Popen | None) -> None:
    if child is None or child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)


def browser_command(url: str, profile: Path) -> list[str]:
    # An executable override is useful for smoke tests and alternate browsers.
    override = os.environ.get("BP_SIM_BROWSER")
    if override:
        executable = shutil.which(override)
        if not executable:
            raise RuntimeError(f"Prehliadač neexistuje: {override}")
        return [executable, url]
    firefox = shutil.which("firefox")
    if firefox:
        return [firefox, "--no-remote", "--new-instance", "--profile", str(profile),
                "--new-window", url]
    for name in ("chromium", "chromium-browser", "google-chrome"):
        executable = shutil.which(name)
        if executable:
            return [executable, f"--user-data-dir={profile}", "--no-first-run",
                    "--new-window", url]
    raise RuntimeError("Chýba Firefox alebo Chromium. Nainštaluj prehliadač a spusti ikonu znova.")


def ready_runtime(workspace: Path, run_id: str | None = None) -> Path:
    if run_id and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise RuntimeError("Neplatné ID behu.")
    runtime = workspace / "runtime"
    state_file = workspace / "UPDATE-STATE.json"
    if state_file.is_file():
        state = json.loads(state_file.read_text())
        if run_id:
            matches = {(workspace / relative).resolve() for relative in state.get("versions", {}).values()
                       if isinstance(relative, str) and
                       (workspace / relative / "results/simulations" / run_id).is_dir()}
            if len(matches) != 1:
                raise RuntimeError(f"Beh {run_id} neexistuje alebo má rovnaké ID vo viacerých verziách.")
            runtime = matches.pop()
        else:
            runtime = (workspace / state.get("active_runtime", "runtime")).resolve()
        if not runtime.is_relative_to(workspace.resolve()):
            raise RuntimeError("Stav aktualizácií obsahuje neplatnú cestu k runtime.")
    if not (workspace / "READY").is_file() or not (runtime / ".venv/bin/python").is_file():
        raise RuntimeError("Simulátor ešte nie je pripravený. V rozbalenom BP-Simulator najprv spusti setup.sh.")
    if not (runtime / "tools/simulator_server.py").is_file():
        raise RuntimeError("V pracovnom runtime chýba server. Zopakuj prípravu z balíka.")
    expected = hashlib.sha256((PACKAGE / "PACKAGE-MANIFEST.json").read_bytes()).hexdigest()
    recorded = (workspace / "PACKAGE-ID").read_text().strip() if (workspace / "PACKAGE-ID").is_file() else ""
    if recorded != expected:
        raise RuntimeError("Pracovný runtime patrí inému balíku. Spusti setup.sh v novom pracovnom priečinku.")
    return runtime


def start_server(runtime: Path, workspace: Path, log) -> tuple[subprocess.Popen, str]:
    with socket.socket() as probe:
        probe.settimeout(.2)
        preferred_port = 0 if probe.connect_ex(("127.0.0.1", 8766)) == 0 else 8766
    child = subprocess.Popen([str(runtime / ".venv/bin/python"), "tools/simulator_server.py",
                              "--port", str(preferred_port)], cwd=runtime, stdout=subprocess.PIPE,
                             stderr=log, text=True, bufsize=1, start_new_session=True,
                             env={**os.environ, "BP_SIM_WORKSPACE": str(workspace)})
    assert child.stdout is not None
    readable, _, _ = select.select([child.stdout], [], [], 20)
    if not readable:
        stop(child)
        raise RuntimeError("Lokálny server sa nespustil do 20 s. Pozri logs/launcher-*.log.")
    line = child.stdout.readline().strip()
    match = URL_LINE.fullmatch(line)
    if not match:
        stop(child)
        raise RuntimeError(f"Lokálny server neoznámil adresu: {line or 'bez výstupu'}")
    url = match.group(1)
    for _ in range(40):
        if child.poll() is not None:
            raise RuntimeError("Lokálny server sa pred otvorením stránky ukončil.")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return child, url
        except OSError:
            time.sleep(.1)
    stop(child)
    raise RuntimeError("Lokálny server neodpovedá na kontrolnú požiadavku.")


def launch() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", help="otvoriť verziu, v ktorej vznikol uložený beh")
    args = parser.parse_args()
    workspace = Path(os.environ.get("BP_SIM_WORKSPACE", desktop() / "BP-Simulator-Workspace")).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    logs = workspace / "logs"
    logs.mkdir(exist_ok=True)
    with (workspace / ".launcher.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            tell("Simulátor už beží v samostatnom okne.")
            return 0
        runtime = ready_runtime(workspace, args.run)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_path = logs / f"launcher-{stamp}-{os.getpid()}.log"
        server = browser = None
        profile = None
        try:
            with log_path.open("w", buffering=1) as log:
                server, url = start_server(runtime, workspace, log)
                if args.run:
                    url += "?" + urlencode({"run": args.run})
                print(f"Server: {url}", file=log)
                profile_root = workspace / "browser-profiles"
                profile_root.mkdir(exist_ok=True)
                profile = Path(tempfile.mkdtemp(prefix="session-", dir=profile_root))
                (profile / "user.js").write_text(
                    'user_pref("browser.shell.checkDefaultBrowser", false);\n'
                    'user_pref("browser.aboutwelcome.enabled", false);\n'
                    'user_pref("browser.startup.page", 0);\n')
                # WebGL v snap Firefoxe môže po štarte stratiť grafický kontext.
                # Softvérové GL udrží mapový podklad aj pri nestabilnom ovládači GPU.
                browser_env = {**os.environ, "LIBGL_ALWAYS_SOFTWARE": "1",
                               "MOZ_WEBRENDER_SOFTWARE": "1", "MOZ_X11_EGL": "0"}
                browser = subprocess.Popen(browser_command(url, profile),
                                           cwd=runtime, stdout=log, stderr=log,
                                           env=browser_env)
                print(f"Browser PID: {browser.pid}", file=log)
                while browser.poll() is None:
                    if server.poll() is not None:
                        raise RuntimeError("Lokálny server sa počas otvoreného prehliadača ukončil.")
                    time.sleep(.25)
                print(f"Browser closed: {browser.returncode}", file=log)
                return 0 if browser.returncode == 0 else 1
        finally:
            stop(server)
            # If the server failed, do not close the user's browser window.
            if profile is not None and (browser is None or browser.poll() is not None):
                shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    for name in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(name, on_signal)
    try:
        raise SystemExit(launch())
    except Stopped:
        raise SystemExit(0)
    except (OSError, RuntimeError) as error:
        tell(str(error))
        raise SystemExit(1)
