"""Select an immutable, hash-pinned OMM archive for every simulator orbit consumer."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from simulator_platform import ROOT, sha
from fetch_orbits import verify_snapshot

GROUP_REFERENCE = {
    'iridium-NEXT': 'config/orbit-iridium-reference.json',
    'globalstar': 'config/orbit-globalstar-reference.json',
    'starlink': 'config/orbit-starlink-reference.json',
}
SNAPSHOT_PATH = re.compile(r'data/orbits/[A-Za-z0-9_-]+\Z')
SHA256 = re.compile(r'[a-f0-9]{64}\Z')


def validate_pin(pin: dict, group: str | None = None) -> dict:
    if (type(pin) is not dict or set(pin) != {'path', 'manifest_sha256'} or
            type(pin['path']) is not str or not SNAPSHOT_PATH.fullmatch(pin['path']) or
            type(pin['manifest_sha256']) is not str or not SHA256.fullmatch(pin['manifest_sha256'])):
        raise ValueError('Neplatný odkaz na orbitálny archív alebo SHA-256')
    folder = ROOT / pin['path']
    if folder.is_symlink() or not folder.is_dir() or not (folder / 'manifest.json').is_file():
        raise ValueError('Pripnutý orbitálny archív chýba')
    if sha(folder / 'manifest.json') != pin['manifest_sha256']:
        raise ValueError('Pripnutý orbitálny archív má iný SHA-256 manifestu')
    manifest = verify_snapshot(folder)
    if group is not None and group not in manifest['groups']:
        raise ValueError(f'V archíve chýba konštelácia {group}')
    return manifest


def config_for(group: str, satellite: dict | None, origin: str | None = None,
               duration_s: float = 15) -> dict:
    if group not in GROUP_REFERENCE:
        raise ValueError('Neznáma konštelácia')
    config = json.loads((ROOT / GROUP_REFERENCE[group]).read_text())
    pin = satellite.get('orbit_snapshot') if satellite else None
    if pin is not None:
        manifest = validate_pin(pin, group)
        config['snapshot'] = dict(pin)
        if origin is not None:
            record = manifest['groups'][group]
            start = datetime.fromisoformat(origin.replace('Z', '+00:00'))
            earliest = datetime.fromisoformat(record['earliest_epoch_utc'])
            latest = datetime.fromisoformat(record['latest_epoch_utc'])
            if start < earliest or start + timedelta(seconds=duration_s) > latest + timedelta(hours=config['max_age_h']):
                raise ValueError(f'{group}: zvolený UTC čas je mimo 48-hodinového okna pripnutých OMM; vyber novší archív alebo iný čas')
    return config


def snapshots() -> list[dict]:
    listed = []
    for manifest_path in sorted((ROOT / 'data/orbits').glob('*/manifest.json'), reverse=True):
        pin = {'path': str(manifest_path.parent.relative_to(ROOT)),
               'manifest_sha256': sha(manifest_path)}
        try:
            manifest = validate_pin(pin)
        except (ValueError, OSError, KeyError, json.JSONDecodeError):
            continue
        listed.append({**pin, 'fetched_utc': manifest['fetched_utc'],
                       'provider': manifest['provider'], 'groups': sorted(manifest['groups'])})
    return listed


def newest_default() -> tuple[dict, str]:
    choices = snapshots()
    if not choices:
        raise ValueError('Nie je dostupný žiadny overený orbitálny archív')
    selected = choices[0]
    fetched = datetime.fromisoformat(selected['fetched_utc']).astimezone(timezone.utc)
    return ({key: selected[key] for key in ('path', 'manifest_sha256')},
            fetched.strftime('%Y-%m-%dT%H:%M:%SZ'))
