# Zostavenie spoločného natívneho paketového programu z vlastného C++ zdroja a knižníc ns-3, SNS-3
# a Vanetza.
"""Compile the integrated ns-3/Vanetza/SNS-3 packet program."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from simulator_platform import CHECKOUT, OPENSSL, ROOT, VANETZA, VANETZA_BUILD


# Preklad používa knižnice jediného podporovaného runtime ns-3.38/SNS-3 3.38 a uloží build log.
# Výstup je jeden proces pre pozemnú aj satelitnú paketovú vetvu.
def compile_packet_engine(output: Path, source: Path) -> Path:
    """Use the same libraries and compiler options as the verified native runner."""
    libraries = sorted((VANETZA_BUILD / "lib/static").glob("*.a"))
    if not libraries:
        raise RuntimeError("Vanetza static libraries absent")
    includes = [CHECKOUT / "build/include", VANETZA, OPENSSL,
                OPENSSL / "x86_64-linux-gnu", VANETZA / "vanetza/asn1/support",
                VANETZA / "vanetza/asn1/its", VANETZA / "vanetza/asn1/its/r2"]
    binary = output / "simulator-packet-engine"
    modules = ("buildings", "satellite", "point-to-point", "internet", "wave",
               "wifi", "mobility", "propagation", "network", "core")
    argv = ["g++", "-std=c++17", "-O0", "-g0", *(f"-I{item}" for item in includes),
            str(source), "-Wl,--start-group", *(str(item) for item in libraries),
            "-Wl,--end-group", f"-L{CHECKOUT / 'build/lib'}",
            f"-Wl,-rpath,{CHECKOUT / 'build/lib'}",
            *(f"-lns3.38-{module}-debug" for module in modules),
            "-lboost_date_time", "/lib/x86_64-linux-gnu/libcrypto.so.3",
            "-pthread", "-o", str(binary)]
    with (output / "build.log").open("w") as stream:
        completed = subprocess.run(argv, cwd=ROOT, stdout=stream,
                                   stderr=subprocess.STDOUT,
                                   env=dict(os.environ, NS_LOG=""), timeout=180)
    if completed.returncode:
        log = (output / "build.log").read_text()
        raise RuntimeError(f"Native build failed ({completed.returncode}); {output / 'build.log'}\n"
                           + log[-4000:])
    return binary
