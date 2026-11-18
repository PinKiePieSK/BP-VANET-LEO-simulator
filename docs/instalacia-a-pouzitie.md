# Inštalácia a obsluha simulátora VANET/LEO

## Systém a balík

Podporovaná čistá inštalácia: Ubuntu 24.04 x86_64, Python 3.12, prístup k balíkom Ubuntu. Súčasťou `BP-Simulator.zip` je zdroj, pripnutý ns-3.38/SNS-3 3.38, Vanetza, Python wheels a výrez OSM Slovenska. Git checkout veľké závislosti neobsahuje.

Zo súkromného vydania na GitHube stiahni ZIP a súbor `.sha256` do rovnakého priečinka:

```bash
sha256sum -c BP-Simulator.zip.sha256
unzip BP-Simulator.zip
cd BP-Simulator
bash setup.sh
```

`setup.sh` overí balík a OSM vstup, doinštaluje chýbajúce systémové balíky, zostaví Vanetza a ns-3/SNS-3, vykoná preflight a krátky pozemný beh. Vytvorí ikony **BP Simulátor** a **BP Simulátor – aktualizovať**. Záznam inštalácie je v `BP-Simulator-Workspace/logs/setup.log`.

Pracovné dáta sú v `BP-Simulator-Workspace` na ploche; cestu možno pri inštalácii určiť premennou `BP_SIM_WORKSPACE`. Zdroj v rozbalenom balíku, pracovný runtime a výsledky sú oddelené. Neodstraňuj workspace, ak chceš zachovať scenáre a staré behy.

## Editor a terminál

Ikona **BP Simulátor** otvorí lokálny editor. V ňom sa vytvárajú cesty, budovy, autá a RSU; technická stránka upravuje spoločné parametre SUMO, ns-3 a SNS-3. Spustenie behu uloží vstupy a výstupy pod jeho ID. Popis ovládania, vstupov a výstupov je v `TECHNICKA-SPRAVA.md` pribalenom k ZIPu.

Pripravené uložené scenáre sú `realna-d1-pozemna`, `realna-d1-satelit`, `navrh-koridor-pozemna` a `navrh-koridor-satelit`. Terminálové spustenie z rozbaleného balíka:

```bash
bash run.sh preflight config/simulator-smoke.json
bash run.sh run config/simulator-smoke.json pokus-1
bash run.sh verify pokus-1
bash run.sh replay pokus-1
```

Každý nový beh potrebuje jedinečné ID. `verify` kontroluje presné vstupy, zdroje a surové stopy; `replay` otvorí ich prehratie. `run.sh` používa aktuálny runtime a pri overení alebo prehratí starého behu vyberie jeho pôvodnú verziu kódu. Podrobnosti o súboroch výsledku sú v technickej dokumentácii.

## Aktualizácia

Po oznámení novej verzie zavri editor a spusti ikonu **BP Simulátor – aktualizovať** alebo:

```bash
bash update.sh
```

Prvé spustenie vyžaduje prihlásenie do GitHubu účtom s prístupom k súkromnému repozitáru. Aktualizátor prevezme schválený commit z vetvy `main`, vytvorí nový runtime a prepne naň až po úspešnom preflighte. Každá verzia má vlastné `results/simulations`; staré behy zostávajú overiteľné a prehrateľné. Lokálne uložené scenáre sa do novej verzie nekopírujú; zostávajú v pôvodnom runtime. Ak sú lokálne zmenené spravované zdrojové súbory alebo sa menia pribalené závislosti či spúšťače, aktualizácia sa zastaví.

Pri novom úplnom vydaní rozbaľ nový ZIP a spusti v ňom `bash setup.sh` s tým istým workspace. Inštalátor vytvorí nový runtime vedľa starého, prenesie uložené scenáre a orbitálne vstupy bez prepísania a po kontrolnom behu prepne ikony. Staré runtime a ich výsledky ponechá.

## Model a výsledky

SUMO vypočíta pohyb, Vanetza kóduje ITS správy, ns-3.38 vykonáva pozemný paketový prenos a SNS-3 3.38 voliteľný satelitný prenos medzi RSU. Satelitná vetva používa generický DVB model; mená konštelácií určujú orbitálne a profilové vstupy. Súbory konkrétneho behu sú v jeho `results/simulations/<ID>/`; rozhodujúce vstupy sú v `inputs/` a `run-manifest.json`. Úspešná verifikácia znamená konzistentný beh, nie automaticky doručenú výstrahu. Formáty paketov, rozhodovacia logika a interpretácia výstupov sú v technickej dokumentácii.
