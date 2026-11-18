# Stiahne a uloží pripnutý orbitálny archív. Archív je vstupom pre SGP4 polohy a musí mať pôvod a
# hash, aby sa beh dal zopakovať.
"""Snapshot current GP/OMM JSON for named constellation groups.

Inputs: CelesTrak GROUP endpoints or documented Space-Track/CelesTrak mirrors.
Output: gzip raw JSON
and a provenance manifest under data/orbits/<UTC>. Uses a two-hour local cache,
one request per group, no redirect/retry on HTTP errors. These GP sets list
tracked objects, not a guaranteed roster of operational service satellites.
"""

import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/orbits"
GROUPS = {"starlink": "STARLINK", "iridium-NEXT": "IRIDIUM", "globalstar": "GLOBALSTAR"}
MAX_BYTES = 32 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise HTTPError(request.full_url, code, f"Redirect refused: {newurl}", headers, fp)


# Overí uložený orbitálny archív, jeho manifest a hashe. Bez platného archívu by opakovanie
# výsledku mohlo použiť už aktualizované TLE.
def verify_snapshot(path: Path) -> dict:
    """Check a complete frozen download before it may be reused."""
    manifest = json.loads((path / "manifest.json").read_text())
    if manifest.get("schema") != 1 or set(manifest.get("groups", {})) != set(GROUPS):
        raise ValueError("orbit snapshot manifest is incomplete")
    for group, record in manifest["groups"].items():
        filename = record.get("file")
        if filename != f"{group}.json.gz":
            raise ValueError(f"{group}: unexpected orbit archive path")
        packed = (path / filename).read_bytes()
        if hashlib.sha256(packed).hexdigest() != record["gzip_sha256"]:
            raise ValueError(f"{group}: compressed orbit hash mismatch")
        raw = gzip.decompress(packed)
        if hashlib.sha256(raw).hexdigest() != record["raw_sha256"]:
            raise ValueError(f"{group}: raw orbit hash mismatch")
        if len(json.loads(raw)) != record["objects"]:
            raise ValueError(f"{group}: orbit object count mismatch")
    return manifest


def recent_snapshot(now, provider):
    for path in sorted(DEST.glob("*/manifest.json"), reverse=True):
        manifest = json.loads(path.read_text())
        fetched = datetime.fromisoformat(manifest["fetched_utc"])
        if (0 <= (now - fetched).total_seconds() < 7200 and
                set(manifest["groups"]) == set(GROUPS) and manifest["provider"] == provider):
            verify_snapshot(path.parent)
            return path.parent
    return None


