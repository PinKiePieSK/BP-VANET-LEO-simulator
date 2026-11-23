#!/usr/bin/env python3
"""Launch the simulator directly from its single source and data directory."""
from __future__ import annotations

import argparse
import fcntl
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
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
URL_LINE = re.compile(r"^Simulator: (http://127\.0\.0\.1:\d+/simulator\.html)$")


def on_signal(_number, _frame) -> None:
    raise SystemExit(0)


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
            return [executable, f"--user-data-dir={profile}", "--no-first-run", "--new-window", url]
    raise RuntimeError("Chýba Firefox alebo Chromium")


def start_server(log) -> tuple[subprocess.Popen, str]:
    python = ROOT / ".venv/bin/python"
    if not python.is_file() or not (ROOT / "tools/simulator_server.py").is_file():
        raise RuntimeError("V hlavnom priečinku chýba pripravený simulátor")
    with socket.socket() as probe:
        probe.settimeout(.2)
        port = 0 if probe.connect_ex(("127.0.0.1", 8766)) == 0 else 8766
    child = subprocess.Popen([str(python), "tools/simulator_server.py", "--port", str(port)],
                             cwd=ROOT, stdout=subprocess.PIPE, stderr=log, text=True, bufsize=1,
                             start_new_session=True, env={**os.environ, "BP_SIM_WORKSPACE": str(ROOT)})
    assert child.stdout is not None
    readable, _, _ = select.select([child.stdout], [], [], 20)
    line = child.stdout.readline().strip() if readable else ""
    match = URL_LINE.fullmatch(line)
    if not match:
        stop(child)
        raise RuntimeError(f"Server sa nespustil: {line or 'bez odpovede'}")
    url = match.group(1)
    for _ in range(40):
        if child.poll() is not None:
            raise RuntimeError("Server sa ukončil pred otvorením stránky")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return child, url
        except OSError:
            time.sleep(.1)
    stop(child)
    raise RuntimeError("Lokálny server neodpovedá")


def launch(check_only: bool = False) -> int:
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    with (ROOT / ".launcher.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Simulátor už beží")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        with (logs / f"launcher-{stamp}-{os.getpid()}.log").open("w", buffering=1) as log:
            server = browser = None
            profile = None
            try:
                server, url = start_server(log)
                print(f"Server: {url}", file=log)
                if check_only:
                    return 0
                profiles = ROOT / "browser-profiles"
                profiles.mkdir(exist_ok=True)
                profile = Path(tempfile.mkdtemp(prefix="session-", dir=profiles))
                (profile / "user.js").write_text(
                    'user_pref("browser.shell.checkDefaultBrowser", false);\n'
                    'user_pref("browser.aboutwelcome.enabled", false);\n')
                browser_env = {**os.environ, "LIBGL_ALWAYS_SOFTWARE": "1",
                               "MOZ_WEBRENDER_SOFTWARE": "1", "MOZ_X11_EGL": "0"}
                browser = subprocess.Popen(browser_command(url, profile), cwd=ROOT,
                                           stdout=log, stderr=log, env=browser_env)
                while browser.poll() is None:
                    if server.poll() is not None:
                        raise RuntimeError("Server sa počas otvoreného okna ukončil")
                    time.sleep(.25)
                return 0 if browser.returncode == 0 else 1
            finally:
                stop(server)
                if profile is not None and (browser is None or browser.poll() is not None):
                    shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    for name in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(name, on_signal)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="start and stop the local server")
    args = parser.parse_args()
    try:
        raise SystemExit(launch(args.check))
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
