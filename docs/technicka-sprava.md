# Technická správa k simulátoru VANET/LEO

**Stav modelu:** 23. 11. 2026. **Runtime:** SUMO, Vanetza v26.06, ns-3.38 a SNS-3 3.38. Táto správa opisuje aktuálny pracovný simulátor v jednom projektovom priečinku, nie výsledky budúceho experimentu.

## 1. Účel a rozsah

Editor pripravuje dopravnú scénu s autami, cestami, budovami a cestnými jednotkami RSU. SUMO vypočíta pohyb áut. V jednom paketovom behu ns-3 modeluje pozemnú sieť ITS-G5; pri zapnutom satelitnom backhaule ten istý proces používa SNS-3 na prenos medzi RSU cez modelovú satelitnú vetvu. Vanetza kóduje a dekóduje CAM, DENM, GeoNetworking a BTP. Vlastný kód určuje, **kedy** správu vytvoriť, **ktorá RSU** ju smie odoslať ďalej a **komu** je určená. Knižnice vypočítajú priebeh a príjem paketu na nakonfigurovaných spojoch.

Satelitná vetva je generický DVB model SNS-3 s orbitálnymi a terminálovými vstupmi. Nie je to emulácia modemu ani prevádzkových pravidiel Starlinku, Iridia či Globalstaru. Úspech verifikácie potvrdzuje konzistenciu konkrétneho behu a stôp; úspešné doručenie sa posudzuje osobitne.

## 2. Inštalácia, spustenie a súbory scenára

Na Ubuntu 24.04 x86_64 klonovať GitHub projekt do `BP-Simulator/` a spustiť `python3 scripts/setup_single_folder.py`. Inštalátor overí pripnutý slovenský OSM súbor, pripraví veľké závislosti z vydania, zostaví Vanetza a ns-3/SNS-3, vykoná preflight a vytvorí ikonu. Aplikácia, vstupy a výsledky v `results/simulations/` zostávajú v tom istom projektovom priečinku. Git sleduje kód a dodané ukážky; lokálne zostavené závislosti a osobné dáta ignoruje.

Pripravené scenáre: `realna-d1-pozemna`, `realna-d1-satelit`, `navrh-koridor-pozemna`, `navrh-koridor-satelit`. Dvojice používajú rovnakú dopravu a rozdielnu komunikačnú vetvu. Dopravný dopyt je syntetický. Pri porovnaní treba zaznamenať verziu balíka, vstupný JSON, seed, číslo ns-3 behu a ID výsledku.

Terminálové rozhranie z koreňa projektu:

```bash
.venv/bin/python tools/simulator_cli.py preflight config/simulator-iridium.json
.venv/bin/python tools/simulator_cli.py run config/simulator-iridium.json results/simulations/moje-meranie-1
.venv/bin/python tools/simulator_cli.py verify results/simulations/moje-meranie-1
```

Každý beh potrebuje nové ID. Pri aktualizácii treba zavrieť okno, v tom istom priečinku vykonať `git pull --ff-only` a znovu spustiť `python3 scripts/setup_single_folder.py`. Staré výsledky sa neprepisujú. Manifest zaznamenáva hashe použitého zdroja, preto starší výsledok nemusí prejsť overením zmeneným kódom; pri vedeckej práci treba zachovať pôvodný commit.

## 3. Ovládanie editora

### Ľavý panel

| Prvok | Účinok |
| --- | --- |
| **Nový z reálnej mapy** | Založí scénu z pripnutého slovenského OSM výrezu pri zvolenom mieste. Importuje jazdné úseky a pôdorysy budov. |
| **Nový prázdny návrh** | Založí scénu s ručne kreslenými cestami. |
| **Uložený scenár**, **Načítať uložený** | Otvorí existujúci návrh. Pred zmenou scény uložiť rozpracované údaje. |
| **Názov nového scenára**, **Uložiť nový scenár** | Uloží kópiu aktuálneho návrhu pod novým ID. Pôvodný uložený scenár sa neprepisuje. |
| **Dĺžka simulácie** | Jeden časový interval pre SUMO, rádio, satelitnú vetvu aj replay; pozemný beh 2–120 s, satelitný 6–120 s. |
| **Smerovanie DENM** | Zdrojová a cieľová RSU a naplánované udalosti výstrahy. Udalosti možno nastaviť aj pri jednotlivom aute alebo na technickej stránke. |
| **Overiť aktuálny scenár** | Spustí vstupnú validáciu bez paketového behu; kontroluje napríklad trasy, adresované uzly, čas a orbitálne vstupy. |
| **Spustiť simuláciu** | Uloží vstupy nového behu, spustí SUMO a paketový backend, potom verifikáciu. |
| **Technický plán behu** | Presný plán z preflightu vrátane zvoleného backendu. |

