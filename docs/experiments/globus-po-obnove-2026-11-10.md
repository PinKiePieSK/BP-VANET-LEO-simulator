# Glóbus po obnovení stránky — 10. 11. 2026

## Problém a zmena

Používateľ hlásil, že po obnovení stránky v režime reálnej mapy sa Zem niekedy vykreslí ako ovál; po prepnutí medzi prázdnym návrhom a reálnou mapou je guľatá. Pred zmenou mal kontajner MapLibre pri štarte `display:none`. MapLibre sa teda mohol vytvoriť bez skutočných rozmerov, zatiaľ čo prepnutie režimu vyvolalo ďalšiu inicializáciu. V testovacom prehliadači sa ovál pred zmenou nepodarilo zopakovať, takže toto je vysvetlenie založené na štarte vykresľovania a používateľskom pozorovaní, nie meranie chyby vo Firefoxe.

`viewer/simulator.css` teraz skrýva mapu cez `visibility:hidden`; jej rozmery sú dostupné od vytvorenia. `viewer/earth-map.js` znovu prispôsobí MapLibre plátno po zobrazení a pri zmene rozmerov kontajnera. `viewer/simulator.html` má nové verziované odkazy na oba súbory, aby obyčajné obnovenie načítalo opravu aj pri staršej cache. Geometria scenára ani sieťový model sa nemenili.

## Overenie

- V lokálnom editore sa po obnovení v reálnom režime zobrazil kruhový glóbus. Po prepnutí prázdny návrh → reálna mapa ostal kruhový; ďalšie obnovenie v reálnom režime ho nezdeformovalo.
- DOM po obnovení hlásil mapový kontajner 806 × 488 px a MapLibre canvas 806 × 488 px, vrátane CSS rozmerov. Vizuálne sa kruhový okraj zachoval.
- `.venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: 38 testov OK. `scripts/refresh_study_code.py --check`: 64 aktívnych súborov aktuálnych.
- Nový ZIP: `verify.py` PASS pre 10 231 položiek, `unzip -tq` bez chýb a `verify.py` PASS po rozbalení. Rozdiel oproti predchádzajúcemu balíku tvoria iba `engine/viewer/earth-map.js`, `simulator.css` a `simulator.html`.
- Pracovný adresár na ploche má zhodné tri súbory a aktuálne ID balíka. Testovací štart `launch.py` prešiel. Starší stále otvorený editor na porte 8766 dostal rovnakú cielenú opravu UI; HTTP server vracia nové HTML, CSS a JS s kódom 200. Jeho ostatný kód, scenáre a výsledky zostali nedotknuté.

Skutočné používateľské okno Firefoxa nebolo automatizáciou vizuálne odčítané; po jeho obnovení treba v prípade opakovania hlásenia zaznamenať veľkosť okna a snímku.
