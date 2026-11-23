#!/usr/bin/env python3
"""Fast-forward the one local simulator folder to the approved GitHub main."""
from __future__ import annotations

import fcntl
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/PinKiePieSK/BP-VANET-LEO-simulator.git"
SERVER_CHECK = """import sys
sys.path.insert(0, 'scripts')
from launch_local import start_server, stop
with open('/dev/null', 'w') as log:
    server, url = start_server(log)
    stop(server)
print(url)
"""


def command(root: Path, *args: str, environment: dict[str, str] | None = None) -> str:
    completed = subprocess.run(args, cwd=root, env=environment, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"{' '.join(args[:3])} zlyhalo: {detail}")
    return completed.stdout.strip()


def git(root: Path, *args: str, environment: dict[str, str] | None = None) -> str:
    return command(root, "git", *args, environment=environment)


def configure_auth(root: Path, repository: str) -> None:
    if not repository.startswith("https://github.com/"):
        return
    executable = shutil.which("gh")
    if not executable:
        local = root / "local-bin/gh"
        executable = str(local) if local.is_file() and os.access(local, os.X_OK) else None
    if not executable:
        raise RuntimeError("Chýba GitHub CLI (gh) potrebný na prístup k súkromnému repozitáru")
    git(root, "config", "--local", "credential.https://github.com.helper",
        "!" + shlex.quote(executable) + " auth git-credential")


def revision(root: Path, name: str) -> str:
    return git(root, "rev-parse", name)


def update(root: Path = ROOT, repository: str = REPOSITORY) -> dict[str, str]:
    root = root.resolve()
    if not (root / ".git").exists():
        raise RuntimeError("Aktualizácia vyžaduje Git klon simulátora")
    with (root / ".launcher.lock").open("a") as launcher_lock, \
            (root / ".update.lock").open("a") as update_lock:
        for lock in (launcher_lock, update_lock):
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("Zavri simulátor alebo počkaj na dokončenie inej aktualizácie")
        if git(root, "branch", "--show-current") != "main":
            raise RuntimeError("Aktualizovať možno iba vetvu main")
        actual_remote = git(root, "remote", "get-url", "origin")
        if actual_remote.removesuffix(".git") != repository.removesuffix(".git"):
            raise RuntimeError(f"Neočakávaný Git remote: {actual_remote}")
        if git(root, "status", "--porcelain=v1", "--untracked-files=no"):
            raise RuntimeError("Najprv vyrieš miestne zmeny sledovaných súborov")
        configure_auth(root, repository)
        environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        before = revision(root, "HEAD")
        git(root, "fetch", "origin", "main", environment=environment)
        after = revision(root, "origin/main")
        ancestor = subprocess.run(("git", "merge-base", "--is-ancestor", before, after),
                                  cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ancestor.returncode:
            raise RuntimeError("GitHub main nie je pokračovaním miestnej verzie; automatická aktualizácia sa zastavila")
        changed = before != after
        if changed:
            git(root, "merge", "--ff-only", "origin/main", environment=environment)
        try:
            command(root, sys.executable, "scripts/setup_single_folder.py")
            # The updater already owns .launcher.lock, so probe the server directly.
            command(root, str(root / ".venv/bin/python"), "-c", SERVER_CHECK)
        except (OSError, RuntimeError) as error:
            if changed:
                git(root, "reset", "--hard", before)
            raise RuntimeError(f"Aktualizácia neprešla kontrolou; zdroj obnovený na {before[:12]}: {error}") from error
        return {"status": "UPDATED" if changed else "CURRENT", "revision": after}


if __name__ == "__main__":
    try:
        print(json.dumps(update(), sort_keys=True))
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
