#!/usr/bin/env python3
"""Create the current simulator source bundle and relocatable ZIP."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "BP-Simulator"
PINNED_SCENARIOS = {"realna-d1-pozemna", "realna-d1-satelit",
                    "navrh-koridor-pozemna", "navrh-koridor-satelit"}
sys.path.insert(0, str(ROOT / "tools"))
from simulator_inventory import VIEWER_FILES


def active_tool_files() -> set[str]:
    """Follow imports of the current CLI and server entry points."""
    folder = ROOT / "tools"
    modules = {path.stem: path for path in folder.glob("*.py")}
    pending = ["simulator_cli", "simulator_server", "fetch_orbits"]
    seen = set(pending)
    scripts = set()
    while pending:
        path = modules[pending.pop()]
        module_name = path.stem
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
        references = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                references.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                references.add(node.module.split(".")[0])
        if module_name in {"simulator_cli", "simulator_satellite_runner", "simulator_ground_runner", "simulator_ground_verifier"}:
            # These files are also recorded by SHA in current run manifests.
            scripts.update(re.findall(r"tools/([A-Za-z_][A-Za-z0-9_-]*\.(?:py|sh))", source))
        for name in references:
            if name in modules and name not in seen and not name.startswith("test_"):
                seen.add(name)
                pending.append(name)
    return {name + ".py" for name in seen} | scripts


def active_src_files() -> set[str]:
    folder = ROOT / "src"
    available = {path.name: path for path in folder.iterdir() if path.is_file()}
    # Only the current packet engines; historical probes are kept outside the package.
    needed = {"vanet-ground-network.cc", "vanet-leo-network.cc",
              "cam-decoder.cc", "denm-decoder.cc"}
    missing = needed - set(available)
    if missing:
        raise FileNotFoundError(f"active native sources missing: {sorted(missing)}")
    pending = list(needed)
    while pending:
        source = available[pending.pop()].read_text(errors="replace")
        for name in re.findall(r'#include\s+"([A-Za-z0-9_.-]+)"', source):
            if name in available and name not in needed:
                needed.add(name)
                pending.append(name)
    return needed


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def ignore(directory: str, entries: list[str]) -> set[str]:
    here = Path(directory)
    result = {name for name in entries if name in {"__pycache__", ".pytest_cache", "results", ".venv", "archive"}
              or name.endswith((".pyc", ".pyo"))}
    if here == ROOT / "tools":
        keep = active_tool_files()
        result |= set(entries) - keep
    if here == ROOT / "config":
        keep = {"ground-radio-reference.json", "orbit-iridium-reference.json",
                "orbit-globalstar-reference.json", "orbit-starlink-reference.json",
                "ground-experiment.json",
                "simulator-example.json", "simulator-smoke.json",
                "simulator-starlink.json", "simulator-iridium.json",
                "simulator-globalstar.json", "scenarios"}
        result |= set(entries) - keep
    if here == ROOT / "config/scenarios":
        result |= set(entries) - {name + ".json" for name in PINNED_SCENARIOS}
    if here == ROOT / "data/inputs":
        result |= set(entries) - {"simulator-examples", "user"}
    if here == ROOT / "data/derived":
        result |= set(entries) - {"terrain-cache"}
    if here == ROOT / "data/inputs/user":
        # Only the four paired examples accompany their saved scenario files.
        result |= set(entries) - PINNED_SCENARIOS
    if here == ROOT / "src":
        result |= set(entries) - active_src_files()
    if here == ROOT / "viewer":
        keep = {name.split("/", 1)[0] for name in VIEWER_FILES}
        result |= set(entries) - keep
    if here == ROOT / "vendor/ns-3.38-ocb-eval":
        result |= {"build", "cmake-cache", ".lock-ns3_linux_build", "trace.csv",
                   "editable-v2_decoded.csv", "editable-v2_mobility.csv"}
        result |= {name for name in entries if name.endswith((".pcap", ".log"))}
    if here == ROOT / "vendor/ns-3.38-ocb-eval/contrib/satellite/data/antennapatterns":
        pinned = {"BpTwoLeoIslPinned20261022", "BpTwoLeoStaticUtPinned20261022"}
        result |= {name for name in entries if name.startswith("Bp") and name not in pinned}
    if here == ROOT / "vendor/ns-3.38-ocb-eval/contrib/satellite/data/constellations":
        # Native runs create these inputs again from the pinned orbit archive.
        result |= {name for name in entries if name.startswith("bp-")}
    if here == ROOT / "vendor/ns-3.38-ocb-eval/contrib/satellite/data/sims/default":
        result |= {"SimInfo.log", "SimDiff.log"}
    if here == ROOT / "build/vanetza-v26.06":
        result |= {name for name in entries if name.endswith((".log", ".pcap"))}
    return result


def copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir() and not source.is_symlink():
        shutil.copytree(source, target, symlinks=True, ignore=ignore)
    elif source.is_symlink():
        target.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, target)


def inventory(folder: Path) -> dict[str, dict]:
    records = {}
    for path in sorted(folder.rglob("*")):
        rel = str(path.relative_to(folder))
        if rel == "PACKAGE-MANIFEST.json":
            continue
        if path.is_symlink():
            records[rel] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            records[rel] = {"kind": "file", "bytes": path.stat().st_size, "sha256": digest(path)}
    return records


def verify(folder: Path) -> dict:
    manifest = json.loads((folder / "PACKAGE-MANIFEST.json").read_text())
    if manifest.get("schema_version") != 1 or manifest.get("runtime") != "ns-3.38/SNS-3 3.38":
        raise ValueError("portable package schema/runtime mismatch")
    actual = inventory(folder)
    if actual != manifest["contents"]:
        missing = set(manifest["contents"]) - set(actual)
        extra = set(actual) - set(manifest["contents"])
        changed = {key for key in set(actual) & set(manifest["contents"])
                   if actual[key] != manifest["contents"][key]}
        raise ValueError(f"portable package changed: missing={sorted(missing)[:4]}, "
                         f"extra={sorted(extra)[:4]}, changed={sorted(changed)[:4]}")
    return {"status": "PASS", "files_and_links": len(actual)}


def desktop() -> Path:
    try:
        value = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True).strip()
        if value:
            return Path(value).expanduser()
    except (OSError, subprocess.CalledProcessError):
        pass
    return Path.home() / "Desktop"


def create(destination: Path) -> dict:
    destination = destination.resolve()
    archive = destination.with_suffix(".zip")
    if destination.exists() or archive.exists():
        raise ValueError("portable folder or ZIP already exists; choose a new destination")
    destination.mkdir(parents=True)
    for rel in ("src", "tools", "config", "viewer", "data/inputs", "data/orbits",
                "data/derived", "build/vanetza-v26.06",
                "build/openssl-dev-local", "vendor/ns-3.38-ocb-eval",
                "requirements-orbits.txt", "requirements-orbit-validation.txt",
                "requirements-p5-analysis.txt"):
        copy(ROOT / rel, destination / "engine" / rel)
    copy(ROOT / "release/python-wheels", destination / "engine/release/python-wheels")
    copy(ROOT / "release/osm", destination / "osm")
    # Point the runtime input directory at the bundled antenna patterns.
    additional = destination / "engine/data/additional-input"
    additional.mkdir()
    (additional / "antennapatterns").symlink_to(
        "../../vendor/ns-3.38-ocb-eval/contrib/satellite/data/antennapatterns")
    (destination / "engine/vendor/ns-3.38-ocb-eval/scratch/vanet-sns3.cc").unlink(missing_ok=True)
    (destination / "engine/vendor/ns-3.38-ocb-eval/contrib/satellite/data/additional-input").unlink(missing_ok=True)
    for source, name in (("portable_setup.sh", "setup.sh"), ("portable_run.sh", "run.sh"),
                         ("portable_import.sh", "import.sh"), ("portable_verify.py", "verify.py"),
                         ("portable_launch.py", "launch.py"),
                         ("portable_install_shortcut.py", "install_shortcut.py"),
                         ("bp-simulator.svg", "bp-simulator.svg")):
        copy(ROOT / "scripts" / source, destination / name)
    copy(ROOT / "docs/simulator-odovzdanie.md", destination / "README.md")
    copy(ROOT / "docs/technicka-sprava-simulatora-2026-11-18.md", destination / "TECHNICKA-SPRAVA.md")
    for link in (destination / "engine/build/openssl-dev-local").rglob("*"):
        if link.is_symlink() and not link.exists():
            link.unlink()
    payload = {"schema_version": 1, "runtime": "ns-3.38/SNS-3 3.38",
               "support": "Ubuntu 24.04 x86_64, CPython 3.12", "contents": inventory(destination)}
    (destination / "PACKAGE-MANIFEST.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    verify(destination)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as packed:
        for path in sorted(destination.rglob("*")):
            rel = str(Path(NAME) / path.relative_to(destination))
            if path.is_dir() and not path.is_symlink():
                info = zipfile.ZipInfo(rel + "/")
                info.create_system = 3
                info.external_attr = (0o40755 << 16)
                packed.writestr(info, b"")
            elif path.is_symlink():
                info = zipfile.ZipInfo(rel)
                info.create_system = 3
                info.external_attr = (0o120777 << 16)
                packed.writestr(info, os.readlink(path))
            else:
                packed.write(path, rel)
    return {"status": "PACKAGED", "folder": str(destination), "zip": str(archive),
            "zip_bytes": archive.stat().st_size, "zip_sha256": digest(archive),
            "files_and_links": len(payload["contents"])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=desktop() / NAME)
    args = parser.parse_args()
    print(json.dumps(create(args.destination), sort_keys=True))
