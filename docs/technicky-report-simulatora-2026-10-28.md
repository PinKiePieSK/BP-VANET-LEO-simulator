# Technický report simulátora VANET a LEO

**Stav k 28. 10. 2026.** Tento report opisuje aktuálnu používateľskú cestu U9, najmä režim `combined_advanced`, a oddeľuje ju od starších samostatných experimentov U0–U8. Je to inventár schopností a hraníc implementácie, nie návrh finálnych scenárov ani tvrdenie o výkone komerčných sietí. Opiera sa o [zadanie BP](zadanie-bp.md), [U9 CLI](../tools/bp_u9.py), [natívny engine](../src/u9-full-advanced.cc), [priamu vetvu auta](../src/u9-full-direct-advanced.h), [packetový audit](../tools/check_u9_advanced.py), [U9 experiment](experiments/u9-advanced-2026-10-28.md) a nový overený beh uvedený nižšie.

## 1. Stručný stav

Simulátor už vie v **jednom procese ns-3 a v jednom simulačnom čase** spojiť pohyb áut, pozemné CAM vysielanie V2V/V2I, satelitný backhaul jednotlivých RSU, priamy hypotetický satelitný terminál vo vybraných autách, odpovede do áut, odovzdanie upozornenia cez satelit inej RSU a prepnutie terminálov medzi modelovými satelitmi. Každá RSU má v `combined_advanced` vlastný satelitný UT a používateľský uzol; priamy UT majú iba autá v `direct_cars`. Vstupy a výsledky majú manifesty, raw stopy a opätovný checker.

Toto je **výskumný generický model**. Pozemné rádio je parametrický ITS-G5/802.11p model, satelit je SNS-3 s generickým DVB user/feeder rádiom a modelovými ISL. Doppler a smerovanie antény auta sú rozhodovacia podmienka pred odoslaním aplikácie. Žiadna z týchto vrstiev nie je kalibrovaný modem, plánovač, beam mapa ani dostupnosť Starlinku, Iridia alebo Globalstaru. Prenosné vydanie je overené pre Ubuntu 24.04 x86_64 a Python 3.12; postup je v [zázname vydania](experiments/u9-portable-2026-10-28.md).

Posledný **nový** skúšobný beh `portable-test-20261028144328` z 28. 10. 2026 skončil `PASS` aj po samostatnom `verify`: 24 áut, 31 RSU, 4 orbitálne objekty, 182 vytvorených reportov RSU, 158 prijatých na bráne a 158 odpovedí do áut; 24 áut prijalo upozornenie cez inú RSU, 33/33 sekundárnych terminálov potvrdilo prepnutie a 9/9 priamych CAM dostalo odpoveď. Sú to počty **jednej syntetickej konfigurácie a jedného seedu**, nie pravdepodobnosti reálnej služby. Dôkaz: `~/Desktop/BP-Simulator-Workspace/tests/latest-portable-test-verify.json` a `~/Desktop/BP-Simulator-Workspace/runtime/results/u9_runs/portable-test-20261028144328/`.

## 2. Z čoho vzniká premávka

