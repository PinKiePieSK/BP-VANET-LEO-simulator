#!/usr/bin/env python3
"""Verify every source file in an unpacked portable simulator bundle."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "PACKAGE-MANIFEST.json").read_text())
assert manifest["schema_version"] == 1
assert manifest["runtime"] == "ns-3.38/SNS-3 3.38"
actual = {}
for path in sorted(root.rglob("*")):
    rel = str(path.relative_to(root))
    if rel == "PACKAGE-MANIFEST.json":
        continue
    if path.is_symlink():
        actual[rel] = {"kind": "symlink", "target": os.readlink(path)}
    elif path.is_file():
        value = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                value.update(chunk)
        actual[rel] = {"kind": "file", "bytes": path.stat().st_size,
                       "sha256": value.hexdigest()}
if actual != manifest["contents"]:
    missing = set(manifest["contents"]) - set(actual)
    extra = set(actual) - set(manifest["contents"])
    changed = {key for key in set(actual) & set(manifest["contents"])
               if actual[key] != manifest["contents"][key]}
    raise SystemExit(f"Package changed: missing={sorted(missing)[:5]}, "
                     f"extra={sorted(extra)[:5]}, changed={sorted(changed)[:5]}")
pins = {
    "engine/vendor/ns-3.38-ocb-eval": "392e36833ce3c7e0ecde4188043f76345402d5a7",
    "engine/vendor/ns-3.38-ocb-eval/contrib/satellite": "739a10dbe1db02fd2c4064501e4a48994e0b79f3",
    "engine/vendor/ns-3.38-ocb-eval/contrib/traffic": "c68daaf18fadd3393bbb141fedf13fb94a99b6e2",
    "engine/vendor/ns-3.38-ocb-eval/contrib/magister-stats": "c613ba7c8cbf284cf0aa24ca778974f711b56370",
    "engine/vendor/ns-3.38-ocb-eval/contrib/satellite/data": "faf7d763438b43139af3d78ff30e4130b2692bd9",
    "engine/build/vanetza-v26.06": "fb6c551030dcc12b924299bf401e35e5fe814713",
}
for relative, expected in pins.items():
    found = subprocess.check_output(["git", "-C", str(root / relative), "rev-parse", "HEAD"],
                                    text=True, stderr=subprocess.DEVNULL).strip()
    if found != expected:
        raise SystemExit(f"Wrong source pin: {relative}")
print(f"PASS: {len(actual)} source files and links verified")
