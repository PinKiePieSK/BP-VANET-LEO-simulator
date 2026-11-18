# Obnova na natívnom Ubuntu a jediný runtime ns-3.38

Tento postup opisuje pôvodnú obnovu projektu. Aktuálny prenosný simulátor pripravuje `setup.sh` podľa [odovzdávacieho návodu](simulator-odovzdanie.md). Pôvodné skripty `check_migration.py` a `obnovit-native-ubuntu.sh` sú zachované v `scripts/legacy/`.

Aktualizované 26. 10. 2026 po obnove prenosového archívu a zjednotení všetkých aktívnych vetiev.

Aktívny checkout je výhradne `vendor/ns-3.38-ocb-eval`; ns-3.48 bol po migrácii odstránený. Zachovaj celý projekt vrátane skrytých Git adresárov, zdrojov Vanetza v `build/vanetza-v26.06`, OpenSSL hlavičiek, `data/`, `results/` a `archive/`. Historické výsledky a ich verzie sa neprepisujú. Obnovovací skript spúšťaj v novej kópii, lebo regeneruje `.venv` a build cache. Aktuálne experimentálne príkazy sú v [reprodukcii](reprodukcia.md).

## Závislosti a obnova

Ubuntu 24.04, Python 3.12, GCC 13. Pripnutý SUMO `1.18.0+dfsg-3build5` a OpenSSL runtime `3.0.13-0ubuntu3.16`.

```bash
sudo apt-get update
sudo apt-get install git git-lfs rsync build-essential cmake ninja-build pkg-config \
  python3 python3-venv python3-pip python3-dev sumo sumo-tools \
  libxml2-dev libgsl-dev libsqlite3-dev libboost-all-dev libssl-dev python3-matplotlib
python3 scripts/check_migration.py
bash scripts/obnovit-native-ubuntu.sh
```

Skript obnoví `.venv` vrátane pripnutých P5 analytických balíkov a generované cache Vanetza/ns-3.38, zostaví satelitné knižnice, Wi-Fi/WAVE, CSMA, buildings a integrovaný pilot. Neodstraňuje raw výsledky ani zdroje. Predvolený limit sú dve úlohy; na slabšom stroji `BP_BUILD_JOBS=1`. Len Python: `BP_SKIP_CPP=1`.

`data/additional-input` je samostatný dátový adresár; nesmie závisieť od odstráneného checkoutu. `archive/pre-ns338-migration-20261025` obsahuje pôvodné projektové zdroje a SHA-256 pre historický audit, nie spustiteľný ns-3.48.

## Verzie

- ns-3.38: `392e36833ce3c7e0ecde4188043f76345402d5a7`
- SNS-3 satellite: `739a10dbe1db02fd2c4064501e4a48994e0b79f3`
- traffic: `c68daaf18fadd3393bbb141fedf13fb94a99b6e2`
- stats: `c613ba7c8cbf284cf0aa24ca778974f711b56370`
- data: `faf7d763438b43139af3d78ff30e4130b2692bd9`
- Vanetza: `fb6c551030dcc12b924299bf401e35e5fe814713`

Presný stav skúšok a obmedzení je v [denníku obnovy](experiments/obnova-native-2026-10-25.md). Súbory z pôvodného prenosového archívu môžu stále obsahovať 3.48; po obnove starého archívu treba aplikovať aktuálne projektové zmeny. Historické manifesty s cestou `/home/ubuntu` sa nemenia.

## Spustenie

```bash
.venv/bin/python tools/scenario_server.py --port 8765
```

Otvor `http://127.0.0.1:8765/`. Na nové experimenty používaj nové výsledkové adresáre. Po obnove bol osobitne doplnený a overený model handoveru jedného UT v P3; jeho syntetické preladenie nie je handoverom komerčného operátora. Hranice editora a finálneho P5 experimentu sú v [návode](navod-na-pouzitie.md).
