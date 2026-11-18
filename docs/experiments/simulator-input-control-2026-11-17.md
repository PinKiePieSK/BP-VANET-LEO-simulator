# Ovládanie vstupov budov, RSU a technických vrstiev — 17. 11. 2026

## Rozsah

Editor teraz používa rovnaký štýl objektových kariet pre cestu, auto, budovu a RSU. Pri ručnej budove možno meniť pôdorys a tri scenárové odhady výšky. Pri OSM budove možno zmeniť jednotlivé body pôdorysu, výšky a zvolený variant. Zmenené OSM budovy zostávajú označené ako ručne upravené a pri opätovnom importe rovnakého miesta sa zachovajú. V pozemnom rádiovom modeli sa použije zvolený variant výšky, nie každá z troch hodnôt súčasne.

Každá RSU má polohu, pozemnú a satelitnú rolu, montáž satelitného terminálu a vlastný pozemný rádiový profil: výkon, šumové číslo, TX/RX zisk a voliteľnú pevnú výšku antény. Nezadané hodnoty dedia spoločný profil. **Predvolené rádio** odstráni individuálne prepísania. Globálny OSM záznam prenesie tento profil pri zmene pracovného výrezu.

Technická stránka je rozdelená na spoločný čas, SUMO, pozemné ns-3, aplikačnú konfiguráciu komunikácie, SNS-3 a hranice modelu. Ukazuje účinné hodnoty na uzloch aj editovateľné spoločné vstupy: DCC, prahy CAM/DCC, antény, smerové fronty, sloty, teploty, MODCOD, ARQ/ACM, čas prepnutia, čas aplikácie ISL a zorný uhol smerovej montáže. Rozhranie mení otvorený scenár cez validovaný most; uložený JSON je zdrojom natívneho behu.

`tools/simulator_engine_controls.py` drží predvolené hodnoty a rozsahy. Staršie scenáre dedia pôvodné hodnoty; pre starý scenár sa DCC odvodí z existencie DENM, pokiaľ nemá explicitný prepínač. Nový scenár obsahuje explicitný profil. Smerové časové vstupy musia nasledovať v poradí žiadosť o prepnutie → aplikácia ISL profilu → rezervované uvoľnenie dávky. Dávkovanie je v aktuálnom zjednotenom behu vypnuté.

## Natívny dôkaz

- Pozemný scenár: `data/inputs/user/rsu-radio-20261117-ground/scenario.json`; surový beh `results/simulations/kontrola-rsu-radio-ground-20261117-final4/`. Päť áut, dve RSU, DENM, DCC zapnuté; jedna RSU používa 26 dBm, 4 dB, 3/2 dBi a 12 m, druhá dedí 20 dBm, 7 dB, 0/0 dBi a výšku podľa strechy/minima.
- Satelitný scenár: `data/inputs/user/rsu-radio-20261117-satellite/scenario.json`; surový beh `results/simulations/kontrola-rsu-radio-satelit-20261117-final2/`. Rovnaký individuálny profil RSU, DCC vypnuté, časy 1,1/2,6/3,6 s. Natívny log hlási tieto časy a presné hodnoty oboch PHY; integrovaný ns-3/SNS-3 checker prešiel s jedným aktívnym satelitom, 564 CAM, jednou DENM v bráne a dvoma potvrdenými prijatiami vo vzdialených autách.
- Kontrola porovnáva uložený svet a scenár, presné bajty `rsu-radio.csv`, natívne hlásenie parametrov konkrétneho PHY a hashe surových stôp. Pokus s nedostatočnou presnosťou C++ logu bol opravený pred prijatím výsledku; predchádzajúce priebežné priečinky sa nepoužívajú ako finálny dôkaz.
- Regresia: 43 testov `test_simulator_*.py` PASS; 68 aktívnych súborov študijnej kópie prešlo generovaním a `--check`. Živé rozhranie overilo individuálnu zmenu 20 → 26 dBm, návrat cez **Predvolené rádio**, profil RSU v technickej časti a prepnutie DCC.
- `simulator_cli.py verify` po dokončení zdrojov znovu vrátil PASS pre oba uvedené finálne behy. Pracovný runtime má zhodný obsah 84 balených súborov `src/tools/viewer/config`; nový server v ňom vrátil 34 spoločných premenných a nový návrh s rovnakými predvolenými hodnotami.
- Balík na ploche overil 10 235 súborov a odkazov. ZIP prešiel `sha256sum -c` a `unzip -tq`; SHA-256 ZIPu je `1e31b836970d712b9a7e2d145051238fdba530aaf691c0adfcf50afe3597d5d2`. Identita manifestu aj pracovného runtime je `f1224d1be390d365b51c850c8e883a78a5ac46f717329445c3004e12b345a801`. Predchádzajúci balík je zálohovaný v `~/Documents/BP-Simulator-Archiv/previous-before-input-control-20261117/`.

## Hranica tvrdenia

Zmenené hodnoty sú vstupy výskumného modelu, nie lokálne merania ani konfigurácia komerčného modemu. Pevné zostávajú kontrakty formátu a podporovanej architektúry, najmä 100 ms krok mobility/CAM, 10 MHz OCB, typ správ a generický DVB backend. Technická stránka tieto hranice zobrazuje ako pevné. Pri starších uložených behoch netvrdíme, že nové prepínače boli vtedy aktívne.

Už otvorený Firefox beží so starým importovaným Python kódom servera. Po uložení rozpracovaného návrhu treba zavrieť okno a znovu spustiť ikonu; samotné obnovenie stránky nový serverový modul nenačíta. Rozpracovaný stav používateľa nebol pri nasadení prerušený.
