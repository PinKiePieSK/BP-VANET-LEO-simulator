# Simulátor VANET/LEO

Výskumný simulátor pre prenos správ medzi vozidlami, cestnými jednotkami (RSU) a satelitnou vetvou. Pohyb vozidiel počíta SUMO. Pozemný paketový prenos používa ns-3.38 s 802.11p OCB; správy CAM a DENM kóduje Vanetza. Integrované scenáre pridávajú generický satelitný model SNS-3 3.38.

## Rozsah modelu

- Editor pripravuje mapu, cestnú sieť, vozidlá, RSU, budovy, rádiové parametre a orbitálny vstup.
- Runner prevádza cestnú sieť a trasy do SUMO, spúšťa pozemný alebo integrovaný paketový beh a ukladá surové stopy.
- Verifikátor kontroluje vstupy, zdrojové hashe a stopy pred zobrazením výsledku v replay.

Satelitná vetva je referenčný model založený na SNS-3. Výsledky nepredstavujú meranie ani validovanú predikciu komerčnej satelitnej služby. Podrobnosti o paketovej ceste, výstupoch a hraniciach modelu sú v [technickej správe](docs/technicka-sprava.md).

## Inštalácia

Podporované prostredie: Ubuntu 24.04 x86_64, Python 3.12 a Firefox alebo Chromium. Repozitár aj závislostný archív sú verejne dostupné. Zoznam systémových balíkov je v [inštalačnom návode](docs/instalacia-a-pouzitie.md). Po ich inštalácii:

```bash
git clone https://github.com/PinKiePieSK/BP-VANET-LEO-simulator.git BP-Simulator
cd BP-Simulator
python3 scripts/setup_single_folder.py
```

Príprava stiahne závislostný archív z GitHub vydania, overí jeho SHA-256, vytvorí `.venv`, zostaví Vanetza a ns-3/SNS-3 a vykoná preflight. Pracovný adresár je Git klon; názov cieľového priečinka nie je súčasťou konfigurácie simulácie.

## Spustenie a kontrola

Po príprave možno použiť ikonu **BP Simulátor** na ploche alebo príkazy z koreňa klonu:

```bash
.venv/bin/python scripts/launch_local.py
.venv/bin/python tools/simulator_cli.py preflight config/simulator-example.json
.venv/bin/python tools/simulator_cli.py run config/simulator-smoke.json results/simulations/moj-pokus
.venv/bin/python tools/simulator_cli.py verify results/simulations/moj-pokus
```

Každý beh vyžaduje nové ID výsledkového priečinka. Dodané scenáre sú v `config/scenarios/`; podrobnejšie použitie editora a CLI uvádza [inštalačný návod](docs/instalacia-a-pouzitie.md).

## Aktualizácia a lokálne dáta

Po zatvorení simulátora spusti z koreňa klonu:

```bash
python3 scripts/update_local.py
```

Aktualizátor prijíma iba pokračovanie vetvy `main` bez miestnych zmien sledovaných súborov. Po aktualizácii zopakuje prípravu a skontroluje štart servera. `.venv/`, `vendor/`, `build/`, `imports/`, `cache/`, `logs/`, `results/` a osobné scenáre v `config/scenarios/` a `data/inputs/user/` sú lokálne dáta mimo Gitu. Pri presune na ďalší počítač ich treba preniesť samostatne.

`src/` obsahuje natívne enginy, `tools/` runner a verifikátory, `viewer/` rozhranie, `config/` referenčné konfigurácie a `data/` vstupy. Runtime závislostí sa pripravuje v `vendor/` a `build/`.

## Zdroje dát a vydanie

Mapový výrez Slovenska obsahuje dáta © prispievatelia OpenStreetMap, dostupné pod ODbL 1.0. Pôvod a kontrolné súčty orbitálnych vstupov sú v manifestoch `data/orbits/`. Licenčné súbory ns-3, SNS-3, Vanetza a ďalších závislostí zostávajú pri ich zdrojoch v závislostnom archíve. Spôsob distribúcie zdroja a závislostí opisuje [dokumentácia vydania](docs/vydanie.md).