### Pracovná mapa

Režim **Reálna mapa** používa OSM; režim **Prázdny svet** umožňuje kresliť vlastnú cestnú sieť. Šírka a výška určujú lokálny výrez v metroch. Súradnice X rastú na východ, Y na sever. Zmena miesta na glóbuse mení geografický stred, nie orientáciu lokálnych osí. Koliesko nad mapou približuje, pravé tlačidlo s ťahom posúva; `+`, `−` a **Zarámovať** menia pohľad.

Nástroj **Vybrať** otvorí parametre objektu. **Cesta**: klikmi vložiť začiatok, medzibody a koniec; **Dokončiť cestu** uloží geometriu, **Krok späť/dopredu** mení rozkreslené body, **Zrušiť** zahodí návrh. Uzly sú explicitné ID; spoločný uzol vytvára spojenie. Pri ručnej ceste možno meniť súradnicu koncového uzla a spolu s ňou sa presunú konce všetkých naviazaných úsekov. Medzibod mení iba tvar úseku. Súradnice OSM cesty sú v editore len na čítanie. **Auto** vloží vozidlo na použiteľný úsek. **RSU** vloží cestnú jednotku. **Budova** kreslí obdĺžnik iba v prázdnom svete; OSM budovy sa importujú z mapy.

**Náhodná doprava** určuje počet nových áut a cieľovú dĺžku ich jázd ako percento dostupného času. Generátor vytvorí syntetické trasy podľa cestného grafu; trieda cesty ovplyvňuje výber pri generovaní, samostatný rýchlostný limit je vstup SUMO. Tieto nastavenia nemenia už vygenerované autá. **Odhad výšky budov** prepína nízky/stredný/vysoký variant, ak OSM výška nie je známa.

**Parametre objektu** sa otvoria kliknutím na objekt alebo voľbou jeho ID v zozname. **Skupinová trasa** vyberá viac áut (aj `Shift` + klik), nastavuje spoločný cieľ alebo nové náhodné trasy; spoločný cieľ zachová rozostup 12 m. **Vrstvy mapy** samostatne zapínajú scenárové cesty, autá, RSU, miesto, orientačné pokrytie, pakety, fyzikálny stav, mriežku a vrstvy reálneho podkladu. Vypnutie vrstvy nemení simulačný vstup.

### Parametre jednotlivých objektov

| Objekt a záložka | Vstupy a význam |
| --- | --- |
| **Cesta** | ID, OSM názov/ID, uzly, body X/Y, dĺžka, smer jazdy, počet pruhov v každom povolenom smere, rýchlostný limit. Pri jednosmerke je iba smer začiatok → koniec. Trieda ručnej cesty slúži generátoru áut. SUMO dostane smerové hrany, pruhy, rýchlosť a sieťové spojenia. |
| **Auto / Vstupy SUMO** | ID a typ `passenger_<ID>`, maximálna a počiatočná rýchlosť, automatická alebo vlastná rýchlosť pri štarte, poloha na prvom úseku, smer a poradie smerových hrán trasy, cieľová poloha. Model auta obsahuje zrýchlenie, brzdenie, `sigma` (náhodnosť vodiča), dĺžku, šírku, minimálny odstup a faktor rýchlosti. **Predvolené** zruší individuálne odchýlky. Odchod je v aktuálnom zjednotenom behu v čase 0, pruh vyberá SUMO ako `best`. |
| **Auto / Ostatné vstupy** | Politika ITS-G5: všetky uzly, len autá alebo vypnuté; referenčné auto CAM je voľba na sledovanie výsledku, nie podmienka vysielania ostatných áut. Individuálne rádio: výkon, šumové číslo, TX/RX zisk, výška antény; **Predvolené rádio** obnoví spoločný profil. Tu možno naplánovať DENM. |
| **RSU / Uzol a ns-3** | ID, poloha X/Y, zapnutie pozemného ITS-G5, individuálny výkon, šumové číslo a zisky, výška antény vlastná alebo vypočítaná nad strechou; **Predvolené rádio** obnoví spoločný profil. |
| **RSU / SNS-3 a správy** | Zapnutie satelitného backhaulu, zdrojová alebo cieľová RSU. Terminál vyžaduje zapnuté pozemné rádio. Pri Starlinku možno nastaviť náklon a azimut modelovej montáže. |
| **Budova / Pôdorys** | Pri ručnej budove stred, šírka a dĺžka; pri OSM budove jednotlivé body X/Y a zdroj. |
| **Budova / Výška a model** | Nízka, stredná a vysoká výška; účinný variant je spoločný pre prostredie. Geometria a výška ovplyvňujú tienenie pozemného kanála a satelitnú kontrolu výhľadu. |

