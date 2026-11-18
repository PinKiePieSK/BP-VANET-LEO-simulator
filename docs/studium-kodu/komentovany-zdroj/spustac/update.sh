#!/usr/bin/env bash
# Terminálový vstup pre ručný update. Po skončení nechá okno otvorené, aby bolo vidieť úspech
# alebo chybu prihlásenia, sťahovania či preflightu.
set -uo pipefail
# `package` určuje cestu alebo režim spúšťača: `"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`.
package="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$package/update.py" update
status=$?
if [[ -t 0 ]]; then
  read -r -p 'Stlač Enter na zatvorenie okna… ' _
fi
exit "$status"
