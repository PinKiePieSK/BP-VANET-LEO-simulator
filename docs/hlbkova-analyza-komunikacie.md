# Analýza komunikácie vo VANET a LEO pre bakalársku prácu

> Toto je cieľová analýza napísaná 22. 10. 2026. Jej vtedajšie hodnotenie implementácie a úvahy o ns-3.48 sú historické. Stav po P0–P5, vykonané experimenty a otvorené limity uvádzajú [aktuálny stav](stav-a-dalsi-postup.md), [plán](pracovny-plan-simulatora.md) a [rukopis](../thesis/rozpracovana-praca.md).

**Stav:** 22. 10. 2026. **Úloha dokumentu:** technický cieľ pre čo najvernejšiu dosiahnuteľnú simuláciu inteligentnej cestnej dopravy so satelitným úsekom. Súčasný pilot je iba dôkaz funkčnej integrácie; jeho obmedzenia neurčujú cieľovú kvalitu práce. Pri ďalšej práci treba meniť tvrdenia spolu s verziou štandardu, zdrojom parametra a zodpovedajúcim experimentom.

## Hlavné rozhodnutie o cieľovej simulácii

Výsledkom má byť **reprodukovateľný, geograficky a časovo konzistentný paketový experiment**, ktorý spája mikroskopickú premávku, štandardné lokálne V2X správy, skutočnú geometriu LEO konštelácie, konkrétne terminály a služby, realistické obmedzenia rádia, prechody medzi satelitmi/beamami, brány, fronty a vzdialenú aplikáciu. Parametre sa majú kalibrovať voči normám, výrobcom a podľa možnosti nezávislým meraniam; validácia má použiť iné dáta než kalibrácia. Nástroj sa vyberá podľa toho, či túto cestu dokáže spojiť bez zmeny významu paketov, nie podľa názvu „Starlink“ v príklade.

Najvyššia dosiahnuteľná vernosť neznamená vymyslieť nepublikovaný proprietárny rámec. Tam, kde výrobca interný scheduler, beam/routing alebo MAC nepublikuje, má mať model **zdrojovanú vonkajšiu fyziku a topológiu** a **empiricky kalibrované správanie služby** s intervalom neistoty. Podrobnejší, ale nesprávny DVB model by nebol realistickejšou replikou Starlinku, Iridia ani Globalstaru. Presný cieľ po vrstvách a podmienky prijatia sú v oddiele „Cieľová vernosť po vrstvách“.

## 1. Presné zadanie a hranice práce

Oficiálne zadanie vyžaduje: (1) analyzovať princípy VANET, inteligentnej dopravy a spôsoby komunikácie, (2) analyzovať konštelácie LEO a stručne relevantné simulačné nástroje, (3) navrhnúť infraštruktúru VANET s integrovanou satelitnou komunikáciou, (4) pripraviť scenáre výkonnostného testovania, (5) infraštruktúru a scenáre implementovať a (6) vykonať experimenty a zhodnotiť výsledky. Motiváciou je spojenie vozidiel medzi sebou, s infraštruktúrou a internetom, vrátane ciest cez Iridium, Globalstar alebo Starlink. [Presné znenie zadania a usmernenie vedúceho](zadanie-bp.md) sú uložené samostatne, aby sa rozsah práce dal kedykoľvek skontrolovať.

### Výber satelitného rozšírenia ns-3

Vedúci odporučil porovnať `ns-3-leo`, SNS-3, Hypatiu a `anysam/starlink_ns3` podľa podporovaných orbít, verzie ns-3, príkladov a dokumentácie. Podrobné miestne overenie je v [analýze satelitných modelov](vyber-satelitneho-modelu.md).