Ručne upravená trasa auta sa pred uložením kontroluje: úseky musia existovať, naväzovať cez rovnaký uzol, rešpektovať smer a zakázané odbočenia; priamy obrat na opačnú hranu toho istého úseku sa odmieta. **Odstrániť** vymaže vybraný objekt zo scenára.

### Glóbus a orbitálny náhľad

Kliknutie na glóbus vyberá miesto simulácie. **Konštelácia** prepína pripnutý orbitálny profil. **Celá Zem** a **K miestu pokusu** menia pohľad. **Orbitálny archív** určuje dátový snapshot; **Začiatok simulácie UTC** určuje spoločný časový pôvod. **Ukážka 10 s**, posuvník a prepínače satelitov či obálky slúžia náhľadu. Grafický glóbus môže zobrazovať celý katalóg; paketový beh používa len vybranú topológiu. Pohľad **Obloha nad miestom** a legenda rozlišujú satelity nad maskou, fyzikálnych kandidátov a paketový podgraf. Náhľad ani orientačná obálka nepotvrdzujú skutočné rádiové doručenie.

### Prehrávanie

Po behu sa použije jeho ID v poli **ID behu** a tlačidlo **Otvoriť**. Server načíta len beh, ktorého vstupy, zdroje a surové stopy prešli verifikáciou. **▶/pauza** a časový posuvník menia zobrazený okamih; v zozname udalostí možno vybrať paket a filtrovať spoj. Detail ukazuje etapy prenosu, surové bajty a dekódované polia. Pri ASN.1 UPER nemusia hranice polí zodpovedať celým bajtom. **Overený súhrn behu** obsahuje počty z raw stôp. **Fyzikálna cesta vybraného uzla** zobrazuje oddelene výhľad, RF podmienky a paketové doručenie; JSON/CSV export uloží audit. Geometricky možná cesta nie je automaticky prijatý paket.

## 4. Stránka „Technické parametre“

Odkaz vpravo hore otvára technickú stránku nad editorom. **Aktuálny scenár** zobrazí rozpracované hodnoty, **Uložený scenár** načíta uloženú verziu, **Stiahnuť vstupy JSON** exportuje scenár, svet a dopravu. Označenie **Tu** znamená upraviteľnú hodnotu na tejto stránke; **Simulátor** nastavenie v mapovom editore; **Zdroj** vstup bez editácie v danom riadku; **Odvodené** vypočítanú hodnotu; **Pevné** vlastnosť aktuálneho modelu; **Predpoklad** výskumný parameter. Zmena hodnoty sa prenesie do otvoreného návrhu; ďalší beh treba uložiť pod novým ID.

