# Audit pracovného simulátora — 18. 11. 2026

## Príčina zlyhaného otvorenia posledného behu

Beh `20261118t082054zd8e90527` v pracovnom runtime skutočne dokončil natívny SUMO/ns-3/SNS-3 výpočet. Má finálny `run-manifest.json`, výsledok `PASS`, 6 áut, 2 RSU, 1 aktívnu družicu, 1 DENM prijatý bránou a 3 vzdialené prijatia autom. Starý server bežal od 17. 11. 21:13 a v pamäti držal Python moduly pred neskoršou zmenou zdrojov. Volanie statusu preto vrátilo 409 a ako dôvod chybne uviedlo posledný riadok worker logu, hoci ten obsahoval úspešný JSON. `./.venv/bin/python tools/simulator_cli.py verify results/simulations/20261118t082054zd8e90527` prešlo. Čerstvo spustený server vrátil 200 pre status a replay.

Server teraz pri existujúcom finálnom manifeste označí neúspech overenia ako `unverified` a vypíše skutočný dôvod. Nepovoľuje obísť verifikáciu. Po zmene kódu treba ukončiť otvorený server a znova spustiť ikonu; samotný refresh stránky nenačíta nové Python moduly.

## Nový beh a grafické prehratie

- Nový pozemný beh: `results/simulations/audit-20261118-ground-smoke`, konfigurácia `config/simulator-smoke.json`, 6 s, 5 áut, 3 RSU. `run` aj `verify`: `PASS`; 92 CAM TX, 233 CAM RX, 7 prijatí DENM, bez teleportu. Prehrávač otvoril beh, zobrazil paketové udalosti po posune času a správne skryl satelitný fyzikálny audit.
- Posledný satelitný beh: `bash run.sh verify 20261118t082054zd8e90527`: `PASS`. V novom serveri sa otvoril replay, fungoval časový posuvník, ▶/pauza, detail CAM s raw bajtmi a fyzikálny audit. Opravené kreslenie auditových značiek, ktoré používalo nedefinovanú premennú. Kontrola konzolových chýb prehliadača bola prázdna.
- Načítanie mapy už pred asynchrónnym scenárom nevyvolá prechodnú chybu rendereru. Technická stránka sa načítala so skupinami SUMO, ns-3, SNS-3 a aplikačnej komunikácie. Neaktívny čas dávkovania satelitných správ je zobrazený ako pevné „vypnuté“.

## Balík

Balík na ploche obsahuje `TECHNICKA-SPRAVA.md` namiesto starého `STUDIUM-NA-2-DNI.md`; nevkladá študijnú komentovanú kópiu, legacy viewer ani Python cache. `python3 verify.py`: `PASS`, 10 236 súborov a odkazov. `unzip -t`: bez chyby. ZIP SHA-256: `a22147b0261f412e6fc215498b63d3bbe1d66bee4e81b9c5f98c86c53a98735c`. Spúšťač overil identitu aktualizovaného pracovného runtime a oba existujúce behy prešli verifikáciou cez `run.sh`. Starší balík je zachovaný v `~/Documents/BP-Simulator-Archiv/20261118-pred-technickou-spravou/`.

Overenie sa týka aktuálneho pracovného počítača. Čistá inštalácia na druhom Ubuntu 24.04 a výsledné vedecké metriky jednotlivých scenárov sú samostatné kroky. Starý otvorený Firefox stále používa svoj pôvodný server, kým sa nezavrie a ikona nespustí znova.

## Odovzdanie na GitHub a čistenie starých verzií

Súkromný repozitár `PinKiePieSK/BP-VANET-LEO-simulator` obsahuje zdrojový kód, scenáre a dokumentáciu bez lokálnych pokynov pre asistenta. Vydanie `v2026-11-18` obsahuje prenosný ZIP a jeho kontrolný súčet. GitHub pri ZIPe uvádza SHA-256 `a22147b0261f412e6fc215498b63d3bbe1d66bee4e81b9c5f98c86c53a98735c`, totožný s overeným lokálnym balíkom. Čerstvý klon úspešne prešiel kompiláciou Python súborov v `tools/` a `scripts/`. Kontrolný súčet vydania sa dal stiahnuť a zhodoval sa s miestnym súborom. Počas záverečnej kontroly `verify.py` overil 10 236 súborov a odkazov a existujúci satelitný beh znova prešiel verifikáciou.

Po tomto overení boli staré lokálne verzie v `~/Documents/BP-Simulator-Archiv/`, staré párové pracovné prostredie a pôvodný `BP-prenos-2026-10-25` presunuté do Koša. Aktívny zdrojový projekt, pracovný runtime, výsledky v ňom a aktuálny prenosný balík zostali na mieste.
