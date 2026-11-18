#!/usr/bin/env bash
# Príkazový vstup pre preflight, beh a nezávislé overenie. Všetky tri príkazy deleguje na jeden
# aktuálny Python runner v pracovnom runtime.
set -euo pipefail
# `package` určuje cestu alebo režim spúšťača: `"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`.
package="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
desktop="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
desktop="${desktop:-$HOME/Desktop}"
# `workspace` určuje cestu alebo režim spúšťača:
# `"${BP_SIM_WORKSPACE:-$desktop/BP-Simulator-Workspace}"`.
workspace="${BP_SIM_WORKSPACE:-$desktop/BP-Simulator-Workspace}"
export BP_SIM_WORKSPACE="$workspace"
# `runtime` určuje cestu alebo režim spúšťača: `"$workspace/runtime"`.
runtime="$workspace/runtime"
if [[ ! -f "$workspace/READY" || ! -x "$runtime/.venv/bin/python" ]]; then
  echo 'Run bash setup.sh first.' >&2
  exit 2
fi
# `package_id` určuje cestu alebo režim spúšťača: `"$(sha256sum "$package/PACKAGE-MANIFEST.json" |
# cut -d' ' -f1)"`.
package_id="$(sha256sum "$package/PACKAGE-MANIFEST.json" | cut -d' ' -f1)"
if [[ ! -f "$workspace/PACKAGE-ID" || "$(cat "$workspace/PACKAGE-ID")" != "$package_id" ]]; then
  echo 'This workspace belongs to a different simulator package. Run setup.sh in a fresh workspace.' >&2
  exit 2
fi
cd "$runtime"
# `command` určuje cestu alebo režim spúšťača: `"${1:-}"`.
command="${1:-}"
# Príkazy preflight, run, verify a server sa všetky presmerujú do pripraveného pracovného runtime.
# Predtým sa porovná PACKAGE-ID; balík sa nesmie potichu používať s runtime zostaveným z iného
# zdroja.
case "$command" in
  preflight)
    scenario="${2:-config/simulator-example.json}"
    exec .venv/bin/python tools/simulator_cli.py preflight "$scenario" ;;
  run)
    scenario="${2:-config/simulator-example.json}"
    id="${3:-run-$(date -u +%Y%m%d%H%M%S)}"
    exec .venv/bin/python tools/simulator_cli.py run "$scenario" "results/simulations/$id" ;;
  verify)
    [[ $# -eq 2 ]] || { echo 'Usage: bash run.sh verify RUN_ID' >&2; exit 2; }
    exec .venv/bin/python tools/simulator_cli.py verify "results/simulations/$2" ;;
  server)
    exec .venv/bin/python tools/simulator_server.py --port "${2:-8765}" ;;
  refresh-orbits)
    [[ $# -eq 1 ]] || { echo 'Usage: bash run.sh refresh-orbits' >&2; exit 2; }
    exec .venv/bin/python tools/fetch_orbits.py --provider celestrak ;;
  *)
    echo 'Usage: bash run.sh {preflight [scenario.json]|run [scenario.json] [run-id]|verify run-id|server [port]|refresh-orbits}' >&2
    exit 2 ;;
esac