| Skupina | Všetky podstatné parametre a účinok |
| --- | --- |
| **Scenár a spoločný čas** | Dĺžka, UTC začiatok, počet vzoriek, krok 0,1 s, seed, číslo ns-3 run, režim a ID overeného behu. Seed určuje náhodný stav použitých častí výpočtu; pri porovnaní držať seed aj `ns3_run` rovnaké. |
| **SUMO / Mapa a pohyb** | Zdroj mapy, rozmery, stred WGS84, počty áut/RSU/ciest/smerových hrán, jednosmerky, maximálne pruhy, zakázané odbočenia, rozsah rýchlostí, budovy, variant výšok, pôvod dopravy a parametre generátora. OSM import je zdroj geometrie; `netconvert` z neho vytvorí dopravnú sieť. |
| **SUMO / Vozidlá a cesty** | Krok SUMO, dopravný seed, vypnutá normalizácia súradníc, výsledná sieť, spoločný model auta (zrýchlenie, brzdenie, `sigma`, rozmery, odstup, faktor rýchlosti). Katalóg áut ukazuje individuálne výnimky, odchod, štart/cieľ a celú trasu. Katalóg ciest ukazuje smer, uzly, pruhy a rýchlosť zvlášť pre každý smer. `road.net.xml` môže čísla mierne zaokrúhliť; pre finálny výklad skontrolovať výsledný súbor. |
| **ns-3 / ITS-G5** | 802.11p OCB, 10 MHz kanál 172–184, PHY rýchlosť 3/6/12/24 Mb/s, frekvencia, Friis alebo mestský model, výkon TX, šumové číslo RX, anténne zisky, tieňovanie, výška antény auta a minimálna/strešná výška RSU, časový posun uzla. Katalógy obsahujú rádiový profil každej RSU a budovy s pôdorysom a tromi výškami. Pri prítomných budovách sa účinne použije model `urban_osm_building`. |
| **Aplikačná konfigurácia** | Referenčné auto, individuálna politika a rádiový profil každého auta, politika RSU, súradnice RSU, DCC prahy CBR a intervaly, spúšťače CAM (poloha/rýchlosť/smer), interval nízkofrekvenčnej časti, maximum intervalu a periodické opakovania. DENM má zdrojové auto, operáciu `new/update/cancel`, čas, action sequence, platnosť, geografický polomer a opakovanie. Typ udalosti je pevne `trafficCondition/trafficJam`; geografický broadcast má najviac tri skoky. |
| **SNS-3 / Konštelácia a paketová vetva** | Konštelácia, orbitálny archív, vybrané katalógové ID a ISL spojenia, zdrojová/cieľová RSU, brána, uplink/downlink frekvencia, maska elevácie, výkon terminálu a modelový zisk lúča, čas žiadosti o prepnutie a aplikácie profilu, fronty a obsluha RSU, kapacity a fronty ISL. Dávkovanie aplikačných správ je v aktuálnom runneri vypnuté. |
| **SNS-3 / Terminál a fyzikálne podmienky** | Predvolený alebo vlastný profil; zorný uhol a montáž, nosná, kompenzácia a tolerancia Dopplera, zenitový kužeľ, rýchlosť smerovania a prijímací uhol. Ďalej výšky budov, teploty prijímačov, feeder frekvencia, front družice, riadiaci slot, šírenie ISL, modulácia, ARQ a ACM. Diagnostický `link_budget` sa zobrazuje osobitne a **neovláda** natívny paketový kanál. |
| **Hranice modelu** | Zobrazuje použitý backend a nemodelované veci: operátorské modemy, automatické rozpoznanie DENM a dopravnú reakciu auta na prijatú výstrahu. |

Nie každý údaj na technickej stránke je samostatný voľný vstup: niektoré hodnoty sú odvodené, pevné alebo aktivované len v satelitnom režime. Pre presné porovnanie je smerodajný JSON a manifest **konkrétneho behu**, nie aktuálne otvorený editor po ďalšej zmene.

## 5. Výpočtový tok a rozhodnutia

1. Editor uloží `scenario.json` (čas, rádio, DENM, satelit a politiky), `world.json` (súradnice, cesty, budovy, RSU) a `demand.json` (autá a trasy). Validátor odmietne nesúvislé trasy, neprípustné časy a neplatnú konfiguráciu siete.
2. Z ciest vzniknú smerové hrany a spojenia SUMO; zakázané odbočenia sa premietnu do spojení. `netconvert` vytvorí sieť, SUMO simuluje pohyb a výstup sa vzorkuje každých 0,1 s. Keď auto dokončí krátku trasu pred koncom komunikačného okna, posledná poloha sa drží do konca. To je explicitný modelový predpoklad, nie skutočné správanie premávky.
3. Vlastný C++ kód pri každej vzorke auta vyhodnotí CAM. Prvý CAM sa odošle; ďalší vznikne pri prekročení nastavenej zmeny polohy, rýchlosti alebo smeru a minimálneho intervalu. Pri nečinnosti platí periodický interval, najviac `cam_tgen_max_ms`. DCC meria obsadenosť kanála za 1 s a podľa prahov CBR predĺži minimum na stredný alebo vysoký interval. Rozhodnutia sú v `dcc_decisions.csv`. Vysielať smie každé auto s povoleným rádiom; referenčné auto iba určuje sledovaný príklad.
4. Naplánovaná udalosť vytvorí DENM s action ID, časom detekcie, referenčným časom, platnosťou a geografickou oblasťou. Vanetza ho prenesie ako GeoNetworking geografický broadcast cez BTP/ITS-G5; `radius_m` a najviac tri skoky obmedzujú šírenie. Opakovanie, aktualizácia a zrušenie sa riadia plánom scenára. Prijímač odmietne vlastnú, expirovanú, neznámu ukončovaciu, duplicitnú alebo staršiu verziu. Prijatie DENM samo nemení trasu ani rýchlosť auta.
5. V integrovanom režime sa iba prijatý a dekódovaný DENM na určenej zdrojovej RSU, od auta s povolenou komunikáciou do RSU, odošle cez lokálny IP/UDP spoj terminálu. Terminál ho pošle cez SNS-3 k bráne. Brána po prijatí pošle rovnaké DENM bajty aktívnym cieľovým RSU okrem pôvodnej; ak je určená cieľová RSU, iba jej. Cieľová RSU po príjme cez terminál znovu vysiela DENM na pozemnom ITS-G5. Ak paket nie je na ktorejkoľvek linke prijatý, následná etapa nevznikne. Poloha satelitu sama nevytvára doručenie.

