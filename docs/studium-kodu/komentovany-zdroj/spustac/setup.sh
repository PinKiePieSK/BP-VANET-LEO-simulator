#!/usr/bin/env bash
# Pripraví systémové závislosti, Python prostredie, Vanetza a ns-3.38/SNS-3. Pri novom balíku
# uloží nový runtime vedľa pôvodného, aby staršie behy zostali overiteľné.
set -euo pipefail

# `package` určuje cestu alebo režim spúšťača: `"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`.
package="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
desktop="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
desktop="${desktop:-$HOME/Desktop}"
# `workspace` určuje cestu alebo režim spúšťača:
# `"${BP_SIM_WORKSPACE:-$desktop/BP-Simulator-Workspace}"`.
workspace="${BP_SIM_WORKSPACE:-$desktop/BP-Simulator-Workspace}"
mkdir -p "$workspace/logs" "$workspace/imports" "$workspace/scenarios" "$workspace/tests"
# `workspace` určuje cestu alebo režim spúšťača: `"$(cd "$workspace" && pwd)"`.
workspace="$(cd "$workspace" && pwd)"
if [[ "$workspace" == "$package" || "$workspace" == "$package/"* ]]; then
  echo 'Workspace must be outside the portable source folder.' >&2
  exit 2
fi
exec > >(tee -a "$workspace/logs/setup.log") 2>&1

if [[ "$(uname -m)" != x86_64 ]] || ! grep -q '^ID=ubuntu$' /etc/os-release ||
   ! grep -q '^VERSION_ID="24.04"$' /etc/os-release; then
  echo 'Supported clean install: Ubuntu 24.04 x86_64.' >&2
  exit 2
fi
required=(git gh build-essential cmake ninja-build pkg-config python3 python3-venv python3-dev wget ca-certificates
          sumo sumo-tools libxml2-dev libgsl-dev libsqlite3-dev libboost-all-dev libssl-dev zstd)
if ! command -v osmium >/dev/null 2>&1 && [[ ! -x "$workspace/tools/osmium/usr/bin/osmium" ]]; then
  required+=(osmium-tool)
fi
missing=()
for item in "${required[@]}"; do
  if ! dpkg-query -W -f='${Status}' "$item" 2>/dev/null | grep -qx 'install ok installed'; then
    missing+=("$item")
  fi
