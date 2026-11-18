# Simulátor VANET/LEO pre bakalársku prácu

Aktuálny simulátor pripravuje pohyb vozidiel v SUMO, CAM a DENM vo Vanetza a pozemný paketový prenos v ns-3.38. Pri satelitnom scenári beží pozemné ITS-G5 a generický DVB prenos SNS-3 3.38 v jednom procese ns-3. Výstup obsahuje surové stopy, nezávislý verifier a replay. Model netvrdí, že reprodukuje skutočné modemy alebo prevádzkovú dostupnosť Starlinku, Iridia a Globalstaru.

**Spustenie po stiahnutí z GitHubu:** v súkromnom repozitári je zdroj aplikácie, scenáre, testy a dokumentácia. Z vydania (Releases) stiahni `BP-Simulator.zip` aj kontrolný súčet `BP-Simulator.zip.sha256`, over ich príkazom `sha256sum -c BP-Simulator.zip.sha256`, ZIP rozbaľ a spusti `bash setup.sh`. Prenosný ZIP obsahuje aj pripnutý ns-3/SNS-3, Vanetza, offline Python balíky a slovenský OSM výrez. Samotný Git checkout tieto veľké závislosti neobsahuje a neslúži ako čistý inštalačný balík.

- [Odovzdanie a použitie simulátora](docs/simulator-odovzdanie.md)
- [Technická správa k aktuálnej verzii](docs/technicka-sprava-simulatora-2026-11-18.md)
- [Oficiálne zadanie BP](docs/zadanie-bp.md)

Spustenie aktuálneho editora v tomto vývojovom projekte:

```bash
.venv/bin/python tools/simulator_server.py --port 8765
```

Otvoriť `http://127.0.0.1:8765/simulator.html`. Technické nastavenia sú prístupné priamo z editora. Nové behy sa ukladajú do `results/simulations/`. Používaný kód je priamo v `tools/`, `src/` a `viewer/`; staré sondy, stránky a testy sú v ich podpriečinkoch `legacy/`. Historické výsledky zostali zachované.

Prenosný balík pre ďalší počítač vytvára `python3 scripts/package_simulator.py --destination /cesta/BP-Simulator`. Obsahuje pripnutý ns-3/SNS-3, Vanetza, orbitálne vstupy a OSM výrez; samotný zdrojový checkout tieto veľké súbory neobsahuje. ZIP a inštalačný postup sú opísané v odovzdávacom dokumente.
