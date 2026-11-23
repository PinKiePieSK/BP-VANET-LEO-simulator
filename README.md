# Simulátor VANET/LEO

Simulátor spája pohyb vozidiel v SUMO s paketovým prenosom ITS-G5 v ns-3.38. CAM a DENM kóduje Vanetza. Scenáre so satelitnou vetvou používajú SNS-3 3.38 v tom istom procese ns-3.

## Jeden projektový priečinok

Zdrojový kód na GitHube a lokálne spúšťaný kód sú ten istý Git projekt. Ikona na ploche smeruje priamo na `scripts/launch_local.py` v tomto priečinku. `src/`, `tools/`, `viewer/`, `config/` a `data/` sú súčasťou projektu; `.venv/`, prípadný miestny `local-python/`, `vendor/`, `build/`, `imports/`, `cache/`, `logs/` a `results/` vznikajú alebo zostávajú lokálne v tom istom priečinku a Git ich ignoruje. Osobné uložené scenáre sú v `config/scenarios/` a `data/inputs/user/`; štyri dodané ukážky sú sledované Gitom.

Na čistom Ubuntu 24.04 x86_64 si priprav systémové nástroje uvedené v [návode](docs/instalacia-a-pouzitie.md), prihlás GitHub CLI k súkromnému repozitáru a spusti:

```bash
git clone https://github.com/PinKiePieSK/BP-VANET-LEO-simulator.git BP-Simulator
cd BP-Simulator
python3 scripts/setup_single_folder.py
```

Inštalátor stiahne pripnuté veľké závislosti z existujúceho vydania, overí ich SHA-256 a pripraví ich priamo tu. Zdrojové súbory berie z klonovaného commitu; nevytvára druhý pracovný runtime. Na ploche vytvorí jedinú ikonu. Nový commit na GitHube nemení otvorenú lokálnu aplikáciu automaticky; aktualizácia kódu v tomto jednom priečinku je `git pull --ff-only` pri zatvorenom simulátore, potom `python3 scripts/setup_single_folder.py`.

## Spustenie a overenie

```bash
.venv/bin/python scripts/launch_local.py
.venv/bin/python tools/simulator_cli.py preflight config/simulator-example.json
.venv/bin/python -m unittest discover -s tools -p 'test_*.py' -q
```

Nové behy a surové stopy sa ukladajú do `results/simulations/`. Staršie výsledky zachovávaj; ich `run-manifest.json` obsahuje hashe vstupov a použitých zdrojových súborov. Podrobnosti sú v [inštalačnom návode](docs/instalacia-a-pouzitie.md) a [technickej správe](docs/technicka-sprava.md).
