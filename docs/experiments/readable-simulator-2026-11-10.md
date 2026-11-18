# Zjednotenie názvov aktívneho simulátora — 10. 11. 2026

## Rozsah

Aktívny vstup `tools/simulator_cli.py` a server `tools/simulator_server.py` používajú opisné názvy. Všetkých 38 aktívnych Python modulov, šesť natívnych C++ súborov, testy, importy, build argumenty, UI volania, stopové značky, názvy konfigurácií a študijné kotvy boli zosúladené. Historické sondy, experimentálne denníky a ich výsledky zostali uložené ako história. Pôvodné aktívne súbory pred premenovaním sú v `archive/pre-readable-names-20261110.tar.gz`; úplná mapa je v `archive/pre-readable-names-20261110-map.json`.

Hlavné miesta: `bp_u9.py` → `simulator_cli.py`; `u9_server.py` → `simulator_server.py`; `u9_run_ground.py` → `simulator_ground_runner.py`; `u9_native_editor.py` → `simulator_satellite_runner.py`; `u9-ground-cam-dcc.cc` → `vanet-ground-network.cc`; `u9-full-integration-per-rsu.cc` → `vanet-leo-network.cc`. Aktuálny verifier prijíma aktuálne zdrojové hashe; staré výsledky zostávajú v archíve pre historické vyhodnotenie. Nezmenil sa význam CAM (lokálny príjem) ani DENM (voliteľný most cez RSU/SNS-3).

`docs/BP-KOMPLET-NA-2-DNI.md` je jediný úplný materiál na štúdium; balík ho obsahuje ako `STUDIUM-NA-2-DNI.md`. Ukážková stopa pochádza z nového overeného behu `results/simulations/readable-corridor-final-20261110`, event `d319516eb46351c4`. Pri `car3` je čas od DENM TX 135,655 ms simulačného času.

## Overenie zdrojového projektu

- `python3 scripts/refresh_study_code.py --check`: 64 aktívnych súborov aktuálnych.
- `.venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: 38 testov OK.
- Pozemný beh `results/simulations/readable-ground-20261110`: verifier PASS; 92 CAM TX, 233 CAM RX, 7 príjmov DENM. Finálny pracovný runtime zopakoval rovnaký výsledok v `final-ground-20261110`.
- Satelitný beh `results/simulations/readable-iridium-final-20261110`: verifier PASS; 92 CAM TX, 1 príjem gateway, 2 vzdialené príjmy DENM. Finálny pracovný runtime zopakoval rovnaký výsledok v `final-iridium-20261110`.
- Uložený kreslený koridor `results/simulations/readable-corridor-final-20261110`: verifier PASS; 875 CAM TX, 1 príjem gateway, 2 vzdialené príjmy DENM. Časy v učebnom materiáli sú odčítané z jeho `native/baseline/trace.csv`.

## Overenie prenosu

Finálny `BP-Simulator.zip` má SHA-256 `e5fbed72125b25ca65eb5727854ecb3e2f396581da0b4afb6d15014c29b7b797`. `verify.py` prešiel pre 10 231 súborov a odkazov v balíku aj po rozbalení ZIPu pomocou `unzip`; `unzip -tq` nehlási chybu. Python 3.12 prostredie sa nainštalovalo z offline wheelov, Vanetza a ns-3.38/SNS-3 3.38 sa preložili z rozbalených zdrojov. V čistej kópii zo ZIPu prešiel pozemný aj Iridium preflight, run a verify (92/233/7 CAM TX/CAM RX/DENM RX na zemi; 92 CAM TX, 1 gateway RX a 2 vzdialené DENM RX pri satelite). HTTP server vrátil 200 pre editor, technickú stránku, nový návrh a technický model.

Po presune do finálneho pracovného priestoru sa porovnalo 88 aktívnych zdrojových/vstupných súborov s balíkom bez rozdielu. `run.sh` z balíka na ploche prešiel pozemným, Iridium a uloženým D1 satelitným scenárom (`final-real-map-20261110`); D1 mal 1 478 CAM TX, 1 príjem gateway a 3 vzdialené príjmy. Samostatné profily Starlink a Globalstar z plochy tiež prešli preflight, run a verify; oba mali 92 CAM TX, 1 príjem gateway a 2 vzdialené príjmy DENM. Ikona/launcher sa spustili s testovacím prehliadačom a server sa korektne ukončil. Kontrola `BP-Simulator.zip.sha256` na ploche prešla. Starší otvorený editor stále beží proti svojmu pôvodnému pracovnému adresáru, preto sa tento adresár presunie do archívu až po zatvorení jeho procesu. Pri Ubuntu 26.04 sa na miestny test používa Python 3.12 a vypína sa `NS3_WARNINGS_AS_ERRORS`, pretože GCC 15 mení upozornenie upstream ns-3.38 na chybu. Distribučný `setup.sh` deklaruje čistú inštaláciu iba pre Ubuntu 24.04 x86_64; skúška na čistej 24.04 ešte nie je vykonaná.
