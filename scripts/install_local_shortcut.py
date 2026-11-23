#!/usr/bin/env python3
"""Point the desktop icon at the single local Git project."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def desktop() -> Path:
    try:
        path = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
        if path:
            return Path(path).expanduser()
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
    shutil.copy2(ROOT / "scripts/bp-simulator.svg", icon_dir / "bp-simulator.svg")
    target = target_dir / "BP-Simulator.desktop"
    target.write_text(
        "[Desktop Entry]\nVersion=1.0\nType=Application\nName=BP Simulátor\n"
        "Comment=Spustiť simulátor z jediného projektového priečinka\n"
        f"Exec=python3 {quoted(ROOT / 'scripts/launch_local.py')}\n"
        f"Path={ROOT}\nIcon=bp-simulator\nTerminal=false\n"
        "StartupNotify=true\nCategories=Education;Science;\nActions=Update;\n\n"
        "[Desktop Action Update]\nName=Aktualizovať simulátor\n"
        f"Exec=python3 {quoted(ROOT / 'scripts/update_local.py')}\n"
        f"Path={ROOT}\nTerminal=true\n")
    target.chmod(0o755)
    gio = shutil.which("gio")
    if gio:
        subprocess.run([gio, "set", str(target), "metadata::trusted", "true"],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return target


if __name__ == "__main__":
    print(install())