| Krok | Zdroj a správanie | Čo sa dá ovplyvniť |
| --- | --- | --- |
| Cestná premávka | `world_template` definuje cestnú sieť, pevné RSU a geografický rámec; `demand` určuje autá, čas odjazdu, trasu a počiatočnú rýchlosť. SUMO vytvorí pohyb a FCD. Vzorový dopyt 24 áut je výslovne **syntetický**. | Upraviť kompatibilný world/demand JSON: počet áut a RSU, ich polohy, trasy, odjazdy, georeferenciu. Preflight kontroluje schému a následne úplné polohy všetkých áut v okne. Označenie `measured_trips` vyžaduje dohľadateľný URL zdroj, samotné označenie však nie je kalibrácia. |
| Vzorkovanie | U9 prenáša do ns-3 polohu, rýchlosť a smer každého auta zo SUMO po **100 ms**. Bežný scenár začína rádiové vzorky v čase **10 s**. | `sample_count` a seed; spoločný rozšírený režim aktuálne vyžaduje 20 vzoriek. Začiatok a krok nie sú vo verejnom U9 JSON voľné položky. |
| Vznik CAM | **Všetky** autá s ITS-G5 posudzujú vyslanie pri každej vzorke. Prvá CAM sa vyšle; ďalšiu spustí pohyb nad 4 m, zmena rýchlosti nad 0,5 m/s, zmena smeru nad 4° alebo periodické pravidlo, ak uplynul minimálny interval. CAM obsahuje skutočne vzorkovanú polohu, rýchlosť, smer, station ID a generationDeltaTime. Počet CAM teda nie je rovný počtu áut × počtu vzoriek. `source_id` iba určuje sledovaný referenčný zdroj; ostatné autá stále vysielajú. | Zmeniť mobilitu, počet áut, seed a pozemný rádiový režim. Kód má výskumné DCC podľa CBR, ale aktuálny U9 scenár ho nastavuje na `false`; DCC on/off je samostatný nižší V5 experiment, nie prepínač vo formulári U9. |
| Príjem CAM na RSU | Každá RSU je pozemný prijímač. Keď RSU skutočne dekóduje CAM od auta, prvá RSU, ktorá ju dekóduje, vytvorí report. Ďalšie prijatia tej istej CAM sa zaznamenajú ako duplicity. Výber teda závisí od udalostí rádia, nie od pevnej najbližšej RSU. | Rozmiestnenie RSU, rádio, vysielací výkon, šumové číslo a ponúkaná CAM záťaž. Politika „prvé skutočné dekódovanie“ je v aktuálnom engini pevná. |
| Satelitná aplikačná premávka | RSU vytvorí **nový** `ICB1` iba z prijatej CAM. Vzdialená aplikácia odpovie `GRA1`; RSU potom adresuje `I2V1` pôvodnému autu. Vybrané autá navyše môžu tú istú skutočnú CAM vložiť do priamej `CAM1` satelitnej obálky. | Výber `direct_cars`, satelitný strom, gateway, zisk/výkon, ISL rýchlosť a fronty, predpoklady mobilného linku. Priama vetva sa ponúka až od 11 s; samotný nevybraný automobil satelitnú prevádzku nevytvára. |
| Upozornenie do inej RSU | V `combined_advanced` brána pri prvom prijatom reportovanom deji z **inej** RSU vytvorí **jednu** správu `ALR1`, pošle ju cez satelit cieľovému RSU UT, cez miestnu IP/LAN do cieľovej RSU a tá ju odvysiela autám. Je to syntetický spúšťač, nie zistená dopravná zápcha. | Nastaviť `alert_target_rsu` a vstupnú prevádzku. Typ udalosti, detekčný algoritmus, priorita a všeobecné pravidlá distribúcie zatiaľ nie sú scenárovými parametrami. |

`flows` a `technologies` vo world JSON slúžia najmä na deklaráciu a validáciu. Samotný [world generátor](../tools/u9_editable_scenario.py) ich označuje `network_execution: schema_only` a `execution: not_implemented`; ľubovoľný pridaný tok vo world JSON sa **automaticky nestane** novou paketovou aplikáciou. Skutočné správy zapína U9 `mode` a engine. Obyčajný súbor CSV so súradnicami sa musí najprv previesť na validný world/demand JSON; `import.sh` ho iba uloží do pracovného priečinka.

## 3. Použité technológie, protokoly a obsah správ

