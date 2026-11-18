#!/usr/bin/env bash
set -euo pipefail
package="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
desktop="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
desktop="${desktop:-$HOME/Desktop}"
workspace="${BP_SIM_WORKSPACE:-$desktop/BP-Simulator-Workspace}"
export BP_SIM_WORKSPACE="$workspace"
runtime="$workspace/runtime"
if [[ ! -f "$workspace/READY" || ! -x "$runtime/.venv/bin/python" ]]; then
  echo 'Run bash setup.sh first.' >&2
  exit 2
fi
package_id="$(sha256sum "$package/PACKAGE-MANIFEST.json" | cut -d' ' -f1)"
if [[ ! -f "$workspace/PACKAGE-ID" || "$(cat "$workspace/PACKAGE-ID")" != "$package_id" ]]; then
  echo 'This workspace belongs to a different simulator package. Run setup.sh in a fresh workspace.' >&2
  exit 2
fi
cd "$runtime"
command="${1:-}"
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
