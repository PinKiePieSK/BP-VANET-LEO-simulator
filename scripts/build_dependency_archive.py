#!/usr/bin/env python3
"""Build the source and data archive required by setup_single_folder.py."""
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

from package_simulator import copy


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = "bp-vanet-leo-dependencies"
DIRECTORIES = (
    "vendor/ns-3.38-ocb-eval",
    "build/vanetza-v26.06",
    "build/openssl-dev-local",
    "data/derived",
    "release/python-wheels",
    "release/osm",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(destination: Path) -> tuple[int, str]:
    destination = destination.expanduser().resolve()
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bp-dependency-stage-") as temporary:
        stage = Path(temporary) / ARCHIVE_ROOT
        stage.mkdir()
        for relative in DIRECTORIES:
            copy(ROOT / relative, stage / relative)
        additional = stage / "data/additional-input"
        additional.mkdir()
        (additional / "antennapatterns").symlink_to(
            "../../vendor/ns-3.38-ocb-eval/contrib/satellite/data/antennapatterns")
        (stage / "vendor/ns-3.38-ocb-eval/scratch/vanet-sns3.cc").unlink(missing_ok=True)
        (stage / "vendor/ns-3.38-ocb-eval/contrib/satellite/data/additional-input").unlink(missing_ok=True)
        for link in (stage / "build/openssl-dev-local").rglob("*"):
            if link.is_symlink() and not link.exists():
                link.unlink()
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for path in sorted(stage.rglob("*")):
                name = str(path.relative_to(stage.parent))
                if path.is_symlink():
                    target = os.readlink(path)
                    if Path(target).is_absolute() or not (path.parent / target).resolve().is_relative_to(stage.resolve()):
                        raise ValueError(f"Symlink outside archive: {name}")
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                    archive.writestr(info, target)
                elif path.is_dir():
                    info = zipfile.ZipInfo(name + "/")
                    info.create_system = 3
                    info.external_attr = 0o40755 << 16
                    archive.writestr(info, b"")
                else:
                    archive.write(path, name)
    return destination.stat().st_size, sha256(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    size, digest = build(parser.parse_args().destination)
    print(f"bytes={size} sha256={digest}")