ns-3 nastavuje uzly, Wi-Fi/OCB, kanál, mobilitu, zásobníky IPv4/UDP a PHY/MAC udalosti. SNS-3 vytvára satelitnú topológiu a modeluje generickú DVB vetvu. IP adresy RSU terminálov a brány prideľuje ns-3 podľa topológie vytvorenej naším kódom; autá na ITS-G5 komunikujú cez GeoNetworking/BTP a nemajú pre CAM/DENM vlastnú IP adresu. Rozhodovanie, či sa výstraha prepošle, je v našom kóde; samotný paketový prenos, oneskorenie a strata sú výsledkom nakonfigurovaných modelov a ich behov.

### Ďalší experimentálny tok CAM

Keď je integrovaný beh bez režimu DENM, RSU môže z **prvého skutočne dekódovaného CAM** pre daný pár station ID/generationDeltaTime vytvoriť report `ICB1`. Duplicitné prijatia inými RSU sa odmietnu. Report prejde cez obmedzený front k bráne, jej odpoveď `GRA1` sa vracia k zdrojovej RSU a tá môže vyslať pozemné potvrdenie `I2V1`. Toto je vlastný výskumný aplikačný protokol, nie formát operátora. Je oddelený od prenosu DENM medzi RSU; oba režimy sa nesmú zamieňať pri interpretácii výsledkov.

## 6. Obsah paketov

| Správa | Formát a význam |
| --- | --- |
| **CAM** | ETSI ITS CAM kódovaný ASN.1 UPER; identifikácia stanice, generationDeltaTime, poloha, výška, rýchlosť, smer, rozmery auta a vybrané kontajnery. Vanetza ho vkladá do BTP-B portu CAM a GeoNetworking SHB s limitom jeden skok, potom do OCB rámca. |
| **DENM** | ETSI ITS DENM ASN.1 UPER s action ID (station ID + sequence), časmi, validity, geografickým polomerom, príčinou `trafficCondition/trafficJam`, prípadnou aktualizáciou/ukončením. BTP-B port DENM, GeoNetworking GBC najviac tri skoky. V satelitnej vetve sa tie isté aplikačné DENM bajty prenesú v UDP; nie je to pôvodný pozemný rámec. |
| **ICB1** | `ICB1` (4 B), verzia (1 B), ID reportu (8 B), čas vzniku v µs (8 B), rezervovaný bajt, dĺžka CAM (1 B), SHA-256 CAM (32 B), CAM UPER (41 alebo 43 B v aktuálnom profile). Celkom 55 + dĺžka CAM. |
| **GRA1** | `GRA1` (4 B), verzia (1 B), ID reportu (8 B), SHA-256 celého ICB1 (32 B), rezervovaný bajt. Celkom 46 B. |
| **I2V1** | `I2V1` (4 B), verzia (1 B), ID reportu (8 B), station ID (4 B), SHA-256 ICB1 (32 B), rezervovaný bajt. Celkom 50 B. |

Zoznam v replay ukazuje rozličné **etapy** tej istej správy: vytvorenie UPER, odoslanie GN/BTP, PHY prenos, príjem, dekódovanie, IP/UDP spoj, prípadne bránu a vzdialený pozemný príjem. Počet vytvorených správ sa nesmie vydávať za počet doručených správ. `ICB1`, `GRA1` a `I2V1` sú definované v `src/vanet-leo-network.cc`; CAM a DENM v oboch aktuálnych C++ enginoch.

