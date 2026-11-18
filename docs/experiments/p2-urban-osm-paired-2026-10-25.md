# P2: párovaný mestský CAM/OCB pilot na editovateľnej a OSM trase

**Stav 25. 10. 2026:** ucelený pilot **PASS**, 21 z 21 prípadov a 54 Python testov. **Celá brána P2 ostáva otvorená:** kontrolované straty na LAN, user/feeder linke, vo fronte a pri deadline ešte neboli vyvolané a kladný C++ beh stále vyžaduje úplný satelitný úspech. Výsledky sú dôkazom paketovej integrácie a rádiovej citlivosti v modeli, nie odhadom dostupnosti alebo výkonu služby operátora.

## Metóda a hranice vstupu

Obe sady používajú jeden ns-3.38/SNS-3 3.38 clock a tú istú overiteľnú cestu `Vanetza UPER CAM → GN/BTP → 802.11p OCB → RSU → ICB1 → UT → SAT0 → modelová ISL → SAT1 → proxy GW → GRA1 → opačná ISL → RSU → experimentálne I2V1 → auto`. Šesť primárnych CAM od `car0` vzniká v čase 20,0 až 22,5 s po 0,5 s. ICB1 96 B vznikne iba z CAM skutočne dekódovaného na RSU. GRA1 referencuje ID a SHA-256 presného ICB1. Je to výskumná informácia o dopravnom stave s prahom 60 s od vytvorenia ICB1; kontrakt `safety_claim=false` nevydáva tvrdenie o včasnej bezpečnostnej výstrahe.

- **Editovateľná SUMO cesta:** riedka zostava má tri autá a RSU; hustá má sedem áut a RSU. Každé ďalšie auto v hustej zostave vyšle svoj platný GN/BTP/UPER CAM v každom zo šiestich časových okien, spolu 36 CAM navyše. Na tej istej syntetickej trase sa meria LOS, vynútený NLOS a lokálne syntetické tienenie.
- **OSM Bratislava:** existujúca cestná sieť `road.net.xml` a syntetické SUMO trasy boli znovu spustené s krokom 0,5 s, `seed=314159`. V okne 20,0 až 22,5 s sa používajú skutočné FCD body troch vozidiel zo simulácie; dve ďalšie autá vyšlú spolu 12 CAM. RSU je hypoteticky umiestnená 12 m napravo od polohy `car0` v čase 21 s (48,1492686526° N; 17,1099619081° E). WGS84 z FCD sa porovnáva s waypointmi pri každom replayi. Sieť pochádza z OSM, **dopravný dopyt, RSU ani kanál nie sú kalibrované meraním v Bratislave**.
- Obe sady používajú 5,9 GHz/10 MHz OCB, 6 Mbit/s, 20 dBm, autá vo výške 1,5 m a RSU vo výške 5 m. Rádiová citlivosť používa `ThreeGppV2vUrbanPropagationLossModel` vo verzii ns-3.38 s vypnutým shadowingom. LOS/NLOS je vynútený; `urban_building` vloží jediný **syntetický** kváder 10 × 10 × 10 m medzi `car0` a RSU v prvom bode. Nie je to budova z OSM ani kalibrovaný model ITS-G5. Model 3GPP TR 37.885 je metodika pre LTE/NR V2X, preto jeho prevzatie pre OCB interpretujeme výlučne ako citlivostnú skúšku ([3GPP TR 37.885](https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3209)).

V každej rádiovej skupine sú tri párované vetvy so spoločnou trajektóriou, časom, vyslaným primárnym CAM a seed/run: **S0** zablokuje iba odoslanie z UT do satelitu; **S1** má dve LEO a modelovú ISL; **S2** odstráni modelovú ISL. Lokálne V2V/V2I zostáva aktívne vo všetkých vetvách. S1 okamžite vracia GRA1, takže jeho neskorší stav OCB môže byť odlišný od S0/S2; nepredpokladáme rovnaké príjmy za zásahom. Archivovaná OMM geometria pre UTC 22. 10. 2026 je retrospektívny geometrický kandidát, nie potvrdenie služby.

## Overené výsledky

Menovateľ je **šesť ponúknutých primárnych CAM** na skupinu. „Lokálne“ je počet prijatých párov primárny CAM–oprávnený príjemca; zahŕňa autá aj RSU. Pri riedkej a OSM sade je maximum 18, pri hustej 42. Číslo „Wi-Fi drop“ je počet callbackov `PhyRxDrop` cez všetkých príjemcov a pakety, **nie** počet stratených primárnych správ. V stĺpci RSU/GW/auto je počet v S1.

| Trasa a rádio | Lokálne S0 / S1 / S2 | RSU / GW / auto S1 | Wi-Fi PHY drop S1 |
| --- | ---: | ---: | ---: |
| syntetická riedka LOS | 18 / 18 / 18 | 6 / 6 / 6 | 0 |
| syntetická hustá LOS | 42 / 42 / 42 | 6 / 6 / 6 | 0 |
| syntetická hustá, kváder | 19 / 21 / 19 | 4 / 4 / 4 | 91 |
| syntetická riedka NLOS | 4 / 4 / 4 | 4 / 4 / 4 | 28 |
| OSM LOS | 18 / 18 / 18 | 6 / 6 / 6 | 0 |
| OSM NLOS | 6 / 6 / 6 | 6 / 6 / 6 | 30 |
| OSM, syntetický kváder | 7 / 7 / 7 | 6 / 6 / 6 | 39 |

