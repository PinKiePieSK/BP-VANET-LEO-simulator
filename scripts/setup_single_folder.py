#!/usr/bin/env python3
"""Prepare a Git checkout in place, without a second package or workspace."""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "PinKiePieSK/BP-VANET-LEO-simulator"
DEPENDENCY_RELEASE = "v2026-11-18.2"
DEPENDENCY_SHA256 = "26aad5ec65a52e889c201ce2b9df781ad45bd24964ba5ab7a552db4e6f4ac5e9"
PBF_SHA256 = "4af3affa32fdc294ade673b409a0dc7f5c6c908875776ff06530d7bd923a9185"
ARCHIVE_ROOTS = {
    "BP-Simulator/engine/vendor/": "vendor/",
    "BP-Simulator/engine/build/": "build/",
    "BP-Simulator/engine/release/python-wheels/": "release/python-wheels/",
    "BP-Simulator/engine/data/derived/": "data/derived/",
    "BP-Simulator/engine/data/additional-input/": "data/additional-input/",
    "BP-Simulator/osm/": "release/osm/",
}


def run(*command: str, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dependencies_ready() -> bool:
    return all((ROOT / name).is_file() for name in (
        "vendor/ns-3.38-ocb-eval/ns3",
        "build/vanetza-v26.06/CMakeLists.txt",
        "build/openssl-dev-local/usr/include/openssl/ssl.h",
    )) and (ROOT / "release/python-wheels").is_dir() and \
        (ROOT / "release/osm/slovakia-261031.osm.pbf").is_file()


def github_cli() -> str | None:
    executable = shutil.which("gh")
    if executable:
        return executable
    local = ROOT / "local-bin/gh"
    return str(local) if local.is_file() and os.access(local, os.X_OK) else None


def configure_git_auth() -> None:
    if not (ROOT / ".git").exists():
        return
    executable = github_cli()
    if executable:
        helper = "!" + shlex.quote(executable) + " auth git-credential"
        run("git", "config", "--local", "credential.https://github.com.helper", helper)


def extract_dependencies(archive: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="bp-deps-", dir=ROOT) as directory:
        stage = Path(directory)
        with zipfile.ZipFile(archive) as packed:
            for item in packed.infolist():
                prefix = next((key for key in ARCHIVE_ROOTS if item.filename.startswith(key)), None)
                if prefix is None:
                    continue
                relative = PurePosixPath(item.filename[len(prefix):])
                if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
                    continue
                target = stage / ARCHIVE_ROOTS[prefix] / Path(*relative.parts)
                if not target.resolve().is_relative_to(stage.resolve()):
                    raise ValueError(f"Unsafe dependency archive path: {item.filename}")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                mode = (item.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    link = packed.read(item).decode()
                    if Path(link).is_absolute() or not (target.parent / link).resolve().is_relative_to(stage.resolve()):
                        raise ValueError(f"Unsafe dependency symlink: {item.filename}")
                    target.symlink_to(link)
                else:
                    with packed.open(item) as stream, target.open("wb") as output:
                        shutil.copyfileobj(stream, output)
                    target.chmod((item.external_attr >> 16) & 0o777 or 0o644)
        for relative in ARCHIVE_ROOTS.values():
            folder = stage / relative
            destination = ROOT / relative
            if not folder.exists():
                raise RuntimeError(f"Dependency archive lacks {relative}")
            if destination.exists():
                raise RuntimeError(f"Cannot replace existing dependency directory: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            folder.rename(destination)


def ensure_dependencies() -> None:
    if dependencies_ready():
        return
    if any((ROOT / name).exists() for name in ("vendor", "build", "release/python-wheels")):
        raise RuntimeError("Incomplete local dependencies; inspect vendor/, build/ and release/python-wheels/")
    local_archive = os.environ.get("BP_SIM_DEPENDENCY_ZIP")
    if local_archive:
        archive = Path(local_archive).expanduser().resolve()
        if sha256(archive) != DEPENDENCY_SHA256:
            raise RuntimeError("Local dependency ZIP has a different SHA-256")
        extract_dependencies(archive)
        return
    executable = github_cli()
    if not executable:
        raise RuntimeError("Install GitHub CLI (gh) and log in to access the private dependency release")
    with tempfile.TemporaryDirectory(prefix="bp-download-") as directory:
        folder = Path(directory)
        run(executable, "release", "download", DEPENDENCY_RELEASE, "--repo", REPOSITORY,
            "--pattern", "BP-Simulator.zip", "--dir", str(folder))
        archive = folder / "BP-Simulator.zip"
        if sha256(archive) != DEPENDENCY_SHA256:
            raise RuntimeError("Downloaded dependency ZIP has a different SHA-256")
        extract_dependencies(archive)


def ensure_osm() -> None:
    source = ROOT / "release/osm/slovakia-261031.osm.pbf"
    if sha256(source) != PBF_SHA256:
        raise RuntimeError("Bundled Slovakia OSM input has a different SHA-256")
    target = ROOT / "imports/osm"
    target.mkdir(parents=True, exist_ok=True)
    for name in (source.name, source.name + ".md5", "slovakia.poly"):
        destination = target / name
        if not destination.exists():
            shutil.copy2(ROOT / "release/osm" / name, destination)
    if sha256(target / source.name) != PBF_SHA256:
        raise RuntimeError("Local Slovakia OSM input has a different SHA-256")
    manifest = target / "slovakia-261031.manifest.json"
    if not manifest.exists():
        manifest.write_text(json.dumps({
            "source": "Geofabrik OpenStreetMap extract",
            "url": "https://download.geofabrik.de/europe/slovakia-261031.osm.pbf",
            "source_data_utc": "2026-10-31T21:23:06Z",
            "prepared_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "distribution": "pinned GitHub dependency release",
            "file": source.name, "size_bytes": source.stat().st_size,
            "sha256": PBF_SHA256, "official_md5": "aae555909069471a265628a112f0ff34",
            "official_md5_verified": True, "coverage_polygon": "slovakia.poly",
            "license": "OpenStreetMap ODbL 1.0; attribution: OpenStreetMap contributors",
        }, indent=2) + "\n")


def ensure_python() -> None:
    if not (ROOT / ".venv/bin/python").is_file():
        executable = os.environ.get("BP_SIM_PYTHON") or shutil.which("python3.12")
        if not executable:
            raise RuntimeError("Install Python 3.12 before preparing the simulator")
        run(executable, "-m", "venv", str(ROOT / ".venv"))
    python = str(ROOT / ".venv/bin/python")
    for requirements, hashed in (("requirements-orbits.txt", True),
                                 ("requirements-orbit-validation.txt", False),
                                 ("requirements-p5-analysis.txt", False)):
        command = [python, "-m", "pip", "install", "--no-index", "--find-links", "release/python-wheels"]
        if hashed:
            command.append("--require-hashes")
        run(*command, "-r", requirements)
    run(python, "-m", "pip", "check")


def ensure_native() -> None:
    static = ROOT / "build/vanetza-v26.06-cmake/lib/static/libvanetza_asn1_its_r2.a"
    if not static.is_file():
        alias = Path(tempfile.gettempdir()) / ("bp-openssl-" + hashlib.sha256(str(ROOT).encode()).hexdigest()[:12])
        if alias.exists() and not alias.is_symlink():
            raise RuntimeError(f"OpenSSL alias is occupied: {alias}")
        alias.unlink(missing_ok=True)
        alias.symlink_to(ROOT / "build/openssl-dev-local", target_is_directory=True)
        run("cmake", "-S", "build/vanetza-v26.06", "-B", "build/vanetza-v26.06-cmake",
            "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTS=OFF", "-DBUILD_SOCKTAP=OFF",
            "-DVANETZA_WITH_GEOGRAPHICLIB=OFF", "-DVANETZA_WITH_CRYPTOPP=OFF",
            "-DVANETZA_WITH_OPENSSL=ON", f"-DOPENSSL_INCLUDE_DIR={alias}/usr/include",
            "-DOPENSSL_CRYPTO_LIBRARY=/lib/x86_64-linux-gnu/libcrypto.so.3",
            "-DOPENSSL_SSL_LIBRARY=/lib/x86_64-linux-gnu/libssl.so.3",
            "-DCMAKE_C_FLAGS=", f"-DCMAKE_CXX_FLAGS=-I{alias}/usr/include/x86_64-linux-gnu")
        run("cmake", "--build", "build/vanetza-v26.06-cmake", "--target", "btp", "asn1_its_r2",
            "--parallel", os.environ.get("BP_BUILD_JOBS", "2"))
    checkout = ROOT / "vendor/ns-3.38-ocb-eval"
    library = checkout / "build/lib/libns3.38-satellite-debug.so"
    if not library.is_file():
        python = str(ROOT / ".venv/bin/python")
        link = checkout / "contrib/satellite/data/additional-input"
        link.unlink(missing_ok=True)
        link.symlink_to(Path("../../../../../data/additional-input"), target_is_directory=True)
        cmake_args = [
            "-DNS3_ENABLED_MODULES=core;network;mobility;internet;applications;point-to-point;csma;buildings;wifi;wave;satellite;traffic;magister-stats",
            "-DCMAKE_CXX_FLAGS=-O0",
        ]
        if shutil.which("gcc-13") and shutil.which("g++-13"):
            cmake_args.extend((f"-DCMAKE_C_COMPILER={shutil.which('gcc-13')}",
                               f"-DCMAKE_CXX_COMPILER={shutil.which('g++-13')}"))
        run(python, "./ns3", "configure", "--build-profile=debug", "--enable-examples", "--disable-tests", "--",
            *cmake_args, cwd=checkout)
        run(python, "./ns3", "build", "sat-cbr-example", "-j", os.environ.get("BP_BUILD_JOBS", "2"), cwd=checkout)
        run("cmake", "--build", "cmake-cache", "--target", "libwave", "libcsma", "libbuildings",
            "--parallel", os.environ.get("BP_BUILD_JOBS", "2"), cwd=checkout)
    sys.path.insert(0, str(ROOT / "tools"))
    from simulator_platform import repair_generated_ns3_headers
    repair_generated_ns3_headers()


def main() -> None:
    if not (ROOT / "tools/simulator_cli.py").is_file():
        raise RuntimeError("Run setup from the simulator Git project")
    required = ("git", "g++", "cmake", "ninja", "sumo", "netconvert", "pkg-config", "zstd")
    missing = [name for name in required if not shutil.which(name)]
    if missing:
        raise RuntimeError("Install system build tools before setup: " + ", ".join(missing))
    configure_git_auth()
    ensure_dependencies()
    ensure_osm()
    ensure_python()
    ensure_native()
    run(str(ROOT / ".venv/bin/python"), "tools/simulator_cli.py", "preflight", "config/simulator-example.json")
    if os.environ.get("BP_SIM_SKIP_SHORTCUT") != "1":
        run(sys.executable, "scripts/install_local_shortcut.py")
    print(f"PASS: one simulator folder at {ROOT}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
