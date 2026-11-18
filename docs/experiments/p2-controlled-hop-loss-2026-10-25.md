# P2: kontrolované straty na LAN a modelovej ISL v oboch smeroch

**Stav 25. 10. 2026:** päť z piatich behov PASS, 57/57 Python testov OK. Toto uzatvára samostatnú jednotku P2 pre fyzické prijímacie chyby na dvoch presne určených P2P hranách. Celá fáza P2 zostáva rozpracovaná: satelitné user/feeder RF chyby, fronty, opakovania a dynamické CAM/DCC ešte nemajú ekvivalentnú kontrolovanú skúšku. [Predchádzajúci mestský/OSM pilot](p2-urban-osm-paired-2026-10-25.md) zostáva v pôvodnom výsledkovom adresári s pôvodným hashom C++ zdroja.

## Zásah a porovnateľnosť

Runner `tools/run_p2_fault_hops.py` vygeneruje tú istú výskumnú OSM/SUMO trasu Bratislavy, UTC 22. 10. 2026 12:46:32, `seed=314159`, šesť primárnych CAM od `car0` po 500 ms a 12 súbežných CAM dvoch ďalších áut. Všetky prípady používajú mestský LOS model, 802.11p OCB a obojsmernú referenčnú cestu `RSU→UT→SAT0→modelová ISL→SAT1→GW→SAT1→modelová ISL→SAT0→UT→RSU→auto`. Päť vetiev zdieľa pôvodné bajty šiestich CAM a všetky vstupné waypointy. Poruchový `event_id` je `ca0000000000c5d0`, teda tretí primárny CAM.

Nový zdroj `src/editable-v2-ocb-p2-drop-audit.cc` pripája selektívny ns-3 `ErrorModel` na **prijímajúce zariadenie**. Model dekóduje celé ID z ICB1/GRA1 v rámci, zahodí iba jednu určenú správu a zapíše surový P2P rámec pred odovzdaním vyššej vrstve. LAN `PointToPointNetDevice` navyše samo vydá natívny `PhyRxDrop`; pri SNS-3 `PointToPointIslNetDevice` nie je zodpovedajúci raw drop trace, preto je záznam v jeho skutočne použitej metóde `ErrorModel::DoCorrupt`. Checker overuje IP a UDP kontrolné súčty zahodeného rámca, presný ICB1/GRA1 obsah, čas poruchy a chýbajúci následný hop. Porucha je **deterministický test klasifikácie**, nie odhad bitovej chybovosti siete.

| Vetva | Jeden zásah na udalosti 3 | GW / vytvorené ICB1 | I2V1 v aute / 6 | Posledný potvrdený krok stratenej správy |
| --- | --- | ---: | ---: | --- |
| `none` | bez zásahu | 6 / 6 | 6 | celá cesta |
| `lan_report` | RSU→UT, príjem na UT LAN | 5 / 6 | 5 | RSU vyslalo ICB1 |
| `isl_report` | SAT0→SAT1, príjem na SAT1 ISL | 5 / 6 | 5 | UT vyslalo ICB1 do SNS-3; `PacketTrace` potvrdzuje SAT0 |
| `isl_ack` | SAT1→SAT0, príjem na SAT0 ISL | 6 / 6 | 5 | GW vyslala presný GRA1 |
| `lan_ack` | UT→RSU, príjem na RSU LAN | 6 / 6 | 5 | UT vyslal presný GRA1 na LAN |

Vo všetkých vetvách zostalo šesť CAM dekódovaných na RSU a lokálny CAM príjem 18/18 oprávnených párov. Report vytvorený na RSU je menovateľ vzdialeného doručenia podľa kontraktu P0. Pri chybách návratu už vzdialená aplikácia report **má**; chýba iba oznámenie v aute. Každý prijatý report bol pred výskumným prahom 60 s. Diagnostický prah 100 ms nesplnil žiadny report v žiadnej vetve; 100 ms nie je zvolený bezpečnostný ani servisný deadline a nenahrádza 60 s kontrakt. Z piatich párovaných krátkych behov nemožno odhadovať prevádzkovú PDR.

## Raw dôkaz a reprodukcia

`results/p2_fault_hops_20261025` obsahuje manifest s SHA-256 zdroja, runnera, generátora, kontraktu, OSM/SUMO, orbitálnych vstupov a všetkých raw výstupov. Každá vetva má `trace.csv`, OCB/LAN PCAP, `PacketTrace.log`, záznamy surových IP bajtov na oboch ISL smeroch a sumarizačný log. `p2-fault-verification.json` a `p2-fault-metrics.csv` uvádzajú príčinu každého ID, posledný potvrdený krok, vzdialené/aplikačné doručenie, geometrického kandidáta a `attachment_control_state=not_observed`.

`tools/check_p2_fault_hops.py` znovu číta raw stopy a vyžaduje rovnaký CAM/ICB1 medzi vetvami, správne IP/UDP checksumy, zdroj GRA1 v SHA-256 presného ICB1, neskoršiu neprítomnosť zahodeného ID a presný počet päť úspešných ostatných správ. Dva negatívne testy po **aktualizácii manifest hashov** menia bajt zahodeného ISL rámca alebo odstraňujú záznam poruchy; oba musia skončiť zamietnutím. Pôvodné P2 mestské/OSM checkery (12+9 prípadov) a P1 raw replay po doplnení prešli znovu. Pri analýze sa zároveň opravilo rozpoznanie natívneho názvu `PhyRxDrop` bez závislosti od veľkosti písmen.

```bash
cd '/home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca'
.venv/bin/python tools/check_p2_fault_hops.py results/p2_fault_hops_20261025
.venv/bin/python -m unittest discover -s tools -p 'test_*.py'
.venv/bin/python tools/run_p2_fault_hops.py vendor/ns-3.38-ocb-eval results/MOJE_NOVE_P2_FAULT_ID
```

Posledný príkaz vyžaduje nové prázdne výsledkové ID. OSM cestná sieť je skutočná geometria, ale dopravný dopyt, RSU, anténa, DVB rádio, proxy brána aj ISL sú výskumné modely alebo predpoklady. Test `ErrorModel` sa nesmie označiť ako kalibrácia reálnej linkovej chybovosti.

## Nasledujúca brána P2

Zostáva vyvolať a raw stopou potvrdiť stratu na DVB user a feeder kanáli bez zámeny so zlyhaním registrácie terminálu, skutočný drop v identifikovanej fronte, a oddeliť retransmisie od opakovaných trace udalostí. Potom sa rozhodne o dynamickom ETSI CAM/DCC profile a jeho overiteľnom kóde. Ak konkrétny SNS-3 callback nedokáže určiť príčinu, v per-event zázname musí ostať `unknown` alebo `not_observed`.
