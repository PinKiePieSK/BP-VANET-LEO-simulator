# Inštalácia a používanie simulátora VANET/LEO

## Podporované prostredie

Inštalačný postup je určený pre Ubuntu 24.04 alebo 26.04 x86_64 s grafickým prostredím. Repozitár `PinKiePieSK/BP-VANET-LEO-simulator` a archívy sú verejne dostupné; GitHub účet sa nevyžaduje. Windows, macOS, ARM a iné verzie Linuxu nie sú podporované týmto inštalátorom.

## Prvá inštalácia

1. Na naklonovanie potrebuješ Git a na spustenie prípravy systémový `python3`. V bežnej inštalácii Ubuntu je Python už prítomný. Ak Git alebo Python chýba, nainštaluj ich:

   ```bash
   sudo apt-get update
   sudo apt-get install git python3
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

`setup_single_folder.py` skontroluje systémové balíky a chýbajúce nainštaluje cez `sudo apt-get`; heslo sa zadáva iba do terminálu. Stiahne samostatný Python 3.12.14 a pripnutý archív závislostí, oba overí SHA-256 pred rozbalením. Potom vytvorí `.venv`, zostaví Vanetza a ns-3.38/SNS-3 3.38, vykoná preflight a vytvorí ikonu na ploche. Prvé zostavenie môže trvať dlhšie podľa výkonu počítača. Názov adresára `BP-Simulator` je len príklad; skripty odvodzujú koreň projektu zo svojho umiestnenia.

Zdroj aplikácie pochádza z Git commitu. GitHub vydanie projektu dodáva zostaviteľné závislosti, Python wheels, mapové dáta a prenosný Python pôvodom z [python-build-standalone 20260825](https://github.com/astral-sh/python-build-standalone/releases/tag/20260825). Inštalátor pripína oba presné archívy a ich kontrolné súčty. Inštalácia z archívu zdrojov bez adresára `.git` nepodporuje automatický updater.

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
