# P2: DVB chyby, fronta, deadline a interval CAM

**Stav 26. 10. 2026:** brána P2 splnená pre výskumný referenčný model ns-3.38/SNS-3 3.38. Nový spoločný pilot má **8/8** overených variantov; celá Python regresia má **61/61** testov. Výsledky sú v `results/p2_complete_20261026`, surový audit v `p2-complete-verification.json` a per-message menovateľ v `p2-complete-metrics.csv`. Predchádzajúci [párovaný mestský/OSM pilot](p2-urban-osm-paired-2026-10-25.md) a [LAN/ISL prijímacie chyby](p2-controlled-hop-loss-2026-10-25.md) zostávajú samostatnými nezmenenými dôkazmi P2.

## Kontrakt a spoločný vstup

Všetky varianty používajú tú istú OSM/SUMO trasu Bratislavy, hypotetické RSU a kolokovaný UT, UTC 22. 10. 2026 12:46:32, `seed=314159`, `run=1`, LOS, súbežné CAM ďalších dvoch áut a ten istý generický DVB/ISL/GW model ako P1. Primárna informácia je 96 B ICB1 vytvorená iba z CAM prijatého RSU. Cieľ kontrolovaných zásahov je tretí primárny `event_id=ca0000000000c5d0`. Všetky priestorové kandidáty vyšli geometricky kladne; stav registrácie/attach terminálu nemá callback a zostáva `not_observed`.

Menovateľ vzdialeného výsledku je počet **unikátnych ICB1 vytvorených RSU**, nie počet MAC vyslaní, `PacketTrace` ENQ/DRP ani počet pozemných príjemcov. Primárny úspech je prijatie presného ID a SHA-256 ICB1 vo vzdialenej aplikácii do **60 s od `RSU_REPORT_CREATED`**, podľa [P0 kontraktu](../../config/bp_experiment_contract_v1.json). Latenciu úspešných správ a neskoré prijatie vykazujeme oddelene.

| Variant | CAM/ICB1 | GW prijaté | Pred 60 s | Odpoveď do auta | Kontrolovaný jav |
| --- | ---: | ---: | ---: | ---: | --- |
| `baseline` | 6 | 6 | 6 | 6 | Bez zásahu. |
| `user_phy` | 6 | 0 | 0 | 0 | `SatGeoHelper` return-user `EM_CONSTANT=1`; natívne `SAT0 PHY RTN DRP`, žiadny ISL report. |
| `feeder_phy` | 6 | 0 | 0 | 0 | `SatGwHelper` return-feeder `EM_CONSTANT=1`; šesť presných ISL reportov, potom natívne `GW PHY RTN DRP`. |
| `isl_queue` | 6 | 5 | 5 | 5 | Jeden presný ICB1 odmietnutý skutočnou `DropTailQueue<Packet>` na SAT0 ISL cez `DropBeforeEnqueue`. |
| `late_app` | 6 | 6 | 5 | 5 | Cieľový paket transportne prišiel do GW, aplikácia ho podržala 60,5 s; prijatie nastalo 60,619894 s po vzniku ICB1, bez spätnej odpovede pre tento neskorý výsledok. |
| `dcc_s0` | 3 | 0 | 0 | 0 | UT satelitné odoslanie blokované; miestne CAM/V2V/V2I zostali aktívne. |
| `dcc_s1` | 3 | 3 | 3 | 3 | Kladná dvojdružicová vetva. |
| `dcc_s2` | 3 | 0 | 0 | 0 | Bez modelovej ISL; miestne CAM/V2V/V2I zostali aktívne. |

S0/S1/S2 majú rovnaké zdrojové bajty troch vyslaných primárnych CAM, rovnakých šesť vstupných pohybových vzoriek a **9/9 miestnych prijatí** v každej vetve (dve autá a RSU × tri CAM). Vzorové body pochádzajú z OSM siete, ale dopravný dopyt, RSU, budova/kanál a proxy GW nie sú kalibrované meraním. Výsledky nie sú prevádzková PDR Starlinku, Iridia ani Globalstaru.

## Dôkaz miesta straty a opakovaní

Nový `src/editable-v2-ocb-p2-complete.cc` používa priamo konfiguráciu SNS-3 prijímača. Pri `user_phy` sa model vráteného user spoja nastaví na konštantnú chybovosť 1; pri `feeder_phy` sa rovnako nastaví prijímač GW. Ide o **zásah pre celý daný spoj počas behu**, vrátane možných riadiacich rámcov, nie o izolované RF zlyhanie jednej komerčnej správy. Checker preto vyžaduje pre každé ponúknuté ID príslušné vyslanie z UT PHY, natívne `PHY RTN DRP` na danom prijímači a neprítomnosť ďalšej aplikačnej fázy. Pri cieľovom user ID bolo **6 vyslaní UT PHY a 6 prijímacích dropov SAT0 PHY**: päť ďalších PHY vyslaní rovnakého `PacketTrace` ID sa vykazuje ako pozorované modelové opakovanie, nie ako päť unikátnych správ. Na feeder cieli bolo jedno UT PHY vyslanie a jeden GW PHY drop.