## 7. Výstupy a ich čítanie

Každý výsledok leží v `results/simulations/<ID>/`. `inputs/` obsahuje presné `scenario.json`, `world.json`, `demand.json`, odvodený `ground.json`, pri satelitnom behu orbitálny referenčný súbor a prípadné prekážky. Pozemný beh má `ground/scenario/sumo/` (`road.*.xml`, `summary.xml`, `fcd.xml`), v `ground/scenario/` sú `waypoints.csv`, `cam.csv`, `dcc_decisions.csv`, `rx.csv`, `phy_state.csv`, `phy_drop.csv`, `trace.csv` a `*.pcap`; `ground/run-manifest.json` viaže natívny podbeh. Integrovaný beh má `native/baseline/`: `waypoints.csv`, `events.csv`, `trace.csv`, `delivery.csv`, `selection.csv`, `queue.csv`, `satellite-ip-trace.csv`, `satellite_rf.csv`, `satellite_visibility_drop.csv`, `PacketTrace.log`, `*.pcap`, vstupné profily rádií a DENM, plus `native/editor-manifest.json`. Presný zoznam sa môže líšiť podľa režimu; úplný inventár je v `run-manifest.json`.

`physical-timeline.json` je odvodená časová kontrola výhľadu, `run-manifest.json` viaže vstupy, aktívne zdroje a raw súbory cez SHA-256. Replay vzniká čítaním a verifikáciou týchto súborov; grafické body sú interpretáciou overených stôp. Pozemné `CAM_UPER_RX` alebo `DENM_UPER_RX` dokazujú aplikačný príjem u konkrétneho uzla. `GATEWAY_DENM_RX` dokazuje príjem v bráne, **nie** ešte v cieľovom aute. RF zamietnutie, chýbajúca viditeľnosť, plný front, PHY strata a aplikačné odmietnutie sú odlišné príčiny.

Pre výskumné porovnanie použiť rovnakú cestnú sieť, vozidlá, RSU, dĺžku, seed a ns-3 run; meniť len vopred určený faktor. Uložiť ID oboch behov a citovať manifest, surové stopy a presne definovanú metriku (napríklad podiel cieľových áut s `DENM_UPER_RX` do stanoveného času). Simulátor zatiaľ nevytvára hotové štatistické vyhodnotenie ani intervaly spoľahlivosti; tie treba spracovať nad overenými behmi.

## 8. Hranice presnosti

OSM nemusí obsahovať kompletnú dopravnú topológiu, pruhové spojenia ani výšky. Import a `netconvert` môžu zmeniť interpretáciu križovatky; preto treba pri výskumnom výreze skontrolovať reálnu mapu, smerové hrany a `road.net.xml`. Výšky bez OSM údaja sú odhady. Náhodná doprava nie je meraná premávka. Model vozidla neobsahuje reakciu na prijatý DENM. DCC a ITS správy nie sú úplná konformančná implementácia všetkých ETSI profilov; bezpečnostné podpisy nie sú implementované. Satelitný fyzikálny audit používa deklarované predpoklady a generický SNS-3 kanál, nie reálnu dostupnosť služby. V súčasnej integrovanej topológii sú terminály na RSU; auto nemá priamy satelitný terminál. Automatický výber topológie v editore typicky vyberie jednu družicu použiteľnú pre RSU a bránu počas celého okna; viacdružicová/ISL topológia vyžaduje explicitný vstup. Grafický katalóg nie je totožný s inštanciami paketového behu.

## 9. Orientácia v implementácii

`tools/simulator_server.py` poskytuje editorové API a replay. `tools/simulator_cli.py` validuje vstupy, spúšťa beh a zapisuje finálny manifest. `tools/simulator_ground_runner.py` a `tools/simulator_satellite_runner.py` pripravujú SUMO výstup a argumenty natívnych enginov. `src/vanet-ground-network.cc` a `src/vanet-leo-network.cc` obsahujú vlastnú aplikačnú logiku a sieťovú konfiguráciu. `tools/simulator_ground_verifier.py` a `tools/simulator_satellite_verifier.py` overujú raw stopy. `viewer/simulator.html`, `simulator.js`, `technical-parameters.js` a `packet-inspector.js` tvoria editor, technickú stránku a prehrávač. `vendor/ns-3.38-ocb-eval` je jediný aktívny ns-3/SNS-3 runtime. `scripts/launch_local.py` otvára tento projekt z ikony na ploche.
