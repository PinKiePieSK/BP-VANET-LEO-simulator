# Volá pripnutý C++ dekóder CAM a prevádza jeho overené ASN.1 polia do čitateľnej podoby. Používa
# sa pre detail paketu a verifier.
"""Decode Release 2 CAM UPER with the same pinned Vanetza ASN.1 library as TX."""
from __future__ import annotations

import json
import subprocess
from functools import lru_cache

from simulator_platform import ROOT, VANETZA, VANETZA_BUILD

SOURCE = ROOT / 'src/cam-decoder.cc'
BINARY = ROOT / 'build/cam-decoder'


def binary():
    if not BINARY.is_file() or BINARY.stat().st_mtime_ns < SOURCE.stat().st_mtime_ns:
        libs = sorted((VANETZA_BUILD / 'lib/static').glob('*.a'))
        if not libs:
            raise RuntimeError('Pinned Vanetza ASN.1 libraries absent')
        includes = (VANETZA, VANETZA / 'vanetza/asn1/support',
                    VANETZA / 'vanetza/asn1/its', VANETZA / 'vanetza/asn1/its/r2')
        BINARY.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['g++', '-std=c++17', '-O0', '-g0',
                        *[f'-I{p}' for p in includes], str(SOURCE),
                        '-Wl,--start-group', *map(str, libs), '-Wl,--end-group',
                        '-lboost_date_time', '-lcrypto', '-pthread', '-o', str(BINARY)],
                       cwd=ROOT, check=True, capture_output=True, timeout=60)
    return BINARY


# `decode_cam()` prekladá raw bajty na významové polia.
@lru_cache(maxsize=1024)
# Spúšťa pripnutý natívny dekóder Vanetza nad raw CAM bajtmi. Výsledok je dôkaz významu polí;
# ručné parsovanie UPER bitov by bolo náchylné na chybu.
def decode_cam(raw_hex: str):
    if len(raw_hex) > 8192 or len(raw_hex) % 2:
        return None
    try:
        bytes.fromhex(raw_hex)
        result = subprocess.run([str(binary()), raw_hex], capture_output=True,
                                text=True, timeout=3, check=False)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (ValueError, OSError, subprocess.SubprocessError, RuntimeError):
        pass
    return None


# Pripája dekódovaný význam ku konkrétnej stope paketu pre UI a verifier. Zachováva pôvodné raw
# bajty, aby preklad nebol jediným dôkazom.
def enrich(stages):
    for stage in stages:
        raw = stage.get('raw_hex', '').lower()
        if raw.startswith('0202'):
            cam = raw
        elif raw.startswith('1100') and len(raw) >= 88 and raw[80:84] == '07d1':
            cam = raw[88:]
        elif raw[:4] in ('4331', '4131') and len(raw) >= 20:
            cam = raw[20:]
        elif raw.startswith('49434231') and len(raw) >= 110:
            cam = raw[110:]
        else:
            continue
        if cam.startswith('0202'):
            stage['decoded_cam'] = decode_cam(cam)
    return stages
