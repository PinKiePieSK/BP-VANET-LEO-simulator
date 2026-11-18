#!/usr/bin/env python3
"""Install a desktop entry pointing to this unpacked portable bundle."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


PACKAGE = Path(__file__).resolve().parent


def desktop() -> Path:
    try:
        value = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True,
                                        stderr=subprocess.DEVNULL).strip()
        if value:
            return Path(value).expanduser()
    except (OSError, subprocess.CalledProcessError):
        pass
    return Path.home() / "Desktop"


def quoted(path: Path) -> str:
    return '"' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '"'


def install() -> Path:
    target_dir = desktop()
    target_dir.mkdir(parents=True, exist_ok=True)
    icon_dir = Path.home() / ".local/share/icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PACKAGE / "bp-simulator.svg", icon_dir / "bp-simulator.svg")
    target = target_dir / "BP-Simulator.desktop"
    target.write_text(
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        "Name=BP Simulátor\n"
        "Comment=Spustiť simulátor a zavrieť server spolu s prehliadačom\n"
        f"Exec=python3 {quoted(PACKAGE / 'launch.py')}\n"
        f"Path={PACKAGE}\n"
        "Icon=bp-simulator\n"
        "Terminal=false\n"
        "StartupNotify=true\n"
        "Categories=Education;Science;\n")
    target.chmod(0o755)
    gio = shutil.which("gio")
    if gio:
        subprocess.run([gio, "set", str(target), "metadata::trusted", "true"],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return target


if __name__ == "__main__":
    print(install())
