#!/usr/bin/env python3
"""Build the Slovak annotated reading copy without changing simulation sources."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import textwrap
from pathlib import Path

from study_auto_comments import automatic_comments


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from simulator_inventory import STUDY_UI_FILES
BASE = ROOT / "docs/studium-kodu"
NOTES = BASE / "komentare.json"
OUTPUT = BASE / "komentovany-zdroj"
LAUNCHERS = {"portable_setup.sh": "setup.sh", "portable_run.sh": "run.sh",
             "portable_import.sh": "import.sh", "portable_verify.py": "verify.py",
             "portable_launch.py": "launch.py",
             "portable_update.py": "update.py", "portable_update.sh": "update.sh",
             "portable_install_shortcut.py": "install_shortcut.py"}
def active_sources() -> dict[str, Path]:
    """Use the same allowlists as the portable package, then add its launchers."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from package_simulator import active_src_files, active_tool_files

    files = {f"src/{name}": ROOT / "src" / name for name in active_src_files()}
    files.update({f"tools/{name}": ROOT / "tools" / name for name in active_tool_files()})
    files.update({f"viewer/{name}": ROOT / "viewer" / name for name in STUDY_UI_FILES})
    files.update({f"spustac/{name}": ROOT / "scripts" / original
                  for original, name in LAUNCHERS.items()})
    return dict(sorted(files.items()))


def comment_block(path: str, prose: str, indent: str = "") -> str:
    """Render ordinary source comments without visible study delimiters."""
    extension = Path(path).suffix
    width = max(58, 96 - len(indent))
    lines = []
    for paragraph in prose.strip().splitlines():
        lines.extend(textwrap.wrap(paragraph, width=width,
                                   break_long_words=False, break_on_hyphens=False)
                     if paragraph.strip() else [""])
    if extension in {".py", ".sh"}:
        return "".join(f"{indent}# {line}\n" if line else f"{indent}#\n" for line in lines)
    if extension == ".html":
        return indent + "<!--\n" + "".join(f"{indent}{line}\n" for line in lines) + indent + "-->\n"
    if extension == ".css":
        return indent + "/*\n" + "".join(f"{indent} * {line}\n" for line in lines) + indent + " */\n"
    return "".join(f"{indent}// {line}\n" if line else f"{indent}//\n" for line in lines)


def annotate(path: str, original: str, note: dict, notes: dict[str, dict]) -> str:
    lines = original.splitlines(keepends=True)
    header = comment_block(path, note["overview"])
    # Preserve shebangs and the HTML doctype, which must precede every comment.
    insert_header = 1 if lines and (lines[0].startswith("#!") or
                                    lines[0].lower().startswith("<!doctype")) else 0
    blocks: dict[int, list[str]] = {insert_header: [header]}
    for section in note.get("sections", []):
        anchor = section["before"]
        hits = [i for i, line in enumerate(lines) if anchor in line]
        if len(hits) != 1:
            raise ValueError(f"{path}: anchor {anchor!r} occurs {len(hits)} times")
        indentation = re.match(r"\s*", lines[hits[0]]).group()
        blocks.setdefault(hits[0], []).append(comment_block(path, section["explanation"], indentation))
    # Ručné výklady pokrývajú dôležité rozhodnutia, automatika doplní vybrané funkcie.
    manual = set(blocks) - {insert_header}
    for line, explanations in automatic_comments(path, original, manual, notes).items():
        indentation = re.match(r"\s*", lines[line]).group()
        blocks.setdefault(line, []).extend(comment_block(path, prose, indentation) for prose in explanations)
    rendered = "".join("".join(blocks.get(i, ())) + line for i, line in enumerate(lines))
    rendered += "".join(blocks.get(len(lines), ()))
    # The exact original line must follow the comment planned for its position.
    cursor = 0
    for index, line in enumerate(lines):
        expected = "".join(blocks.get(index, ())) + line
        if not rendered.startswith(expected, cursor):
            raise ValueError(f"{path}: source line changed at {index + 1}")
        cursor += len(expected)
    if rendered[cursor:] != "".join(blocks.get(len(lines), ())):
        raise ValueError(f"{path}: unexpected text after source")
    return rendered


def symbols(path: str, original: str) -> list[str]:
    """Create a navigation index, not a guessed explanation of function behavior."""
    if path.endswith(".py"):
        tree = ast.parse(original)
        return [f"{node.name}()" for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    if path.endswith((".js", ".cc", ".h")):
        names = re.findall(r"\b(?:function|class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)\b", original)
        return list(dict.fromkeys(names))[:80]
    return []


def build(check: bool) -> None:
    notes = json.loads(NOTES.read_text())
    files = active_sources()
    if set(notes) != set(files):
        raise ValueError(f"annotations must cover every active file: missing={sorted(set(files)-set(notes))}, "
                         f"extra={sorted(set(notes)-set(files))}")
    stale = {str(path.relative_to(OUTPUT)) for path in OUTPUT.rglob("*") if path.is_file()} - set(files)
    if check and stale:
        raise ValueError(f"study copy contains inactive files: {sorted(stale)}")
    if not check:
        for name in stale:
            (OUTPUT / name).unlink()
    index = ["# Komentovaný aktívny kód\n",
             "Táto kópia slúži na štúdium. Spustiteľný zdroj aj prenosný ZIP zostávajú čisté. "
             "Generátor vkladá len bežné komentáre medzi nezmenené riadky pôvodného kódu.\n",
             "Po každej úprave aktívneho kódu spusti `python3 scripts/refresh_study_code.py`; "
             "príkaz `--check` skontroluje, či študijná kópia nezaostáva.\n"]
    for name, source in files.items():
        original = source.read_text()
        rendered = annotate(name, original, notes[name], notes)
        target = OUTPUT / name
        if check:
            if not target.is_file() or target.read_text() != rendered:
                raise ValueError(f"studijná kópia nie je aktuálna: {name}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered)
        digest = hashlib.sha256(original.encode()).hexdigest()[:12]
        index.append(f"## [{name}](komentovany-zdroj/{name})\n")
        index.append(notes[name]["overview"].strip().replace("\n", " ") + "\n")
        found = symbols(name, original)
        if found:
            index.append("Orientácia v súbore: " + ", ".join(f"`{s}`" for s in found) + ".\n")
        index.append(f"Pôvodný SHA-256: `{digest}…`\n")
    index_text = "\n".join(index)
    if check:
        if (BASE / "INDEX.md").read_text() != index_text:
            raise ValueError("index študijného kódu nie je aktuálny")
    else:
        (BASE / "INDEX.md").write_text(index_text)
    print(f"PASS: {len(files)} aktívnych súborov, " + ("aktuálne" if check else "vygenerované"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    build(parser.parse_args().check)
