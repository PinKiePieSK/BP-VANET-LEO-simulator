# U5: servisná vetva nad čerstvými overenými reportmi U4

**Stav:** prijímací natívny pôvod U4 + deterministický servisný replay, 27. 10. 2026. **Vstup:** `config/u5-service-bridge.json` pinne [U4 výsledný manifest](../../results/u4_parametric_full_20261027/run-manifest.json) a historický [V6 profilový kontrakt](../../config/v6_service_contract.json). **Výstup:** `results/u5_service_full_20261027/`. Toto je alternatívna vetva **od okamihu RSU_REPORT_CREATED**, nie pokračovanie po stratách v generickom DVB. Report, ktorý U4 natívna satelitná vetva stratila po RSU, sa preto môže v predpokladanej servisnej vetve doručiť; nespočítavame obe vetvy ako jednu trasu.

## Reprodukcia a kontrakt

```bash
.venv/bin/python tools/run_u5_service_bridge.py --output results/<novy-adresar>
.venv/bin/python tools/check_u5_service_bridge.py results/<novy-adresar>
.venv/bin/python tools/test_u5_service_bridge_mutation.py results/<novy-adresar>
```

Runner odmieta prepísanie existujúceho výstupu. Pred vytvorením servisných udalostí opätovne spustí úplný U4 checker. Z jeho `baseline/trace.csv`, `identity.csv`, `cam.csv` a `waypoints.csv` získa **všetkých 35** reportov vytvorených RSU. Zachová 20 pôvodných 96 B a 15 pôvodných 98 B ICB1; identita, SHA-256 CAM v tele, rodič CAM, RSU, čas a zdrojový raw riadok sa kontrolujú. Výber `n1`, `n4` a `all` predstavuje prvý 1, 4 a všetkých 35 reportov podľa pôvodného času RSU a ID. Ide o vnorené časti toho istého behu, nie nezávislé pokusy. Adaptér nemá natvrdo zadaných šesť správ a `sample_sizes` možno meniť po medzu overeného vstupu.

Každý event v servisnom CSV obsahuje pôvodné ICB1 a CAM ID, natívny RSU a číslo zdrojového riadku, presný čas, bajty, dôvod a kľúč časového pravidla. Manifest obsahuje tabuľku vzorcov časov. Checker nezávisle prepočítava IP/UDP kontrolné súčty, serializáciu v smerovej fronte, frontový limit, predpokladaný jednosmerný čas, deterministický SHA-256 stratový zásah, miestne MO retry, MT návrat a metriku. Každý čas má tak buď pôvod v U4 raw riadku, alebo presne pomenovaný vzorec s parametrami a ich zdrojom.

| Architektúra | Implementovaná hranica | Zakázané zamieňanie |
| --- | --- | --- |
| Iridium Certus/SkyLink | Modelový IP/UDP UL/DL, smerové fronty a limit publikovaného produktu z V6 | Žiadny Iridium RF/MAC, skutočná gateway/mesh cesta ani automatický LTE fallback |
| Starlink Performance | Modelový IP/UDP UL/DL; stav vyčerpanej priority podľa zmrazeného V6 registra | Žiadny meraný beam, optické ISL, plánovač alebo dostupnosť účtu |
| Globalstar RM200M | Natívne telá MO/MT bez IP datagramu a bez ISL; 96/98 B MO a 46 B MT v publikovaných hraniciach | `MO_TERMINAL_ACCEPT` a `MODEL_NETWORK_ACCEPT` sú **modelové** hranice, nie potvrdenia operátora |

Dostupnosť služby je explicitný scenárový stav D. Historické publikované produktové čísla B vo V6 kontrakte zostávajú zmrazeným podkladom z 26. 10. 2026; aktuálna oprávnenosť plánu, SKU, antény a regiónu nebola týmto behom overená. Modelové rýchlosti, fronty, strata, časy a retry sú D. `RSU_RECEIPT_RX` je lokálne aplikačné potvrdenie RSU, nie natívne U4 `CAR_I2V1_RX`, potvrdenie modemu ani operátora. Geometrický kandidát sa do U5 nepremieta na dostupnosť služby; vstupné V6 geometrie patria inej historickej šesťsprávovej dávke a nie sú ticho recyklované.

## Prijímací dôkaz

Úplný výstup má **51 vetiev**: 3 veľkosti dávky × 17 deklarovaných prípadov troch profilov. Manifest SHA-256: `0f65ebcd3663bae8060fc246ae0dab09ba1d73cd140bf2b5c112947ac07646d8` (po finálnej kontrole sa aktualizuje, ak sa zmení checker). U5 checker prešiel nad 51/51 vetvami a opätovne skontroloval U4 zdroj.

| Dávka | Základ každého profilu: vzdialene / späť RSU | Služba nedostupná | Globalstar MT nedostupné | Iridium vysoká citlivosť | Starlink vysoká citlivosť |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 1/1 | 0/0 | 1/0 | 1/1 | 1/1 |
| 4 | 4/4 | 0/0 | 4/0 | 4/3 | 4/3 |
| 35 | 35/35 | 0/0 | 35/0 | 31/29 | 31/25 |

Pri 35 správach `iridium/sensitivity_high` zaznamenal 1 odmietnutie pre plnú UL frontu, 3 modelové UL straty a 2 DL straty. `globalstar/sensitivity_high` vytvoril 40 miestnych MO pokusov vrátane piatich opakovaní po modelovej strate; 35 správ prišlo vzdialene a 32 potvrdení sa vrátilo na RSU. Toto sú výsledky **zadaných deterministických predpokladov**, nie odhad PDR či porovnanie skutočnej kvality operátorov. `n1`, `n4` a `all` sú závislé vzorky bez empirického intervalu.

Negatívna brána: šesť sémantických zmien raw stopy (rodič CAM, IP bajty, MO bajty, čas, MT smerový stav a archivovaný natívny pôvod) a štyri neplatné konfigurácie musia byť odmietnuté aj po prepočítaní hashov. Historické V6 výsledky sa nemenia. Kalibrácia a nezávislá validácia zostávajú `null`; ich výskumný protokol a spoločná analýza pokračujú v U6.
