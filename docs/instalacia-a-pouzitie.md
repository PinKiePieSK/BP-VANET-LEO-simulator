# Inštalácia a obsluha simulátora VANET/LEO

## Jediný adresár

Aktívny zdroj, lokálne zostavené závislosti, uložené scenáre a výsledky patria do jedného priečinka `BP-Simulator/`. Ikona spúšťa server z tohto priečinka. GitHub sleduje zdrojové súbory, konfigurácie, štyri ukážkové scenáre a skripty; miestne `.venv/`, prípadný `local-python/`, `vendor/`, `build/`, `imports/`, `cache/`, `logs/`, `results/` a osobné scenáre zostávajú v tomto istom priečinku, ale Git ich neodosiela.

Podporovaná čistá inštalácia používa Ubuntu 24.04 x86_64 a Python 3.12. Pred inštaláciou treba mať prístup k súkromnému repozitáru cez Git a GitHub CLI (`gh auth login`), webový prehliadač Firefox alebo Chromium a systémové závislosti:

```bash
sudo apt-get update
sudo apt-get install git gh build-essential cmake ninja-build pkg-config python3.12 python3.12-venv python3.12-dev sumo sumo-tools libxml2-dev libgsl-dev libsqlite3-dev libboost-all-dev libssl-dev zstd osmium-tool firefox
gh auth login
gh repo clone PinKiePieSK/BP-VANET-LEO-simulator BP-Simulator
cd BP-Simulator
python3 scripts/setup_single_folder.py
```

Skript používa iba tento projektový priečinok. Veľké pripnuté závislosti prevezme z vydania `v2026-11-18.2`, overí SHA-256, pripraví Python 3.12, Vanetza a ns-3.38/SNS-3 3.38, overí scenár a vytvorí ikonu na ploche. Kód aplikácie zostáva kódom klonovaného commitu na GitHube. Dátový výrez Slovenska ukladá do `imports/osm/` a mapovú cache do `cache/osm/` v tom istom priečinku.

## Súbory scenára a behu

Editor vytvára nové scenáre ako `config/scenarios/<id>.json`, `data/inputs/user/<id>/world.json` a `data/inputs/user/<id>/demand.json`. Dodané ukážky sú `realna-d1-pozemna`, `realna-d1-satelit`, `navrh-koridor-pozemna` a `navrh-koridor-satelit`. Osobné scenáre a ich výsledky nezmaž pri aktualizácii.

Počas spustenia vznikne požiadavka a log v `results/jobs/`. Každý beh má jedinečný priečinok `results/simulations/<id>/` s kópiami vstupov, surovými stopami a `run-manifest.json`. Overenie kontroluje vstupy, hashe zdrojov a raw stopy. Úspešné overenie znamená konzistentný beh; počet doručených správ vyhodnoť samostatne.

Príkazy z koreňa projektu:

```bash
.venv/bin/python scripts/launch_local.py
.venv/bin/python tools/simulator_cli.py preflight config/scenarios/realna-d1-pozemna.json
.venv/bin/python tools/simulator_cli.py run config/scenarios/realna-d1-pozemna.json results/simulations/moj-pokus-1
.venv/bin/python tools/simulator_cli.py verify results/simulations/moj-pokus-1
```

## Aktualizácia bez druhého runtime

Zavri okno simulátora a v projektovom priečinku spusti `python3 scripts/update_local.py`, alebo v ponuke ikony na ploche zvoľ „Aktualizovať simulátor“. Aktualizátor preverí čistotu sledovaných súborov, stiahne novú vetvu `main`, vykoná iba pokračujúci posun, znovu pripraví projekt a overí štart servera. Pri neúspešnej príprave vráti zdrojový kód na pôvodný commit. `results/` a osobné scenáre zostávajú v tom istom priečinku. Starší `run-manifest.json` obsahuje hashe pôvodného zdroja a nemusí prejsť overením novým kódom. GitHub vydanie `v2026-11-18.2` je len pripnutý zdroj veľkých závislostí, nie ďalší pracovný runtime.
