# Kreslenie cesty: krok späť a dopredu — 10. 11. 2026

V nástroji Cesta sú vedľa „Dokončiť cestu“ a „Zrušiť“ dve šípky `↶` a `↷`. Jedno stlačenie vráti alebo obnoví jeden bod rozpracovanej cesty. Po pridaní nového bodu sa história krokov dopredu vymaže; po zrušení, Escape alebo úspešnom dokončení sa vymažú obe histórie. Šípky sú vypnuté, keď nemajú čo vykonať. Majú prístupný názov a tooltip.

Implementácia používa spoločný stav `draft` a `roadRedo` v `viewer/simulator.js`. Oba povrchy, SVG pracovná mapa aj MapLibre kliknutie, používajú `addRoadPoint`. Snapshot pri prepnutí režimu mapy uchováva aj históriu. Táto funkcia mení len rozpracované body; hotový cestný segment sa zapíše až pri „Dokončiť cestu“.

## Overenie

- V lokálnom prehliadači na `:8767` pri novom prázdnom návrhu: 0 bodov (obe šípky vypnuté) → 2 body → späť na 1 bod → dopredu na 2 body. Nový bod po kroku späť vypol šípku dopredu; Zrušiť odstránilo body a vyplo obe šípky. Konzola bez chyby.
- `.venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: 38 testov, OK.
- Nový prenosný balík `~/Desktop/BP-Simulator` má 10 231 súborov a odkazov, `verify.py` PASS; `unzip -tq` bez chyby; samostatne rozbalený ZIP má tiež `verify.py` PASS. Štyri zmenené súbory editora sú bajtovo identické v zdroji, pracovnom prostredí, desktopovom balíku aj rozbalenom ZIPe. `bash run.sh preflight config/simulator-smoke.json` prešiel; SHA-256 ZIPu zodpovedá kontrolnému súboru.
- Stále otvorený starší editor na porte 8766 dostal rovnakú úpravu s pôvodnými názvami API; jeho predchádzajúce súbory sú zálohované v `~/Documents/BP-Simulator-Archiv/old-open-window-road-history-files-20261110`. HTTP kontrola vrátila nové podklady. Rozpracovaný stav v otvorenej karte sa nemenil; zmena sa načíta pri obnovení stránky.
- Študijné komentáre pre aktívne súbory boli obnovené a `scripts/refresh_study_code.py --check` prešiel. Predchádzajúci desktopový balík je v `~/Documents/BP-Simulator-Archiv/before-road-history-20261110`.
