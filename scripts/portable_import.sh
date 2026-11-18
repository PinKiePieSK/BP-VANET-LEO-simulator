#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 && -f "$1" ]] || { echo 'Usage: bash import.sh /path/to/input.json-or-csv' >&2; exit 2; }
desktop="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
desktop="${desktop:-$HOME/Desktop}"
workspace="${BP_SIM_WORKSPACE:-$desktop/BP-Simulator-Workspace}"
[[ -f "$workspace/READY" ]] || { echo 'Run bash setup.sh first.' >&2; exit 2; }
name="$(basename -- "$1")"
case "$name" in
  *.json|*.csv|*.osm|*.xml) ;;
  *) echo 'Supported input file extensions: .json, .csv, .osm, .xml' >&2; exit 2 ;;
esac
mkdir -p "$workspace/imports" "$workspace/runtime/data/inputs/user"
[[ ! -e "$workspace/imports/$name" && ! -e "$workspace/runtime/data/inputs/user/$name" ]] || {
  echo 'Input name already exists; rename the new file to preserve previous evidence.' >&2
  exit 2
}
if [[ "$name" == *.json ]]; then
  python3 -m json.tool "$1" > /dev/null
fi
cp -- "$1" "$workspace/imports/$name"
if [[ "$name" == *.json ]]; then
  cp -- "$workspace/imports/$name" "$workspace/runtime/data/inputs/user/$name"
  echo "Imported scenario input: data/inputs/user/$name"
else
  echo "Stored raw input: $workspace/imports/$name"
  echo 'Súradnice ulož ako vstupný súbor sveta a trás pred spustením scenára.'
fi
