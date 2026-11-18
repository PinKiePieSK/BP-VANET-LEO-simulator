#!/usr/bin/env bash
set -uo pipefail
package="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$package/update.py" update
status=$?
if [[ -t 0 ]]; then
  read -r -p 'Stlač Enter na zatvorenie okna… ' _
fi
exit "$status"
