# Simulátor VANET/LEO

Simulátor spája pohyb vozidiel v SUMO s paketovým prenosom ITS-G5 v ns-3.38. CAM a DENM kóduje Vanetza. Scenáre so satelitnou vetvou používajú SNS-3 3.38 v tom istom procese ns-3.

## Inštalácia

Na Ubuntu 24.04 x86_64 stiahni z [vydaní](https://github.com/PinKiePieSK/BP-VANET-LEO-simulator/releases) súbory `BP-Simulator.zip` a `BP-Simulator.zip.sha256`:

```bash
sha256sum -c BP-Simulator.zip.sha256
unzip BP-Simulator.zip
cd BP-Simulator
bash setup.sh
```

Inštalátor zostaví pribalené závislosti, overí beh a vytvorí spúšťaciu ikonu. Prístup k súkromnému repozitáru je potrebný na stiahnutie vydania a neskoršie aktualizácie. Zdrojový Git checkout neobsahuje veľké pripnuté závislosti ani OSM výrez; na čistú inštaláciu slúži ZIP.

## Použitie a aktualizácie

Editor otvorí ikona **BP Simulátor**. Na aktualizáciu zo schválenej vetvy `main` zavri editor a spusti ikonu **BP Simulátor – aktualizovať** alebo `bash update.sh` v rozbalenom balíku. Aktualizácia vytvorí nový runtime; staršie behy zostanú pri verzii, v ktorej vznikli. Zmeny pribalených závislostí a inštalačných skriptov sa vydávajú v novom ZIPe.

- [Inštalácia a obsluha](docs/instalacia-a-pouzitie.md)
- [Technická dokumentácia](docs/technicka-sprava.md)

## Vývojový zdroj

Aktívny kód je v `src/`, `tools/` a `viewer/`. Editor vo vývojovom prostredí:

```bash
.venv/bin/python tools/simulator_server.py --port 8765
```

Otvor `http://127.0.0.1:8765/simulator.html`. Nové behy sa ukladajú do `results/simulations/`. Prenosný balík sa vytvorí príkazom `python3 scripts/package_simulator.py --destination /cesta/BP-Simulator --source-revision COMMIT_SHA`; zadaný commit musí zodpovedať zdrojom v balíku.