Frontová skúška nastaví kapacitu skutočnej SAT0 ISL fronty na jeden paket. V čase 21,050 s vloží do nej **16 B syntetickú skúšobnú obsadzujúcu položku**, ktorú v čase 21,200 s odstráni; položka nie je používateľský dátový tok ani vyslaný paket. Cieľový ICB1 pri pokuse o vloženie vyvolá natívny `DropBeforeEnqueue` s celými raw PPP/IPv4/UDP/ICB1 bajtmi; checker ich znovu dekóduje vrátane kontrolných súčtov a porovná s RSU reportom. Skúška tak dokazuje správne meranie **frontového dropu v skutočnom modeli**, nie realistickú distribúciu preťaženia. Pre chýbajúce ID bez pozorovaného callbacku sa nesmie priradiť táto príčina.

`late_app` oddeľuje transportný príchod `GATEWAY_REPORT_RX` od aplikačného `GATEWAY_ACCEPT`. Skúšobná aplikačná fronta zadrží presné raw ICB1 o 60,5 s. Toto je kontrola kontraktu deadline, nie tvrdenie o 60 s satelitnom oneskorení. V metrikách je neskoré prijatie samostatný `late_acceptance_latency_s`; `remote_latency_s` pre úspechy pred 60 s zostáva pri tejto správe prázdne.

Checker uvádza pre každý report `loss_reason`, poslednú potvrdenú fázu, geometrického kandidáta, `attachment_control_state`, aplikačné doručenie, včasnosť, návrat do auta, počet vyslaní UT PHY a počet ďalších vyslaní toho istého interného ID. Toto je presne pozorovateľná podmnožina opakovaní; iné MAC/servisné retransmisie bez jednoznačného callbacku sa neodhadujú. Neidentifikovaná príčina musí zostať `unknown`; v tejto kontrolovanej sade nie je žiadna takáto strata. Starší mestský audit dokladá `WIFI_PHY_RX_DROP_REASON_9` pri nedoručení do RSU; starší hop audit pokrýva LAN a modelovú ISL v oboch smeroch. Spolu dôkazy rozlišujú rádio/RSU, LAN, DVB user, modelovú ISL, DVB feeder, frontu a deadline.

## Vybraný CAM/DCC profil a hranica normy

Časové prahy vychádzajú z [ETSI EN 302 637-2 V1.4.1, §6.1.3](https://www.etsi.org/deliver/etsi_en/302600_302699/30263702/01.04.01_60/en_30263702v010401p.pdf): interval 100–1000 ms, zmena smeru **>4°**, polohy **>4 m**, rýchlosti **>0,5 m/s** alebo horný interval 1000 ms; `T_GenCam_Dcc` je minimálny interval poskytnutý management entitou. Aktuálny pilot ponúka `sampled_cam_dynamics` a parameter `dcc_interval_ms=1000`; podľa šiestich vzoriek po 500 ms vyšle CAM v časoch 20,0/21,0/22,0 s a zaznamená tri `CAM_DCC_INTERVAL_HOLD`. Pri 100 ms minimálnom intervale a tejto trase sa zachová šesť ponúk. Prístupový DCC rámec opisuje [ETSI TS 102 724 V1.1.1](https://www.etsi.org/deliver/etsi_ts/102700_102799/102724/01.01.01_60/ts_102724v010101p.pdf).

**Nejde o certifikovanú implementáciu ETSI CAM/DCC.** SUMO vzorky sú po 500 ms, zatiaľ čo §6.1.3 požaduje kontrolu najviac po 100 ms; `T_GenCam_Dcc=1000 ms` je explicitný citlivostný vstup, nie výsledok merania zaťaženia kanála alebo implementovaný prístupový DCC stavový automat. Povinný prvý low-frequency container a ďalšie pravidlá CAM služby nie sú týmto časovým pilotom overené. Pri tvrdení o normovej zhode alebo bezpečnostnom DENM by bola potrebná osobitná implementácia a konformitný audit. Súčasná výskumná úloha má v P0 `safety_claim=false`, preto DENM nie je zvolený payload.

## Reprodukcia a limity

```bash
cd '/home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca'
.venv/bin/python tools/check_p2_complete.py results/p2_complete_20261026
.venv/bin/python -m unittest discover -s tools -p 'test_*.py'
```

Nový beh vyžaduje **nový prázdny** výstupný adresár:

```bash
.venv/bin/python tools/run_p2_complete.py vendor/ns-3.38-ocb-eval results/MOJE_NOVE_P2_ID
```

`run-manifest.json` viaže hash C++ zdroja, runnera, OSM/SUMO vstupov, orbitálnych/modelových súborov a každého raw výstupu. Checker kontroluje presné CAM→ICB1→GRA1/I2V1 bajty, PCAP, ISL IPv4/UDP checksumy, interné paketové ID, frontový callback a časové poradie. Tri negatívne testy zmenia raw frontový paket, odstránia PHY drop alebo posunú neskoré prijatie pred deadline **a aktualizujú manifest hash**; sémantický audit ich odmietne. Pilot má jeden seed, jednu krátku orbitálnu epochu a hypotetickú bránu. Štatistické intervaly, kalibrácia dopravy/radia a operátorské služby patria do P4/P5, skutočný single-UT handover do P3.
