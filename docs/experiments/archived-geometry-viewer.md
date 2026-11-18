# Archivovaný geometrický prehrávač Bratislava (60 s)

## Účel a rozsah

Režim `archived_geometry_only` v existujúcom lokálnom editore synchronizuje **syntetickú** cestu, zaznamenané polohy dvoch áut, pevné RSU a archivované GP/OMM geometrické vzorky skupín Starlink, Iridium NEXT a Globalstar. Slúži na kontrolu súradnicovej a časovej väzby, nie na meranie sieťovej služby. Nemá paketové udalosti, RF model, lúče, terminály, brány, medzisatelitné spoje ani výpočet doručenia. Výber objektu sa robí pre pevné miesto RSU, nie pre každé auto.

Archív je **retrospektívny**: prehrávanie začína `2026-10-22T12:45:00.000000Z`, kým manifest GP snapshotu uvádza získanie `2026-10-22T12:49:43.719531+00:00`. Tieto dáta teda neboli k dispozícii terminálu v čase začiatku prehrávania. Vek jednotlivých OMM elementov je v orbitálnom CSV a jeho metadátach; nejde o potvrdenie prevádzkového stavu objektu alebo dostupnosti služby.

## Vstupy, algoritmus a jednotky

| Vstup | Použitie | SHA-256 |
| --- | --- | --- |
| `data/inputs/bratislava-synthetic-road/scenario.json` | pôvodná cestná polylínia, RSU, dve autá | `eda3528728a07aa09758901210928bb2d1a4f39bf2fb7f0fd2e6e60a2c7fd66c` |
| `data/derived/georeference/bratislava-synthetic-road-20261022.csv` | 236 polôh áut, lokálne metre a WGS84 | `81ae33f307311b2e13c32837d409cb292852a54bfb44a7b2826f7ec8e6abdd33` |
| `data/derived/multi-constellation/bratislava-20261022T124500Z.csv` | kandidáti a vybrané objekty nad 10° v čase 0/30/60 s | `ea0af7d113bb40b4a96e8adf0bcf5f49799aad934996a9555b56a0cd7054b278` |
| `data/orbits/20261022T124815Z-retlector/manifest.json` | hashované archivované OMM zrkadla CelesTrak GP | `d28ad3618304780d3cd118e83e8a2e88c14d015fa022c3082ba7b2f624d826` |

`tools/build_archived_geometry_replay.py` kontroluje hashe CSV, metadát, manifestu a vybraných OMM záznamov. Kontroluje zhodu UTC štartu a WGS84 súradníc pevného RSU. Cesta sa kreslí z pôvodnej päťbodovej polyline, nie z trajektórie auta. Dve trajektórie vznikli v SUMO; uložené polohy sú v intervaloch 0,5 s do 59,5 s (car0 120 a car1 116 bodov). Pre zobrazenie pohybu medzi týmito bodmi sa používa lineárna vizuálna interpolácia, po poslednom bode poloha zostáva stáť. Táto interpolácia nie je novým behom SUMO.

Orbitálne počty kandidátov, výber katalógového ID, elevácia a šikmá vzdialenosť pochádzajú z 30 s vzoriek CSV. Pri posune medzi vzorkami sa zobrazuje posledná dostupná vzorka; nepripisuje sa nový handover ani priebeh počtu kandidátov. Pre lepšiu orientáciu sa samostatne propaguje **iba už vybraný objekt** po 5 s krokoch pomocou SGP4/WGS72 a Astropy TEME→ITRS s archivovaným zdrojom EOP (`0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`). Jeho WGS84 zemepisná stopa je vizuálna poloha satelitu, nie poloha rádiového lúča; medzi 5 s bodmi sa neinterpoluje. V 30 s hraniciach sa prepočítaná elevácia, azimut a vzdialenosť porovnávajú s uloženými vzorkami s toleranciou `1e-5` stupňa alebo kilometra. Zdieľajú SGP4 jadro, takže nejde o nezávislé overenie propagácie.

