# Upratanie aktívneho kódu simulátora — 3. 11. 2026

## Rozsah

Aktívny prenosný balík teraz obsahuje 36 Python modulov v `tools/`, šesť vlastných C++ súborov v `src/` a aktuálne súbory editora v `viewer/`. Zoznam sa odvodzuje od vstupov `bp_u9.py`, `u9_server.py` a `fetch_orbits.py`; server, balík a študijná kópia používajú rovnaký zoznam webových súborov z `simulator_inventory.py`.

Pred zmenou sa cez importy dostávalo do balíka 65 Python súborov. Najmä `u9_native_editor.py` používal celý experimentálny runner U4 iba kvôli kompilácii, checker používal U4 checker iba kvôli parsovaniu ISL skoku a orbitálny kód ťahal staré sondy. Potrebné funkcie sú teraz v `simulator_platform.py`, `simulator_coordinates.py`, `simulator_orbits.py`, `simulator_satellite_inputs.py`, `simulator_build.py` a `simulator_packet_trace.py`. Žiadny aktívny modul neimportuje historický `run_*`, `check_*`, `prepare_*`, `scenario_v3`, `v3_leo_topology` alebo `u4_model_inputs`.

Z koreňov boli presunuté staré sondy a testy do `tools/legacy/` (283 súborov, ďalšie štyri zastarané testy po kontrole), staré C++ sondy do `src/legacy/` (82 súborov), staré stránky do `viewer/legacy/` (23 súborov) a staré migračné a pilotné skripty do `scripts/legacy/` (12 súborov). Zoznam presunutých súborov je v príslušnom `ARCHIVED-2026-11-03.txt`. Z aktívneho C++ enginu bola odstránená skrytá vetva `U9_DIRECT_CARS` a jej neštandardný formát `CAM1`; starý kód zostal iba v historickej časti. Starý balík zdrojov pred úpravou je uložený v `archive/pre-cleanup-simulator-20261103/`.

Pri opakovanom natívnom behu sa našla kolízia generovaného anténneho súboru: po malej zmene časových podkladov mal rovnaký názov, ale inú polohu. Identita nového SNS-3 vstupu preto zahŕňa aj vypočítanú referenčnú polohu. Funkcia `put_exact()` naďalej odmieta prepísať rozdielny obsah pod existujúcou identitou.

Medzivýsledky počas úpravy vrátane prvého odmietnutého pokusu sú v `results/diagnostics/code-cleanup-20261103/`; iba finálne behy nižšie zostali medzi aktuálnymi simuláciami.

## Overenie

Porovnanie starého a nového orbitálneho kódu na pripnutom archíve Iridium NEXT: 79 objektov, rovnaké vybrané ID, časové vzorky, ECEF súradnice, elevácie, hash EOP a lokálny prevod ENU → WGS84. Sada aktuálnych testov: **35 testov OK**, vrátane odmietnutia poškodeného IPv4/UDP paketu a odrezaného PCAP. Neplatné testy odstráneného priameho režimu a testy viazané na staré zdrojové hashe sú pri historickom kóde.

| Beh | Skutočná paketová kontrola |
| --- | --- |
| `results/simulations/cleanup-ground-final-20261103` | Pozemný CAM/DENM, 5 áut, 3 RSU, 237 prijatí CAM a 3 prijatia DENM; `run` aj `verify` PASS. |
| `results/simulations/cleanup-iridium-final-20261103` | Natívny SNS-3 generický DVB; DENM v bráne 1, na vzdialených autách 2; `run` aj `verify` PASS. |
| `results/simulations/cleanup-starlink-20261103` | Natívny SNS-3 generický DVB; DENM v bráne 1, na vzdialených autách 2; `run` aj `verify` PASS. |
| `results/simulations/cleanup-globalstar-20261103` | Natívny SNS-3 generický DVB; DENM v bráne 1, na vzdialených autách 2; `run` aj `verify` PASS. |

Staré výsledky a ich manifesty sa nezmenili. Manifesty s hashmi pred úpravou sa nedajú vydávať za nový beh; na ich interpretáciu slúži zachovaná zdrojová snímka a pôvodné archívy. Nové behy sa kontrolujú voči novým zdrojom.

## Prenosný balík a spustenie

Balík `/home/samuel-petrik/Desktop/BP-Simulator/` a ZIP `/home/samuel-petrik/Desktop/BP-Simulator.zip` obsahujú iba aktívny simulátor. Kontrola manifestu overila 11 261 súborov a odkazov; ZIP má 12 109 položiek, bez poškodenej položky. Aktuálny SHA-256 ZIP: `890b7fcf8eb2a0f3a11ccf9c8a9da970656d5463ba031ad5f080dc58854596ab`.

Po čistej inštalácii prenosného balíka do samostatného pracovného prostredia prešli skutočné behy `portable-cleanup-ground-20261103` a `portable-cleanup-iridium-20261103` aj ich samostatné `verify`. Druhý beh použil natívny `single_ns3_sns3_packet_process` a generický DVB model SNS-3; jedna správa DENM dorazila do brány a dve vzdialené autá ju prijali. Server z čistej inštalácie otvoril aktuálny editor a technické parametre; neaktuálne stránky a API vrátili 404.

Ikona `/home/samuel-petrik/Desktop/BP-Simulator.desktop` teraz smeruje na nový balík. Predchádzajúci balík bol odložený v `archive/pre-cleanup-portable-20261103/`; starý otvorený proces a jeho výsledky zostali nedotknuté. Nové spustenie používa nový balík a čisto zostavené pracovné prostredie cez `/home/samuel-petrik/Desktop/BP-Simulator-Workspace`.

## Kontrola odkazov a behu editora

Následný HTTP audit 3. 11. 2026 odhalil dve chyby v serverovom čítaní behu: GET vetva ešte očakávala `/api/u9/runs` namiesto `/api/simulator/runs` a výsledok verifiera prepísal API stav `complete` hodnotou `PASS`. Obe vetvy sú opravené v `tools/u9_server.py`; aktuálne testy kontrolujú odpoveď hotového behu, všetky webové súbory a lokálne odkazy v oboch HTML stránkach. Prešlo 35 testov.

V izolovanom HTTP behu prešli `editor/check`, `editor/save`, zoznam a načítanie scenára, `preflight`, spustenie pozemného behu, stav `complete`, replay, detail paketu a satelitný fyzikálny audit. Dočasný scenár a výsledok z tohto auditu boli po úspechu odstránené. Samostatne prešli orbitálny náhľad a desaťsekundové polohy. V prehliadači sa načítala reálna mapa s 5 779 cestnými úsekmi, technická stránka zachovala rozpracovaný scenár a satelitný replay zobrazil 244 paketových spojení aj dekódované bajty CAM; konzola nehlásila JavaScript chyby.

Staré otvorené okno bolo po tejto oprave zatvorené. Spúšťač z aktuálneho balíka otvoril Firefox a nový server na porte 8766; jeho `GET /api/simulator/runs/workspace-iridium-20261103` vrátil stav `complete`, jednu aktívnu družicu a dve prijatia DENM vo vzdialených autách.
