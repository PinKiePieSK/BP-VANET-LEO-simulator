# V6 — kontrakt troch servisných architektúr

Stav: vykonateľná **servisná vrstva scenárov/citlivosti** nad šiestimi natívne vytvorenými ICB1 reportmi z ns-3.38/SNS-3 3.38. Nie je to implementácia operátorského RF/MAC, plánovača, provisioningu ani nameraná dostupnosť. Natívny pôvod aplikácie a samostatné vykonanie servisného replayu sú pri každom behu rozlíšené v manifeste.

## Vstup a hranica modelu

Vstup je presná bajtová RSU aplikácia `RSU_REPORT_CREATED` zo zmrazeného natívneho [P4 zdroja](../../results/p4_certus_native_20261026/positive/trace.csv). Všetkých 17 V6 vetiev má rovnakých šesť ID, 96-bajtový ICB1 report a časy RSU. Po tejto hranici pracuje samostatný deterministický Python adaptér. Cesta cez operátora **nie je** vykonaná v SNS-3; generický DVB fyzikálny model z V4 ostáva samostatnou referenciou.

Satelitné OMM/EOP trajektórie a viditeľnosť zostávajú len `GEOMETRY_CANDIDATE_DIAGNOSTIC`. Iridium má kandidáta terminál–objekt; Starlink priamu geometriu cez hypotetický stred Viedne; Globalstar spoločný objekt pre RSU a hypotetický stred Nemea. Tieto proxy body nie sú overené operátorské gateway. Model preto nevyvodzuje attach, handover, beam, routovanie, prevádzkový výpadok ani latenciu z geometrie. Dostupnosť služby je explicitný scenárový stav s pôvodom D. Audit kontroluje, že zmena príznaku geometrického kandidáta nemení servisné doručenie.

| Profil | Totožnosť modelu | Transport a topológia | Známe obmedzenie | Neznáma prevádzka |
| --- | --- | --- | --- | --- |
| Iridium | SkyLink 5100 / Certus 9770, plán Certus 100, pevná RSU v Bratislave, 22. 10. 2026 | IP/UDP; terminál → Iridium sieť → neznáma gateway/mesh cesta | publikované maximá UL 22 kb/s a DL 88 kb/s | reálny goodput, beam, gateway, fronta, výpadky; LTE fallback sa nevykazuje ako satelitné doručenie |
| Globalstar | RM200M, pevná RSU, hypotetická dvojstranná MO/MT služba | natívne MO/MT správy; spoločný satelit/gateway kandidát, **bez ISL**; žiadny IP datagram v správe | MO 9–144 B; MT 9–128 B | skutočná gateway, anténa/certifikácia, potvrdenie siete, MT delivery a retry pravidlá |
| Starlink | Performance Gen3, predpoklad Local Priority 50 GB, pevná RSU | IP/UDP; aktívny beam a gateway/optická trasa neznáme | publikovaný režim po vyčerpaní priority: 0,5 Mb/s UL a 1 Mb/s DL, podmienený konkrétnym plánom/regiónom | skutočná rýchlosť, priorita na účte, plánovač, prekážky a trasa |

Oficiálne produktové zdroje: [Iridium 9770](https://www.iridium.com/products/iridium-certus-9770/), [SkyLink 5100](https://www.iridium.com/products/skylink-5100-iot), [Globalstar RM200M](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet1.pdf), [Starlink Performance](https://starlink.com/pg/specifications/7), [Starlink po vyčerpaní priority](https://starlink.com/mk/support/article/ce6af7c3-6bc5-1349-ef29-ed7451d0f656). Prístup/overenie: 26. 10. 2026. Ponuky a podmienky sa menia; viazanie na skutočný účet, SKU, anténu a oprávnenú oblasť treba ešte doložiť. Hodnota B znamená publikovanú produktovú vlastnosť, nie nameraný výkon konkrétnej inštalácie.

## Rozhranie scenára

Jediný editovateľný V6 kontrakt je [`config/v6_service_contract.json`](../../config/v6_service_contract.json). Profil obsahuje operátora, SKU, modul, generáciu, anténu, plán, mobilitu, geografiu a dátum. Architektúra, známe limity, základné parametre aj override každej vetvy majú `{value,status,source,scope}`. A = reprodukovateľný lokálny vstup/výstup, B = publikovaná vlastnosť, C = kalibrovaný model, D = neoverený scenárový predpoklad. V6 nepoužíva C. Zdroj a rozsah sú vo výslednom manifeste skopírované spolu s hashmi vstupov.

`--validate-only` overuje typ transportu, chýbajúci pôvod, pevné RSU, povinné brány, Globalstar limity, prípustné IP kapacity a maximum Certus. `--config` a `--output` umožňujú vytvoriť nový nemenný variant. Skript odmietne existujúci výstupný priečinok.

Servisné stavy sú explicitné: pre Iridium satelit, výpadok a vylúčený LTE fallback; pre Globalstar MO/MT, výpadok, samostatný MT výpadok a nekvalifikovaná proxy gateway; pre Starlink priorita, vyčerpaná priorita, výpadok a prekážka. Každá služba má základ, úplný výpadok a dve citlivosti. 60 s deadline je výskumná hranica, nie SLA. IP/UDP má smerové serializačné fronty a kontrolné súčty. Globalstar má lokálne aplikačné retry a odlišné `MO_TERMINAL_ACCEPT`, `MODEL_NETWORK_ACCEPT`, `REMOTE_APP_RX`, `MT_NATIVE_TX` a `RSU_RECEIPT_RX`; žiadny z týchto názvov netvrdí pozorované potvrdenie operátora. GRA1 je naše voliteľné aplikačné potvrdenie.

## Zakázané závery a ďalšie dáta

Bez párovaných nezávislých meraní neexistuje empirická kalibrácia PDR, oneskorenia ani dostupnosti a neporovnávame operátorov ako reálne služby. Numerické poradie v konkrétnej citlivosti je vlastnosť zvolených predpokladov. Potrebné sú konkrétne nasadené SKU/firmvér, certifikovaná anténa a montáž, aktivovaný plán a zostatok dát, operátorské merania na rovnakých miestach a časoch s identickými aplikačnými payloadmi a dôvodmi strát. Pre Globalstar navyše skutočná gateway/účet a oddelený MO acceptance/MT delivery záznam; pre Iridium režim satelit-only oproti LTE; pre Starlink prekážky, stav priority a región. Tieto dáta patria do budúcej V7 kalibrácie a nezávislej validácie, nie do skrytej úpravy V6 predpokladov.