# Stiahne nový archív a zapíše jeho pôvod, čas a kontrolné súčty. Sťahovanie je príprava vstupu;
# neprebieha počas uzavretého paketového behu.
def fetch(now, provider):
    cached = recent_snapshot(now, provider)
    if cached:
        return cached, "cached"
    incomplete = [p for p in DEST.glob(f"*-{provider}") if p.is_dir() and
                  not (p / "manifest.json").exists() and
                  0 <= now.timestamp() - p.stat().st_mtime < 7200]
    snapshot = max(incomplete) if incomplete else DEST / (
        now.strftime("%Y%m%dT%H%M%SZ") + "-" + provider)
    snapshot.mkdir(parents=True, exist_ok=True)
    opener = build_opener(NoRedirect())
    groups = {}
    for group, prefix in GROUPS.items():
        output = snapshot / f"{group}.json.gz"
        mirror_status = None
        if provider == "retlector" and not output.exists():
            status_url = f"https://retlector.eu/{group}/status"
            with opener.open(Request(status_url, headers={"User-Agent": "VANET-LEO-BP-orbit-snapshot/1.0"}),
                             timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"{group}: mirror status HTTP {response.status}; stopped")
                mirror_status = response.read(4096).decode("utf-8")
            fields = dict(line.split(": ", 1) for line in mirror_status.splitlines() if ": " in line)
            if (fields.get("Status") not in ("Fresh", "Stale") or
                    int(fields.get("Age", "999999").split()[0]) > 86400):
                raise RuntimeError(f"{group}: mirror cache exceeds 24 h or has no usable data; stopped")
        if provider == "celestrak":
            url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=JSON"
        elif provider == "retlector":
            url = f"https://retlector.eu/{group}/json"
        else:
            url = f"https://www.orbicentral.net/gp.php?GROUP={group}&FORMAT=json"
        if output.exists():
            raw = gzip.decompress(output.read_bytes())
        else:
            request = Request(url, headers={"User-Agent": "VANET-LEO-BP-orbit-snapshot/1.0"})
            with opener.open(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError(f"{group}: HTTP {response.status}; stopped")
                raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError(f"{group}: response larger than {MAX_BYTES} bytes")
        objects = json.loads(raw)
        if not isinstance(objects, list) or not objects:
            raise ValueError(f"{group}: empty or invalid OMM JSON")
        if any(not isinstance(o, dict) or not str(o.get("OBJECT_NAME", "")).startswith(prefix)
               or "EPOCH" not in o or "NORAD_CAT_ID" not in o for o in objects):
            raise ValueError(f"{group}: unexpected object name or missing OMM fields")
        ids = [str(o["NORAD_CAT_ID"]) for o in objects]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{group}: duplicate catalog number")
        if any(o.get("TIME_SYSTEM", "UTC") != "UTC" for o in objects):
            raise ValueError(f"{group}: OMM TIME_SYSTEM is not UTC")
        epochs = [datetime.fromisoformat(o["EPOCH"].replace("Z", "+00:00")) for o in objects]
        epochs = [e if e.tzinfo else e.replace(tzinfo=timezone.utc) for e in epochs]
        ages_h = [(now - e).total_seconds() / 3600 for e in epochs]
        if not any(0 <= age <= 48 for age in ages_h):
            raise ValueError(f"{group}: no orbit element is fresh enough for a new experiment")
        if not output.exists():
            output.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
        groups[group] = {"source_url": url, "file": output.name,
                         "mirror_cache_status": mirror_status,
                         "retrieved_utc": datetime.fromtimestamp(output.stat().st_mtime,
                                                                  timezone.utc).isoformat(),
                         "raw_sha256": hashlib.sha256(raw).hexdigest(),
                         "gzip_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                         "objects": len(objects), "earliest_epoch_utc": min(epochs).isoformat(),
                         "latest_epoch_utc": max(epochs).isoformat(),
                         "epoch_age_hours_min": round(min(ages_h), 3),
                         "epoch_age_hours_max": round(max(ages_h), 3),
                         "epoch_within_48h": sum(0 <= age <= 48 for age in ages_h),
                         "catalog_numbers_over_99999": sum(int(i) > 99999 for i in ids)}
    manifest = {"schema": 1, "fetched_utc": now.isoformat(), "provider": provider,
                "upstream": {"celestrak": "CelesTrak GP",
                             "retlector": "CelesTrak GP",
                             "orbicentral": "Space-Track GP"}.get(provider),
                "format": "CelesTrak GP OMM-keyword JSON, raw bytes gzip with mtime 0",
                "time_system": "UTC; CelesTrak omits redundant TIME_SYSTEM in JSON/CSV GP",
                "groups": groups,
                "scope": "tracked group objects; operational membership, beam/service status and gateways unverified",
                "usage_policy": "https://celestrak.org/usage-policy.php",
                "source_note": {"retlector": "Third-party CelesTrak cache; verify age and identity",
                                "orbicentral": "Third-party Space-Track redistribution; verify epochs",
                                "celestrak": "Direct CelesTrak GP download"}[provider]}
    (snapshot / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify_snapshot(snapshot)
    return snapshot, "downloaded"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("celestrak", "retlector", "orbicentral"),
                        default="celestrak")
    args = parser.parse_args()
    path, status = fetch(datetime.now(timezone.utc), args.provider)
    print(json.dumps({"status": status, "path": str(path),
                      "manifest": json.loads((path / "manifest.json").read_text())}))