Súradnice aut a cesty sú lokálne metre (+x východ, +y sever). RSU je na `(800, 675) m` a WGS84 `(48.1486°, 17.1077°, 0 m)`. Orbitálne výstupy používajú UTC, stupne, kilometre a milisekundy jednosmerného šírenia vo vákuu. Pravidlo 10° je čisto geometrická maska voči RSU a nevyjadruje prijateľnú kvalitu signálu.

## Výstup a reprodukcia

Výstupom je `data/derived/viewer/bratislava-archived-geometry-replay.json` so SHA-256 `3a1f55ad9f6ed68552db37f7226b798812b332920c76f9e050c737ef8bc1064f` a sprievodné metadáta. Výstup má samostatný typ `archived_geometry_only`; API `/api/archived-geometry/replay` kontroluje hash a nemieša ho s `/api/runs/.../replay` historického paketového behu SNS-3. Sada skupín obsahuje po tri 30 s vzorky. Vybrané ID sú Starlink `64434, 64434, 49762`, Iridium NEXT `43253` a Globalstar `37190` v časoch 0/30/60 s. V každej skupine je 13 vypočítaných 5 s zemepisných polôh vybraného objektu.

Z koreňa projektu:

```bash
.venv/bin/python tools/build_archived_geometry_replay.py \
  --georeference-csv data/derived/georeference/bratislava-synthetic-road-20261022.csv \
  --georeference-metadata data/derived/georeference/bratislava-synthetic-road-20261022.metadata.json \
  --orbit-csv data/derived/multi-constellation/bratislava-20261022T124500Z.csv \
  --orbit-metadata data/derived/multi-constellation/bratislava-20261022T124500Z.metadata.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --scenario data/inputs/bratislava-synthetic-road/scenario.json \
  --output data/derived/viewer/bratislava-archived-geometry-replay.json
.venv/bin/python tools/check_archived_geometry_replay.py
.venv/bin/python tools/scenario_server.py --port 8765
```

V `http://127.0.0.1:8765/` rozbaliť **Archivovaná geometria**, vybrať skupinu a stlačiť **Otvoriť archivovanú geometriu**. Existujúce ovládanie umožňuje pauzu, posun, rýchlosť 0,25× až 8× a slučku. Terminál výslovne uvádza, že pre tento režim niet paketov ani obsahu správ. Výber skupiny nemení pohyb áut ani paketový beh iných režimov.

## Kontrola a výsledok tohto míľnika

Hypotéza: uložené polohy áut, miesto RSU a vybrané satelitné objekty možno časovo zosúladiť a vizuálne prehrávať bez toho, aby sa geometria prezentovala ako sieťová dostupnosť. Kontrolný variant tvorí oddelený existujúci paketový replay; tento nový režim obsahuje nulové paketové polia a nulové sieťové metriky. Test `tools/check_archived_geometry_replay.py` len číta uložené zdroje a znovu v pamäti vygeneruje identické bajty výstupu. Kontroluje hash, 236 bodov áut, päť bodov pôvodnej cesty, deväť 30 s orbitálnych vzoriek a 39 polôh vybraných objektov. Výsledok: `PASS`, SHA-256 vyššie. Samostatné kontroly: kompilácia Python modulov a načítanie API s HTTP 200. V tomto míľniku neprebehol nový ns-3 experiment; žiadne PDR, jitter ani dostupnosť služby z geometrie nevyhodnocujeme.

Obmedzenie: editor zobrazuje syntetický cestný úsek ukotvený pri Bratislave a sledované objekty z archivovaných GP. Neobsahuje skutočnú mapu ulíc, reliéf, tieniace objekty, antény, rádiovú vrstvu, prevádzkový stav operátora ani model priamych terminálov auto–satelit. Pre presnosť paketovej komunikácie treba samostatný validovaný sieťový scenár; táto vizualizácia sama o sebe nepreukazuje žiadne doručenie.
