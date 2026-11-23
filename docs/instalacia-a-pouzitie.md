# Inštalácia a používanie simulátora VANET/LEO

## Podporované prostredie

Inštalačný postup je určený pre Ubuntu 24.04 x86_64 s Pythonom 3.12 a grafickým prostredím. Repozitár `PinKiePieSK/BP-VANET-LEO-simulator` a závislostný archív sú verejne dostupné; GitHub účet sa nevyžaduje. Windows, macOS a ARM nie sú overené cieľové platformy.

## Prvá inštalácia

1. Nainštaluj systémové závislosti:

   ```bash
   sudo apt-get update
   sudo apt-get install git build-essential cmake ninja-build pkg-config python3.12 python3.12-venv python3.12-dev sumo sumo-tools libxml2-dev libgsl-dev libsqlite3-dev libboost-all-dev libssl-dev zstd osmium-tool firefox
   ```

2. Naklonuj repozitár do zvoleného adresára:

   ```bash
   cd ~/Documents
   git clone https://github.com/PinKiePieSK/BP-VANET-LEO-simulator.git BP-Simulator
   cd BP-Simulator
   ```

3. Priprav závislosti a skontroluj inštaláciu:

   ```bash
   python3 scripts/setup_single_folder.py
   .venv/bin/python scripts/launch_local.py --check
   ```

`setup_single_folder.py` prevezme pripnutý archív závislostí z určeného GitHub vydania a pred rozbalením skontroluje SHA-256. Potom vytvorí Python prostredie, zostaví Vanetza a ns-3.38/SNS-3 3.38, vykoná preflight a vytvorí ikonu na ploche. Kompilácia pri prvej inštalácii môže trvať niekoľko minút. Názov adresára `BP-Simulator` je len príklad; skripty odvodzujú koreň projektu zo svojho umiestnenia.

Zdroj aplikácie pochádza z Git commitu. GitHub vydanie dodáva zostaviteľné závislosti, Python wheels a mapové dáta. Inštalácia z archívu zdrojov bez adresára `.git` nepodporuje automatický updater.

## Spustenie a scenáre

Simulátor otvorí ikona **BP Simulátor** alebo príkaz z koreňa klonu:

```bash
.venv/bin/python scripts/launch_local.py
```

Editor ukladá osobné scenáre do `config/scenarios/<id>.json` a ich mapové a dopravné vstupy do `data/inputs/user/<id>/`. Dodané príklady sú `realna-d1-pozemna`, `realna-d1-satelit`, `navrh-koridor-pozemna` a `navrh-koridor-satelit`. CLI umožňuje samostatný preflight, beh a verifikáciu:

```bash
.venv/bin/python tools/simulator_cli.py preflight config/scenarios/realna-d1-pozemna.json
.venv/bin/python tools/simulator_cli.py run config/scenarios/realna-d1-pozemna.json results/simulations/moj-pokus-1
.venv/bin/python tools/simulator_cli.py verify results/simulations/moj-pokus-1
```

Každému behu priraď nové ID. Výsledkový priečinok obsahuje kópie vstupov, surové stopy a `run-manifest.json`. Verifikácia kontroluje integritu behu; z jej výsledku samotného nevyplýva doručenie každého paketu. Formáty a interpretácia metrík sú v [technickej správe](technicka-sprava.md).

## Aktualizácia

Zavri okno simulátora a v koreňovom adresári klonu spusti:

```bash
python3 scripts/update_local.py
```

Rovnaký príkaz je dostupný ako akcia **Aktualizovať simulátor** v ponuke ikony na ploche. Updater vyžaduje vetvu `main`, pôvodný GitHub remote a čisté sledované súbory. Povolí iba fast-forward, následne zopakuje prípravu a overí štart servera. Pri zlyhaní prípravy vráti sledovaný zdrojový kód na predchádzajúci commit.

Git nesleduje `.venv/`, `vendor/`, `build/`, `imports/`, `cache/`, `logs/`, `results/` ani osobné scenáre. Aktualizátor tieto dáta nemaže. Staršie výsledky môžu mať manifest s hashmi predchádzajúceho zdroja; pre reprodukciu používaj zdrojový commit uvedený v danom manifeste.
