# U9: ovládanie glóbusu a vyradenie vetvy auto–satelit

## Stav

- Miesto pokusu sa na glóbuse určuje ľavým kliknutím. Tlačidlo na aktiváciu výberu a upraviteľné polia súradníc boli odstránené. Pri priblížení na cestu zostáva zachované umiestňovanie objektov a cieľov trás.
- Technické parametre sa zobrazujú v tom istom okne nad editorom. Editor zostáva načítaný; návrat zachová neuložené polohy, rozpracované polia a stav scenára. Zmeny technických parametrov sa prenášajú späť do editora.
- Aktuálny scenár má schému 6. Autá majú len pozemný režim `ground`; satelitný terminál patrí iba RSU. Backend odmieta staré polia a terminál vozidla. Priama vetva auto–satelit je mimo aktívneho editora a prenosného balíka. Historické zdroje sú v `archive/retired-direct-20261102/`; existujúce výsledky zostali zachované.
- Uložené scenáre starších schém sa v aktuálnom zozname nezobrazujú. Na výskumné porovnanie zostávajú v zdrojovom archíve.

## Overenie

- V prehliadači: klik na glóbus nastavil miesto `50.95044°, -20.86334°`; po otvorení technických parametrov a návrate zostal neuložený názov, zmenený seed aj vložená RSU. V aktuálnej stránke nie sú pôvodné ovládacie prvky ani priama voľba auto–satelit; pri načítaní neboli chyby JavaScriptu.
- `v6-ground-clean-20261102`: 5 áut, 3 RSU, 6 s. `run` aj nezávislé `verify`: PASS.
- `v6-rsu-sat-clean-20261102`: 5 áut, 3 RSU, 2 RSU so satelitným backhaulom, Iridium NEXT, 6 s. `run` aj nezávislé `verify`: PASS. Servisný backend zaznamenal prijatie na cieľovej RSU a upozornenie dvoch áut.
- Preflight odmietol `direct_cars` aj `direct_satellite` v schéme 6.
- Prenosný balík: manifest PASS (11 269 súborov a odkazov), preflight zabaleného 6 s scenára PASS, ZIP SHA-256 a kontrola `unzip -t` PASS. Nasadený runtime na ploche spustil a nezávisle overil 6 s smoke beh s 5 autami a 3 RSU: PASS.
- V pracovnom runtime bolo 28 uložených scenárov schémy 5. Z 15 vznikli overené kópie schémy 6 bez priamej vetvy. Zvyšných 13 neprešlo bez zmeny UTC mimo 48 h okna orbitálneho archívu alebo bez predĺženia satelitného pokusu na aspoň 6 s; pôvodné súbory zostali zachované.

Výsledky sú výskumným servisným modelom s orbitálnou geometriou a ns-3.38, nie zárukou prevádzkovej dostupnosti operátora.