done
if ((${#missing[@]})); then
  echo "Installing missing Ubuntu packages: ${missing[*]}"
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}"
fi
if ! command -v firefox >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1 &&
   ! command -v chromium-browser >/dev/null 2>&1 && ! command -v google-chrome >/dev/null 2>&1; then
  echo 'Installing Firefox for the desktop launcher.'
  sudo apt-get install -y firefox
fi
osm_dir="$workspace/imports/osm"
mkdir -p "$osm_dir"
osm_name="slovakia-261031.osm.pbf"
# Pripnutý výrez Slovenska je priamo v balíku, preto príprava nevisí na historickej adrese
# Geofabrik, ktorá môže zmiznúť. Súbor sa skopíruje do pracovného priečinka a následne sa overí
# MD5 aj SHA-256.
for name in "$osm_name" "$osm_name.md5" slovakia.poly; do
  if [[ ! -f "$package/osm/$name" ]]; then
    echo "Bundled OSM input missing: $name" >&2
    exit 2
  fi
  if [[ ! -f "$osm_dir/$name" ]]; then
    cp "$package/osm/$name" "$osm_dir/$name"
  fi
done
(cd "$osm_dir" && md5sum -c "$osm_name.md5")
python3 - "$osm_dir" <<'PY'
import datetime
import hashlib
import json
import pathlib
import sys

folder = pathlib.Path(sys.argv[1])
source = folder / 'slovakia-261031.osm.pbf'
digest = hashlib.sha256()
with source.open('rb') as stream:
    for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
        digest.update(block)
expected = '4af3affa32fdc294ade673b409a0dc7f5c6c908875776ff06530d7bd923a9185'
if digest.hexdigest() != expected:
    raise SystemExit('Slovakia PBF does not match the pinned Geofabrik SHA-256')
manifest = {
    'source': 'Geofabrik OpenStreetMap extract',
    'url': 'https://download.geofabrik.de/europe/slovakia-261031.osm.pbf',
    'source_data_utc': '2026-10-31T21:23:06Z',
    'prepared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    'distribution': 'bundled pinned snapshot',
    'file': source.name,
    'size_bytes': source.stat().st_size,
    'sha256': expected,
    'official_md5': 'aae555909069471a265628a112f0ff34',
    'official_md5_verified': True,
    'coverage_polygon': 'slovakia.poly',
    'license': 'OpenStreetMap ODbL 1.0; attribution: OpenStreetMap contributors',
}
(folder / 'slovakia-261031.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
PY
python3 "$package/verify.py"
# `package_id` určuje cestu alebo režim spúšťača: `"$(sha256sum "$package/PACKAGE-MANIFEST.json" |
# cut -d' ' -f1)"`.
package_id="$(sha256sum "$package/PACKAGE-MANIFEST.json" | cut -d' ' -f1)"
if [[ "$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != 3.12 ]]; then
  echo 'The bundled Python wheels require Python 3.12.' >&2
  exit 2
fi
jobs="${BP_BUILD_JOBS:-2}"
if ! [[ "$jobs" =~ ^[1-8]$ ]]; then
  echo 'BP_BUILD_JOBS must be between 1 and 8.' >&2
  exit 2
fi

exec 9>"$workspace/.launcher.lock"
if ! flock -n 9; then
  echo 'Close the simulator before installing a new package.' >&2
  exit 2
fi
base_revision="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["revision"])' "$package/UPDATE-BASE.json")"
if ! [[ "$base_revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo 'The package has no published source revision.' >&2
  exit 2
fi
# Pracovný runtime sa pripravuje mimo čistého balíka. Pri zmene základného ZIPu vznikne nová
# verzia vedľa starej; pôvodné zdroje a výsledky sa neprepíšu.
runtime="$workspace/runtime"
migration=0
if [[ -f "$workspace/READY" ]]; then
  if [[ ! -f "$workspace/PACKAGE-ID" ]]; then
    echo 'The existing workspace has no package identity.' >&2
    exit 2
  fi
  if [[ "$(cat "$workspace/PACKAGE-ID")" == "$package_id" ]]; then
    if [[ ! -f "$workspace/UPDATE-STATE.json" ]]; then
      cp "$package/UPDATE-BASE.json" "$workspace/UPDATE-STATE.json"
    fi
    python3 "$package/install_shortcut.py"
    echo "Already prepared: $(python3 "$package/update.py" runtime-path)"
    exit 0
  fi
  migration=1
  # `runtime` určuje cestu alebo režim spúšťača: `"$workspace/.versions/$base_revision"`.
  runtime="$workspace/.versions/$base_revision"
  mkdir -p "$workspace/.versions"
fi
if [[ ! -d "$runtime" ]]; then
  cp -a "$package/engine" "$runtime"
fi
mkdir -p "$runtime/results/simulations" "$runtime/data/inputs/user"
if [[ "$migration" == 1 ]]; then
  previous="$(python3 - "$workspace" <<'PY'
import json,pathlib,sys
# `workspace` určuje cestu alebo režim spúšťača: `pathlib.Path(sys.argv[1]).resolve()`.
workspace=pathlib.Path(sys.argv[1]).resolve()
state=workspace/'UPDATE-STATE.json'
relative=json.loads(state.read_text()).get('active_runtime','runtime') if state.is_file() else 'runtime'
old=(workspace/relative).resolve()
if not old.is_relative_to(workspace) or not old.is_dir():
    raise SystemExit('Invalid previous runtime')
print(old)
PY
)"
  for rel in config/scenarios data/inputs/user data/orbits; do
    if [[ "$previous" != "$runtime" && -d "$previous/$rel" ]]; then
      mkdir -p "$runtime/$rel"
      cp -an "$previous/$rel/." "$runtime/$rel/"
    fi
  done
fi
cd "$runtime"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install --no-index --find-links release/python-wheels --require-hashes -r requirements-orbits.txt
  .venv/bin/python -m pip install --no-index --find-links release/python-wheels -r requirements-orbit-validation.txt
  .venv/bin/python -m pip install --no-index --find-links release/python-wheels -r requirements-p5-analysis.txt
fi
.venv/bin/python -m pip check

if [[ ! -f build/vanetza-v26.06-cmake/lib/static/libvanetza_asn1_its_r2.a ]]; then
  alias_id="$(printf '%s' "$runtime" | sha256sum | cut -c1-12)"
  openssl_alias="/tmp/bp-portable-openssl-$alias_id"
  if [[ -e "$openssl_alias" && ! -L "$openssl_alias" ]]; then
    echo "Refusing to replace non-symlink $openssl_alias" >&2
    exit 1
  fi
  ln -sfn "$runtime/build/openssl-dev-local" "$openssl_alias"
  cmake -S build/vanetza-v26.06 -B build/vanetza-v26.06-cmake \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DBUILD_SOCKTAP=OFF \
    -DVANETZA_WITH_GEOGRAPHICLIB=OFF -DVANETZA_WITH_CRYPTOPP=OFF \
    -DVANETZA_WITH_OPENSSL=ON \
    "-DOPENSSL_INCLUDE_DIR=$openssl_alias/usr/include" \
    -DOPENSSL_CRYPTO_LIBRARY=/lib/x86_64-linux-gnu/libcrypto.so.3 \
    -DOPENSSL_SSL_LIBRARY=/lib/x86_64-linux-gnu/libssl.so.3 \
    -DCMAKE_C_FLAGS= \
    "-DCMAKE_CXX_FLAGS=-I$openssl_alias/usr/include/x86_64-linux-gnu"
  cmake --build build/vanetza-v26.06-cmake --target btp asn1_its_r2 --parallel "$jobs"
fi

if [[ ! -f vendor/ns-3.38-ocb-eval/build/lib/libns3.38-satellite-debug.so ||
      ! -f vendor/ns-3.38-ocb-eval/build/lib/libns3.38-wave-debug.so ]]; then
  (
    cd vendor/ns-3.38-ocb-eval
    ln -sfn ../../../../../data/additional-input contrib/satellite/data/additional-input
    ./ns3 configure --build-profile=debug --enable-examples --disable-tests -- \
      '-DNS3_ENABLED_MODULES=core;network;mobility;internet;applications;point-to-point;csma;buildings;wifi;wave;satellite;traffic;magister-stats' \
      '-DCMAKE_CXX_FLAGS=-O0'
    ./ns3 build sat-cbr-example -j "$jobs"
    cmake --build cmake-cache --target libwave libcsma libbuildings --parallel "$jobs"
  )
fi

.venv/bin/python tools/simulator_cli.py preflight config/simulator-example.json > "$workspace/logs/preflight.json"
if [[ "${BP_SKIP_SMOKE:-0}" != 1 ]]; then
  .venv/bin/python tools/simulator_cli.py run config/simulator-smoke.json \
    results/simulations/portable-smoke-$(date -u +%Y%m%d%H%M%S) > "$workspace/logs/smoke.json"
fi
# Až po preflighte a krátkom behu sa zapíše nová mapa verzií a identita balíka. Staré výsledky sa
# pri verifikácii vyberajú podľa runtime, v ktorom vznikli.
python3 "$package/update.py" adopt-package "$runtime"
python3 "$package/install_shortcut.py"
echo "PASS: simulator ready in $runtime"
echo "Results and imported inputs stay inside $workspace"