| Vrstva / úsek | Čo naozaj používame | Hranica |
| --- | --- | --- |
| Mobilita a geometria | SUMO, FCD po 100 ms, WGS84/ENU, archivované orbitálne vstupy s propagáciou a kontrolou elevácie/ISL priechodnosti. | Geometrický kandidát nedokazuje aktívny beam ani dostupnosť služby. |
| Auto ↔ auto / auto → RSU | ns-3.38 Wi-Fi 802.11p **OCB**, kanál 5,9 GHz/10 MHz a modelová rýchlosť OFDM 6 Mb/s; Vanetza vytvára ASN.1 UPER **CAM**, GeoNetworking single-hop broadcast a **BTP-B** port CAM. | Implementovaná je skúmaná podmnožina ITS-G5; nie úplná ETSI zhoda, bezpečnostná PKI ani C-V2X. |
| Pozemný kanál | `friis` alebo `urban_los` v U9; nastaviteľný výkon 0–33 dBm a noise figure 0–20 dB. ns-3 zaznamenáva PHY stavy, CBR a dôvody zahodenia. | `urban_los` používa modelový trvalý LOS; automatické merané tienenie, NLOS a budovy nie sú vo verejnom U9 JSON. Staršie V5 sondy ich majú oddelene. |
| RSU LAN a vzdialená aplikácia | Modelová ns-3 point-to-point LAN RSU↔UT (v rozšírenom engine 100 Mb/s, 100 µs), IPv4/**UDP** medzi RSU, satelitným používateľským uzlom a bránou. `ICB1`, `GRA1`, `ALR1`, priama `CAM1` a jej `ACK2` sú aplikačné payloady vytvorené projektom. | Nejde o štandardné správy operátora ani nameranú lokálnu sieť. |
| Satelit | SNS-3 3.38, generické **DVB-S2/RCS2** user/feeder PHY/MAC, parametrický výkon/zisk a obojsmerné modelové point-to-point ISL hrany s kapacitou a frontou. Samostatný UT na každú RSU a vybrané auto v rozšírenom režime. | Nie sú to RF/MAC špecifikácie Starlinku, Iridia ani Globalstaru; ISL graf je scenárový feeder-rooted strom. |
| Návrat do auta / lokálne upozornenie | `I2V1` ide cielene cez OCB na pôvodné auto; `ALR1` ide z cieľovej RSU cez OCB broadcast. Sú to projektové EtherType rámce, **nie CAM cez GN/BTP**. | Nie je implementovaná všeobecná ETSI DENM aplikácia. |
| Staršie servisné profily | U5/U7 majú **samostatný** deterministický replay na hranici služby: model IP/UDP pre Iridium a Starlink, model MO/MT bez IP/ISL pre Globalstar. | Replay nie je v spoločnom U9 `combined_advanced` packet engine a nie je operátorskou PHY/MAC simuláciou; jeho endpoint je RSU. |

| Obsah | Kto ho vytvára a čo znamená |
| --- | --- |
| `CAM` | Vanetza/ASN.1 správa o stave auta; v aktuálnej vetve 41/43 B UPER podľa prítomnosti nízkofrekvenčnej časti. Pozemný GN/BTP rámec je väčší. |
| `ICB1` | Projektový report RSU, 96/98 B: identita a čas udalosti, hash a presné bajty prijatej CAM. Nevznikne bez RSU dekódovania CAM. |
| `GRA1` / `I2V1` | Projektová 46 B odpoveď brány s väzbou na report; následná 50 B správa RSU pre pôvodné auto. Nezamieňať potvrdenie RSU s prijatím v aute. |
| `CAM1` / `ACK2` | Priamy satelitný prenos vybraného auta: projektová obálka s indexom auta, station ID, generationDeltaTime a pôvodnými CAM bajtmi; brána vráti `ACK2` tomu istému autu. |
| `ALR1` | Projektové 49 B upozornenie s ID reportu, cieľovou RSU a hashom reportu. Nevzniká z detektora zápchy. |
| `P3PR/P3PA`, `HPR1/HPA1` | Modelové sondy a odpovede na potvrdenie sieťovej cesty po prepnutí satelitného terminálu. Potvrdená sonda nie je dôkaz doručenia každej aplikácie po prepnutí. |

## 4. Aké komunikačné vetvy a behy sa dajú spustiť

Všetky nasledujúce režimy sú v [U9 CLI](../tools/bp_u9.py) a používajú rovnaký príkaz `preflight → run → verify`, ale **nie všetky simulujú rovnaké vrstvy**.

| Režim U9 | Čo skutočne vykonáva | Čo v tomto režime chýba |
| --- | --- | --- |
| `v2v_only` | Viac áut vysiela/prijíma skutočné CAM cez OCB; 0 RSU, 0 satelitov. | RSU report, brána, satelit a infraštruktúrna odpoveď. |
| `local` | CAM → RSU → projektová lokálna aplikácia → odpoveď autu. | Pozemný WAN a satelitný úsek. |
| `ground` | CAM → RSU → modelový pozemný IPv4/UDP backhaul → brána → návrat. | Satelitný úsek. |
| `native_generic_dvb` | CAM → RSU → generická SNS-3 DVB/ISL cesta → brána → návrat; U4 parametrická kapacita a RF. | V tejto staršej U9 vetve RSU zdieľajú jeden satelitný terminál; priame auto UT, upozornenie do inej RSU. |
| `direct_car_satellite` | Oddelený test SUMO polôh a hypotetických automobilových UT; kladná vetva a kontrola bez ISL, projektové testovacie `CAR1` bajty. | Nie je to spoločný OCB/satelitný proces a payload nie je skutočná CAM. |
| `combined_direct_cam` | Spoločné hodiny OCB a priamych automobilových UT; priama obálka obsahuje skutočnú CAM, kladná vetva a kontrola bez ISL. | Satelitný backhaul RSU a upozornenie do inej RSU. |
| `combined_full` | V jednom behu CAM/V2V/V2I, vlastný UT každej RSU, RSU backhaul, priamy CAM satelit vybraných áut, odpovede; handover primárnej RSU. | Handover ostatných terminálov, ALR1 do inej RSU, Doppler/anténna brána. |
| **`combined_advanced`** | Všetky vyššie uvedené spoločné vetvy vrátane ALR1 do inej RSU, handoveru všetkých sekundárnych UT a aproximácie Dopplera/smerovania pre priamy automobilový link. | Detekcia skutočnej zápchy, ľubovoľná aplikačná politika, operátorský modem a kalibrácia. |

U5/U7 `service_boundary_replay` pre Starlink, Iridium a Globalstar je dostupný **osobitnou cestou pôvodného projektu**; nie je deviatym U9 režimom, v U9 webe ani v prenosnom `run.sh` menu. Nesmie sa kombinovať s U9 DVB výsledkom ako ďalší fyzický hop. Viac podrobností je v [U5 dôkaze](experiments/u5-service-bridge-2026-10-27.md).

## 5. Čo sa dá meniť a čo je zatiaľ pevné

| Vstup v U9 JSON | Súčasný význam / hranica |
| --- | --- |
| `world_template`, `demand` | World a dopyt pod `data/inputs/`; menia sieť ciest, polohy RSU, autá, trasy a hustotu. Je to najdôležitejší spôsob modulácie ponúkanej komunikačnej záťaže. Bežný import surového CSV ešte nie je priame prepojenie. |
| `mode`, `direct_cars`, `alert_target_rsu` | Zapínajú podloženú vetvu, vyberajú autá s UT a inú cieľovú RSU v `combined_advanced`. Každé auto nemá automaticky satelitný terminál. |
| `seed`, `ns3_run`, `utc_origin` | Náhodnosť a čas orbitálnej geometrie; konkrétne UTC môže byť odmietnuté dostupnosťou orbitálnych vstupov a geometrickým preflightom. Niektoré staršie režimy majú referenčné UTC pevné. |
| `radio.mode`, `tx_power_dbm`, `noise_figure_db` | U9 umožňuje `friis`/`urban_los`, výkon 0–33 dBm, noise figure 0–20 dB. DCC je v U9 zatiaľ pevne vypnuté. |
| `satellite.catalog_ids`, `isls`, `gateway`, `mask_deg`, serving/target/feeder | Scenárový orbitálny pool, obojsmerný ISL strom, hypotetická brána a výskumný cieľ handoveru; preflight odmieta nespojené alebo geometricky nemožné trasy. Štyri objekty vo vzore neznamenajú štyri aktívne aplikačné cesty. |
| `beam_gain_dbi`, `ut_power_dbw`, `forward/reverse_isl_bps`, `forward/reverse_queue_packets` | Citlivosť generickej RF a kapacít/front; nie zmerané čísla operátora. |
| `link_policy` | V `combined_advanced`: `rf_hz`, podiel Dopplerovej kompenzácie, tolerancia zvyšku, uhol od zenitu, rýchlosť natáčania a polovičná šírka lúča. `direct_link.csv` ukazuje rozhodnutie pre každý priamy kandidát. Toto blokuje ponuku **pred** SNS-3, nemení vnútorné DVB PHY. |

**Aktuálne tvrdé a praktické hranice:** minimálne 2 autá; pre všetky režimy okrem `v2v_only` aspoň 1 RSU; pre spoločné natívne režimy najviac 512 RSU a v rozšírenom režime najviac 1533 vybraných priamych automobilových UT z dôvodu adresovania. `combined_advanced` vyžaduje 20 vzoriek, minimálne 2 satelity, explicitný cieľ handoveru a feeder-rooted strom. Preflight má geometrické okno 10–13 s; následný checker kontroluje aj plné vykonané okno. Počet uzlov je konfigurovateľný **v rámci týchto hraníc a výkonu stroja**, nie neobmedzený ani overený pre každú kombináciu. Jedna hypotetická brána a pevné aplikačné spúšťače sú súčasťou aktuálneho modelu.

## 6. Čo meriame a v akých stopách to vidno

| Pozorovanie | Raw dôkaz / interpretácia |
| --- | --- |
| SUMO pohyb a priebeh cestnej premávky | `ground/scenario/sumo/fcd.xml`, `summary.xml`, waypointy; počty realizovaných áut, rýchlosť, kolízie a teleporty v simulácii. Správa spätne nemení trasu ani správanie vodiča. |
| Vznik a doručenie CAM | `cam.csv`, `dcc_decisions.csv`, `rx.csv`, `ocb_decoded.csv`, `ocb-*.pcap`; počty vyslaných/prijatých CAM, príjemcovia, miestna PDR, čas a bajty. PDR má menovateľ **ponúknuté dvojice vysielač–prijímač**, nie počet všetkých áut. |
| Záťaž a rádiové straty | `phy_state.csv`, `phy_drop.csv`, `queue.csv`; CBR, PHY dôvody a modelové zahodenie vo fronte. `dcc_decisions.csv` je stopa rozhodnutí aj keď je DCC vypnuté. |
| Výber RSU a aplikačný reťazec | `selection.csv`, `identity.csv`, `events.csv`, `trace.csv`, `delivery.csv`; presné ID a bajty CAM → ICB1 → GRA1 → I2V1, výber prvej dekódujúcej RSU, duplicity, časové poradie, prijatie na bráne a správne cieľové auto. Rozlišujeme vytvorený report, prijatie na bráne a návrat do auta. |
| Satelitné udalosti | SNS-3 `PacketTrace.log`, LAN/OCB PCAP, `run.log`, Rx power stopy, ISL a frontové stopy; paketové hop-y, IP/UDP bajty, prijatie či blokovanie. Samotná elevácia nie je dôkaz doručenia. |
| Priamy link a handover | `direct_movement.csv`, `direct_link.csv`, terminálové udalosti v `run.log`; poloha, radiálna rýchlosť, Doppler, smer antény, dôvod blokovania, sonda/odpoveď, potvrdenie alebo rollback. |
| ALR1 do inej RSU | `trace.csv`, ISL záznam a OCB PCAP cieľovej RSU/áut; checker porovná rovnaké bajty, cieľovú IP, report pôvodu a poradie všetkých úsekov. |
| Reprodukovateľnosť | `run-manifest.json` na viacerých úrovniach obsahuje scenár, vstupy, hashe zdrojov a raw súborov; `verify` z raw stôp znovu spočíta výsledok. Zmena zdroja či vstupu môže zneplatniť starý manifest. |

U9 web na `/u9-simulator.html` vie načítať preset/uložený JSON, vykonať preflight, spustiť beh a ukázať súhrn; server povoľuje súčasne iba jeden aktívny U7/U9 beh. **Nie je** to grafický editor všeobecnej cestnej siete ani detailný prehrávač každej raw udalosti. Časové značky v raw stopách umožňujú vypočítať latenciu konkrétneho úseku, ale U9 súhrn sám ešte nepublikuje všeobecné p95/p99, intervaly spoľahlivosti ani prevádzkovú dostupnosť. Starší U6/U7 analyzátor má vlastný vedecký výsledkový kontrakt pre svoje režimy; jeho hodnoty sa nepripisujú automaticky novému U9 behu.

## 7. Experimenty, ktoré dnes vieme a nevieme urobiť

**Priamo cez U9 scenár:** porovnať čisté V2V, lokálnu/pozemnú/generickú satelitnú cestu, počty a rozmiestnenie áut/RSU v podporenej škále, výber áut s priamym UT, cieľovú RSU upozornenia, satelitný strom a handover cieľ, výkon/zisk a kapacitu ISL, veľkosť fronty, pozemný výkon/šum, seed a prípustnú UTC. `combined_advanced` umožňuje citlivosť Dopplera a smerovania antény. Sú to paketové behy s raw kontrolou, nie len odhadnuté percentá.

**Samostatné kontrolné experimenty, ktoré existujú v zdrojoch:** 100 % strata prijatia na ISL pri spoločnom behu, prísna Dopplerova alebo anténna brána, V5 DCC on/off, staršie NLOS/budova/tienenie sondy, U5 profilové prípady služby dostupná/nedostupná a citlivosti. Negatívny `no-ISL` pre `combined_advanced` používa osobitný zdroj a checker; **nie je** to univerzálny parameter každého uloženého U9 scenára. Samostatné výsledky sa musia párovať podľa rovnakých vstupov a endpointov.

**Zatiaľ nie ako jeden všeobecný U9 experiment:** automatický vznik zápchy a DENM z dopravnej udalosti; spätná zmena rýchlosti alebo trasy po prijatí upozornenia; ľubovoľný typ paketu, veľkosť, frekvencia a cieľ cez JSON; nepretržitá meraná internetová či operátorská záťaž; kombinácia U9 s verný Starlink/Iridium/Globalstar RF/MAC profilmi; komerčný beam/attach/routing; ľubovoľný mesh ISL graf; automatický prevod ľubovoľného OSM/CSV súboru na U9 scenár; všeobecné automatické hľadanie najlepšieho satelitu a garancia neobmedzenej škály. V U9 chýbajú aj spoločné používateľské ovládače pre DCC a NLOS, hoci nižšie modely existujú.

## 8. Praktické spustenie a interpretácia pre ďalšiu prácu

V prenosnom priečinku `~/Desktop/BP-Simulator`:

```bash
./setup.sh
./run.sh preflight config/u9-advanced-24cars-31rsu-4sat.json
./run.sh run config/u9-advanced-24cars-31rsu-4sat.json moj-novy-beh
./run.sh verify moj-novy-beh
./run.sh server 8765
```

`setup.sh` pripraví lokálny runtime; behy a nové vstupy sa ukladajú do `~/Desktop/BP-Simulator-Workspace/`, nie do čistého balíka. V U9 webe možno JSON scenár upraviť, overiť a uložiť. Pri zmene dopytu/mapy treba vytvoriť validný world/demand pod `runtime/data/inputs/`, zmeniť cesty v scenári a vykonať preflight. Výsledok má dostať nové ID; runner existujúci priečinok neprepisuje.

**Záver pre konzultáciu s vedúcim:** máme technicky funkčný a opätovne kontrolovateľný výskumný základ na výber finálnych scenárov. Pred vedeckými tvrdeniami treba určiť primárnu udalosť/aplikáciu, cieľový endpoint a deadline, párované scenáre a opakované seedy/epochy, spôsob tvorby realistického dopytu a ktoré výsledky budú iba citlivosťou modelu. Ak má práca hodnotiť dopravný účinok upozornenia, bude nutné pridať skutočný detektor udalosti a spätnú väzbu do mobility. Ak má tvrdiť parametre konkrétneho operátora, potrebujeme nezávislé merania a kalibráciu; súčasný generický DVB a servisný replay na to nestačia.
