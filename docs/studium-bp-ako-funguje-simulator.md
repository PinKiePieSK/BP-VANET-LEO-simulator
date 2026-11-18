# Ako funguje aktuálny simulátor bakalárskej práce

**Stav k 5. 11. 2026.** Tento sprievodca vysvetľuje aktuálny editor U9 a aktívnu vetvu CAM/DENM v `ns-3.38/SNS-3 3.38`. Je určený na čítanie aj bez nedávnej skúsenosti s programovaním. Presný katalóg každého vstupného poľa je v [sprievodnom katalógu](studium-bp-katalog-vstupov.md). Predchádzajúci [dvojdňový úvod](studium-bp-za-dva-dni.md) stačí na prvú orientáciu.

## 1. Čo sa v práci skúma

**VANET** je sieť, v ktorej vozidlá komunikujú medzi sebou (**V2V**) a s cestnou infraštruktúrou (**V2I/I2V**). Lokálna správa sa prenáša cestným rádiom. **LEO** je nízka obežná dráha; satelitný úsek môže preniesť informáciu medzi vzdialenými oblasťami cez satelitné terminály pri cestných jednotkách **RSU**. Aktívny editor neumožňuje satelitný terminál v aute. Pozri [oficiálne zadanie](zadanie-bp.md) a jeho technickú interpretáciu v [analýze komunikácie](hlbkova-analyza-komunikacie.md).

Model má dve hlavné vetvy:

```text
V2V: auto A -- CAM alebo DENM / GN-BTP / 802.11p OCB --> auto B

V2I: auto A -- tá istá lokálna rádiová vetva --> zdrojová RSU
                                                 |
                                                 | vlastná aplikačná politika
                                                 v
                                         LAN/IP/UDP -> UT -> LEO -> GW
                                                                   |
                                                                   v
                                                         vzdialený UT/RSU
                                                                   |
                                                 GN-BTP / OCB -> vzdialené autá
```

Nie každá CAM ide cez satelit. V aktuálnom režime CAM/DENM sa cez satelitný most prenáša **prijatá DENM**, keď platí politika zdrojovej RSU a vznikne paketová cesta. Na vzdialenej RSU sa DENM znovu vydá do lokálnej oblasti. Historické režimy v tom istom C++ súbore vytvárali zo skutočne prijatej CAM vlastný report `ICB1` a odpoveď `GRA1/I2V1`; aktuálny runner zapína `--cam_denm_mode=1`. [Kód voľby režimu](../tools/u9_native_editor.py), [aplikačná vetva C++](../src/u9-full-integration-per-rsu.cc), [overenie aktívnych typov](../tools/u9_check_cam_denm.py).

## 2. Najskôr päť základov kódu

V tomto projekte `scenario`, `world` a `demand` sú **slovníky JSON**: názov poľa je kľúč, za ním je hodnota. Napríklad `scenario['seed']` znamená „zober hodnotu poľa `seed` zo scenára“. Pole `cars` je zoznam; `for car in cars` prejde autá po jednom. `if satellite_enabled:` vykoná nasledujúci blok len pri zapnutom satelitnom režime. `raise ValueError(...)` zastaví prípravu pre neplatný vstup.