| Nástroj | Model a príklady | Kompatibilita overená v projekte | Rozhodnutie |
| --- | --- | --- | --- |
| [SNS-3](https://github.com/sns3/sns3-satellite) | GEO/LEO príklady, SGP4, DVB user/feeder PHY/MAC, UT/GW, ISL, viac režimov regenerácie; zdokumentované príklady a testy. | Spoločná sada tagov `ns-3.48`/`3.48` sa zostavila a jej LEO príklad preniesol pakety. | Základ paketovej integrácie a referenčný DVB satelitný profil. |
| [Hypatia](https://github.com/snkas/hypatia) | Predpočítava dynamickú LEO topológiu a routing; packet-level ns-3 experimenty. | Miestny checkout používal ns-3.31; port na novšiu verziu nebol prevzatý ako overený základ. | Referencia pre orbity a smerovanie; nie zdroj presného rádiového protokolu operátora. |
| [ns-3-leo](https://gitlab.ibr.cs.tu-bs.de/tschuber/ns-3-leo) | LEO linky a príklady; rádiový kanál používa zjednodušený prah/error model podľa [autorského článku](https://d-nb.info/1253136572/34). | Autorský článok opisuje ns-3.30; miestne zostavenie nebolo overené. | Alternatíva na topologické scenáre, slabší dôkaz kompatibility s dnešným projektom. |
| [Anysam Starlink ns-3](https://github.com/anysam/starlink_ns3) | Paketové príklady so satelitnými linkami modelovanými generickými ns-3 linkami. | Repo obsahuje ns-3.30.1; lokálne sa nepreukázal operátorský PHY/MAC. | Názov Starlink nie je dôkazom zhody so Starlink rámcami. |

SNS-3 3.48 je dnes zostavený **referenčný DVB satelitný model** a predbežná integračná základňa. Finálny nástroj a skladba modelov sa majú potvrdiť rozhodovacou skúškou v oddiele 7.1 podľa toho, ktorá cesta dosiahne vyššiu overiteľnú vernosť celej trasy. [SNS-3](https://github.com/sns3/sns3-satellite) uvádza LEO/GEO príklady, ISL, SGP4 a režimy regenerácie; [Hypatia](https://github.com/snkas/hypatia) je vhodná najmä na časovo premenlivú topológiu a smerovanie. Zdroje nepreukazujú podporu MEO v konkrétnom otestovanom scenári, preto ju tabuľka netvrdí.

**Hlavná výskumná otázka:** Ako sa zmení doručenie, oneskorenie, premenlivosť oneskorenia a dostupnosť aplikácií VANET, keď sa medzi cestnú sieť a vzdialenú aplikáciu vloží realisticky definovaný LEO segment? Odpoveď sa musí rozložiť po jednotlivých úsekoch. Priama kolízna výstraha medzi susednými autami a vzdialený dátový tok cez satelit sú rozdielne služby s rozdielnymi požiadavkami. Tvrdenie, že LEO má oneskorenie „porovnateľné s pozemnou sieťou“, treba v práci merať pre konkrétnu trasu a percentil; samotná výška orbity takú ekvivalenciu nedokazuje.

**Pravidlo vierohodnosti:** Použitie názvu Starlink, Iridium či Globalstar v scenári dovoľuje porovnať zdrojovanú geometriu, topológiu, verejné pásma a typ služby. Nepotvrdzuje interné rámce, plánovač, beamforming, handover ani routovanie operátora. Neznáme parametre sa zapisujú ako predpoklady a skúmajú citlivosťou. Štandard 3GPP NTN alebo DVB je samostatný profil; nemožno ho bez dôkazu zameniť za proprietárnu sieť.

## 2. Mapa uzlov, médií a smerov

```text
auto A ── lokálne V2V ── auto B
  │
  ├── V2I/I2V ── RSU ── pozemná LAN ── pevný satelitný terminál
  │                                            │ používateľský RF spoj
  └── palubný satelitný terminál ──────────────┤
                                               LEO 1 ── voliteľná ISL ── LEO 2
                                                │                            │
                                         feeder RF spoj ─────────── feeder RF spoj
                                                │                            │
                                             gateway ── IP/core sieť ── server/ďalšia RSU
```

| Komunikácia | Koncové body a obvyklý účel | Cesta, ktorú treba modelovať | Kľúčová poznámka |
| --- | --- | --- | --- |
| V2V | Obe vozidlá; vzájomná poloha, pohyb, nebezpečenstvo | Priamy lokálny ITS-G5/802.11p alebo LTE/NR PC5 | Nepotrebuje RSU ani internet. Lokálne jednoskokové výstrahy nemajú závisieť od satelitného backhaulu. |
| V2I/I2V | Auto ↔ RSU; výstraha, stav križovatky, navigačné informácie | Lokálne rádio; podľa služby broadcast/geocast alebo individuálna komunikácia | RSU je ITS stanica, nie automaticky satelitný modem. |
| V2N | Auto ↔ internetová služba | 4G/5G Uu cez základňovú stanicu, prípadne auto → RSU → backhaul | Je to širšia kategória než V2I; zahŕňa core a server. |
| RSU → satelit | RSU potrebuje LAN a samostatný terminál UT | RSU → LAN → UT → service/user link → LEO → feeder/ISL → GW → server | Satelit nahrádza alebo dopĺňa backhaul, nie lokálny bezpečnostný kanál. |
| Auto → satelit | Špeciálne vybavené auto s terminálom a použiteľnou anténou | Auto/UT → service link → LEO → GW → sieť | Vozidlové 802.11p rádio samo satelit nekontaktuje; potrebné sú výkon, anténa, výhľad a služba. |
| Satelit ↔ satelit | Prenos medzi LEO uzlami | Optický alebo RF ISL, ak ho konštelácia má | Smerovanie a dostupnosť ISL sa menia s geometriou a politickou/topologickou konfiguráciou. |
| Server → iné auto | Distribúcia informácie medzi vzdialenými oblasťami | Uplink z prvého regiónu, sieťové spracovanie, downlink do druhého, lokálne I2V | Treba zaznamenať oba smery a každú bránu; nejde o jediný „satelitný skok“. |

RSU môže výstrahu **lokálne znova vyslať**, agregovať informácie alebo vystupovať ako **IP router**. Tieto varianty majú odlišné pakety a časy: pri aplikačnom proxy vznikne nový UDP/IP datagram, pri routeri zostáva pôvodný IP datagram (mení sa napr. TTL a linková hlavička). V návrhu musí byť pri každom uzle uvedené, ktorú rolu plní.

## 3. Protokolový zásobník na cestnej strane

### 3.1 Európska cesta ITS-G5

Referenčná európska cesta pre lokálne kooperatívne správy je `CAM/DENM/CPM alebo infraštruktúrna správa → bezpečnostný obal (ak je zapnutý) → BTP → GeoNetworking → ITS-G5/802.11 OCB → rádiový kanál`. BTP je ľahký nespoľahlivý transport s 4-bajtovou hlavičkou; číslo portu označuje službu. GeoNetworking realizuje geografické adresovanie a šírenie, napr. single-hop broadcast, topologically scoped broadcast, geobroadcast alebo geounicast. V bežnej ceste CAM cez BTP/GeoNetworking **nie je povinne IP ani UDP**. ETSI výslovne povoľuje viac profilov prístupu vrátane ITS-G5, LTE/NR V2X a IP profilu; konkrétny profil treba zvoliť a pomenovať. [ETSI BTP](https://www.etsi.org/deliver/etsi_en/302600_302699/3026360501/01.02.01_60/en_3026360501v010201p.pdf), [GeoNetworking](https://www.etsi.org/deliver/etsi_en/302600_302699/3026360401/01.03.01_60/en_3026360401v010301p.pdf), [infraštruktúrne profily ETSI TS 103 301 V2.2.2](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf).

ITS-G5/802.11p určuje rádiovú časť v 5 GHz ITS pásme: OFDM PHY, kanál/prenosovú rýchlosť, prístup k médiu, súťaž o kanál, retransmisie unicastu podľa konfigurácie a rádiové rámce. `AdhocWifiMac` v tomto projekte s profilom `WIFI_STANDARD_80211p` simuluje iba zjednodušený Wi-Fi MAC/PHY. **Nie je to plný OCB, GeoNetworking, BTP, DCC ani podpísaná ETSI CAM.** Historický modul ns-3 WAVE mal `OcbWifiMac` a `Wifi80211pHelper`, ale miestny ns-3.48 ich nepoužíva. [ETSI EN 302 663](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf), [dokumentácia ns-3 WAVE](https://www.nsnam.org/docs/release/3.35/models/html/wave.html), [miestny model](model.md).

### 3.2 Alternatíva C-V2X

LTE-V2X a NR-V2X používajú pri priamom V2V/V2I rozhranie **PC5 sidelink**. Pri prístupe do mobilnej siete sa používa **Uu** cez eNodeB/gNodeB a jadro; PC5 a Uu nie sú totožné cesty. Pri NR sidelinku má pridelenie zdrojov režim 1 (plánovanie sieťou) a režim 2 (výber UE z dostupného poolu); podporované sú broadcast, groupcast a unicast podľa profilu a verzie. Aplikačná správa CAM/DENM môže zostať rovnakou sémantickou službou nad inou prístupovou technológiou, no rádiové rámce, plánovanie a kolízie sa zmenia. Súčasný projekt PC5 ani Uu neimplementuje; ak sa majú porovnávať s ITS-G5, treba samostatný validovaný modul, spektrum, konfiguráciu a kontrolný experiment. [3GPP TS 38.300 Rel-19](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/19.02.00_60/ts_138300v190200p.pdf), [3GPP TS 23.287](https://www.etsi.org/deliver/etsi_ts/123200_123299/123287/17.06.00_60/ts_123287v170600p.pdf), [ETSI TS 103 301](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf).

### 3.3 Americký variant, ktorý sa nesmie miešať s ETSI dátovým modelom

SAE J2735 definuje napríklad **Basic Safety Message (BSM)**. Jej povinná časť I nesie identifikátor, čas, polohu, rýchlosť, smer, akcelerácie, brzdy a rozmery; časť II je voliteľná a môže niesť ďalší stav vozidla alebo históriu trajektórie. Je to iná aplikačná schéma než CAM. Americká cesta DSRC/WAVE používa sieťové služby IEEE 1609.3 vrátane WSMP pre krátke správy a môže podporovať aj IP; identifikácia služby cez PSID nie je BTP port. Ak by sa skúmal americký profil, treba pripnúť konkrétnu verziu J2735 a prístup DSRC/WAVE alebo C-V2X; BSM sa nesmie označiť za CAM len preto, že obe opisujú stav auta. [SAE J2735](https://saemobilus.sae.org/standards/j2735_202409-v2x-communications-message-set-dictionary), [IEEE 1609.3](https://standards.ieee.org/ieee/1609.3/10360/), [US DOT prehľad polí BSM](https://rosap.ntl.bts.gov/view/dot/27999/dot_27999_DS1.pdf).

## 4. Aké správy sa reálne používajú

V tabuľke sú uvedené **typy služieb**, nie tvrdenie, že ich všetky používa každé auto, každá RSU alebo táto simulácia. Pri jednej hlavnej experimentálnej vetve odporúčame európsky profil CAM + DENM + dve RSU správy; ďalšie správy možno zaradiť, ak sa skúma ich vlastný use case.

| Správa | Kto ju zvyčajne vytvára → kto ju prijíma | Účel a typické polia | Charakter šírenia / modelový dôsledok |
| --- | --- | --- | --- |
| **CAM** (Cooperative Awareness Message) | Auto alebo RSU → okolie | Identita ITS stanice, čas, typ stanice, poloha; auto navyše smer, rýchlosť, rozmery, akcelerácia a voliteľné roly/stav | Priebežné lokálne zdieľanie vlastného stavu; generovanie závisí od dynamiky a preťaženia kanála, teda pevné „1 paket/s“ je iba pilot. [ETSI TS 103 900 V2.2.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.02.01_60/ts_103900v020201p.pdf). |
| **DENM** (Decentralized Environmental Notification Message) | Auto alebo RSU, ktoré identifikovalo udalosť → relevantná geografická oblasť | ID udalosti (`actionId`), čas zistenia/aktualizácie, poloha udalosti, platnosť, typ stanice; príčina, dôveryhodnosť a miesto/rozsah udalosti podľa kontajnerov | Spúšťa sa udalosťou, môže sa opakovať, aktualizovať, zrušiť; prijímač potláča duplicity podľa ID a času. [ETSI TS 103 831 V2.2.1](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.02.01_60/ts_103831v020201p.pdf). |
| **CPM** (Collective Perception Message) | Vozidlo alebo RSU so senzormi → okolie | Referenčný čas/poloha, informácie o senzoroch, vnímaná oblasť, objekty a ich ID, relatívna poloha/pohyb a neistota | Správa o **pozorovaných objektoch**, nie opakovanie vlastného stavu CAM; variabilná veľkosť a viac objektov zvyšujú zaťaženie. [ETSI TS 103 324](https://www.etsi.org/deliver/etsi_ts/103300_103399/103324/02.01.01_60/ts_103324v020101p.pdf). |
| **MAPEM** | RSU/križovatka → vozidlá | Geometria križovatky, jazdné pruhy, spojenia a povolené manévre | Pomerne statická mapa; verzia a ID križovatky musia sedieť so SPATEM. [ETSI TS 103 301](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf). |
| **SPATEM** | Radič svetiel/RSU → vozidlá | Stav signálnych skupín, fáza, časovanie/odhad prechodu | Časovo citlivejší stav križovatky; bez prepojenia na dopravný radič sú hodnoty len syntetické. [ETSI TS 103 301](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf). |
| **IVIM** | Správca komunikácie/RSU → vozidlá | Značenie, obmedzenia, dopravné informácie, geografická a časová platnosť | Užitočné na vzdialene vytvorenú informáciu, ktorú RSU lokálne distribuuje. [ETSI TS 103 301](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf). |
| **SREM/SSEM** | Vozidlo → RSU / RSU → vozidlo | Žiadosť o prednostný prejazd a odpoveď/stav | Skutočná obojsmerná výmena, vhodná na RTT a splnenie deadline. [ETSI TS 103 301](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf). |
| **BSM** | Vozidlo → okolie, americký profil | Stav vozidla podľa SAE J2735 | Samostatný alternatívny experiment, nie súčasne „tá istá správa“ ako CAM. [SAE](https://saemobilus.sae.org/standards/j2735_202409-v2x-communications-message-set-dictionary). |
| **Aplikačné dáta cez IP** | Auto/RSU/terminál ↔ server | Vzdialená diagnostika, hlásenie, agregovaný incident, odpoveď služby | UDP pri krátkych správach; TCP/QUIC podľa aplikácie a potreby spoľahlivosti. Identifikátor, čas, priorita a deadline musia byť definované v aplikácii. [RFC 768](https://www.rfc-editor.org/rfc/rfc768.html). |

Z [ETSI registra BTP portov](https://www.etsi.org/deliver/etsi_ts/103200_103299/103248/02.03.01_60/ts_103248v020301p.pdf) vyplýva napríklad CAM `2001`, DENM `2002`, MAPEM `2003`, SPATEM `2004`, IVIM `2006`, SREM `2007`, SSEM `2008` a CPM `2009`. Sú to **BTP porty**, nie UDP porty. Čísla dávajú zmysel až po určení konkrétneho ETSI komunikačného profilu.

### 4.1 Pole po poli: minimálne verné aplikačné modely

**CAM podľa zvolenej verzie ETSI:** `ItsPduHeader` nesie `protocolVersion`, `messageId`, `stationId`. Nasleduje čas vytvorenia (`generationDeltaTime`) a kontajnery. Základný kontajner obsahuje typ stanice a referenčnú polohu s neistotou; povinný vysokofrekvenčný kontajner vozidla zahŕňa aspoň smer, rýchlosť, smer jazdy, dĺžku/šírku a pozdĺžne zrýchlenie, ďalšie dynamické polia závisia od verzie a voliteľnosti. Nízko frekvenčný a špeciálny kontajner dopĺňajú rolu či stav. Presné typy, rozsahy, „unavailable“ hodnoty, ASN.1 a pravidlá PER kódovania treba prevziať z **jednej pripnutej edície**, nie ručne improvizovať binárny formát. [ETSI TS 103 900 V2.2.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.02.01_60/ts_103900v020201p.pdf), [ETSI ASN.1](https://forge.etsi.org/rep/ITS/asn1/cam_ts103900).

**DENM:** povinné polia management kontajnera vo vydaní TS 103 831 V2.2.1 sú `actionId`, `detectionTime`, `referenceTime`, `eventPosition`, `validityDuration`, `stationType`; `termination`, dosah, smer dopravy a interval opakovania sú podmienené/voliteľné. Situačný kontajner môže niesť kvalitu informácie a `causeCode`/podtyp; lokalizačný kontajner môže spresniť cestnú polohu. Stavová mašina musí rozlišovať **novú udalosť → aktualizáciu/opakovanie → zrušenie alebo vypršanie**. Opakované prijatie toho istého `actionId` nie je nová unikátna výstraha. [ETSI TS 103 831 V2.2.1](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.02.01_60/ts_103831v020201p.pdf).

**CPM:** `ItsPduHeader`, management kontajner s referenčným časom a polohou a zoznam typovaných kontajnerov pre pôvodcu, senzory, vnímané regióny a objekty. Objekt má `objectId`; jeho stav je relatívny k referenčnému rámcu a čas merania sa musí odlíšiť od času odoslania. Počet pozorovaných objektov a počet skutočne vložených objektov sa môžu líšiť. Výsledná dĺžka nie je konštantná. [ETSI TS 103 324](https://www.etsi.org/deliver/etsi_ts/103300_103399/103324/02.01.01_60/ts_103324v020101p.pdf).

**Infraštruktúrne správy:** v simulácii musí MAPEM a SPATEM používať rovnaké ID križovatky a pruhové/signalizačné väzby; zvolený cyklus radiča musí skutočne vytvoriť časový vývoj SPATEM. SREM má väzbu na konkrétnu požiadavku a SSEM na jej stav. Bez takýchto väzieb by šlo iba o ľubovoľné UDP dáta s prilepeným názvom správy. [ETSI TS 103 301](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf).

### 4.2 Konkrétne výmeny v navrhnutej infraštruktúre

**Lokálna výstraha:** Auto A deteguje prekážku. Vytvorí DENM s jedným `actionId`, polohou, príčinou, časom platnosti a cieľovou geografickou oblasťou. Auto B aj RSU ju prijmú cez lokálny kanál. Opakovanie toho istého DENM sa v štatistike ráta ako pokus o doručenie tej istej udalosti. Prijímač si overí podpis/čas, potlačí duplicity a rozhodne, či udalosť platí pre jeho polohu. Táto cesta nesmie čakať na LEO; satelit môže výstrahu ďalej distribuovať inému regiónu.

**Vzdialené hlásenie cez RSU:** RSU prevezme udalosť, vytvorí aplikačný IP/UDP report obsahujúci pôvodný `event_id`, čas a overenú polohu, odošle ho na pevný UT. UT použije satelitný user link, prípadnú ISL, feeder link a gateway; server report prijme. Ak vzdialená RSU na jeho základe vytvorí vlastnú lokálnu DENM, treba zdokumentovať, či pôvodný `actionId` iba prenáša, alebo vzniká nový autorizovaný pôvodca udalosti. Koncové podpisy a deduplikácia sa nesmú rozbiť nevedomým „prebalením“ správy.

**Odpoveď zo siete:** Server môže vrátiť potvrdenie prijatia reportu, pokyn alebo aktualizáciu stavu. Je to nový tok v opačnom smere s vlastným deadline; UDP samo negarantuje potvrdenie a linkové ACK na jednom rádiovom hope nedokazuje, že server správu dostal. Pre RTT treba párovať request/response ID na aplikácii a merať obe samostatné jednosmerné zložky, ak sú potrebné.

## 5. Čo presne obsahuje „paket“

**Paket nemá jednu univerzálnu hlavičku.** Pri každom meraní treba povedať, na ktorej vrstve bol zachytený. Príklad európskej lokálnej cesty je:

```text
802.11/ITS-G5 rámec
  MAC hlavička: adresy/riadenie/sekvencia (podľa typu rámca)
  GeoNetworking: verzia, next header, typ a podtyp, hop limit,
                 životnosť, dĺžka payloadu, zdrojová poloha;
                 pri geocaste cieľová oblasť a ďalšie polia
  voliteľný bezpečnostný obal: signer/certifikát alebo jeho digest,
                            čas/oblastné údaje, podpis
  BTP: cieľový port + zdrojový port alebo port info (spolu 4 B)
  ITS aplikačná správa: napr. ASN.1 UPER CAM/DENM
  PHY: preambula, modulácia/kódovanie, prenášané symboly
```

GeoNetworking nemá rovnakú dĺžku pri všetkých typoch rámca. Špecifické rozloženie hlavičky pre single-hop broadcast, geobroadcast a geounicast je definované v [ETSI EN 302 636-4-1](https://www.etsi.org/deliver/etsi_en/302600_302699/3026360401/01.03.01_60/en_3026360401v010301p.pdf); pri bezpečnosti sa použije profil [ETSI TS 103 097](https://www.etsi.org/deliver/etsi_ts/103000_103099/103097/01.04.01_60/ts_103097v010401p.pdf). Presná veľkosť CAM je premenlivá kvôli voliteľným kontajnerom, PER a bezpečnostnému obalu. Nemožno preto bez konfigurácie napísať napríklad „CAM má 300 B“ ako všeobecnú vlastnosť štandardu.

Súčasný pilot používa **iný zásobník**:

```text
300 B aplikačný ns-3 Packet = SeqTsHeader + deterministický obsah
  → UDP (8 B) → IPv4 (typicky 20 B bez options)
  → lokálny 802.11p profil / bodová LAN / SNS-3 satelitný kanál
```

`SeqTsHeader` má presne **12 B**: 4 B poradové číslo v sieťovom poradí bajtov a 8 B časová značka vo vnútorných časových krokoch ns-3, nie čas UTC. Zvyšných **288 B** je v pilote vzor `(seq + index) mod 256`. `flow` je názov toku v logu, nie pole samotného 300-bajtového payloadu. Pri jednoduchom IPv4 bez options, fragmentácie a ďalšej linkovej hlavičky má 300 B aplikačný obsah + 8 B UDP + 20 B IPv4 = **328 B IP datagram**. Rádiový rámec je väčší; jeho presnú dĺžku treba odčítať z konkrétneho PCAP/trace. Aplikačné proxy na RSU a termináli payload skopírujú, ale vytvoria nové UDP/IP odoslania. `packet_uid` alebo rovnaký aplikačný hash preto neznamená identické rádiové bity cez všetky úseky. [Implementácia pilotu](../src/vanet-sns3.cc), [ns-3 definícia SeqTsHeader](https://gitlab.com/nsnam/ns-3-dev/-/blob/ns-3.48/src/applications/model/seq-ts-header.cc), [RFC 768](https://www.rfc-editor.org/rfc/rfc768.html), [RFC 791](https://www.rfc-editor.org/rfc/rfc791.html).

**Navrhnutá meracia hlavička pre budúce aplikácie** (nie súčasný štandard CAM) má obsahovať `schema_version`, `message_type`, `origin_station_id`, `flow_id`, `message_id`, `sequence`, `creation_time_ns`, `expiry_time_ns/deadline`, `priority`, `payload_length`, `payload_hash` a podľa typu `event_id` alebo `intersection_id`. Identifikátor udalosti sa nesmie zamieňať so sekvenciou opakovania; čas vytvorenia sa musí zachovať cez všetky proxy. Skutočné CAM/DENM/CPM majú používať štandardnú ASN.1 schému; táto meracia hlavička je len vnútorná kontrola experimentu a musí sa pri výpočte on-air veľkosti započítať, ak sa naozaj posiela.

### 5.1 Úrovne zhody obsahu

1. **Aplikačný význam:** rovnaká udalosť/poloha/priorita, aj keď sa sérializácia zmení.
2. **Aplikačné bajty:** rovnaký hash užitočného obsahu od auta po server; pilot túto úroveň overuje.
3. **Sieťový datagram:** rovnaká IP hlavička a porty; pri proxy to neplatí.
4. **Linkový rámec:** pri prechode Wi-Fi → káblový spoj → satelit sa vždy mení.
5. **Fyzické symboly:** závisia od modulácie, kódovania, frekvencie a kanála; nie sú obnoviteľné z aplikačného hash-u.

Pri meraní teda ukladať `message_id`/`flow_id` na aplikácii a osobitné ID alebo čas na každom hope. Koreláciu uvádzať ako **dokázanú** iba tam, kde surový trace obsahuje dostatočné identifikátory a časové poradie.

### 5.2 Bezpečnosť a súkromie v packet path

Pri kooperatívnej výstrahe musí prijímač riešiť autentickosť, integritu, oprávnenie odosielateľa, čerstvosť správy a duplicity. ETSI definuje podpísaný obal a certifikačné profily; pseudonymné identifikátory chránia pred jednoduchým dlhodobým sledovaním. Podpis a certifikát/digest pridávajú bajty a spracovanie, kontrola času a oblasti môže viesť k zahodeniu ešte pred aplikáciou. Satelitný backhaul typicky prenáša už vytvorenú aplikačnú správu v inom linkovom rámci; jeho vlastná autentifikácia terminálu nenahrádza dôveryhodnosť pôvodného V2X hlásenia. [ETSI TS 103 097](https://www.etsi.org/deliver/etsi_ts/103000_103099/103097/01.04.01_60/ts_103097v010401p.pdf), [ETSI TS 102 941](https://www.etsi.org/deliver/etsi_ts/102900_102999/102941/02.01.01_60/ts_102941v020101p.pdf).

Pre prvé sieťové experimenty možno kryptografiu nahradiť **explicitným časovým a veľkostným overheadom**, ale nesmie sa potom tvrdiť bezpečnostná vernosť. Ak sa testuje falošná DENM, replay alebo zmena pseudonymu, treba modelovať autorizáciu, časovú toleranciu a rozhodnutie prijímača; samotné úspešné PHY doručenie falošného paketu nie je úspešná bezpečná aplikácia.

## 6. Satelitný zásobník, správy a fyzika

### 6.1 Štyri rôzne úseky

**User/service link** je RF spoj terminál ↔ satelit. **Feeder link** je RF spoj satelit ↔ gateway. **ISL** je samostatný satelit ↔ satelit. **Pozemná core/IP sieť** spája gateway so serverom, ďalšími bránami a internetom. Pri transparentnom „bent-pipe“ satelite sa rádiový signál prekladá/zosilňuje a spracovanie je prevažne na Zemi; pri regeneratívnom satelite sa časť PHY/MAC alebo sieťová vrstva ukončí na orbite. To mení miesto front, routovania a trace bodov. [SNS-3 režimy regenerácie](https://github.com/sns3/sns3-satellite), [3GPP TS 38.300 NTN](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/19.00.00_60/ts_138300v190000p.pdf).

Na user linku treba definovať frekvenciu, šírku pásma, výkon, EIRP, zisk a smerovanie antény, citlivosť/G/T, minimálnu eleváciu, polarizáciu, voľnopriestorový útlm, atmosférické a dažďové straty, tienenie karosériou, Doppler, moduláciu/kódovanie, HARQ/ARQ podľa zvoleného modelu a plánovanie zdrojov. Pri optickej ISL treba pridať akvizíciu, smerovanie lúča a obmedzenie geometrickej viditeľnosti; pri RF ISL frekvenciu, zisk a interferenciu. Výpočet Earth-space strát má použiť vhodnú verziu [ITU-R P.618](https://www.itu.int/rec/R-REC-P.618/en), s plynnou absorpciou podľa [P.676](https://www.itu.int/rec/R-REC-p.676/en) a lokálnymi štatistikami zrážok podľa [P.837](https://www.itu.int/rec/R-REC-P.837/en), ak sú pre vybrané pásmo a scenár relevantné. Neznámy parameter sa nesmie nenápadne nastaviť na „ideálny“.

Približné jednosmerné oneskorenie sa skladá z `Σ vzdialenosť/c + čakanie na médium/plánovač + vysielací čas + fronty + spracovanie + prípadný handover/retransmisia`. Pre link budget v dB: `P_rx = EIRP_tx + G_rx − FSPL − L_atm − L_rain − L_point − ďalšie straty`; `FSPL = 20 log10(4πd/λ)`. Viditeľnosť a elevácia určujú šikmú vzdialenosť, nie samotná nominálna výška. Pre Globalstar transparentný relay musí byť v tom istom čase viditeľný terminál aj vhodná gateway; pre mesh možno použiť platnú ISL trasu, ak je dostupná.

### 6.2 Dátové verzus riadiace správy satelitnej siete

Satelitná prevádzka nie je iba IP payload. Implementácia zvoleného **DVB-S2/RCS2 referenčného profilu** môže zahŕňať nadviazanie terminálu (logon request/accept), synchronizáciu času a polohy, prideľovanie return-link slotov, žiadosti o kapacitu, kontrolné tabuľky superrámcov, kódové/modulačné režimy, bursty, handover a dáta používateľa. Tieto presné názvy a polia patria k DVB/RCS2; napríklad [ETSI EN 301 545-2 V1.5.1](https://www.etsi.org/deliver/etsi_en/301500_301599/30154502/01.05.01_20/en_30154502v010501a.pdf) špecifikuje logon request a prácu s timeslotmi. Pri SNS-3 treba pre každú z týchto funkcií overiť, či ju konkrétny scenár **zapol**; samotná podpora knižnice ešte neznamená zapnutie vo výslednom behu. DVB rámce a kontrolné správy nemožno nazvať Starlink/Iridium/Globalstar rámcami.

**3GPP NTN** je ďalší samostatný štandardizovaný variant s pojmami service/feeder link, UE, bunka, timing advance, Doppler compensation, random access, paging, beam a switchover. Možno ho uviesť v teórii ako alternatívnu architektúru, no aktuálny SNS-3 DVB pilot nie je 3GPP NTN simuláciou. [3GPP TS 38.300 Rel-19](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/19.00.00_60/ts_138300v190000p.pdf).

### 6.3 Tri operátorské profily

| Profil | Verejne doložená architektúra | Čo môže simulácia poctivo prevziať | Čo ostáva neznáme a musí sa modelovať citlivosťou |
| --- | --- | --- | --- |
| **Starlink** | LEO prístup cez vhodný terminál; verejný opis Ku/Ka/E antén a optických ISL/mesh. [Starlink Technology](https://starlink.com/technology). | Časovo platné orbitálne dáta, zdrojované pásmo konkrétneho terminálu/generácie, user/feeder/optické ISL, gateway geografia. | Proprietárny RF/MAC rámec, scheduler, admission control, handover, dynamické smerovanie a profil terminálu. Číslo „až 200 Gb/s“ na stránke je horná produktová hodnota ISL, nie garantovaná kapacita jednej simulovanej trasy. |
| **Iridium** | LEO sieť s L-band používateľským spojom a štyrmi RF crosslinkmi na satelit; gateway spracúva prevádzku. [Iridium Network](https://www.iridium.com/network). | Mesh s RF ISL, odlišný link budget a kapacitná trieda služby, vhodná brána. | Vnútorné rozvrhovanie, rámce, dynamické routovanie, presné parametre služby a terminálu. Štyri crosslinky sú topologická schopnosť, nie záruka štyroch použiteľných liniek v každom okamihu. |
| **Globalstar** | LEO `bent-pipe`: terminál ↔ satelit ↔ pozemná brána; spoločnosť uvádza Walker-24 a pozemné brány. [Globalstar Who We Are](https://www.globalstar.com/en-ap/about/who), [investorský technický prehľad](https://investors.globalstar.com/static-files/ca62cad1-878b-4328-9b4a-91c4f68b8c8b). | Transparentný relay bez ISL, súbežnú viditeľnosť terminálu a gateway, S/L používateľské a C feeder pásmo podľa konkrétnej služby. | MAC/rámce, presné aktuálne rozmiestnenie funkčných gateway, plánovač a terminál. Globalstaru sa nesmie pridať ISL kvôli zjednoteniu grafu. |

Pri „priamom aute na satelit“ určiť presný typ služby: širokopásmový terminál, úzkopásmový modem alebo store-and-forward odosielanie majú neporovnateľné dátové rýchlosti a správanie. Dopravná správa nie je automaticky podporovaná každou službou. Dátum zdroja orbitálnych elementov, terminálu a cenníkových/prevádzkových limitov patrí do konfiguračného manifestu; staré TLE nemôžu dokazovať dnešné pokrytie.

### 6.4 Konkrétna služba a terminál sú súčasťou experimentu

| Kandidát pre model | Verejne overiteľná schopnosť | Dôsledok pre paketový experiment |
| --- | --- | --- |
| Starlink Performance alebo iný aktuálne povolený mobilný terminál s príslušným plánom | Starlink uvádza podporované zariadenia a obmedzenia použitia za jazdy; Performance je určený na mobilné nasadenie. [Podpora Starlink pre in-motion](https://starlink.com/sz/support/article/50e933eb-54f5-1a77-cc85-c6c8325564cf), [špecifikácia Performance](https://starlink.com/public-files/specification_sheet_performance.pdf). | IP tok, montáž/výhľad, spotreba, plán služby a oblasť použitia. Špecifikácia produktu nie je garantovaná distribúcia oneskorenia. |
| Iridium Certus 100 | Mobilná IP služba do 88 kb/s podľa výrobcu. [Iridium Certus 100](https://www.iridium.com/services/iridium-certus-100). | IP porovnanie so Starlinkom je možné iba pri zaťažení, ktoré sa do tejto kapacitnej triedy zmestí; profil terminálu/antény musí byť konkrétny. |
| Iridium Certus 9704/IMT | Výrobca opisuje správovú službu a maximálnu správu 100 kB. [Iridium 9704](https://www.iridium.com/products/iridium-certus-9704-module). | Samostatný **message-service** scenár, nie voľná zámennosť s Certus IP linkou. Čas doručenia sa meria na hranici API správy. |
| Globalstar RM200M | Dvojsmerné IoT správy podľa výrobcu: mobile-originated 9–144 B a mobile-terminated 9–128 B. [RM200M datasheet](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet.pdf). | Referenčný 300 B UDP paket **nie je natívny RM200M paket**. Scenár musí použiť povolenú veľkosť správy, aplikačné segmentovanie alebo kompresiu a zahrnúť jej oneskorenie. |
| Globalstar STX3 | Jednosmerné odosielanie správ z terminálu; výrobca uvádza opakované bursty. [STX3](https://www.globalstar.com/getmedia/2b486e44-178a-431c-af1d-23cc59ed6b83/stx3-sles-sheet.pdf). | Vhodné na telemetriu auta → server, nie na obojsmerný round trip. Pri opakovaných burstoch počítať unikátne doručené správy. |

Porovnanie má preto dve osi: **spoločná aplikačná úloha**, ktorú všetky vybrané služby skutočne podporujú (napr. krátke hlásenie polohy/udalosti), a **natívny profil každej služby**, ktorý ukáže jej vlastnú kapacitu a obmedzenia. Pri spoločnej úlohe sa môže líšiť enkapsulácia, fragmentácia a frekvencia; primárnou metrikou je doručenie rovnakej informácie včas. Pre IP širokopásmové služby možno zvlášť porovnávať goodput pri rovnakom zaťažení. Údaj „rovnaký 300 B UDP paket cez všetky tri siete“ by nepopisoval reálnu službu RM200M/STX3.

## 7. Cieľová vernosť po vrstvách

| Vrstva | Cieľový model a vstupy | Ako sa overí |
| --- | --- | --- |
| Doprava | Skutočný cestný úsek z OSM/SUMO, opravené pruhy a križovatky, realistický dopyt podľa dostupných dopravných dát; viac hustôt, smerov a rýchlostí. Ak sa skúma vplyv výstrahy na premávku, obojsmerný TraCI/libsumo krok. | Poloha, tok, rýchlosť a dojazdový čas oproti nezávislému dopravnému podkladu; OSM geometria sama nevytvára reálny dopyt. [SUMO OSM import](https://sumo.dlr.de/docs/Tutorials/Import_from_OpenStreetMap.html), [TraCI](https://sumo.dlr.de/docs/TraCI.html). |
| Lokálne V2X | Pripnutý ETSI ITS-G5 profil s reálnym CAM/DENM ASN.1, BTP, GeoNetworking, DCC, prípadne bezpečnostným obalom; 802.11p OCB a model LoS/NLoS, fadingu, preťaženia a tienenia vozidlami/zástavbou. C-V2X PC5 je samostatná alternatíva, nie skrytá zámena. | Dekódovanie na prijímači, správna stavová mašina DENM, reprodukovateľné dĺžky a generovanie CAM, PDR podľa vzdialenosti a hustoty oproti meraniam. [Vanetza](https://github.com/riebl/vanetza), [reálne ITS-G5 dáta](https://github.com/BMEAutomatedDrive/v2xdatasets). |
| Geografia/LEO | Spoločný UTC začiatok, WGS84 poloha cesty, RSU, UT a GW; časovo blízke a archivované GP/OMM alebo TLE elementy; SGP4; zemský zákryt, minimálna elevácia, beam footprint a dostupnosť gateway/ISL. | Nezávislý výpočet elevácie/vzdialenosti pre vzorky času; vstupná epocha a SHA-256. OMM je vhodné aj tam, kde TLE formát nepokryje nové katalógové čísla. [CelesTrak GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php). |
| RF satelit | Konkrétny terminál/služba: EIRP, anténa/G/T, pásmo, šírka kanála, Doppler, LoS/tienenie, atmosféra/dážď, link margin, prenosové rýchlosti a chybovosť. Oddeliť user, feeder a ISL. | Dimenzionálne skontrolovaný link budget, vzorka `P_rx`, SNR a margin pre vybrané elevácie; interval pri nepublikovaných parametroch. V ns-3.48 existujú aj 3GPP NTN loss modely, ich použitie v SNS-3 však vyžaduje integračný a validačný test. [ns-3 propagation](https://www.nsnam.org/docs/models/html/propagation.html). |
| MAC a služba | Attach/logon, prideľovanie slotov alebo empirický service envelope, fronty, priorita, opakovania, handover a servisné limity. Proprietárnu časť nahradiť funkciou kalibrovanou na reálne merania, nie DVB mechanizmom len kvôli detailnosti. | RTT, one-way delay ak sú k dispozícii synchronizované merania, percentily strát/výpadkov, čas obnovy a goodput na dátach nepoužitých pri kalibrácii. [Mobilné merania Starlinku](https://tma.ifip.org/2024/wp-content/uploads/sites/13/2024/05/tma2024-final53.pdf). |
| Koncové aplikácie | Reálne obmedzenia API konkrétnej služby; lokálna výstraha, vzdialený report, odpoveď a dátový tok ako oddelené triedy. Každá správa má ID, čas vzniku, platnosť/deadline, veľkosť a adresátov. | Rovnaká informácia po celom packet path, žiadne skryté proxy doručenie, explicitný rozsah príjemcov a miera včasných unikátnych správ. |

**Kalibrácia a validácia sú odlišné operácie.** Parametre rádiového útlmu, servisného oneskorenia alebo handoveru sa najprv nastavujú na jednej časti referenčných dát; na inej trase/čase/zaťažení sa bez ďalšej úpravy porovná rozdelenie vzdialenosti, PDR, RTT, jitteru, výpadkov a goodputu. Verejný [dataset ITS-G5 so správami CAM/DENM a RF metadátami](https://github.com/BMEAutomatedDrive/v2xdatasets) a [mobilné merania Starlinku v strednej Európe](https://tma.ifip.org/2024/wp-content/uploads/sites/13/2024/05/tma2024-final53.pdf) sú kandidáti na takúto kontrolu; geografický, časový a terminálový nesúlad s naším scenárom sa musí uviesť. Pre Iridium/Globalstar treba hľadať merania **tej istej služby a terminálu**, inak výsledok zostane intervalom odhadov, nie validáciou operátora.

**Priorita pri obmedzenom čase BP:** najprv dokončiť a validovať jednu celú trasu `auto → ITS-G5 → RSU → pevný UT → LEO → GW → server` vrátane skutočných lokálnych správ, koncovej identity udalosti a merateľných dôvodov strát. Potom pridať mobilný UT, zmenu satelitu/beam-u a ďalšie operátorské profily. Viac pomenovaných operátorov s neoverenými predpokladmi by nedalo vernejší výsledok než jedna dôsledne overená trasa. Každý rozšírený profil má prejsť rovnakými bránami nižšie.

**Záznam vernosti pri každom behu** musí pri každej vrstve uviesť `implementované / kalibrované / citlivosť / mimo modelu`, zdroj a dátum parametra, konkrétny typ terminálu, zdroj meraní a interval platnosti záveru. Graf bez tohto záznamu sa nesmie vykladať ako výkon komerčnej služby. Osobitne treba označiť, ktoré bajty na trase sú pôvodná ETSI správa, ktoré sú report vytvorený RSU a ktoré sú internou satelitnou enkapsuláciou.

### 7.1 Voľba implementačnej cesty

**Primárny kandidát:** jeden ns-3 beh so SUMO mobilitou a SNS-3 pre satelit, doplnený o korektné ITS správy a GN/BTP/DCC/bezpečnosť a opravený lokálny OCB MAC. Výhoda je spoločný čas, paketové fronty a trace. Pred rozhodnutím treba otestovať, či kompatibilný C-ITS stack možno pripojiť k ns-3.48 bez rozsiahlej neoveriteľnej vlastnej implementácie, a zistiť, ktoré vydania ETSI ASN.1 skutočne podporuje. Samotný `AdhocWifiMac` cieľ OCB nesplní.

**Alternatíva s vyššou vernosťou cestnej vrstvy:** [Artery/Vanetza](https://github.com/riebl/artery/blob/master/docs/architecture.md) poskytuje SUMO spolu s ETSI ITS-G5 stackom a prístupovým rádiom v OMNeT++; satelitná časť by potrebovala samostatné validované prepojenie alebo synchronizovanú kosimuláciu. Táto cesta má zmysel, ak protokolovo správny lokálny C-ITS prenos v ns-3 neprejde integračným testom. Treba tiež overiť podporovanú edíciu CAM/DENM ASN.1, OCB správanie zvoleného rádia a dôvody zahodenia; samotný názov frameworku ich negarantuje. Dva nezávislé behy bez synchronizovaných front, spätnej väzby a spoločnej identity správy nemožno prezentovať ako jednu end-to-end paketovú simuláciu.

**Satelitná voľba podľa cieľa:** SNS-3 DVB má ostať kontrolným fyzickým referenčným profilom a dôkazom integrácie. Pre menovaného operátora treba v tom istom simulačnom čase použiť jeho geometriu, topológiu a terminálové limity; otvorené vrstvy modelovať fyzikálne a uzavreté vrstvy kalibrovaným servisným modelom. Rozhodnutie „SNS-3 ako jediná pravda pre všetky tri siete“ by znížilo vernosť práve v miestach, ktoré má BP skúmať.

**Rozhodovacia skúška pred veľkou implementáciou:** na jednej ulici a jednej satelitnej trase vytvoriť štandardne dekódovateľný CAM a DENM, preniesť vybraný report cez satelit až na server, dokázať čas a identitu správy na každom hope a vyvolať skutočný handover. Zmerať čas zostavenia, výkonnosť a chýbajúce moduly oboch kandidátskych ciest. Až z tohto výsledku pripnúť finálny toolchain a rozsah vernosti.

### 7.2 Čo musí platiť, aby sa model dal označiť za najvernejší dosiahnuteľný

Plán je **hypotéza o postupe**, nie záruka presnosti. Na začiatku implementácie treba vybrať konkrétny región, obdobie, terminál a službu a zostaviť inventár dostupných referenčných dát. Až podľa neho možno rozhodnúť, ktoré komponenty budú fyzikálne reprodukované, ktoré sa dajú validovať meraním a ktoré ostanú intervalom citlivosti. Pri každej hypotéze treba pred meraním stanoviť prijateľnú chybu modelu voči dostupnej referencii; hranica sa nesmie vybrať až po výsledku.

| Úroveň tvrdenia | Nutný dôkaz | Prípustný záver |
| --- | --- | --- |
| Funkčná integrácia | Dekódovateľná správa, platný packet path, kladný a záporný test. | Správa prešla implementovanou trasou. |
| Fyzikálne a protokolovo vierohodný model | Konzistentná geografia/čas, štandardný lokálny stack, zdrojované link budgety, validované orbity a obmedzenia terminálu. | Model zachytáva zdokumentované mechanizmy zvolenej trasy. |
| Kvantitatívne validovaný profil | Kalibrácia na jednej sade dát a splnenie vopred určených chýb pre PDR, oneskorenie, dostupnosť a handover na nezávislých dátach rovnakého terminálu/služby a porovnateľných podmienok. | Výsledok má doloženú predikčnú presnosť v uvedenom rozsahu podmienok. |
| Operátorský odhad bez validačných dát | Zdrojované parametre, otvorené predpoklady a analýza citlivosti. | Interval správania možného profilu; nemožno tvrdiť presnú výkonnosť skutočného operátora. |

Ak merania rovnakej služby a terminálu nie sú dostupné, najvyššia poctivo dosiahnuteľná úroveň pre daný operátorský profil je **fyzikálne vierohodný model s intervalom neistoty**. Realistické orbity ani detailný DVB MAC tento nedostatok samy neodstránia. Ak sú merania k dispozícii, minimálny validačný balík má pokryť pohyb/státie, otvorený výhľad/tienenie, nízku/vysokú eleváciu, ľahkú/vyššiu záťaž a prechod medzi obsluhujúcimi satelitmi tam, kde ho služba podporuje. Rozsah, pre ktorý dáta neexistujú, musí zostať výslovne mimo validovaného záveru.

## 8. Rozdiel medzi cieľom a dnešným pilotom

| Komponent | Overený stav | Význam pre výskumný záver |
| --- | --- | --- |
| SUMO → vozidlá | Dve vozidlá, syntetická cesta; FCD polohy sa prenesú do ns-3. | Funkčná mobilita, ešte nie dopravná reprezentatívnosť ani spätný vplyv správy na vodiča. [Model](model.md). |
| Pozemný prenos | Profil `WIFI_STANDARD_80211p`, generický `AdhocWifiMac`, UDP/IPv4 a 300 B payload. | Skutočný ns-3 paketový tok, ale nie kompletný ETSI ITS-G5/CAM stack. [Kód](../src/vanet-sns3.cc). |
| RSU → pevný UT | Aplikačné proxy cez ns-3 `PointToPointHelper`. | Obsah payloadu sa kontroluje; nejde o neprerušené IP smerovanie ani Ethernet PHY/MAC. [Integračný denník](experiments/sns3-integracia.md). |
| SNS-3 LEO | Dva testovacie LEO satelity, DVB user/feeder link a jedna modelovaná ISL; 10/25 vzdialených správ prešlo v konkrétnom behu. | Dôkaz integrácie a paketového priechodu modelovanou ISL. Historické TLE z roku 2014 a nekoregistrovaná geografia neumožňujú výrok o dnešnom pokrytí. [Integračný denník](experiments/sns3-integracia.md). |
| Mobilný UT v aute | Pokus zlyhal v handoveri SNS-3; izolovaný úspešný experiment neexistuje. | Priama trasa auto → LEO je zatiaľ cieľ, nie hotový výsledok. [Denník zlyhania](experiments/mobile-ut-handover-failure.md). |
| Editor/prehrávač | Generuje jednu cestu, dve autá, RSU, beh a časovú os s payloadmi. | Pomôcka pre reprodukciu; obrazové interpolácie nemenia sieťové dáta. [Denník editora](experiments/visualny-editor.md). |

V referenčnom behu je vzdialený tok obmedzený aj miestnym dosahom RSU; 10/25 sa nesmie pomenovať „40 % dostupnosť satelitu“. Súčasné metriky sú platné iba pre zvolený krátky syntetický scenár, jeden seed a 1 správu/s. Pred porovnaním operátorov treba najskôr ukázať, že každý úsek skutočne funguje a že príčina straty je rozlíšiteľná.

## 9. Cieľový implementačný návrh

### 9.1 Päť funkčných vrstiev modelu

1. **Doprava:** SUMO sieť, vozidlá, rýchlosť, smer, križovatky, záťaž a voliteľná reakcia vozidiel na doručenú informáciu cez TraCI. Bez TraCI možno tvrdiť iba kvalitu komunikácie, nie zvýšenie bezpečnosti alebo plynulosti dopravy. [SUMO FCD](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html).
2. **Geografia a orbity:** jedna geodetická kotva pre mapu, konzistentný prevod SUMO `(x,y)` ↔ WGS84, poloha RSU/UT/GW, časová epocha TLE/ephemeríd, SGP4 alebo iný zdokumentovaný propagátor, elevácia a viditeľnosť. Všetky súradnice a časové bázy musia mať jednotky.
3. **Pozemná sieť:** kalibrované lokálne rádio, OCB MAC, interferencia, preťaženie, tienenie a rozmiestnenie RSU. Cieľový profil obsahuje ASN.1 CAM/DENM, BTP, GeoNetworking, DCC a bezpečnostný obal podľa pripnutých verzií. Zjednodušený 802.11p pilot zostáva kontrolou pipeline, nie koncovým modelom tejto vrstvy.
4. **Satelitný segment:** oddelený pevný UT a mobilný UT, user/feeder/ISL, gateway, viditeľnosť, beam/handover, fronty, kapacita, modulácia/kódovanie alebo ich riadne pomenované náhradné modely. Režim transparentný/regeneratívny je súčasť konfigurácie, nie skrytý predpoklad.
5. **Aplikácia a meranie:** jasné typy správ, vznik, deadline, deduplikácia, časová pečiatka, log každého hopu, per-hop PHY/MAC dôvod zlyhania tam, kde je dostupný. Pri proxy uchovať koncový `message_id` a zaznamenať nový IP tuple.

### 9.2 Pravidlá generovania prevádzky

| Trieda | Odporúčaný experimentálny profil | Prečo |
| --- | --- | --- |
| Priebežná awareness | CAM odvodená od polohy/rýchlosti a príslušných spúšťačov z pripnutej verzie normy; aspoň variant 1–10 Hz podľa podmienok a DCC | Otestuje obsadenie kanála a starnutie polohy; 1 Hz pilot nepokrýva hustý scenár. [ETSI CAM](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.02.01_60/ts_103900v020201p.pdf). |
| Udalostná výstraha | DENM pri nehode, prekážke alebo práci na ceste; opakovanie, update, expiry, zrušenie | Dôležitý je deadline a počet jedinečných prijímajúcich vozidiel, nie iba priemerná PDR. [ETSI DENM](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.02.01_60/ts_103831v020201p.pdf). |
| Križovatka | MAPEM pri zmene mapy a SPATEM podľa radiča svetiel; v oddelenom scenári SREM/SSEM | Spája RSU so skutočným významom dát a obojsmerným požiadavkom. [ETSI infraštruktúrne služby](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf). |
| Vzdialené dáta | Auto/RSU → server cez satelit; malá správa a samostatný kapacitný prúd | Oddeľuje latenciu krátkych správ od preťaženia; satelit môže byť záložný backhaul. |

Abstraktný payload s presnou veľkosťou a časovaním možno použiť pri izolovanom ladení kanála alebo frontu. **Cieľové end-to-end experimenty používajú skutočné ASN.1 kódovanie vybraných ETSI správ**, overené dekódovaním na prijímači, a dokumentujú každú zmenu reprezentácie pri prechode cez RSU alebo satelitnú službu. Ku každému grafu treba uviesť, ktorá úroveň vernosti sa používa.

## 10. Sada scenárov, ktorá pokrýva zadanie

Spoločné sú: tá istá SUMO trajektória/mapa, časový interval, zdroje správ, porovnávaný počet prijímačov, seed/run, geografická kotva a meracie body. Scenáre nemajú byť „tri rôzne mapy = tri operátori“; rozdiel satelitnej topológie sa musí dať izolovať.

| ID | Porovnanie a hypotéza | Zásah a kontrola | Primárna metrika |
| --- | --- | --- | --- |
| S0 | Lokálne V2V/V2I funguje bez satelitu. | Riedka/hustá prevádzka, polohy RSU, iba pozemský segment. | PDR podľa vzdialenosti, latency/deadline, channel busy ratio. |
| S1 | Satelitný backhaul RSU doručí vzdialené hlásenie tam, kde chýba pozemné WAN. | RSU s pevným UT vs pozemný WAN referenčný link; rovnaké vstupy. | Koncové doručenie, p50/p95/p99 oneskorenie, rozklad po hopoch. |
| S2 | ISL zachová trasu, keď lokálny satelit nevidí bránu. | Tá istá geometria s povolenou/zakázanou ISL; Globalstar má iba platný bez-ISL profil. | Dostupnosť v čase a cena dodatočných skokov. |
| S3 | Mobilný UT vo vozidle prekoná úsek mimo dosahu RSU, ale závisí od výhľadu/handoveru. | Priama trasa s/bez RSU, tienenie a beam handover; až po oprave mobilného UT. | Úspešný attach, výpadky, deadline miss. |
| S4 | Preťaženie zasiahne kritické správy inak než kapacitný tok. | Dve intenzity vozidiel, veľkosti payloadu, priorita, rôzny podiel ponúkaného zaťaženia/kapacity. | PDR podľa triedy, fronty, percentily, férovosť. |
| S5 | Satelitný výpadok má lokálne obmedzený dopad, ak V2V ostáva lokálne. | Výpadok user/feeder/ISL, zlyhanie GW; lokálny bezpečnostný tok beží ďalej. | Per-hop loss cause, time-to-recovery, unikátni príjemcovia DENM. |
| S6 | Konkrétna satelitná služba, terminál a topológia určujú, ktoré cestné hlásenia dorazia včas. | Starlink mobilné IP, Iridium Certus IP/správy a Globalstar RM200M pri rovnakej krátkej informácii; osobitne ich natívne zaťaženie. Citlivosť neznámych parametrov. | Včas doručená unikátna informácia, interval neistoty, servisný limit a príčina nedoručenia. |
| S7 | Doručená informácia môže zmeniť dopravný výsledok. | Až po implementácii spätnej väzby TraCI: s/bez výstrahy pri kontrolovanej nehode. | Kolízie/near miss, brzdenie, cestovný čas; oddelene od sieťových metrík. |

**Cieľová sada** zahŕňa S0–S6: lokálne V2X, pevný satelitný backhaul, mobilný terminál, ISL/brány, záťaž a výpadky, plus zdrojované porovnanie konkrétnych služieb troch operátorov. Každý scenár sa skúša na mestskej a mimomestskej geometrii, pri riedkej a hustej premávke, vo viacerých časoch/epohách konštelácie a s viacerými seedmi; presný počet behov určí pilotná analýza variability a dostupné výpočtové zdroje. S7 sa pridáva, ak má práca kvantifikovať zlepšenie bezpečnosti či plynulosti dopravy, pretože to vyžaduje spätnú väzbu do SUMO. Pri S6 sa spoločná krátka aplikačná informácia porovná cez služby, ktoré ju podporujú; natívne kapacitné a správové profily sa vyhodnotia zvlášť.

Scenáre sa realizujú po bránach vernosti, nie ako slepý kartézsky súčin všetkých parametrov. Najprv sa overí koncová trasa a lokálny protokol, potom geografická a orbitálna správnosť, mobilita/handover, servisná kalibrácia a až napokon štatistické rozšírenie. Pre každú hypotézu sa vopred určí jedna primárna metrika, deadline a rozhodujúca zmena podmienky; ďalšie parametre sa pridávajú tam, kde odhalia neistotu alebo interakciu.

## 11. Metriky, štatistika a atribúcia príčin

**PDR** = počet unikátnych aplikačných správ doručených zvolenému príjemcovi / počet správ, ktoré sa mali odoslať počas definovaného meracieho okna. Pri broadcast treba menovateľ definovať ako množinu **oprávnených párov správa–príjemca** (napr. auto v relevantnej oblasti), nie počet TX. Pri geocaste zaznamenať počet prijímačov v cieľovej oblasti v čase vytvorenia správy. Pri DENM opakovania nerozmnožujú počet udalostí.

**One-way delay** = `t_rx_app − t_created_app` pre doručené správy a pri zosúladených simulačných hodinách. V simulácii sú spoločné hodiny jednoduchšie než v reálnom systéme. Popri priemere vykazovať medián, p95/p99 a podiel doručený **pred deadline**; strata nemá priradené oneskorenie. **Jitter** treba definovať konkrétne, napr. RFC 3393 IPDV alebo priemernú absolútnu zmenu oneskorenia susedných prijatých správ, a potom používať tú istú definíciu vo všetkých scenároch. [RFC 3393](https://www.rfc-editor.org/rfc/rfc3393.html).

**Dostupnosť** rozdeliť na (a) geometrickú viditeľnosť, (b) pripojený terminál s prideleným kanálom, (c) end-to-end aplikačné doručenie v časovom okne. Tieto hodnoty môžu byť odlišné. **Goodput** počíta užitočné aplikačné bajty prijaté za čas; throughput na PHY zahŕňa overhead a opakovania. **CBR/obsadenie kanála**, per-hop zahodenie, dĺžky front, počty handoverov, intervaly bez služby, čas obnovy, počet ISL skokov, prenosové bajty a energetické/terminálové obmedzenia sú ďalšie vysvetľujúce metriky.

Analýza musí rozlišovať príčinu `no-local-contact`, `ground-phy-error`, `ground-mac-contention`, `UT-not-logged-on`, `no-satellite-visibility`, `beam-handover`, `user-link-error`, `ISL-unavailable`, `feeder-unavailable`, `gateway-failure`, `queue-expiry`, `deadline-expiry`, `application-filter`. Ak simulator nedá presný drop reason, označiť ho ako **neurčený**; nevyvodzovať ho z neprítomnosti RX. Výsledky pri viacerých seedoch vykazovať po behoch a s intervalom neistoty; kontrola a variant musia používať párované dopravné vstupy. Náhodné seed nie je náhradou za viac dopravných geometrií a časových epoch orbít.

## 12. Verifikačné brány pred tvrdením o výsledku

1. **Zadanie a scenár:** každá výskumná otázka má scenár, kontrolu, hypotézu a explicitný packet path; implementácia zodpovedá schéme.
2. **Dopravná geografia:** SUMO bez neželaných teleportov/kolízií; zhodná zemepisná poloha auta, RSU a UT; dátum a súradnicový systém uložené.
3. **Orbitálna plausibilita:** platná epocha, zdroj a SHA-256 TLE/ephemeríd; elevácia a vzdialenosť na každom satelitnom hop-e; nemožné linky sa nevytvoria.
4. **Protokolová pravdivosť:** každý tok má pomenovaný zásobník; sérializácia CAM/DENM/CPM iba ak je skutočne implementovaná; UDP pilot sa volá syntetickým payloadom.
5. **Paketová cesta:** surové TX/RX na aplikácii, pozemnom MAC/PHY, UT, SAT, ISL, GW; identifikátor koncovej správy prežije proxy; zaznamenať počet vyslaní/retransmisií.
6. **Pozitívny a negatívny test:** aspoň jedno doručenie, riadené odstránenie jednej linky, očakávané zhoršenie iba príslušnej cesty, bez záporného oneskorenia.
7. **Reprodukovateľnosť:** commit simulátora/modulov, build profil, konfiguračný manifest, seed/run, vstupné súbory a kontrolné súčty, surové PCAP/traces, skripty na výpočet grafov.
8. **Interpretácia:** výsledok zo SNS-3 DVB profilu sa tak pomenuje; výsledok operátorského profilu označí všetky nenormované predpoklady a intervaly senzitivity.

## 13. Poradie ďalšej práce

**A. Opraviť základ experimentu:** prepojiť SUMO lokálne súradnice s geodetickou polohou UT/GW, zabezpečiť časovo platné orbitálne dáta a meranie viditeľnosti. Vybrať geografický región podľa dostupnosti dopravných dát, satelitnej služby a možnosti externej validácie. Zostaviť jeden experimentálny manifest pre scenár, seed a parametre.

**B. Zafixovať reálne služby:** pri každom operátorovi vybrať konkrétny terminál, plán/API a smer prenosu; zapísať veľkosť správy, kapacitný strop a komunikačný režim. Súčasný 300 B UDP tok ponechať iba ako diagnostiku. Zaviesť pripnutý ASN.1 codec pre CAM/DENM, testovať dekódovanie a doplniť BTP/GeoNetworking/DCC/OCB podľa rozhodovacej skúšky.

**C. Získať funkčný mobilný UT:** na minimálnom SNS-3 scenári izolovať attach/handover bez SUMO, potom vložiť jednu zladenú geodetickú trajektóriu, napokon celú dopravu. Neúspešné behy nepoužívať na výkonnostné závery.

**D. Postaviť a kalibrovať S0–S6:** vykonať lokálnu rádiovú kalibráciu a satelitnú servisnú kalibráciu na otvorených dátach alebo vlastných meraniach, potom validovať na oddelených dátach. Pre širokopásmové IP profily porovnávať aj rovnaký **podiel zaťaženia kapacity**; správové služby merať podľa ich natívnych API a limitov.

**E. Napísať závery presne podľa fidelity:** odlíšiť funkčný dôkaz paketovej integrácie, štatistickú sieťovú vlastnosť modelu a tvrdenie o konkrétnom komerčnom operátorovi. Prínos pre bezpečnosť dopravy tvrdiť až po spätnej väzbe do dopravného modelu alebo na úrovni presne definovanej včasnosti výstrahy.

## Priebežne používané zdroje

- [ETSI CAM Release 2 TS 103 900 V2.2.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.02.01_60/ts_103900v020201p.pdf), [DENM TS 103 831 V2.2.1](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.02.01_60/ts_103831v020201p.pdf), [CPM TS 103 324 V2.1.1](https://www.etsi.org/deliver/etsi_ts/103300_103399/103324/02.01.01_60/ts_103324v020101p.pdf), [infraštruktúrne služby TS 103 301 V2.2.2](https://www.etsi.org/deliver/etsi_ts/103300_103399/103301/02.02.02_60/ts_103301v020202p.pdf).
- [ETSI GeoNetworking](https://www.etsi.org/deliver/etsi_en/302600_302699/3026360401/01.03.01_60/en_3026360401v010301p.pdf), [BTP](https://www.etsi.org/deliver/etsi_en/302600_302699/3026360501/01.02.01_60/en_3026360501v010201p.pdf), [ITS-G5](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf), [bezpečnostný profil](https://www.etsi.org/deliver/etsi_ts/103000_103099/103097/01.04.01_60/ts_103097v010401p.pdf).
- [3GPP TS 38.300](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/19.02.00_60/ts_138300v190200p.pdf), [DVB-RCS2 EN 301 545-2](https://www.etsi.org/deliver/etsi_en/301500_301599/30154502/01.05.01_20/en_30154502v010501a.pdf), [SNS-3](https://github.com/sns3/sns3-satellite), [SUMO FCD](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html).
- [Starlink Technology](https://starlink.com/technology), [Iridium Network](https://www.iridium.com/network), [Globalstar Who We Are](https://www.globalstar.com/en-ap/about/who). Operátorské stránky dokazujú architektúru uvedenú na stránke, nie kompletný overiteľný rádiový protokol.

**Údržba:** Pri zmene verzie ETSI/3GPP alebo produktu operátora aktualizovať číslo vydania, dátum overenia, polia správy a konfiguračný manifest. Pri zmene kódu aktualizovať tabuľku „čo projekt implementuje“ a nikdy neprepisovať historické experimenty novým tvrdením.
