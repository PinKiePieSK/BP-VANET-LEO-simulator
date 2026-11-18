# Individuálne pozemné rádio auta — 17. 11. 2026

Každé auto môže prepísať výkon vysielača, šumové číslo prijímača, TX/RX zisk a výšku pozemnej antény. Nezadané hodnoty dedí zo spoločného profilu scenára. Tlačidlo **Predvolené rádio** prepísania odstráni. Hodnoty sú dostupné v karte auta aj v katalógu áut na technickej stránke. Profil auta z reálnej mapy prežije uloženie a obnovenie OSM výrezu.

Runner zapíše účinný profil každého auta do `car-radio.csv`. Pozemný aj integrovaný ns-3/SNS-3 engine nastaví tieto hodnoty na konkrétnom pozemnom PHY; anténna výška vstupuje do výpočtu pozemného kanála. Overovač porovná CSV so scenárom a natívnym logom. Rádiový profil auta nemení jeho dopravný typ v SUMO ani satelitný terminál RSU.

## Overenie

- `data/inputs/user/car-radio-20261117-ground/`: `car0` má 26 dBm, 4 dB, zisky 3/2 dBi a anténu 2,2 m; `car1` prepísaný len na 18 dBm; ďalšie autá dedia spoločné hodnoty. `results/simulations/kontrola-car-radio-ground-20261117-final2/`: natívny beh a samostatné `verify` PASS, 564 odoslaných CAM, 2497 prijatých CAM, 0 teleportov.
- `data/inputs/user/car-radio-20261117-satellite/`: rovnaký individuálny profil. `results/simulations/kontrola-car-radio-satelit-20261117/`: natívny beh a samostatné `verify` PASS, 564 CAM, jedna DENM doručená bráne a dve potvrdené prijatia vo vzdialených autách. Satelitná vetva používa generický DVB model.
- 44 testov `test_simulator_*.py` PASS; študijná kópia 69 aktívnych súborov `--check` PASS. V lokálnom prehliadači bola overená zmena výkonu 20 → 26 dBm, návrat na 20 dBm tlačidlom **Predvolené rádio** a zobrazenie všetkých piatich rádiových profilov na technickej stránke.
- Prenosný balík na ploche prešiel kontrolou manifestu (10 236 súborov/odkazov) aj `unzip -tq`; SHA-256 ZIPu je `60dc83de84980877a184798d18a6b67bfbfbd6940b4d2740de801b3ce5223423`. Pracovný runtime má zhodný obsah 85 balených súborov `src/tools/viewer/config`, nový `PACKAGE-ID` je `ea2ba405fc4198ae164b829e054e5f416d6b2612c5603a91678b50ee1d2cf059` a jeho preflight prešiel. Predchádzajúci balík je v `~/Documents/BP-Simulator-Archiv/previous-before-car-radio-20261117/`. Už otvorené okno Firefoxu môže do reštartu používať starý importovaný Python server.

Prvý pozemný pokus `kontrola-car-radio-ground-20261117` skončil na chybe v novom overovači (lokálny import zatienil funkciu). Po oprave sa použil nový priečinok `-final2`; neúspešný pokus sa nepoužíva ako výsledok.
