"""Decode actual Release 2 DENM UPER with the pinned Vanetza ASN.1 library."""
from __future__ import annotations

import json
import subprocess
from functools import lru_cache

from simulator_platform import ROOT, VANETZA, VANETZA_BUILD

SOURCE = ROOT / 'src/denm-decoder.cc'
BINARY = ROOT / 'build/denm-decoder'


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


@lru_cache(maxsize=4096)
def decode_denm(raw_hex: str):
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