S0 a S2 mali vo všetkých siedmich skupinách **0 prijatí na GW a 0 I2V1 v aute**, ale uvedené lokálne príjmy ostali. Dve stratené primárne správy v syntetickom tieni a dve v riedkom NLOS majú v surovej stope drop `WIFI_PHY_RX_DROP_REASON_9/rsu0`; v pripnutej verzii ns-3.38 je dôvod 9 `PREAMBLE_DETECT_FAILURE`. Pri OSM NLOS a kvádri bolo RSU blízko primárneho auta: prijalo 6/6, hoci iné autá prijali menej. Zmena 19→21 lokálnych príjmov v hustej tienenej S1 je skutočný rozdiel po okamžitej odpovedi GRA1/I2V1, nie zmena vstupnej trasy alebo CAM.

Všetkých **38** ICB1, ktoré RSU vytvorili v siedmich S1 skupinách, prešlo cez modelový user/ISL/feeder reťazec na GW pred 60 s a odpoveď dorazila do auta. To je súčet pilotných prípadov (6+6+4+4+6+6+6), nie štatistický odhad PDR siete. Medián času CAM→auto v jednotlivých kladných skupinách bol 0,145177 až 0,145231 s. Pozorované LAN dropy aj SNS-3 `PacketTrace` dropy boli v tejto sade nulové. Šesť správ, jedna krátka epocha a jeden seed na skupinu nedávajú interval neistoty ani p95/p99.

## Surový audit

Každý výsledkový adresár má `run-manifest.json` s hashmi zdroja, runnera, vstupov a raw výstupov, `trace.csv`, OCB/LAN PCAP, `PacketTrace.log`, surové bajty oboch ISL smerov, SUMO FCD a modelové vstupy. Checkery znovu skladajú jednotlivé ID, pôvodný CAM, SHA-256 ICB1, celé IPv4/UDP kontrolné súčty, GW/GRA1/I2V1 obsah a časové poradie. Overujú pozorované ENQ/DRP a modelový UT PHY odosielací stav. Per-event CSV rozdeľuje geometrický kandidát, odoslanie cez modelový UT PHY a aplikačné doručenie; stav skutočnej registrácie terminálu je `not_observed`, pri neidentifikovanej strate `unknown`. Numerický PHY drop sa zachováva zo surovej ns-3.38 stopy.

Uložené výsledky: `results/p2_urban_load_20261025` (12 prípadov, `p2-verification.json`, `p2-metrics.csv`) a `results/p2_osm_pair_20261025` (9 prípadov, `p2-osm-verification.json`, `p2-osm-metrics.csv`). Testy menia hash ICB1 v raw trace aj WGS84 waypoint pri aktualizovanom manifeste; sémantický checker oba zásahy odmietne. Regresia má 54/54 Python testov OK; samostatný raw replay P1 zostal PASS.

```bash
cd '/home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca'
.venv/bin/python tools/check_p2_urban_load.py results/p2_urban_load_20261025
.venv/bin/python tools/check_p2_osm_pair.py results/p2_osm_pair_20261025
.venv/bin/python -m unittest discover -s tools -p 'test_*.py'
```

Nový beh musí dostať **nové prázdne ID**, lebo uložené raw výsledky sa neprepisujú:

```bash
.venv/bin/python tools/run_p2_urban_load.py vendor/ns-3.38-ocb-eval results/MOJE_NOVE_P2_URBAN_ID
.venv/bin/python tools/run_p2_osm_pair.py vendor/ns-3.38-ocb-eval results/MOJE_NOVE_P2_OSM_ID
```

## Čo ešte bráni uzavretiu P2

1. Zaviesť **kontrolované** zlyhanie na RSU→UT LAN, SNS-3 user, ISL, feeder a vo fronte/deadline. Zrušiť iba predpoklad „všetky satelitné ponúknuté pakety musia doraziť“ v C++ a nechať checker klasifikovať každé chýbajúce ID podľa skutočne posledného overeného hopu a pozorovaného dropu; bez dôkazu zostáva `unknown`. Otestovať aj odoslanie GRA1 a stratu jeho návratu.
2. Odlíšiť `PacketTrace` počet ENQ/DRP od **opakovania paketu**: aktuálna stopa nevykazuje spoľahlivý per-message počet všetkých retransmisií v MAC. Doplniť taký údaj iba s jednoznačným SNS-3/OCB callbackom a negatívnym testom, alebo ho označiť `not_observed`.
3. Pre rozhodnutie o finálnom CAM časovaní pripnúť profil generovania a skontrolovať jeho implementáciu proti [ETSI EN 302 637-2 V1.4.1, §6.1.3](https://www.etsi.org/deliver/etsi_en/302600_302699/30263702/01.04.01_60/en_30263702v010401p.pdf). Pevných 500 ms leží v intervale 100–1000 ms, ale **neimplementuje** spúšťanie podľa pohybu ani `T_GenCam_Dcc`. Prístupová časť DCC je opísaná v [ETSI TS 102 687 V1.2.1](https://www.etsi.org/deliver/etsi_ts/102600_102699/102687/01.02.01_60/ts_102687v010201p.pdf). Bez zhodnej implementácie sa hustá záťaž neoznačuje ako ETSI DCC prevádzka. DENM pridať iba po explicitnom výbere úlohy včasnej udalostnej výstrahy.
4. Ak má P2 dokazovať „reálnu Bratislavu“, treba nezávisle získať dopravný dopyt, umiestnenie RSU, stavebnú geometriu a rádiové meranie pre kalibráciu. Súčasný výstup sa správne označuje ako výskumná OSM trasa a citlivostný model.

P2 bude HOTOVO až po kontrolovaných negatívnych prípadoch a pravdivom per-hop menovateli/drop reporte. Príprava P3 alebo profilov P4 z tohto pilotu nevyvodzuje výkon skutočných komerčných sietí.
