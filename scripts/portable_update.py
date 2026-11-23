#!/usr/bin/env python3
"""Apply approved Git changes to a separate simulator runtime version."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


REPOSITORY = "https://github.com/PinKiePieSK/BP-VANET-LEO-simulator.git"
BRANCH = "main"
REVISION = re.compile(r"[0-9a-f]{40}\Z")
COPY_ROOTS = {"src", "tools", "viewer", "config"}
PACKAGE_ONLY = {"scripts/package_simulator.py", "scripts/portable_setup.sh",
                "scripts/portable_launch.py", "scripts/portable_run.sh",
                "scripts/portable_update.py", "scripts/portable_update.sh",
                "scripts/portable_import.sh", "scripts/portable_install_shortcut.py",
                "scripts/portable_verify.py"}
PACKAGE_PREFIXES = ("vendor/", "build/", "release/", "data/derived/",
                   "data/additional-input/", "requirements-")


def is_runtime_source(name: str) -> bool:
    parts = PurePosixPath(name).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    if parts[0] in COPY_ROOTS and len(parts) > 1:
        return "legacy" not in parts and not (parts[0] == "tools" and parts[-1].startswith("test_"))
    return parts[0] == "data" and len(parts) > 2 and parts[1] in {"inputs", "orbits"}


def is_saved_scenario(name: str) -> bool:
    return name.startswith(("config/scenarios/", "data/inputs/user/"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def state_path(workspace: Path) -> Path:
    return workspace / "UPDATE-STATE.json"


def read_state(workspace: Path) -> dict:
    path = state_path(workspace)
    if not path.is_file():
        raise RuntimeError("Chýba stav aktualizácií. Nainštaluj balík s podporou update.")
    state = json.loads(path.read_text())
    if state.get("schema_version") != 1 or state.get("repository") != REPOSITORY or state.get("branch") != BRANCH:
        raise RuntimeError("Neznámy alebo poškodený stav aktualizácií.")
    return state


def run_locations(workspace: Path, state: dict, run_id: str) -> set[Path]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise RuntimeError("Neplatné ID behu.")
    return {(workspace / relative).resolve() for relative in state.get("versions", {}).values()
            if isinstance(relative, str) and
            (workspace / relative / "results/simulations" / run_id).is_dir()}


def runtime_path(workspace: Path, run_id: str | None = None) -> Path:
    state = read_state(workspace)
    if run_id:
        matches = run_locations(workspace, state, run_id)
        if len(matches) != 1:
            raise RuntimeError(f"Beh {run_id} neexistuje alebo má rovnaké ID vo viacerých verziách.")
        path = matches.pop()
    else:
        relative = state.get("active_runtime")
        if not isinstance(relative, str) or not relative:
            raise RuntimeError("Aktívny runtime nie je v stave aktualizácií.")
        path = (workspace / relative).resolve()
    if not path.is_relative_to(workspace.resolve()) or not (path / "tools/simulator_server.py").is_file():
        raise RuntimeError("Cesta k runtime je neplatná alebo chýba.")
    return path


def command(*argv: str, cwd: Path | None = None, capture: bool = True) -> bytes:
    completed = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE if capture else None,
                               stderr=subprocess.PIPE if capture else None, check=False)
    if completed.returncode:
        error = completed.stderr.decode(errors="replace").strip() if capture else ""
        raise RuntimeError(f"Príkaz zlyhal ({' '.join(argv[:3])}): {error}")
    return completed.stdout if capture else b""


def git(cache: Path, *args: str) -> bytes:
    return command("git", "--git-dir", str(cache), *args)


def ensure_authentication() -> None:
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("Chýba GitHub CLI. Nainštaluj balík gh a spusti update znova.")
    if subprocess.run([gh, "auth", "status"], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, check=False).returncode:
        print("Prvé prihlásenie do súkromného GitHub repozitára:", flush=True)
        command(gh, "auth", "login", "--hostname", "github.com", "--git-protocol", "https",
                "--web", "--scopes", "repo", capture=False)
    command(gh, "auth", "setup-git")


def fetch(cache: Path, repository: str) -> str:
    if not cache.exists():
        command("git", "clone", "--bare", repository, str(cache))
    elif git(cache, "config", "--get", "remote.origin.url").decode().strip() != repository:
        raise RuntimeError("Aktualizačná cache ukazuje na iný repozitár.")
    git(cache, "fetch", "--prune", "origin", BRANCH)
    revision = git(cache, "rev-parse", "FETCH_HEAD").decode().strip()
    if not REVISION.fullmatch(revision):
        raise RuntimeError("Git nevrátil platný commit.")
    return revision


def changed_paths(cache: Path, old: str, new: str) -> list[str]:
    if not REVISION.fullmatch(old):
        raise RuntimeError("Balík neobsahuje vydaný základný commit; update zatiaľ nie je dostupný.")
    git(cache, "cat-file", "-e", old + "^{commit}")
    git(cache, "merge-base", "--is-ancestor", old, new)
    raw = git(cache, "diff", "--name-only", "--no-renames", "-z", old, new)
    return [item.decode("utf-8") for item in raw.split(b"\0") if item]


def source_blob(cache: Path, revision: str, name: str) -> tuple[bytes, int] | None:
    tree = git(cache, "ls-tree", "-z", revision, "--", name)
    if not tree:
        return None
    record = tree.split(b"\0", 1)[0]
    header, found = record.split(b"\t", 1)
    if found.decode("utf-8") != name:
        raise RuntimeError(f"Nejednoznačná cesta v Git: {name}")
    mode, kind, _object = header.split()
    if kind != b"blob" or mode not in {b"100644", b"100755"}:
        raise RuntimeError(f"Zmena typu súboru vyžaduje nové úplné vydanie: {name}")
    return git(cache, "show", f"{revision}:{name}"), int(mode, 8)


def copy_runtime(current: Path, target: Path) -> None:
    target.mkdir()
    for item in current.iterdir():
        destination = target / item.name
        if item.name in COPY_ROOTS and item.is_dir():
            shutil.copytree(item, destination, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
        elif item.name == "data" and item.is_dir():
            destination.mkdir()
            for child in item.iterdir():
                dst = destination / child.name
                if child.name in {"inputs", "orbits"} and child.is_dir():
                    shutil.copytree(child, dst, symlinks=True)
                else:
                    dst.symlink_to(child.resolve())
        elif item.name == "results":
            (destination / "simulations").mkdir(parents=True)
        else:
            destination.symlink_to(item.resolve())


def apply_blob(target: Path, name: str, blob: tuple[bytes, int] | None) -> None:
    parts = PurePosixPath(name).parts
    if not is_runtime_source(name):
        raise RuntimeError(f"Neplatná aktualizačná cesta: {name}")
    path = target.joinpath(*parts)
    if not path.parent.resolve().is_relative_to(target.resolve()) or path.is_symlink():
        raise RuntimeError(f"Cesta vedie mimo runtime: {name}")
    if blob is None:
        path.unlink(missing_ok=True)
        return
    data, mode = blob
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".update-tmp")
    if temporary.exists():
        raise RuntimeError(f"Kolízia dočasného súboru: {name}")
    temporary.write_bytes(data)
    temporary.chmod(0o755 if mode & 0o111 else 0o644)
    os.replace(temporary, path)


def write_atomic(workspace: Path, filename: str, contents: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=".update-state-", dir=workspace)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, workspace / filename)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_state(workspace: Path, state: dict) -> None:
    write_atomic(workspace, "UPDATE-STATE.json", json.dumps(state, sort_keys=True, indent=2) + "\n")


def adopt_package(workspace: Path, package: Path, runtime: Path) -> dict:
    """Activate a complete ZIP only after setup has built and checked its runtime."""
    workspace = workspace.resolve()
    runtime = runtime.resolve()
    if not runtime.is_relative_to(workspace) or not (runtime / "tools/simulator_server.py").is_file():
        raise RuntimeError("Nový runtime nie je v pracovnom priečinku.")
    base = json.loads((package / "UPDATE-BASE.json").read_text())
    revision = base.get("revision")
    if (base.get("schema_version") != 1 or base.get("repository") != REPOSITORY or
            base.get("branch") != BRANCH or not isinstance(revision, str) or
            not REVISION.fullmatch(revision)):
        raise RuntimeError("Nový balík nemá platný zdrojový commit.")
    relative = str(runtime.relative_to(workspace))
    previous = state_path(workspace)
    if previous.is_file():
        old = read_state(workspace)
        versions = dict(old.get("versions", {}))
        runs = dict(old.get("runs", {}))
    elif (workspace / "PACKAGE-ID").is_file() and (workspace / "READY").is_file():
        old_id = (workspace / "PACKAGE-ID").read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", old_id):
            raise RuntimeError("Pôvodný pracovný priečinok má neplatnú identitu balíka.")
        versions = {"legacy-" + old_id: "runtime"}
        runs = {}
    else:
        versions = {}
        runs = {}
    versions[revision] = relative
    state = {**base, "active_runtime": relative, "versions": versions, "runs": runs}
    write_state(workspace, state)
    write_atomic(workspace, "PACKAGE-ID", digest(package / "PACKAGE-MANIFEST.json") + "\n")
    write_atomic(workspace, "READY", str(runtime) + "\n")
    return {"status": "READY", "revision": revision, "runtime": relative,
            "historical_versions": len(set(versions.values())) - 1}


def update(workspace: Path, repository: str = REPOSITORY, *, authenticate: bool = True,
           validate: bool = True) -> dict:
    workspace = workspace.resolve()
    state = read_state(workspace)
    if not (workspace / "READY").is_file():
        raise RuntimeError("Pracovný runtime ešte nie je pripravený.")
    with (workspace / ".launcher.lock").open("a") as launcher_lock, \
            (workspace / ".update.lock").open("a") as update_lock:
        for lock in (launcher_lock, update_lock):
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("Najprv zavri otvorený simulátor alebo bežiaci update.") from error
        if authenticate:
            ensure_authentication()
        cache = workspace / ".update-git"
        target_revision = fetch(cache, repository)
        old_revision = state.get("revision")
        paths = changed_paths(cache, old_revision, target_revision)
        if target_revision == old_revision:
            return {"status": "CURRENT", "revision": target_revision, "changed_files": 0}
        incompatible = [name for name in paths
                        if name in PACKAGE_ONLY or name.startswith(PACKAGE_PREFIXES)]
        if incompatible:
            raise RuntimeError("Zmenili sa súbory základného balíka; stiahni nové úplné vydanie: " +
                               ", ".join(incompatible[:5]))
        changed = [name for name in paths if is_runtime_source(name) and not is_saved_scenario(name)]
        current = runtime_path(workspace)
        managed = {name: checksum for name, checksum in state.get("managed", {}).items()
                   if not is_saved_scenario(name)}
        for name, expected in managed.items():
            path = current / name
            if not path.is_file() or path.is_symlink() or digest(path) != expected:
                raise RuntimeError(f"Lokálne upravený súbor {name}; update ho neprepíše.")
        runs = dict(state.get("runs", {}))
        result_dir = current / "results/simulations"
        if result_dir.is_dir():
            for folder in result_dir.iterdir():
                if folder.is_dir():
                    runs.setdefault(folder.name, old_revision)
        versions = dict(state.get("versions", {}))
        if changed:
            version_dir = workspace / ".versions"
            version_dir.mkdir(exist_ok=True)
            final = version_dir / target_revision
            if final.exists():
                raise RuntimeError("Cieľová verzia už existuje mimo aktívneho stavu; skontroluj pracovný priečinok.")
            stage = Path(tempfile.mkdtemp(prefix=".pending-", dir=version_dir))
            stage.rmdir()
            try:
                copy_runtime(current, stage)
                for name in changed:
                    prior = current / name
                    if name not in managed and prior.exists():
                        raise RuntimeError(f"Nová verzia by prepísala vlastný súbor: {name}")
                    blob = source_blob(cache, target_revision, name)
                    apply_blob(stage, name, blob)
                    if blob is None:
                        managed.pop(name, None)
                    else:
                        managed[name] = digest(stage / name)
                if validate:
                    command(str(stage / ".venv/bin/python"), "-m", "compileall", "-q", "tools", cwd=stage)
                    command(str(stage / ".venv/bin/python"), "tools/simulator_cli.py", "preflight",
                            "config/simulator-example.json", cwd=stage)
                stage.rename(final)
            except Exception:
                if stage.exists():
                    shutil.rmtree(stage)
                raise
            active_relative = str(final.relative_to(workspace))
        else:
            active_relative = state["active_runtime"]
        versions[target_revision] = active_relative
        state.update(revision=target_revision, active_runtime=active_relative,
                     versions=versions, runs=runs, managed=managed)
        write_state(workspace, state)
        return {"status": "UPDATED", "revision": target_revision,
                "changed_files": len(changed), "ignored_files": len(paths) - len(changed)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("update", "runtime-path", "check-new-run-id", "adopt-package"))
    parser.add_argument("run_id", nargs="?")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    desktop = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True,
                             check=False).stdout.strip() or str(Path.home() / "Desktop")
    workspace = Path(os.environ.get("BP_SIM_WORKSPACE", str(Path(desktop) / "BP-Simulator-Workspace")))
    if args.command == "adopt-package":
        if not args.run_id:
            raise RuntimeError("Chýba cesta k novému runtime.")
        print(json.dumps(adopt_package(workspace, package, Path(args.run_id)), sort_keys=True))
        return 0
    if args.command == "runtime-path":
        print(runtime_path(workspace, args.run_id))
        return 0
    if args.command == "check-new-run-id":
        if not args.run_id:
            raise RuntimeError("Chýba ID nového behu.")
        if run_locations(workspace, read_state(workspace), args.run_id):
            raise RuntimeError(f"ID {args.run_id} už patrí staršiemu behu.")
        return 0
    expected = digest(package / "PACKAGE-MANIFEST.json")
    recorded = (workspace / "PACKAGE-ID").read_text().strip()
    if expected != recorded:
        raise RuntimeError("Pracovný runtime patrí inému základnému balíku.")
    print(json.dumps(update(workspace), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Update zlyhal: {error}", file=sys.stderr)
        raise SystemExit(1)