V C++ je `Station` objekt jednej ITS stanice: drží jej rádio, polohu a stav prijatých správ. `device_->Send(...)` odovzdá bajty rádiovému zariadeniu ns-3. `SetReceiveCallback(...)` povie ns-3, ktorú našu funkciu zavolať pri prijatí. `Simulator::Schedule(...)` vloží budúcu udalosť do kalendára simulácie; `Simulator::Run()` udalosti vykonáva v časovom poradí. **Naplánovanie nie je doručenie.** Doručenie sa dá tvrdiť až po príjmovom callbacku a surovej stope. [Udalosti ns-3 3.38](https://www.nsnam.org/docs/release/3.38/manual/html/events.html).

Príklad z [predletovej kontroly](../tools/bp_u9.py):

```python
if s['satellite_enabled']:
    need(duration >= 6, 'Satelitný beh potrebuje aspoň 6 s')
```

Číta sa: „Ak je satelit zapnutý, skontroluj minimálnu dĺžku; pri neúspechu beh ešte pred spustením odmietni.“ Tento riadok **nevysiela paket**.

## 3. Na čom sú založené nástroje a čo im pridáva náš kód

| Vrstva | Čo dodáva nástroj | Čo sme napísali my | Kde začať čítať |
| --- | --- | --- | --- |
| **SUMO** | Mikroskopickú premávku: každé auto má trasu, jazdí po sieti a reaguje na autá pred sebou, pruhy a križovatky v diskrétnych krokoch. | Editor ciest a áut, prevod JSON na SUMO XML, pravidlá platnosti trás, spustenie a kontrolu FCD. Explicitne nenastavujeme `carFollowModel`, takže platí predvolený model SUMO. | [`u9_editable_scenario.py`](../tools/u9_editable_scenario.py), [oficiálny opis SUMO](https://sumo.dlr.de/docs/SUMO_at_a_Glance.html), [car following](https://sumo.dlr.de/docs/Car-Following-Models.html). |
| **Vanetza** | Implementáciu častí európskeho ITS zásobníka, najmä GeoNetworking, BTP a ASN.1 kódovanie/čítanie CAM a DENM. | Vyplnenie konkrétnych polí CAM/DENM, kedy správu vytvoriť, kam ju lokálne poslať, ktoré prijatie uznať, čo prepojiť so satelitom. | [`Station` v integrovanom engine](../src/u9-full-integration-per-rsu.cc), [Vanetza](https://github.com/riebl/vanetza). |
| **ns-3.38** | Diskrétny kalendár sieťových udalostí, uzly a zariadenia, 802.11p OCB MAC/PHY, rádiový kanál, IP/UDP, LAN a stopy. | Prepojenie Vanetza s `NetDevice`, rozmiestnenie podľa SUMO, voľbu modelu kanála a parametrov, aplikačné callbacky a scenárové filtre. | [`u9-ground-cam-dcc.cc`](../src/u9-ground-cam-dcc.cc), [`u9-full-integration-per-rsu.cc`](../src/u9-full-integration-per-rsu.cc), [ns-3](https://www.nsnam.org/about/what-is-ns-3/), [WAVE/OCB](https://www.nsnam.org/docs/release/3.35/models/html/wave.html). |
| **SNS-3 3.38** | Satelitné uzly UT/SAT/GW, generický DVB user/feeder PHY/MAC, fronty, paketovú stopu a voliteľné modelové ISL. | Výber dráh a topológie, tvorbu vstupov pre SNS-3, výskumný filter user-link podmienok, nastavenie trás, politiky RSU a kontrolu surových paketov. | [`u9_native_editor.py`](../tools/u9_native_editor.py), [`simulator_satellite_inputs.py`](../tools/simulator_satellite_inputs.py), [SNS-3](https://github.com/sns3/sns3-satellite). |

SUMO **nesimuluje rádio**. Vanetza **neurčuje pohyb vozidiel**. ns-3/SNS-3 **nepozná význam „dopravná zápcha“**, kým ho nevytvorí naša aplikácia. Prehliadač **nie je fyzikálny simulátor**: kreslí vstup a prehráva overené stopy.

## 4. Presný tok od editora po výsledok

1. **Editor** drží tri objekty: `scenario` (čo sa má skúmať), `world` (cesty, RSU, georeferencia, dopravné nastavenia) a `demand` (autá a trasy). Zobrazenie technických parametrov mení tie isté objekty cez [`technical-parameters-bridge.js`](../viewer/technical-parameters-bridge.js). Tlačidlá, mapa a replay sú vo [`viewer/simulator.js`](../viewer/simulator.js).
2. **Kontrola pred behom** cez [`bp_u9.preflight`](../tools/bp_u9.py) overí schému verzie 7, každé auto a RSU, jednotky, čas, technológie, rádiové voľby, DENM životný cyklus, prípadný orbitálny archív a politiku terminálov. Pozemný `world.network_execution='schema_only'` je označenie dopravného podkladu; skutočný sieťový beh spúšťa až `bp_u9.run`.
3. **Uloženie** cez [`u9_editor_api.save`](../tools/u9_editor_api.py) vytvorí `data/inputs/user/<id>/world.json`, `demand.json` a `config/scenarios/<id>.json`. Server používa lokálne HTTP endpointy [`u9_server.py`](../tools/u9_server.py).
4. **SUMO príprava**: [`u9_editable_scenario.make_inputs`](../tools/u9_editable_scenario.py) vytvorí `road.nod.xml`, `road.edg.xml`, `vehicles.rou.xml` a RSU body. `netconvert` vyrobí dopravnú sieť `road.net.xml`; `sumo` po kroku 0,1 s vyrobí `fcd.xml` s polohou, rýchlosťou, smerom, zrýchlením a signálmi. [Význam FCD](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html). Vozidlo, ktoré dôjde do cieľa pred koncom komunikačného okna, sa v tomto scenári zastaví a zostane prítomné, aby jeho rádio nezmizlo.
5. **Prevod polôh**: [`u9_prepare_cam.prepare`](../tools/u9_prepare_cam.py) zoberie FCD a vytvorí `waypoints.csv` každých 100 ms. Každý riadok nesie lokálne metre, WGS84, čas, rýchlosť, smer, zrýchlenie, rozmery auta a odvodené hodnoty pre CAM. Zatiaľ je to **vstup do sieťového behu**, nie vyslaná CAM.
6. **Sieť**: pozemný scenár spustí [`u9_run_ground.py`](../tools/u9_run_ground.py) a [`u9-ground-cam-dcc.cc`](../src/u9-ground-cam-dcc.cc). Satelitný scenár spustí [`u9_native_editor.py`](../tools/u9_native_editor.py) a [`u9-full-integration-per-rsu.cc`](../src/u9-full-integration-per-rsu.cc) v jednom procese ns-3/SNS-3. Všetky aktívne autá a terminály majú polohu už pri simulačnom `t=0`.
7. **Overenie**: [`u9_check_ground.py`](../tools/u9_check_ground.py) alebo [`u9_check_cam_denm.py`](../tools/u9_check_cam_denm.py) kontrolujú bajty, čas, PCAP a pri satelite natívnu `PacketTrace.log`; výsledok sa uloží s manifestom hashov. [`u9_editor_api.replay`](../tools/u9_editor_api.py) potom pripraví údaje pre prehliadač. Replay je čítanie uloženého behu, nie jeho pokračovanie.

Editorové tlačidlo „Spusti“ najprv uloží zmenený scenár, potom cez [`u9_server.py`](../tools/u9_server.py) spustí pracovníka `bp_u9.py run`; výsledok je v `results/simulations/<run_id>/`. Výsledkový adresár sa nesmie prepísať. Náhľad konštelácie a glóbus ukazujú kandidátov; sieťový výsledok vzniká až v natívnom behu.

## 5. Súradnice, 3D priestor a význam „dostupnosti“

Editorová pracovná mapa má lokálne `x_m, y_m` v metroch: **+x východ, +y sever**. `georeference` hovorí, ktorému bodu lokálnej mapy (`anchor_x_m, anchor_y_m`) zodpovedá WGS84 zemepisná šírka, dĺžka a výška. Príklad: pri kotve `(2000, 2000)` je RSU `(2100, 2000)` zhruba 100 m východne od zvoleného WGS84 bodu. Presný prevod lokálny ENU → WGS84 robí [`simulator_coordinates.py`](../tools/simulator_coordinates.py); opačný prevod importovaných OSM ciest je v [`u9_osm_road_graph.py`](../tools/u9_osm_road_graph.py). Obrazovka prevracia os Y iba kvôli kresleniu; uložená os Y stále smeruje na sever.

SUMO počíta pohyb v **lokálnej 2D cestnej sieti**. FCD `x/y` sú výsledné pozície auta v SUMO, nie nezmenené súradnice kliknutia v editore. Pri reálnej OSM mape `netconvert` upraví geometriu pruhov pri križovatkách; náš kód preto premieta kliknutú počiatočnú/cieľovú polohu na skutočný SUMO pruh. `u9_prepare_cam` počíta WGS84 pri **pevnom lokálnom ENU up=0**. To znamená, že CAM výška je odvodená z kotvy a tangenciálnej geometrie, **nie meraná nadmorská výška vozovky**. V novom [audite parametrov](experiments/audit-parametrov-2026-11-04.md) sa pri CAM/DENM netvrdí neexistujúca presnosť GNSS; confidence je `unavailable`.

Satelitné dráhy pochádzajú z pripnutého **OMM/GP archívu**; [`simulator_orbits.py`](../tools/simulator_orbits.py) ich šíri pomocou SGP4 a transformuje TEME → zemský ITRS/ECEF v konkrétnom UTC čase. [CelesTrak vysvetľuje OMM/GP formáty](https://celestrak.org/NORAD/documentation/gp-data-formats.php). **Elevácia** je uhol družice nad miestnym horizontom pozorovateľa. **Maska** stanoví minimálnu eleváciu. Pre kandidáta sa používa maximum scenárovej masky a publikovaného rozsahu daného terminálového profilu. [`u9_time_visibility.py`](../tools/u9_time_visibility.py) počíta v čase kandidátov; [`u9_physical_coverage.py`](../tools/u9_physical_coverage.py) odlišuje horizont, terminálovú obálku a neznámy aktívny lúč.

Rozlišuj päť tvrdení v tomto poradí: **(1) dráha je v archíve; (2) družica je nad horizontom; (3) vyhovuje maske a zornému poľu; (4) natívny model umožní prenos; (5) aplikácia skutočne prijme správu.** Krok 2 alebo 3 nikdy automaticky nedokazuje krok 5. Neoverený aktívny lúč, modem, reálna brána a prevádzka operátora bránia prekladu kroku 5 v modeli na komerčnú dostupnosť. Súčasný automatický výber pre natívny beh hľadá **jednu** družicu použiteľnú pre všetky aktívne RSU aj modelovú GW počas celého okna; explicitná viacdružicová topológia je samostatný režim. [Výber topológie](../tools/u9_native_editor.py).

## 6. Kto rozhoduje o vyslaní CAM

1. **SUMO** dá polohu, rýchlosť, smer, zrýchlenie a signály. [`u9_prepare_cam.py`](../tools/u9_prepare_cam.py) ich prevedie do škálovaných jednotiek ETSI (`latitude_e7`, `speed_cmps`, `heading_decideg`, atď.). Rozmery auta pochádzajú z `world.simulation.vehicle_model`.
2. **Náš C++ `Station::check`** sa plánuje pri každej 100 ms vzorke. Pozrie zmenu polohy (>4 m), rýchlosti (>0,5 m/s), smeru (>4°), čas od poslednej CAM a obsadenosť kanála CBR za poslednú sekundu. Pri zapnutom DCC nastaví scenárový minimálny interval 100/250/500 ms podľa prahov CBR. Ide o **výskumnú politiku**, nie potvrdenú úplnú ETSI DCC konformitu. [Integrovaný engine](../src/u9-full-integration-per-rsu.cc), [predvolené prahy](../config/u2-ground-one-rsu.json).
3. Ak politika dovolí odoslanie, **náš `make_cam`** vyplní ASN.1 polia, Vanetza ich zakóduje do UPER bajtov. **Vanetza router** pripraví BTP-B/GeoNetworking **single-hop broadcast** s portom CAM 2001. **Náš adaptér** odovzdá vzniknuté bajty `ns3::WifiNetDevice::Send`.
4. **ns-3** rozhoduje o prístupe k rádiovému médiu, trvaní PHY prenosu, kolíziách a príjme podľa zvoleného rádiového kanála. Pri príjme sa zavolá náš callback, ktorý odovzdá GN bajty Vanetze; tá vráti BTP payload a náš kód dekóduje/overí CAM. CAM sa v tejto vetve **nepreposiela automaticky cez satelit**.

Prečítaj v tomto poradí [`u9_prepare_cam.prepare`](../tools/u9_prepare_cam.py), `Station::check`, `make_cam`, `Station::send_cam`, `Station::request` a `Station::indicate` v [C++ engine](../src/u9-full-integration-per-rsu.cc). Pri každej funkcii si polož tri otázky: **čo je vstup, čo je rozhodnutie, čo je výstup?**

## 7. Kto rozhoduje o DENM a jej preposlaní

V editore sa volí udalosť `source_id`, `at_s`, `sequence`, `operation`, `validity_s`, `radius_m`, `repetition_ms`. **Nejde o automatické rozpoznanie zápchy z dopravy SUMO.** V aktívnej vetve náš `make_denm` vytvorí modelovú udalosť `trafficCondition/trafficJam`, odvodí polohu z auta, nastaví `actionId`, časy, platnosť a pri `cancel` ukončenie. Vanetza DENM zakóduje. `Station::emit_denm` vytvorí GeoBroadcast do kruhu `radius_m`, BTP port 2002, maximálne 3 skoky; Vanetza rieši príslušnú GN logiku, ns-3 fyzický rádiový prenos. **Opakovanie** podľa `repetition_ms` plánuje náš kód pomocou `Simulator::Schedule`. [Funkcie DENM](../src/u9-full-integration-per-rsu.cc), [predletová kontrola životného cyklu](../tools/bp_u9.py), [ETSI DENM](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.03.01_60/ts_103831v020301p.pdf).

Prijímač DENM skontroluje identitu akcie, čas, platnosť a duplicitu. **Naša zdrojová RSU** odošle prijaté presné UPER bajty na LAN iba ak je vybraná ako `rsu_id`, má zapnutý `satellite_backhaul`, správa ešte nebola odoslaná a patrí k pôvodnej akcii. **Naše UT callbacky** po LAN príjme odošlú nové IP/UDP datagramy do SNS-3. **SNS-3** potom simuluje satelitný user/feeder prenos a prípadné ISL. **Naša gateway aplikácia** prijatý obsah pošle do vybranej vzdialenej RSU (`alert_target_rsu`). **Naša vzdialená RSU** upraví len `header.stationId`, ponechá pôvodné `actionId` a obsah udalosti, potom znovu vytvorí lokálny GN/BTP/OCB broadcast. [Zdrojová RSU a UT/GW callbacky](../src/u9-full-integration-per-rsu.cc), [bajtové overenie](../tools/u9_check_cam_denm.py).

To je hlavné rozdelenie práce: **my určujeme význam udalosti, politiku mosta, príjemcu a regeneráciu; Vanetza rieši cestný protokolový zásobník; ns-3/SNS-3 vykonáva sieťový prenos podľa modelu.** Ak sa paket nedostane k RSU, náš most nemá čo odoslať.

## 8. Tienenie a rádio: čo je 2D, 3D a čo je odhad

**Pozemné V2V/V2I rádio.** ns-3 používa `OcbWifiMac` a 10 MHz 802.11p PHY. Scenár volí `friis` (voľný priestor) alebo `urban_los` (3GPP V2V urban útlm s vynúteným LOS). Pri vložených budovách sa účinne použije `urban_osm_building`: náš [`OSMBuildingCondition`](../src/u9-osm-ground-condition.h) z polygónov a zvolenej výšky rozhodne, či **3D úsečka medzi anténami** pretína objem budovy; výsledok LOS/NLOS prevezme **ns-3 3GPP V2V propagation loss model**, ktorý počíta útlm a následný PHY príjem. Budovy teda neznamenajú priamo „paket zahodiť vždy“; menia stav kanála. Toto nie je difrakcia, odraz, presný materiál steny ani meraný mestský kanál.

Anténa auta je v modeli 1,5 m nad lokálnou rovinou. RSU používa `max(5 m, výška strechy + 2 m)`, ak je na pôdoryse budovy. Výšky OSM môžu byť priamo tagované, odvodené z počtu podlaží alebo lokálne odhadnuté; voľba `low/central/high` je **citlivostný scenár**, nie meranie. Ručne nakreslená budova má obdĺžnikový pôdorys a výšku zadanú používateľom. [`u9_local_environment.py`](../tools/u9_local_environment.py), [`u9_ground_obstructions.py`](../tools/u9_ground_obstructions.py), [`viewer/manual-buildings.js`](../viewer/manual-buildings.js), [audit parametrov](experiments/audit-parametrov-2026-11-04.md).

**Satelitný user link.** Poloha družice a terminálu sú 3D; náš natívny filter [`u9-native-satellite-condition.h`](../src/u9-native-satellite-condition.h) počíta smer k družici, odklon od montáže, rýchlosť smerovania antény a zvyškový Doppler. Ak miestna budova pretína začiatok 3D lúča od RSU, alebo zlyhá limit montáže/Dopplera/smerovania, kanál odmietne user-link príjem. SNS-3 popritom používa vlastnú eleváciu, generický DVB PHY/MAC, fronty a modelový zisk. Pri Iridiu/Globalstare sa v natívnom filtri nevymýšľa úzky smerový limit montáže bez doloženej krivky; zadané hodnoty výkonu a zisku sú predpoklady modelu.

**Terén HGT a počasie.** Importovaný raster terénu, OSM budovy a štatistické vrstvy sa používajú v **oddelenej fyzikálnej analýze/náhľade**. Aktívny natívny paketový filter číta budovy pri RSU; **neprevádza celý HGT raster na 3D rádiový terén pre každý paket**. Tienenie lokálneho gateway okolia tiež nie je modelované, keďže modelová brána je mimo výrezu. Polia `weather` a `vegetation` sú spravidla `unknown`; voliteľný `link_budget` počíta citlivosť predpokladov pre audit, nie prevádzkovú dostupnosť operátora ani automatické rozhodnutie natívneho modemu. [Fyzikálny audit](../tools/u9_physical_report.py), [link budget](../tools/u9_link_budget.py), [aktuálna hranica vernosti](decisions/stav-vernosti.md).

## 9. Ako sa rozhoduje o satelitnej ceste

[`u9_native_editor._select_topology`](../tools/u9_native_editor.py) načíta archivované objekty vybranej skupiny, propaguje ich na zvolený UTC čas a overí eleváciu pri každej aktívnej RSU aj pri modelovej bráne. Pri automatickom režime zvolí jednu družicu s najlepším minimálnym výhľadom, ktorá drží účinnú masku po celé okno; inak spustenie zlyhá. Pri explicitnom `catalog_ids` kontroluje vybrané družice, indexy `initial_serving_sat`, `feeder_sat`, `handover_target_sat` a spojitosť stromu `isls`. Globalstar s ISL odmieta. **Orbitálna geometria rozhoduje, čo smie byť kandidátom; skutočné prijatie paketu ešte podlieha natívnemu kanálu.**

[`simulator_satellite_inputs.generate`](../tools/simulator_satellite_inputs.py) vytvorí pre SNS-3 TLE rekonštrukciu, `isls.txt`, polohy UT/GW a diagnostickú anténnu mapu. C++ engine zapne SNS-3 konšteláciu, nastaví DVB parametre a vytvorí pre každú RSU vlastný UT a 100 Mb/s / 100 µs modelovú LAN. Aj pri vypnutom satelitnom režime konkrétnej RSU môže byť v natívnej topológii terminál fyzicky vytvorený; naša aplikačná politika mu zabráni odosielať. Toto je zdokumentovaná [hranica implementácie](experiments/audit-parametrov-2026-11-04.md).

Pri viacdružicovom explicitnom scenári SNS-3 vytvorí modelové ISL zariadenia. **Náš kód** kontroluje graf a nastavuje kapacity/fronty smerom k feeder družici, explicitnú návratovú trasu a vo výskumnom handoveri prenesie stav jedného UT do cieľového satelitu. Potvrdenie vyžaduje obojsmernú skúšobnú správu. To stále nie je dôkaz protokolu Starlink/Iridium/Globalstar. [C++ handover a ISL](../src/u9-full-integration-per-rsu.cc), [dôkaz handoveru](experiments/u9-native-rsu-handover-rf-2026-11-02.md).

## 10. Kde sledovať jeden konkrétny paket

V `results/simulations/<run_id>/` otvor najprv `inputs/scenario.json`, potom `inputs/world.json`, `ground/scenario/sumo/fcd.xml` alebo `native/baseline/sumo/fcd.xml`, `native/baseline/waypoints.csv` a až potom paketové stopy. Pri satelitnom CAM/DENM behu sú najdôležitejšie:

| Súbor | Čo presne hľadať |
| --- | --- |
| `native/baseline/denm-events.csv` | Kedy a z ktorého auta naša aplikácia naplánovala udalosť. |
| `native/baseline/trace.csv` | Bajty a čas v etapách `DENM_UPER_TX`, `RSU_DENM_LAN_TX`, `UT_DENM_SAT_TX`, `GATEWAY_DENM_RX`, `RSU_DENM_REGENERATED`, `DENM_UPER_RX`. Prázdny neskorší stupeň znamená, že sa tam správa nedostala. |
| `native/baseline/ocb-*.pcap` | Skutočné modelové cestné 802.11 rámce; pomáhajú odlíšiť aplikáciu od vyslania na vzduch. |
| `native/baseline/PacketTrace.log` a `satellite-ip-trace.csv` | Interná cesta SNS-3 a väzba IP/UDP datagramu na UID satelitného paketu. PacketTrace nie je záznam komerčných RF bajtov. |
| `native/baseline/satellite_rf.csv`, `phy_drop.csv`, `dcc_decisions.csv` | Prečo modelový user link alebo pozemné rádio prijali/odmietli prenos a prečo sa CAM vytvorila alebo preskočila. |
| `physical-timeline.json`, fyzikálny audit v UI | Časoví geometrickí kandidáti a hranice fyzikálnej interpretácie; nie dôkaz doručenia. |
| `run-manifest.json` | Ktoré vstupy, zdroje a výsledok boli pre tento beh hashovo pripnuté. |

Začni jedným `event_id` v `trace.csv`. Ak je `DENM_UPER_TX`, ale niet `RSU_DENM_LAN_TX`, problém je pred satelitným mostom (dosah, budova, oblasť, politika alebo príjmová logika). Ak je `UT_DENM_SAT_TX`, ale niet `GATEWAY_DENM_RX`, hľadaj `satellite_rf.csv`, `PacketTrace.log`, masku a routing. Ak vzdialená RSU prijala, ale autá nie, hľadaj jej lokálny GN/OCB úsek. [Nezávislý checker](../tools/u9_check_cam_denm.py) toto spája podľa bajtov a časov.

## 11. Jeden skutočný scenár: prečítaj hodnotu až po stopu

Otvor uložený [satelitný koridorový scenár](../config/scenarios/navrh-koridor-satelit.json). V ňom je `source_id="car0"`, `rsu_id="rsu0"`, `alert_target_rsu="rsu1"`, `sample_count=600`, teda 60 sekúnd po 100 ms. Jediná udalosť sa má vytvoriť pri `at_s=5.0`, má `sequence=1`, `operation="new"`, `validity_s=45`, `radius_m=600`, `repetition_ms=0`. Posledné číslo znamená, že náš plánovač nezadá opakované vysielanie tejto udalosti. **600 m je cieľová oblasť GeoNetworking, nie zaručený fyzický dosah rádia.**

V tom istom scenári `radio.tx_power_dbm=20`, `radio.noise_figure_db=7`, `radio.mode="urban_los"`. Chýbajúce voliteľné `rate_mbps` a `channel_number` doplní [`ground_config`](../tools/simulator_inputs.py) na 6 Mbit/s a kanál 180, teda stred 5900 MHz. Oboje sa potom nastaví do pozemného ns-3 rádia; počet doručených rámcov z týchto čísel samotných nevypočítaš bez polôh, kanála a kolízií. `node_policy.cars.car0.ground="all"` dovolí príjem v RSU; obe RSU majú `satellite_backhaul=true`. `satellite.catalog_ids=[]` znamená automatický výber jednej vhodnej družice, nie nulový počet družíc.

Teraz sleduj riadok `denm_events[0]` v tomto poradí:

```text
scenario.json
  -> bp_u9.preflight: platný čas, zdroj, policy, orbita
  -> u9_editable_scenario: SUMO pohyb car0
  -> u9_prepare_cam: waypoint car0 v čase udalosti
  -> make_denm / Station::emit_denm: UPER + GN/BTP
  -> ns-3 prijatie v rsu0
  -> RSU_DENM_LAN_TX -> UT_DENM_SAT_TX
  -> SNS-3 user/feeder/ISL podľa topológie
  -> GATEWAY_DENM_RX -> RSU_DENM_REGENERATED
  -> vzdialené ns-3 rádio -> DENM_UPER_RX v aute
```

Každá šípka má kontrolovateľný dôkaz v [surovej stope](../tools/u9_check_cam_denm.py) a v súboroch opísaných v časti 10. Nie každá šípka musí v každom pokuse nastať. Presný výklad každého čísla v scenári je v [katalógu vstupov](studium-bp-katalog-vstupov.md).

## 12. Desať viet, ktoré máš vedieť vysvetliť bez kódu

1. SUMO vypočíta pohyb áut; sieť v ňom nebeží.
2. JSON editora sa najprv validuje a zmení na dopravný vstup a potom na časové polohy.
3. Naša aplikácia rozhoduje, kedy vznikne CAM/DENM a čo znamená udalosť.
4. Vanetza kóduje správu a vytvára cestný GN/BTP zásobník.
5. ns-3 WAVE simuluje lokálne 802.11p OCB rádio a jeho kanál.
6. RSU posiela na satelit iba obsah, ktorý prijala a ktorý povoľuje naša politika.
7. SNS-3 simuluje generickú DVB satelitnú paketovú cestu, nie modem operátora.
8. Orbitálny archív a elevácia určujú kandidáta, nie garantované doručenie.
9. Budovy menia modelovú pozemnú LOS/NLOS podmienku a user-link filter; raster terénu sa v natívnom pakete nepoužíva ako úplný 3D rádiový svet.
10. Výsledok tvrdí niečo o presne opísanom scenári a raw paketovej stope, nie o prevádzkovej kvalite komerčnej služby.
