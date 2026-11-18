# Prehrávač overených pohyblivých CAM udalostí a geometrie

## Účel, hypotéza a hranica modelu

Tento míľnik spája **už overené** raw udalosti ns-3/Vanetza behu `results/moving_cam_iridium_gate/` s rovnakým UTC úsekom syntetickej SUMO cesty a WGS84 GP geometrie auta/RSU. Hypotéza UI kontroly: skutočné CAM/report bajty a rozhodnutia modelovej gate sa dajú časovo prehrávať bez zámeny za operátorský satelitný prenos. Kontrolný prípad `ungated` nemá bránu, `geometry_positive` má pripnutú kandidátsku geometriu Iridium a `geometry_block` navyše zámerné testovacie vypnutie. Rozhranie nemení simuláciu ani nepočíta novú sieťovú metriku.

Paketová cesta v tomto behu je auto CAM UPER → GN/BTP → ns-3 802.11p → RSU → 96 B UDP report → lokálna LAN → UT proxy → **abstraktný 22 kbit/s point-to-point servisný úsek** → server. Kandidát Iridium NEXT `43253` riadi iba modelovú gate a jednosmerný dodatočný `r/c`; v ns-3 neexistuje satelitný uzol, satelitné RF/MAC, beam, gateway ani operátorské prihlásenie. Všetky skutočne modelované bajty a limity vysvetľuje [rozhodnutie o CAM gate](../decisions/moving-cam-iridium-gate.md). Geometria skupín Starlink a Globalstar je v tomto UI **iba porovnanie**; nikdy neriadi gate.

## Vstupy a overenie

Nástroj `tools/build_moving_cam_replay.py` je read-only voči všetkým zdrojom. Pred výstupom overí manifest raw behu, hashe vstupných súborov v ňom a opätovne spustí existujúci bajtový audit `tools/check_moving_cam_iridium_gate.py` pre všetky tri prípady. Ten kontroluje presné 41 B CAM, 85 B GN/BTP/CAM, 96 B reporty, 126 B PPP/IPv4/UDP rámce a dva PCAPy na prípad vrátane checksumov a následkov brány. Nové metadáta ukladajú SHA-256 každého raw trace CSV, decoded CSV, gate CSV a PCAP. Z raw trace sa preberajú **presné** `time_us`, `stage`, dĺžka a `raw_hex`; pomocné `event_id` rádio RX s nulovou hodnotou sa len normalizuje z CAM generation delta a pôvodná hodnota ostáva v poli `source_event_id`. Kliknutie v UI zobrazí raw hex vybranej udalosti, príslušný 41 B CAM, 121 B pozemný 802.11 PCAP rámec a 96 B report.

Ďalšie kontrolované zdroje: [archivovaný geometrický replay](archived-geometry-viewer.md), SHA-256 `3a1f55ad9f6ed68552db37f7226b798812b332920c76f9e050c737ef8bc1064f`, a [0,5 s geometria áut/RSU voči trom GP skupinám](moving-three-group-cars-rsu-geometry.md), SHA-256 `d5623466356f935abfc651cd41e0d9ff1118a67ce4aebf97081c43af6f8fe5ed`. Cesta, autá a pevné RSU pochádzajú z prvého; počty kandidátov, vybrané ID, elevácia, azimut, šikmá vzdialenosť a jednosmerný vákuový `r/c` pre RSU/car0/car1 z druhého. UTC začiatok všetkých dát je `2026-10-22T12:45:00Z`. Polohy áut sú zaznamenané po 0,5 s; medzi nimi je len vizuálna interpolácia. Orbitálna geometria a poloha vybraného objektu sa vzorkujú po 0,5 s a medzi vzorkami sa neinterpolujú. Vybraný subpoint sa pre každú skupinu vypočíta z archivovaného, hashovaného OMM cez SGP4/WGS72 a Astropy TEME→ITRS; v čase 0/30/60 s sa kontroluje presná zhoda s predchádzajúcim archívom. Tak mapa neukazuje staré ID po skutočnej zmene geometrického výberu v novom 0,5 s rade.

GP snapshot má v manifeste čas získania **12:49:43.719531 UTC**, teda až po začiatku prehrávaného intervalu. Je to retrospektívna rekonštrukcia, nie informácia, ktorú mal terminál v čase 12:45 UTC. Maska **10°** je experimentálna geometrická podmienka, nie parameter antény alebo služby. Jednotky payloadu sú `time_us` v mikrosekundách od UTC začiatku, gate `delay_ns` v nanosekundách, lokálne súradnice cesty v metroch, WGS84 v stupňoch a metroch, šikmá vzdialenosť v kilometroch a samotné `r/c` v milisekundách. PCAP bajty sa nekonvertujú na vymyslené satelitné rámce.

## Výstup, UI a reprodukcia

Výstup `data/derived/viewer/moving-cam-iridium-gate-replay.json` má režim `verified_moving_cam_geometry_replay`, SHA-256 `c2b211e4ca589901eb9b008c9a10450ee3fbbe2558a822eed0b4b87161cba594` a metadáta s hashmi zdrojov. Samostatný GET `/api/moving-cam/replay` ho podáva len pri zhode hasha. Nenahrádza `/api/runs/<id>/replay` historického SNS-3 ani `/api/archived-geometry/replay` čisto geometrického režimu.

Z koreňa projektu:

```bash
# Ak raw results chýbajú, obnoviť overený beh bez sudo:
bash tools/run_moving_cam_iridium_gate.sh

OPENBLAS_NUM_THREADS=1 .venv/bin/python tools/build_moving_cam_replay.py \
  --raw results/moving_cam_iridium_gate \
  --archived-geometry data/derived/viewer/bratislava-archived-geometry-replay.json \
  --vehicle-orbit data/derived/vehicle-orbit/bratislava-cars-rsu-three-groups-20261022.csv \
  --output data/derived/viewer/moving-cam-iridium-gate-replay.json
OPENBLAS_NUM_THREADS=1 .venv/bin/python tools/check_moving_cam_replay.py
.venv/bin/python tools/scenario_server.py --port 8765
```

V `http://127.0.0.1:8765/` rozbaliť **Overený pohyblivý CAM · gate/drop replay**, v poli **Prípad** vybrať **Testovacie vypnutie · 4/6 na serveri**, **Povolená geometria · 6/6** alebo **Kontrola bez brány · 6/6** a stlačiť **Otvoriť overený CAM replay**. Pole **Zobrazovaná GP geometria** ponúka **Iridium NEXT · vstup brány**, **Starlink · len porovnanie** a **Globalstar · len porovnanie**. Časovú os možno pozastaviť, posúvať v kroku 1 ms, prehrať rýchlosťou 0,25× až 8× a zapnúť slučku. Presné časy udalostí ostávajú v µs, aj keď posuvník má milisekundový krok. V termináli sa zobrazujú `GATE_ON/OFF`, raw packet stages a pri kliknutí hex vrátane 41 B CAM, 121 B pozemného 802.11 PCAP rámca a 96 B reportu. Filter **Abstraktný servis** v CAM režime nahrádza všeobecný nápis satelitného backhaulu. Udalosti sú prehľadateľné aj v dialógu uzla; nejde o shell.

## Zaznamenané výsledky a denník

| Prípad | Raw udalosti | CAM pri RSU | Server `SERVER_ACCEPT` | Pravidlo |
| --- | ---: | ---: | ---: | --- |
| `ungated` | 78 | 6/6 | 6/6 | bez gate |
| `geometry_positive` | 78 | 6/6 | 6/6 | kandidát Iridium `43253` povolený |
| `geometry_block` | 72 | 6/6 | 4/6 | zámerný override `[30,520;31,020)` s |

V negatívnom prípade je skutočne zaznamenaný `GATE_OFF` v **30 520 000 µs** (`test_override`), `SERVICE_GATE_RX_DROP` v **30 551 917 µs** pre CAM vytvorený v 30,5 s a `UT_GATE_BLOCK_TX` v **31 000 267 µs** pre CAM vytvorený v 31,0 s. Následný `GATE_ON` je v **31 020 000 µs**. Ide o úmyselný kontrolný zásah, nie o pozorovaný výpadok Iridia. Všetkých šesť CAM dorazí do RSU v každom prípade; štyri reporty v negatívnom prípade dorazia na modelový server.

`tools/check_moving_cam_replay.py` overí hash každého raw zdroja, 0,5 s geometriu, 121 vybraných zemepisných polôh na skupinu, dĺžku každého raw hexu, v každom prípade šesť trojíc 41 B CAM/121 B pozemný PCAP/96 B report, presné stavy brány, dva neúspešné reporty a zostaví výstup znovu **bitovo identicky** v pamäti. Posledný výsledok: `PASS`, SHA-256 vyššie. `node --check viewer/app.js`, `py_compile` a API GET skončili úspešne; API vrátilo HTTP 200 a 345 120 B. Následná vizuálna kontrola v lokálnom prehliadači na porte 8766 otvorila `geometry_block`, posunula čas na 30,700 s a kliknutím na `SERVICE_GATE_RX_DROP` zobrazila 126 B raw rámec, 41 B CAM, 121 B pozemný PCAP rámec, 96 B report a výsledok `in_flight_drop`. Na tejto obrazovke bolo viditeľné `GATE_OFF` v 30,520 s a metrika 4/6. V tejto úlohe neprebehol nový sieťový experiment a nesiahalo sa na raw výsledky.

## Obmedzenia

Prehrávanie presne ukazuje len uložený šesťsprávový beh. Syntetická cestná trasa nie je skutočná ulica; žiadny RF link auto–satelit ani RSU–satelit nebol vytvorený. Doba `r/c` je geometrická jednosmerná časť **jedného** úseku pridaná do abstraktného P2P servisu. Kandidátsky výber a počet objektov neznamená aktívny lúč, podporovaný terminál, členstvo v sieti, priebežnú dostupnosť alebo paketovú cestu cez skutočnú konšteláciu. Tento replay preto poskytuje bajtovo a časovo kontrolovateľný pohľad na **modelový gate/drop experiment**, nie dôkaz o správaní operátora.
