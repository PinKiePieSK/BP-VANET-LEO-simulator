# Ako funguje náš simulátor — podrobný rozbor implementácie

**Čítaný pracovný stav: 1. november 2026.** Tento dokument nadväzuje na `01-zrozumitelny-prehlad.md`. Vysvetľuje jadro aj podporné vrstvy, nie každý riadok externých knižníc. Presný register zdrojov, funkcií a odtlačkov je v `03-zdroje-a-overenie.md` a `audit-zdrojov.json`. Pracovný strom obsahuje aj rozpracované zmeny; report sa preto viaže na prečítané zdroje, nie iba na Git commit.

## 1. Architektúra programu a zodpovednosti jazykov

**Kód:** [bp_u9.py: service_primary](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:81>).

### 1.1 Prečo máme Python, C++ aj JavaScript

JavaScript beží v prehliadači a spravuje návrh scenára, mapu, výber objektov a prehrávanie výsledkov. Python beží lokálne na počítači: kontroluje JSON, pripravuje SUMO, propaguje orbity, spúšťa C++ a kontroluje súbory. C++ beží ako sieťový experiment, pretože ns-3 a Vanetza poskytujú svoje hlavné API v C++.

Nie je to všeobecná mikroservisná aplikácia. Server spúšťa lokálne procesy a odovzdáva im súbory. Hlavnými rozhraniami medzi vrstvami sú JSON, XML a CSV. Až vo vnútri C++ behu sa CAM udalosti a satelitné udalosti prepájajú priamymi volaniami funkcií v spoločnom plánovači ns-3.

| Zdroj | Zodpovednosť |
| --- | --- |
| `viewer/u9-simulator.js` | Stav editora, politika uzlov, uloženie, spustenie, časová os, detail správy |
| `viewer/u9-earth-map.js` | Reálna mapa, lokálne/geografické súradnice a práca s mapovými objektmi |
| `viewer/u9-route-planner.js` | Orientovaný cestný graf, hľadanie trás a výber cieľa |
| `viewer/u9-traffic-spawner.js` | Hromadná tvorba syntetických áut |
| `viewer/u9-globe.js` | Zem, orbitálny náhľad a zobrazenie konštelácie |
| `tools/u9_server.py` | HTTP API, zoznam povolených statických súborov, správa procesu behu |
| `tools/u9_editor_api.py` | Nový draft, uloženie, kontrola, overený replay, detail paketu |
| `tools/bp_u9.py` | Hlavný kontrakt scenára a výber vykonávacej vetvy |
| `tools/u9_editable_scenario.py` | Validácia sveta, generovanie SUMO XML a spustenie dopravy |
| `tools/u9_run_ground.py` | Pozemný runner, build, waypointy a raw výstupy |
| `tools/u9_prepare_cam.py` | Prevod FCD na sieťové vzorky a CAM čas |
| `tools/u9_dynamic_service.py` | Časový plán satelitných trás po termináloch |
| `tools/u9_service_native.py` | Parametre, spustenie a overenie servisného C++ experimentu |
| `src/u9-service-native.cc` | Pozemné CAM/OCB a servisné udalosti v jednom ns-3 procese |
| `src/u9-full-advanced.cc` | Staršie integrované generické SNS-3 DVB jadro |

Názov súboru nie vždy znamená samostatný produkt. Mnohé `probe`, `prototype`, `noisl` a `recovery` sú experimentálne varianty. `tools/legacy` obsahuje zdrojové snapshoty pre staršie dôkazy. Rozhodujúce je, čo importuje a spustí aktuálny runner.

### 1.2 Dve aktívne významové osi

Prvá os je **pozemný režim verzus satelitná vetva**. Druhá os je **nový servisný backend verzus historický generický DVB engine**. Nestačí povedať „používame SNS-3“, pretože to nie je pravda o každom novom satelitnom pakete.

V `bp_u9.py` rozhoduje predikát `service_primary`:

```python
return (not historical and unified_satellite(s) and
        isinstance(s.get('satellite'), dict) and
        s['satellite'].get('dynamic_physical') is True)
```

Pri novom `mode='unified'`, zapnutom satelite a `dynamic_physical=true` ide hlavná vetva do `run_service_native`. Pri historickom overení sa uplatňujú aj staršie kontrakty a zdrojové snapshoty.

## 2. Vstupný kontrakt: čo znamenajú JSON súbory

**Kód:** [bp_u9.py: preflight](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:133>), [bp_u9.py: unified_policy](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:85>).

### 2.1 Scenario, world a demand

`scenario` je riadenie experimentu. Kľúčové údaje sú `schema_version`, `time_policy`, `scenario_id`, `world_template`, `demand`, `source_id`, `rsu_id`, `seed`, `ns3_run`, `utc_origin`, `sample_count`, `radio`, `mode`, `satellite_enabled`, `direct_cars`, `node_policy`, `alert_target_rsu` a `link_policy`.

`world` je priestor a doprava: `roads.nodes`, `roads.segments`, `rsus`, `vehicles`, `georeference`, `simulation` a deklaratívne `flows`. `demand.vehicles` sa pri príprave aplikuje na svet. Vďaka tomu sa dá zachovať rovnaká mapa a meniť dopravný dopyt.

Hodnota `world.network_execution='schema_only'` nehovorí, že celý U9 nevykonáva komunikáciu. Hovorí, že samotný generátor sveta ešte nespúšťa ľubovoľné sieťové aplikácie z `flows`. Komunikačný engine sa pripája neskôr. Pridanie toku do `flows` samo nevytvorí nový UDP vysielač ani DENM aplikáciu.

### 2.2 Individuálna politika uzlov

Pri aute má `node_policy.cars[id]` dve položky:

```json
{"ground": "all", "direct_satellite": false}
```

`ground` je `all`, `cars` alebo `off`. Pri RSU sú to booleany `ground` a `satellite_backhaul`. `unified_policy` kontroluje presné pokrytie všetkých áut a RSU, súlad `direct_cars` s politikou aj odvodenie `satellite_enabled`.

Politika sa do C++ prenáša aj prostredím procesu, cez `u9_node_policy.environment`. V C++ sa načítajú množiny `ground_off_cars`, `cars_only`, `ground_off_rsus`. Zastavenie príjmu na úrovni aplikácie sa nesmie zameniť s vypnutím existencie rádiových zariadení v priestore.

### 2.3 Čo preflight dokáže a čo ešte nedokáže

`preflight` kontroluje typy, presné množiny povolených kľúčov, identifikátory, rozsahy parametrov, kompatibilitu režimu a existenciu vstupov. Pri novom servisnom behu kontroluje hashovaný orbitálny archív, časové okno, montáže a prostredie. Plný plán nad konkrétnymi FCD polohami vzniká až po SUMO.

Podstatné dnešné hranice:

| Pravidlo | Súčasné správanie |
| --- | --- |
| Autá | Aspoň dve; vstupné technológie účastníkov obsahujú ITS-G5 aj pri následne vypnutej politike |
| Čas | Nový jednotný svet 2–120 s; nový satelitný beh aspoň 6 s |
| Vzorky | `sample_count = duration_s * 10`, najviac 1200 |
| Odjazd | V novom spoločnom štarte všetky autá `depart_s=0`; interná príprava ich posunie o nábeh |
| Rádio | Verejné U9 `friis` alebo `urban_los`, výkon 0–33 dBm, noise figure 0–20 dB |
| Satelitná referencia | Aspoň jedna RSU s pozemným aj satelitným rozhraním; referenčné auto `ground='all'` |
| RSU | Najviac 512 v príslušnej spoločnej vstupnej vetve; aj keď nový model nemá rovnakú IP topológiu, kontrola ostala |
| Mapa | Lokálne súradnice sveta 0–2000 m, cestné uzly/úseky do limitov validátora |
| Trasa auta | 1–200 orientovaných úsekov |
| Budovy F4 | Najviac 12 000 importovaných uzavretých budov |

Historické režimy majú ďalšie pevné epochy, počty vzoriek a adresovacie obmedzenia. Nemožno im automaticky prisúdiť rozsah nového `unified`.

Preflight je prijatie konfigurácie, nie dôkaz doručenia. Nový servisný model môže správne prijať scenár a následne vyprodukovať nula doručení, napríklad pri neexistujúcej ceste k bráne.

## 3. Od kliknutia po proces C++

**Kód:** [u9_server.py: Handler](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_server.py:52>), [u9_editor_api.py: save](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:130>), [bp_u9.py: run](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:278>).

### 3.1 Web a lokálny server

`u9_server.py` používa `ThreadingHTTPServer`. Koreň presmeruje na `/u9-simulator.html`. Statické súbory povoľuje explicitná množina `STATIC`. Starý `scenario_server.py` patrí k reprodukcii starších editorov.

Dôležité API:

| API | Správanie |
| --- | --- |
| `GET /api/u9/editor/new` | Prázdny draft s aktuálnym vstupným kontraktom |
| `POST /api/u9/editor/roads` | Cestný výrez a voliteľne lokálne prostredie |
| `POST /api/u9/editor/orbits` | Náhľad konštelácie |
| `POST /api/u9/editor/orbit-motion` | Časové vzorky pohybu satelitov |
| `POST /api/u9/editor/check` | Preflight nad dočasne pripravenými world/demand |
| `POST /api/u9/editor/save` | Nové súbory sveta, dopytu a scenára |
| `POST /api/u9/preflight` | Kontrola uloženého scenára |
| `POST /api/u9/runs` | Spustenie samostatného procesu `bp_u9.py run` |
| `GET /api/u9/runs/<id>` | Stav alebo overený výsledok |
| `GET /api/u9/runs/<id>/replay` | Podklady na prehrávanie |
| `GET /api/u9/runs/<id>/packet/<event_id>` | Kroky a bajty jednej správy |

Server oddeľuje HTTP obsluhu od náročného výpočtu cez `subprocess.Popen`. Uloží žiadosť, log a PID. Zámok bráni spusteniu ďalšieho U9 behu cez tento server počas aktívneho behu. Nie je to všeobecný globálny zámok všetkých ručne spustených terminálových programov.

`save` používa nové adresáre a vytvorenie cieľa režimom `x`. Existujúci scenár sa týmto volaním potichu neprepíše. `check` pripraví dočasné vstupy a vykoná ten istý runnerový preflight.

### 3.2 Skutočné poradie runnera

Zjednodušená rekonštrukcia `bp_u9.run`, nie doslovná celá funkcia:

```python
scenario = load(path)
plan = preflight(scenario)
world, demand, runtime = runtime_inputs(scenario, output)
write_staged_inputs(...)
run_ground(...)
ground_result = verify_ground(...)
derive_inputs(...)
if service_primary(scenario):
    result = run_service_native(output, output / 'service-model')
else:
    result = run_selected_historical_or_ground_branch(...)
write_physical_timeline_if_requested(...)
write_hashed_run_manifest(...)
```

**Poctivý detail o dvoch behoch:** `run_ground` už vykoná samostatný pozemný ns-3 experiment. Nový `run_service_native` potom použije pripravené waypointy a vykoná ďalší C++ beh, ktorý obsahuje aj pozemnú CAM/OCB časť a servisný model. End-to-end servisné tvrdenie sa viaže na `service-model/service-native/cam.csv`, `rx.csv` a `service_packets.csv` z tohto druhého spoločného procesu. Neznamená to, že reporty za behu prichádzajú z prvého nezávislého procesu. Prvá fáza ostáva samostatným pozemným dôkazom a prípravou mobility.

To vysvetľuje aj dĺžku prípravy: okrem SUMO a geometrie sa môže kompilovať a vykonať viac než jeden C++ experiment.

## 4. Mapa, trasy a SUMO

**Kód:** [u9-route-planner.js: function tree](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/viewer/u9-route-planner.js:22>), [u9_editable_scenario.py: make_inputs](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editable_scenario.py:296>), [u9_editable_scenario.py: run](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editable_scenario.py:431>).

### 4.1 Cestný graf

V `u9-route-planner.js` je orientovaný graf. Každý úsek má dĺžku vypočítanú zo svojej polyline. Jednosmerka vytvára jednu orientovanú hranu, obojsmerná cesta dve. `tree` používa prioritnú haldu a aktualizáciu najkratších vzdialeností, teda Dijkstrov princíp. Váha je v základnom stromovom hľadaní dĺžka, nie živá dopravná zápcha.

`pathTo` rekonštruuje zo spätných odkazov zoznam `{segment, direction}`. Ďalšie funkcie spravujú počiatočnú pozíciu, kliknutý cieľ, odhad jazdného času a náhodné prechádzky. Náhodná premávka v editore je generovanie vstupu, nie automatická kalibrácia na sčítanie dopravy.

`u9_osm_road_graph.py` stiahne a spracuje OSM XML výrez, prepočíta body do lokálneho rámca a vytvorí graf. `u9-earth-map.js` zobrazuje podklad cez MapLibre a prepája mapové objekty so svetom. Prehodenie lokálneho a geografického rámca by posunulo rádio aj satelitné výhľady, preto existujú osobitné testy zarovnania polôh.

### 4.2 Generovanie SUMO súborov

`make_inputs` vytvorí `road.nod.xml`, `road.edg.xml`, `vehicles.rou.xml` a `rsus.add.xml`. Úseky dostanú smerové prípony `forward/reverse`. RSU je v SUMO iba bod záujmu s významom polohy; sieťové zariadenie sa vytvorí až v ns-3.

`run` následne spustí `netconvert` a `sumo`. Výstupmi sú sieť, FCD, summary a logy. Dôležité konfiguračné detaily: krok 0,1 s, explicitný seed, nastavenia osobných áut a kontrola, že sa do FCD dostalo každé požadované auto.

Pri reálnej mape majú autá vlastné `vType`, `departSpeed='max'` a `departLane='best'`; zadaná rýchlosť obmedzuje ich maximum. To nie je záväzok, že auto pôjde celú trasu touto rýchlosťou. SUMO zohľadňuje cestu a ostatné vozidlá. Pri manuálnej mape sú niektoré nastavenia typu spoločné.

`align_route_positions` opravuje väzbu kliknutej pozície na vybudovanú SUMO sieť. `hold_vehicles_for_radio_window` pridáva zastavenie na konci krátkej trasy. Chýbajúce auto sa nenahrádza vymyslenou polohou po skončení FCD.

### 4.3 Jednosmerná väzba mobility

Architektúra je offline coupling: najskôr dopravná simulácia, potom sieť nad jej stopou. V aktuálnej ceste nie je živé TraCI riadenie dopravy odozvou siete. Dopravné metriky preto charakterizujú vstupný SUMO pokus, nie dopravný prínos prijatej výstrahy.

## 5. Časové a geografické adaptéry

**Kód:** [bp_u9.py: runtime_inputs](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:46>), [u9_prepare_cam.py: prepare](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_prepare_cam.py:19>).

### 5.1 Interný a používateľský čas

`runtime_inputs` pri novom kontrakte predĺži SUMO horizont o 10 s nábehu a malú rezervu a posunie odjazdy o 10 s. `experiment_clock` nastaví `U9_LOGICAL_END_US`. C++ experiment sa ukončí na presnej hranici, bez automatického dobehnutia paketov po nej.

Pre zobrazovaný čas t platí:

```text
ns-3 čas = 10 s + t
UTC udalosti = scenario.utc_origin + 10 s + t
sample_count = 10 × trvanie v sekundách
```

Posledná pohybová vzorka je na `10 s + T − 0,1 s`. Plán satelitných trás obsahuje aj koncovú vzorku `T`. Nový draft nastaví interný pôvod približne na čas stiahnutia orbitálneho archívu mínus 10 s.

### 5.2 Čo presne je waypoint

`u9_prepare_cam.prepare` vytvorí riadky s poľami:

```text
node_id, station_id, kind, index, time_us, utc,
x_m, y_m, latitude_e7, longitude_e7, altitude_cm,
speed_cmps, heading_decideg, generation_delta_ms
```

`latitude_e7` je zemepisná šírka násobená 10⁷. `speed_cmps` je rýchlosť v centimetroch za sekundu. `heading_decideg` je uhol v desatinách stupňa. Tieto celočíselné reprezentácie sedia s potrebami CAM. `station_id` sa priraďuje od 1001 podľa poradia účastníkov, nie automaticky podľa OSM alebo evidenčného čísla auta.

`generationDeltaTime` je 16-bitový časový údaj odvodený od TAI milisekúnd od referencie 2004 a modulo 65536. Nie je to Unix timestamp. Generátor odmietne kolíziu takýchto identít v jednom prípade. Pri 100 ms mriežke nemusí samotné prekročenie jedného 65,536 s cyklu vytvoriť rovnakú hodnotu na každej vzorke; rozhodujúce je explicitné overenie jedinečnosti.

V C++ `load` kontroluje hlavičku, počet vzoriek, rovnaké časové osi všetkých uzlov, 100 ms krok a jednoznačné identity. Pri aktualizácii je model mobility `ConstantPositionMobilityModel`, ktorému sa v naplánovaných udalostiach mení poloha. Nie je to priebežné fyzikálne zrýchľovanie auta v ns-3.

## 6. Pozemné jadro v `u9-service-native.cc`

**Kód:** [u9-service-native.cc: Runtime](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:48>), [u9-service-native.cc: Station](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:168>), [u9-service-native.cc: void check](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:212>), [u9-service-native.cc: void indicate](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:275>).

### 6.1 Adaptér Runtime

Vanetza potrebuje vlastné časové rozhranie. Trieda `Runtime` ho implementuje nad `ns3::Simulator`. `now()` pridá mikrosekundy ns-3 k UTC pôvodu a `schedule()` naplánuje callback do rovnakého simulátora. Vanetza teda nemá nezávislé hodiny, ktoré by voči ns-3 utekali.

### 6.2 Trieda Station

Jedna `Station` patrí jednému rádiovému uzlu. Má zariadenie, ID, pohybovú stopu, MAC adresu, Vanetza router, BTP dispatcher, predošlú vyslanú vzorku, CBR intervaly a počítadlá.

Konštruktor vypne GeoNetworking security a automatické beaconing správanie, pripojí MAC adresu, BTP-B a CAM port a nastaví receive callback zariadenia. Neimplementuje sa tým kompletná bezpečnostná PKI ETSI ITS.

### 6.3 Rozhodovanie o CAM

`Station::check` pracuje len pre autá. Zistí CBR, minimálny interval, čas od poslednej CAM, prejdenú vzdialenosť a zmenu rýchlosti/smeru.

Zjednodušený ekvivalent pravidla:

```text
motion = vzdialenosť > 4 m alebo |Δv| > 0,5 m/s alebo |Δsmer| > 4°
elapsed_ok = čas od poslednej CAM >= minimum
periodic = čas od poslednej CAM >= aktuálne T_gen
send = prvá CAM alebo (elapsed_ok a (motion alebo periodic))
```

Po pohybovom spúšťači sa interval adaptuje podľa uplynutého času v rozsahu 100–1000 ms. Po troch periodických spúšťačoch sa vracia k 1000 ms. Low-frequency kontajner sa pridáva pri prvej CAM a potom s odstupom aspoň 500 ms. Preto sa mení aj veľkosť zakódovanej CAM.

Ak je DCC zapnuté v nižšom runneri, minimum vychádza z prahov CBR a typicky z intervalov 100/250/500 ms. Je to výskumné pravidlo, nie preukázaná úplná ETSI konformita. Verejná U9 šablóna ho teraz vypína.

### 6.4 Kódovanie a odovzdanie správy

`encode_cam` vyplní `v::asn1::r2::Cam`: hlavičku, station ID, `generationDeltaTime`, basic/high-frequency kontajner, polohu, smer, rýchlosť a ďalšie fixné výskumné hodnoty. Rozmery auta a viaceré dynamické polia sú nastavené konštantami; nejde o plný model senzorov auta. Potom sa vykoná `validate()` a `encode()`.

`send_cam` uloží presné bajty do `sent_cam[(station, gdt)]` a zapíše `CAM_UPER_TX`. **Najprv** volá `service_on_cam_tx`; až následne kontroluje `ground_off_cars`. Preto priame satelitné auto môže ponúknuť CAM aj bez pozemného rámca.

Pre pozemnú vetvu pridá BTP-B hlavičku a požiada GeoNetworking o single-hop broadcast. `Station::request` serializuje vrstvy do jedného bufferu a zavolá:

```cpp
device_->Send(packet, ns3::Mac48Address::GetBroadcast(), 0x8947);
```

EtherType `0x8947` rozlišuje GeoNetworking payload. `GN_BTP_CAM_TX` je fáza ponuky rámca zariadeniu. Ani `CAM_UPER_TX`, ani úspešný návrat `Send` samy osebe nezaručujú príjem na druhom uzle.

### 6.5 Rádiový model

`main` vytvorí `NodeContainer`, nainštaluje mobilitu, Wi-Fi PHY a `QosWaveMacHelper`. Používa `Wifi80211pHelper`, `OcbWifiMac` a konštantnú rýchlosť `OfdmRate6MbpsBW10MHz`. C++ explicitne kontroluje kanál 5900 MHz a šírku 10 MHz.

Pri Friis režime sa nastaví Friis útlm a konštantná rýchlosť šírenia. Mestská vetva používa `ThreeGppV2vUrbanPropagationLossModel` a príslušný `ChannelConditionModel`. Verejné `urban_los` vytvorí `AlwaysLosChannelConditionModel`. Nižšie režimy vedia `NeverLos` alebo budovový stav, ale verejný preflight ich neprijíma.

Je to skutočný rádiový simulačný zásobník s MAC/PHY udalosťami a príjmami, nie bitový elektromagnetický výpočet každej vlny. Parametre, model útlmu a seed určujú jeho rozsah platnosti.

### 6.6 Príjem a spätné overenie bajtov

`receive` odfiltruje politiku a EtherType. GeoNetworking rámec prejde routerom a dispatcherom do `indicate`. Táto metóda dekóduje CAM, validuje ju a kontroluje, či presné prijaté CAM bajty zodpovedajú pôvodnému `sent_cam`.

Ak príjemcom je RSU a auto má `cars_only`, príjem sa v aplikačnej vetve ignoruje. Inak sa zapisuje `rx.csv`. Pri povolenej RSU sa vyvolá `service_on_cam_rx`, teda skutočný dekódovaný pozemný príjem je podmienkou servisného RSU reportu.

### 6.7 CBR a rádiové straty

`on_state` zaznamená intervaly TX, RX a CCA_BUSY. `cbr` ich oreže do posledného sekundového okna, zoradí a zjednotí, aby sa prekrývajúci čas nezapočítal dvakrát. `on_drop` zapisuje ns-3 PHY dôvod.

`PHY_DROPS` nie je univerzálne počítadlo chýb end-to-end. Rámec mohol byť pre niektorý prijímač nedekódovateľný a zároveň úspešne prijatý inde. Jeden broadcast má viac potenciálnych prijímacích vzťahov.

## 7. Orbity: od OMM po lokálnu eleváciu

**Kód:** [u9_orbit_source.py: validate_pin](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_orbit_source.py:21>), [v3_leo_topology.py: load_orbits](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/v3_leo_topology.py:106>), [v3_leo_topology.py: sample](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/v3_leo_topology.py:151>).

### 7.1 Nemenný zdrojový archív

`u9_orbit_source.validate_pin` overí cestu, SHA-256 manifestu a vnútornú integritu snapshotu. `config_for` vyberie referenčnú skupinu a kontroluje časové okno. `v3_leo_topology.load_orbits` overí gzip aj rozbalený JSON, počet objektov, duplicity katalógových ID a vek každej dráhy.

To znamená dva rozdielne počty: počet objektov v archíve a počet objektov vekovo použiteľných pre celý experiment. `candidate_pool_catalog_ids` v servisnom pláne je zase množina objektov skutočne použitých v trasách; podľa názvu by sa mohol nesprávne čítať ako celý preskúmaný katalóg.

### 7.2 Propagácia a prevod rámcov

`sample` vytvorí `SatrecArray`, propaguje všetky vybrané objekty pomocou SGP4 a prevádza výsledok z TEME do ITRS cez Astropy. EOP/IERS dáta sú kontrolované a hashované; automatické sťahovanie IERS je v tejto funkcii vypnuté. SGP4 chyba alebo nedostupný EOP čas má viesť k chybe, nie k tichému vykresleniu nesprávnej polohy.

Geodetická poloha terminálu sa prevádza na zemské súradnice. Elevácia je projekcia smeru na lokálny rámec; vzdialenosť je norma rozdielu polôh. ISL `clearance` kontroluje, či priamku medzi satelitmi nepretína modelovaná Zem. Geometrická priechodnosť ISL ešte neznamená, že existuje konkrétny aktívny laser alebo rádiový crosslink.

### 7.3 Prečo po 0,5 s

`u9_dynamic_service` používa `STEP_US=500_000`. To je päťkrát hrubší krok než pozemná mobilita. `_waypoint` vezme aktuálnu dostupnú vzorku auta. Medzi plánovými bodmi C++ používa posledný platný záznam, nie spojitý nový prepočet orbitálnej trasy pre každý bit.

Hranica viditeľnosti môže teda ležať medzi plánovými vzorkami. To je numerická aproximácia, ktorú treba mať na pamäti pri krátkych výpadkoch a handoveroch.

## 8. Anténa, terén a výšky budov

**Kód:** [u9_antenna_envelope.py: angles_deg](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_antenna_envelope.py:63>), [u9_local_environment.py: impute_building_heights](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_local_environment.py:61>), [u9_local_environment.py: LocalObstructions:](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_local_environment.py:313>).

### 8.1 Anténna obálka

`u9_physical_coverage.PROFILES` obsahuje reprezentatívne user frekvencie a verejne zdôvodnené obálky pre konkrétne terminály. Tieto konštanty sú modelové vstupy s uloženým zdrojom, nie odhad reálneho kanála z aktuálnej telemetrie.

`u9_antenna_envelope.angles_deg` vytvorí lokálne vektory east/north/up a normálu panelu podľa `tilt_deg`, `azimuth_deg` a rámca `north` alebo `vehicle`. Pri aute vo `vehicle` rámci sa pripočíta smer jazdy. Skalárny súčin normalizovaného smeru na satelit a osi antény dá kosínus odchýlky. `starlink_fov_mask` prijme uhol najviac 70°.

Bez explicitnej montáže sa zachováva základná obálka, nie detailná znalosť orientácie konkrétneho panelu. Pri Iridiu a Globalstare nemáme v tejto vrstve kvantifikovaný namontovaný ziskový diagram; neprítomnosť cutoffu preto nie je vyhlásenie o rovnakom zisku vo všetkých smeroch.

### 8.2 Pôvod budov a výšok

`buildings_from_xml` importuje uzavreté OSM building ways. Multipolygon relácie a neúplné pôdorysy nie sú automaticky plnohodnotnou geometriou; eviduje ich počítadlo. OSM budova s tagom `height` dostane označenie neoverenej mapovej výšky. Počet podlaží vytvorí interval 2,5–4 m na podlažie.

Aktuálny `impute_building_heights` dopĺňa chýbajúce výšky z miestnych donorov. Najprv hľadá dostatočný počet porovnateľných typov budov v okolí, potom širšie skupiny a výrez. Stred je medián; interval kombinuje kvantily s pomerným rozpätím. Ak podklady chýbajú, ostáva označený fallback so stredom 9 m a citlivostným rozsahom. Výber donorov v OSM nie je náhodná vzorka mesta, preto tento interval nie je štatistický interval spoľahlivosti.

### 8.3 Lokálny LOS test

`LocalObstructions` pripraví terénny raster 75×75 s krokom 30 m a priestorový index budov v 100 m bunkách. `height` používa bilineárnu interpoláciu. `sight` prevedie smer k satelitu do lokálnej sústavy a porovná výšku lúča s terénom a strechami.

Pre terén sa vzorkuje po 30 m. Pre budovy sa počítajú priesečníky polpriamky s hranami pôdorysu. Výška antény je v tejto vrstve scenárovo 1,5 m pre auto a 3 m pre RSU. Pozemné C++ rádio umiestňuje RSU do 5 m; ide o dva odlišné nastavené modely, nie automaticky jednu kalibrovanú montáž.

Výsledok je `blocked`, `clear` alebo `uncertain`. V intervalovom variante blokuje minimálna výška budovy a maximálna môže vytvoriť neistotu. `height_case` umožňuje low/central/high/interval citlivosť. Plánovač vyhodí `blocked`, ale `uncertain` ponechá s príznakom.

Sú tu aj konkrétne aproximácie: lokálny výrez má konečný rozsah, 30 m DEM nevidí jemné prekážky a veľmi blízky priesečník do 0,5 m sa preskakuje kvôli vlastnému obklopujúcemu pôdorysu. Nie je modelovaná difrakcia ani Fresnelova zóna. Satelitná trasa k proxy bráne má eleváciu, ale tento lokálny mestský obstacle model sa tým automaticky nevykonáva aj v okolí vzdialenej brány.

## 9. Servisný plánovač: konkrétny algoritmus

**Kód:** [u9_dynamic_service.py: plan](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_dynamic_service.py:82>), [u9_dynamic_service.py: _path](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_dynamic_service.py:57>).

`plan` pracuje po časoch a v každom čase po povolených termináloch. Predbežný `_near_site_candidates` vektorovo vynechá satelity, ktoré zaručene nemôžu prejsť eleváciou; presné rozhodnutie sa potom stále robí pre konkrétny terminál.

Postup jedného terminálu:

1. Získa jeho polohu z waypointov.
2. Vypočíta elevácie a dolnú masku z maxima scenárovej a profilovej hranice.
3. Uplatní explicitnú montáž panelu a lokálne prekážky.
4. Zoradí kandidátov podľa elevácie a katalógového ID.
5. Pre kandidátov skúsi `_path` k proxy bráne; pre výber drží najlepších niekoľko prípustných ciest, typicky do ôsmich, a prípadne aj doterajší serving.
6. Uplatní hysteréziu a minimálny dwell time.
7. Uloží verejné katalógové ID, vzdialenosti, elevácie, počty kandidátov a príznaky neistoty.

`_path` najskôr skontroluje, či serving vidí aj gateway. Ak áno, vráti `[serving]`. Globalstar týmto končí. Starlink bez optického predpokladu tiež. Pri Iridiu alebo optickom Starlink variante môže skúsiť druhý satelit viditeľný z brány, pričom overí ISL clearance. Výber zvažuje najviac 24 najlepších gateway kandidátov.

Pri Iridiu obmedzuje modelový stupeň aktívnych ISL na štyri. Nie je to rekonštrukcia skutočnej orbital-plane susednosti. Hrany sa vytvárajú ako výskumný proxy podľa geometrie a aktuálneho spracovania terminálov. Tento algoritmus nemá komerčný shortest-path routing cez celú sieť a nepoužíva ľubovoľný počet ISL.

Prepnutie prebieha pri strate aktuálnej cesty alebo pri dostatočnom zlepšení elevácie: rozdiel aspoň 3° po aspoň 2 s pobytu. Ak aktuálna cesta stratí prípustnosť, dwell nebráni nutnej zmene. Zapisujú sa `serving_transitions` a samostatne `route_changes`; trasa sa môže zmeniť aj zmenou relay pri rovnakom serving.

## 10. Servisný C++ model: štruktúry a časovanie

**Kód:** [u9-service-native.cc: struct ServiceRoute](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:304>), [u9-service-native.cc: ServiceModel](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:309>), [u9-service-native.cc: void hop](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:432>), [u9-service-native.cc: void offer](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:466>).

### 10.1 ServiceRoute a ServiceModel

`ServiceRoute` obsahuje `logical_us`, zoznam `satellites` a `ranges_m`. Pri jednom satelite má cesta dve vzdialenosti: terminál–satelit a satelit–brána. Pri dvoch tri, vrátane ISL.

`ServiceModel` má mapu terminálových plánov, čas obsadenia uplinku/downlinku alebo spoločného half-duplexu, odkazy na `Station`, trace stream a počítadlá. **Nevytvára tu satelitný `NetDevice`, UDP socket ani DVB PHY pre každý servisný hop.** Je to udalostný model architektúry s konkrétnymi bajtmi a časmi.

`route_at` získa riadok indexom `(absolute_us - 10_000_000) / 500_000`. Medzi dvoma riadkami je plán konštantný. CSV sa pri načítaní kontroluje na kompletný 0,5 s krok od nuly po koniec a na servisné architektúrne limity.

### 10.2 Obálka a identita

`payload` vloží dvojbajtový tag, 32-bitové station ID v sieťovom poradí, 32-bitový gdt a voliteľné CAM bajty:

```text
C1 = 2 B tag + 4 B station + 4 B gdt + CAM + voliteľná nulová výplň
K1 = 2 B tag + 4 B station + 4 B gdt
A1 = 2 B tag + 4 B station + 4 B gdt + CAM
```

Pri 41 B CAM je základný C1 report 51 B. `K1` má 10 B. Samotná CAM môže mať podľa kontajnerov inú veľkosť; raw hex je rozhodujúci údaj.

`event_id` je napríklad `RSU_REPORT_OFFER-rsu0-1001-12345`. Obsahuje typ ponuky, vlastníka terminálu, station a gdt. Rovnaká CAM reportovaná ďalšou RSU má iné event ID. Nie je tu stará globálna politika „iba prvá RSU vyhrá“.

### 10.3 Výpočet prenosu v hop()

Označme veľkosť payloadu B, smerovú rýchlosť R, relay rýchlosť Rr, počet satelitov N a vzdialenosti jednotlivých úsekov dᵢ. Implementácia používa mikrosekundy a zaokrúhľovanie nahor:

```text
air_us   = ceil(8 × B × 1 000 000 / R)
relay_us = ceil(8 × B × 1 000 000 / Rr)
prop_us  = súčet ceil(dᵢ × 1 000 000 / 299 792 458)
finish   = start + access_us + air_us + N × relay_us + prop_us
```

`start` je maximum aktuálneho času a obsadenosti daného terminálu/smeru. Pri Globalstare je jedna spoločná obsadenosť pre oba smery. Pri ostatných sú samostatné uplink/downlink časy.

Pre predstavu: samotných 51 B pri 22 kb/s potrebuje asi 18,55 ms, pri 2,4 kb/s 170 ms a pri 1 Mb/s 408 µs. To sú iba serializačné zložky podľa uvedenej rovnice. Celkový čas zahŕňa aj čakanie a ďalšie členy; nejde o meranie latencie služby.

Model rezervuje terminál na `access + air`, nie na celý čas letu. Nezdieľa plný komerčný beam scheduler medzi všetkými terminálmi. Relay čas násobí počtom satelitov; nejde o úplný per-link store-and-forward model každej rádiovej fronty. Serializuje aplikačný payload, nie skutočné IP/UDP, FEC a MAC overhead všetkých služieb.

### 10.4 Pravidlá odmietnutia

| Dôvod | Kedy vzniká |
| --- | --- |
| `terminal_disabled` | Pre terminál nie je tabuľka trás |
| `no_proxy_route` | Pri plánovanom štarte nie je cesta |
| `globalstar_mo_size` / `globalstar_mt_size` | Správa porušuje MO/MT veľkostný interval |
| `outside_experiment` | Štart alebo vypočítaný príjem by bol na konci/za koncom okna |
| `route_changed_in_flight` | Pri doručení už terminál nemá tú istú satelitnú cestu |

Pri zaneprázdnenom termináli sa udalosť môže naplánovať do budúcnosti. Model nemá všeobecnú kapacitne obmedzenú paketovú frontu komerčného modemu, retry ani fragmentáciu nadlimitnej Globalstar správy. Pri handoveri nekontroluje spojitú rádiovú synchronizáciu, ale zhodu plánovej cesty pri doručení. Rovnaké ID cesty nie je dôkaz, že výhľad trval každú mikrosekundu medzi hraničnými vzorkami.

Dôležitý detail počítania: jeden event môže mať úspešný uplink a drop odpovede. Iný event môže vyvolať aj výstrahu a jej samostatný drop. Preto `drops` nemožno bez rozdelenia podľa fázy sčítať s `gateway_received` a očakávať presný počet pôvodných ponúk.

### 10.5 ACK a výstraha

`offer` zaznamená ponuku a zavolá uplink `hop`. Callback prijatia zvýši `gateway_rx_`, zapíše `GATEWAY_RX`, vytvorí `K1` a pošle downlink. Callback zvýši `ack_rx_` a zapíše `TERMINAL_ACK_RX`.

To je servisné potvrdenie terminálu. Pri RSU vlastníkom je RSU, nie pôvodné auto. V tejto vetve nie je následný osobný `I2V1` ACK do auta.

Ak prijatá CAM patrí sledovanému `alert_source`, report pochádza od iného vlastníka než cieľovej RSU a výstraha ešte nebola vydaná, vytvorí sa jediná `A1`. Po príjme na cieľovej RSU sa zavolá `Station::send_alert`. To použije reálny OCB broadcast s EtherType `0x88B6`. `service_on_alert_frame` pri prijímajúcom aute kontroluje presné bajty a zaznamená `CAR_ALERT_OCB_RX`.

Flag výstrahy sa nastaví pri vydaní. Neúspešná prvá výstraha preto nevyvoláva nekonečné automatické opakovanie na ďalších reportoch. Nie je tu detektor fyzickej nehody a prijatie nemení mobilitu.

## 11. RF link budget: nová výpočtová vrstva pracovného stavu

**Kód:** [u9_link_budget.py: evaluate](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_link_budget.py:114>), [u9_link_budget.py: _budget](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_link_budget.py:77>), [u9_service_native.py: write_json](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:132>).

Počas prípravy reportu pribudol `tools/u9_link_budget.py` a jeho zapojenie do `u9_service_native.py` a `bp_u9.py`. Zahrnutý je stav prečítaného kódu; jeho prítomnosť sama osebe neznamená uzavretú experimentálnu bránu F5. Register zachytáva odtlačky.

`evaluate` vytvorí `link-budget.json` po termináloch a časoch pre štyri úseky: `user_uplink`, `user_downlink`, `feeder_uplink`, `feeder_downlink`. User frekvencie preberá z profilov. Feeder frekvenciu vyžaduje ako explicitný predpoklad. ISL budget zostáva označený ako neznámy.

Voľnopriestorový útlm je:

```text
FSPL[dB] = 20 log10(4π × vzdialenosť × frekvencia / c)
```

Radiálna rýchlosť je rozdiel vzdialeností v čase, pokiaľ sa dá odvodiť z kompatibilných susedných záznamov. Doppler:

```text
f_D = −v_radial × f / c
```

Ak scenár dodá EIRP, prijímacie G/T, požadované C/N0 a interval ostatných strát, výpočet zostaví interval:

```text
C/N0 [dBHz] = EIRP [dBW] + G/T [dB/K] + 228,6 − FSPL − straty
rezerva [dB] = C/N0 − požadovaný prah C/N0
```

Interval sa skladá konzervatívne: najnižší EIRP a G/T s najvyššou stratou dávajú dolný výsledok. Neznámy vstup ostáva `unknown`, nie nulový ani automaticky PASS. Voliteľná odchýlková strata panelu je explicitná scenárová kvadratická aproximácia k uhlu 70°, nie nameraný diagram.

Pri vybranom prostredí sa štatistické straty počasia a vegetácie sčítajú iba vtedy, keď sú oba intervaly zadané. Ak nie, RF rezerva sa nedopočíta ako istá. Ak prostredie nie je vybrané, model túto vrstvu nepoužije a počíta nulový prídavný environmentálny člen; tento predpoklad sa eviduje.

**Výpočtová hranica:** v prečítanom C++ `ServiceModel::hop` sa `link-budget.json` nečíta. RF overlay sa uloží a verifier ho vie znovu vypočítať, ale jeho kladná alebo záporná rezerva sama v tomto prečítanom stave neprepína servisné doručovanie. Doppler vo výstupe tiež nie je automaticky vnútorná frekvenčná kompenzácia modemu. Výsledok preto treba uvádzať ako vedľa seba stojaci RF odhad a paketový výsledok, kým ďalšia implementácia výslovne nezmení kontrakt.

## 12. Historická generická SNS-3 DVB cesta

**Kód:** [u9-full-advanced.cc: SimulatorRuntime](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-full-advanced.cc:56>), [run_u9_advanced.py: run](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/run_u9_advanced.py:23>), [check_u9_advanced.py: ](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/check_u9_advanced.py:14>).

### 12.1 Kde sa nachádza

Režimy sa smerujú cez `u9_run_u4`, `run_u9_full_per_rsu` a `run_u9_advanced`. Hlavné zdroje sú `u9-parametric-leo-backhaul.cc`, `u9-full-integration-per-rsu.cc`, `u9-full-advanced.cc` a priama vetva `u9-full-direct-advanced.h`.

Tu sa vytvárajú skutočné modelové uzly a rozhrania SNS-3, IPv4/UDP sockety, RSU–UT LAN a point-to-point ISL. Satelitná user/feeder časť používa generické DVB mechanizmy SNS-3. V `combined_advanced` má RSU vlastný terminál a vybrané autá priame terminály.

### 12.2 Aplikačné správy a reťazec

Pozemná CAM ide cez GN/BTP/OCB. Prvá dekódujúca RSU podľa starej výberovej politiky vytvorí `ICB1`; report má väzbu na presné CAM bajty a identitu. Brána odpovedá `GRA1`, RSU pošle pôvodnému autu `I2V1`. Iná RSU môže dostať `ALR1`. Priama automobilová obálka je `CAM1` s odpoveďou `ACK2`.

Na rozdiel od nového C1/K1/A1 modelu tu teda existuje explicitný návrat RSU→auto pri reportovaní. Tieto správy sú projektové formáty, nie štandardné paketové formáty všetkých operátorov ani kompletná DENM služba.

### 12.3 Handover, sondy a fronty

Staršia vetva pracuje s explicitným serving/target/feeder stromom a riadenými zmenami terminálu. Má stav pripojenia, čas požiadavky, sondy a potvrdenia, rollback/drop správanie podľa variantu. Treba odlíšiť prepnutie jediného UT od historických experimentov s dvoma trvalo existujúcimi UT.

ISL má modelové smerové kapacity a fronty. `noisl` kontrolné zdroje vynucujú chýbajúci prenos, nejde o ďalší normálny operátorský režim. Doppler a steering v advanced priamej vetve fungujú aj ako aplikačná kvalifikačná brána; nemenia tým automaticky fyzikálne jadro SNS-3 na skutočný Starlink modem.

### 12.4 Prečo ju zachovávame

Má raw dôkazy, záporné kontroly a vedeckú hodnotu pre generický DVB experiment. Nový servisný backend odstraňuje niektoré architektúrne obmedzenia pevného podgrafu a dovoľuje servisne odlišné trasy. Nie je to automatická náhrada všetkých detailov SNS-3 dokonalejším PHY. Historické výsledky treba vyhodnocovať podľa ich vlastného manifestu a modelového kontraktu.

## 13. Výstupy: kde hľadať odpoveď na konkrétnu otázku

**Kód:** [u9_service_native.py: run](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:104>).

Príklad adresára nového hlavného behu:

```text
results/u9_runs/<nové-id>/
  inputs/
    scenario.json
    world.json
    demand.json
    ground.json
    orbit-reference.json       # podľa vybranej vetvy
  ground/
    run-manifest.json
    scenario/
      world.json
      waypoints.csv
      sumo/fcd.xml
      sumo/summary.xml
      cam.csv, rx.csv, ocb-*.pcap, ...
  service-model/
    scenario.json, ground.json, waypoints.csv
    routes.json, routes.csv
    link-budget.json           # pri novej RF overlay implementácii
    invocation.json
    manifest.json
    service-native/
      routes.csv
      cam.csv
      rx.csv
      dcc_decisions.csv
      phy_state.csv
      phy_drop.csv
      service_packets.csv
      ocb-*.pcap
      run.log, stderr.log
  physical-timeline.json
  run-manifest.json
```

Presné názvy PCAP a prítomnosť voliteľných súborov určuje runner. Historická DVB cesta má namiesto servisnej vetvy napríklad `full/native/baseline` a SNS-3 PacketTrace. Nehľadaj DVB PHY dôkaz v udalostnej servisnej CSV.

| Otázka | Prvý vhodný dôkaz |
| --- | --- |
| Bolo auto skutočne v dopravnej simulácii? | FCD, SUMO summary a waypointy |
| Vznikla CAM a aké mala bajty? | Servisné `cam.csv`, fáza `CAM_UPER_TX` |
| Bola ponúknutá pozemnému zariadeniu? | `GN_BTP_CAM_TX`, PCAP |
| Prijala ju RSU? | Servisné `rx.csv` |
| Ktorá RSU vytvorila report? | `RSU_REPORT_OFFER` |
| Aká bola satelitná cesta? | `routes.json` a cesta na servisnom TX/RX |
| Aký je RF predpoklad a rezerva? | `link-budget.json`, samostatne od doručenia |
| Dorazili pôvodné bajty do brány? | `GATEWAY_RX` s rovnakým payload hex |
| Vrátila sa odpoveď terminálu? | `TERMINAL_ACK_RX` |
| Dostalo auto výstrahu od cieľovej RSU? | `CAR_ALERT_OCB_RX` a rádiový záznam |
| Prečo sa správa stratila? | `DROP.reason` alebo pozemná PHY/GN stopa podľa úseku |

## 14. Menovatele a metriky bez omylov

**Kód:** [u9_service_native.py: verify](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:204>).

Jedna CAM môže mať viac pozemných prijímateľov, viac RSU reportov a aj priamu satelitnú ponuku. Preto počet servisných ponúk nie je počet áut ani počet jedinečných CAM.

Pre konkrétny servisný experiment možno počítať `gateway_received / offers`, ale znamená to úspech modelových ponúk cez zadaný servisný model. Nie je to dostupnosť operátora. Pri pozemnom PDR treba určiť množinu oprávnených dvojíc vysielač–prijímač a politiku ich zaradenia. Počet RX môže byť väčší než TX, keď jeden broadcast prijme viac uzlov.

Latenciu modelového uplinku možno odvodiť ako `t(GATEWAY_RX) − t(OFFER)`. Terminálový roundtrip je `t(TERMINAL_ACK_RX) − t(OFFER)`. Distribúcia výstrahy má iný endpoint a iný spúšťací okamih. Percentá s rôznymi endpointmi nie sú priamo porovnateľné.

Tvrdý koniec okna započíta aj modelové `outside_experiment`. Taký drop nemusí znamenať fyzikálnu nedostupnosť, iba že prenos nezapadá do definovaného experimentu. Krátke 6 s okná sú citlivé na tento okraj.

Na vedecké porovnanie treba fixovať dopyt, UTC/snapshot, politike, zdroj, endpoint a deadline, párovať varianty a opakovať seedy. Staršie U6/P5 analýzy riešia vlastné intervaly neistoty; neprenesú sa automaticky na ľubovoľný nový U9 výsledok.

## 15. Manifesty a skutočný rozsah verifikácie

**Kód:** [bp_u9.py: verify](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:365>), [u9_service_native.py: verify](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:204>).

### 15.1 Vrstvy integrity

Hlavný `run-manifest.json` pripne scenár, plán, zdrojové SHA-256, vybrané podmanifesty a súhrn. Nový servisný hlavný manifest má verziu 6; to je iný údaj než vstupné `scenario.schema_version=5`.

Servisný `manifest.json` má vlastný súpis súborov, parametre, zdroj runnera/plánovača/C++ a hash binárky. Hashe odhalia neskoršiu zmenu, ale samy nedokazujú fyzikálnu správnosť modelu. Zdroj a binárka sa evidujú; nie je to formálny dôkaz deterministického toolchainu.

### 15.2 Čo robí u9_service_native.verify

Verifier overí známe zdroje, hashe raw súborov a scenár. Prepočíta `plan`, porovná `routes.json` a obe CSV kópie. V novej overlay vetve znovu počíta aj RF výstup.

Zo servisných `cam.csv` a `rx.csv` zostaví očakávané priame a RSU ponuky. Kontroluje, že servisný report má správneho vlastníka, auto, čas a presné C1/CAM bajty. Potom kontroluje časové okno a usporiadanie stopy, povolený počet satelitov podľa služby, príslušnosť k časovej trase, Globalstar veľkosti, väzbu servisných udalostí na pôvodnú ponuku a súlad logového súhrnu s CSV.

Pri `route_changed_in_flight` môže akceptovať predchádzajúcu cestu ako dôvod zahodenia; nezamieňa ju za úspešný aktuálny hop. Kontroluje jednoznačnosť príjmov brány/ACK a základné poradie fáz.

**Dôležitá hranica:** prepočítanie používa rovnaký implementovaný plánovací algoritmus. Je nezávislé od uloženého výsledku, ale nie nezávislý orbitálny solver alebo meranie. Verifier nie je úplný formálny dôkaz každého očakávaného callbacku, každej serializačnej rovnice ani všetkých možných poškodení. Pozemný a historické DVB checkery pridávajú vlastné kontroly; rozsah treba viazať na konkrétny checker.

### 15.3 Historické zdroje a zmeny projektu

V `bp_u9.verify` je rozsiahla kompatibilitná vetva pre presné staré hashe a `tools/legacy` snapshoty. Je to technický dlh aj spôsob zachovania dôkazov po vývoji. Neznamená to, že ľubovoľný starý výsledok sa automaticky prehlási za platný podľa dnešného algoritmu.

Niektoré archívy a manifesty obsahujú presné cesty. Presun projektu môže vyžadovať reprodukciu alebo podporovanú obnovu, nie len zmenu jednej cesty v JSON. Výsledky sa nemajú ručne opravovať, aby vyšli.

## 16. Replay: ako sa raw stopa zmení na animáciu

**Kód:** [u9_editor_api.py: verified_run](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:52>), [u9_editor_api.py: replay](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:453>), [u9_editor_api.py: packet](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:529>).

`verified_run` používa cache úplného overenia. Kľúč zahŕňa manifest a stav výstupných aj zdrojových súborov vrátane legacy snapshotov. Pri zmene musí audit prebehnúť znovu. Cache má obmedzený počet položiek.

`replay` načíta waypointy a vyberie správnu stopu. Ak existuje servisná stopa, `_service_replay` z nej vytvorí udalosti a spojnice. Spojnice úspešnej satelitnej cesty sa skladajú aj spätne podľa `GATEWAY_RX` alebo terminálového príjmu; nie sú to nezávislé jednotlivé satelitné NetDevice RX udalosti. Preto animovaná čiara znamená zobrazenú modelovú cestu.

Pri veľkom behu sa pozície preriedia približne pod 50 tisíc bodov, servisné udalosti majú limit 30 tisíc a spojnice 120 tisíc. Celkové počty sa vracajú osobitne. Ak je udalostí viac, raw výstup sa nestráca; iba sa neposiela celý do jednej UI odpovede.

Pri novom časovom kontrakte sa odpočíta 10 s nábehu. Detail `packet` otvorí konkrétny event a vráti najviac 2000 krokov, s ukážkou raw hex do 512 znakov, teda 256 B. Je to limit prezentácie, nie skrátenie uloženého paketu.

Mapa a glóbus majú tiež náhľadový režim pred behom. Náhľad konštelácie nie je raw výsledok paketového experimentu. Celý vykreslený katalóg nie je počet terminálom používaných družíc.

## 17. Build, závislosti a pracovné adresáre

**Kód:** [u9_run_ground.py: compile_source](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_run_ground.py:45>).

`u9_run_ground.compile_source` používa g++, C++17, statické Vanetza knižnice a ns-3.38 moduly core/network/mobility/propagation/wifi/wave/buildings. Linkuje projektový checkout a nastaví RPATH do jeho knižníc. Nový servisný zdroj používa ten istý build helper; názov vytvorenej binárky môže stále niesť `v5-ground-cam-dcc`, hoci zdroj bol dočasne zvolený ako `u9-service-native.cc`.

SNS-3 moduly sa používajú pri DVB vetve; ich prítomnosť v checkout-e neznamená, že sú súčasťou servisného modelu. Systémový ns-3 ani odstránený ns-3.48 nie sú správnym build základom.

Python vyžaduje projektové závislosti pre NumPy, Astropy, SGP4 a ostatné nástroje. SUMO/netconvert sú samostatné spustiteľné programy. Pre obnovu slúžia projektové skripty a requirements súbory; prenesená CMake cache alebo binárka nie je nový dôkaz správneho buildu.

Kvôli medzerám v absolútnej ceste používajú runnery dočasný krátky alias bez medzier. Nie je to druhý projektový runtime, iba adaptér argumentov pre ns-3 CommandLine. Raw výsledok ostáva v pôvodnom adresári.

Aktívny koreň je `obnova/Bakalarska praca/`. Rodičovský adresár a prenosový archív nie sú zdrojovým koreňom. Prenosná kópia na ploche môže byť samostatný stav; report ju automaticky nestotožňuje s pracovným stromom.

## 18. Ako sa orientovať pri čítaní kódu

Odporúčané poradie čítania:

1. `bp_u9.service_primary`, `preflight` a `run`: zistíš, čo sa naozaj spúšťa.
2. `u9_prepare_cam.prepare`: pochopíš vstupné jednotky, čas a identity.
3. `u9-service-native.cc`: `main`, `Station::check`, `send_cam`, `receive`, `indicate`.
4. `u9_dynamic_service.plan` a `_path`: pochopíš pôvod trasy.
5. `ServiceModel::offer`, `hop`, `route_at`: uvidíš, kedy paket prejde a kedy padne.
6. `u9_service_native.verify`: zistíš, čo výsledok skutočne dokazuje.
7. `u9_editor_api.replay` a `packet`: pochopíš rozdiel medzi raw stopou a obrazovkou.
8. Až potom `u9-full-advanced.cc` a jeho checkery: nebudeš miešať staré a nové správy.

Pri každej funkcii si polož tri otázky: **Aké dáta dostane? Čo zmení alebo naplánuje? Aký raw dôkaz po nej zostane?** Toto je praktickejšie než snažiť sa naraz pamätať celý repozitár.

## 19. Príklad rozboru jednej správy

Predstav si auto `car0`, RSU `rsu0`, ďalšiu RSU `rsu1` a priamy terminál v `car0`.

1. `Station::check` rozhodne, že vzniká CAM. `encode_cam` ju zakóduje.
2. `send_cam` zaznamená `CAM_UPER_TX`. Priamy terminál vytvorí `DIRECT_OFFER-car0-...`.
3. Pozemný GN/BTP rámec ide cez OCB. Ak ho `rsu0` dekóduje, vznikne `rx.csv` záznam a `RSU_REPORT_OFFER-rsu0-...`.
4. Keď ho dekóduje aj `rsu1` s povoleným backhaulom, môže vzniknúť ďalšia samostatná ponuka. Jedna CAM tak už má tri servisné vetvy.
5. Každý terminál má vlastnú trasu, obsadenosť a čas príjmu. Môže uspieť priama vetva a zlyhať RSU vetva, alebo naopak.
6. Pri každom úspešnom prijatí brána vytvorí K1. Príjem na RSU sa nezapočíta ako pozemný ACK v aute.
7. Jedna vhodná správa referenčného zdroja môže spustiť A1 k cieľovej RSU. Až následný OCB príjem je upozornenie auta.
8. Verifier musí nájsť CAM pôvod, zhodné bajty a prípustnú časovú cestu. UI vyberie časť týchto udalostí na zobrazenie.

Ak by si videl „3 gateway RX“, nie sú to automaticky tri rôzne dopravné udalosti. Ak by si videl „0 cars alerted“, nemusí to znamenať nulový satelitný príjem: výstraha mohla byť nezadaná, nedoručená cieľovému terminálu alebo neprijatá pozemným rádiom.

## 20. Stav schopností a zostávajúce medzery

| Oblasť | Čo je implementované v prečítanom stave | Čo sa z toho ešte nesmie odvodiť |
| --- | --- | --- |
| Doprava | SUMO, mapové trasy, FCD a úplné pohybové okno | Kalibrácia na reálnu dopravnú intenzitu alebo účinok výstrahy |
| ITS-G5 | CAM UPER, GN/BTP, OCB MAC/PHY, raw príjmy | Kompletná ETSI interoperabilita, PKI, DENM alebo C-V2X |
| Orbity | Hashovaný OMM, SGP4, EOP, časová geometria | Aktívna služba a beam |
| Antény | Verejné obálky a explicitná montáž FHP | Plný nameraný ziskový diagram všetkých terminálov |
| Prekážky | Lokálny DEM a uzavreté OSM budovy, neisté výšky | Úplný 3D geodetický model, difrakcia a všetky multipolygóny |
| Servisná cesta | Rozlíšená architektúra, najviac jeden ISL, terminálové prepnutia | Skutočný routing/scheduler operátora |
| Servisné pakety | Originálne bajty, časovanie, ACK a výstraha v ns-3 čase | Skutočný modem, retransmisie, zdieľaná beam kapacita |
| RF overlay | FSPL, odvodený Doppler, voliteľné intervaly C/N0 | Automatická RF podmienka doručenia v prečítanom C++ jadre |
| Overenie | Hashe, pôvod správ, replan a kontrola stopy | Formálny dôkaz celej implementácie alebo externá validácia |
| UI | Návrh, spustenie, overený replay a detail | Úplný neskrátený raw záznam každej udalosti v animácii |

Na rozšírenie treba vždy vybrať konkrétnu vrstvu. Ak chceme reálne rádiové tvrdenia, treba doložiť RF a modemové parametre a validovať. Ak chceme dopravný prínos, treba detektor a spätnú väzbu mobility. Ak chceme nové typy správ, treba aplikáciu, formát, identity a checker. Pridanie ďalšieho formulárového poľa samo o sebe tieto vrstvy neimplementuje.

## 21. Ostatné vrstvy repozitára a historické generácie

Nie každý súbor v repozitári sa spustí pri dnešnom kliknutí na Run. Nasledujúca mapa vysvetľuje, prečo je v projekte toľko runnerov a checkerov.

| Rodina | Úloha a miesto v dnešnom systéme |
| --- | --- |
| Pôvodné piloty | `run_pilot.sh`, `run_sns3_pilot.sh`, `vanet-sns3.cc`: prvé integračné a vizuálne dôkazy; samostatné historické cesty |
| `editable-v2-*`, OSM a two-LEO sondy | Overovanie CAM/OCB, geometrie, dvoch LEO, roundtripu a záporných kontrol pred všeobecným U9 |
| P0–P6 | Experimentálny kontrakt, raw reťazce, mestské/stratové experimenty, jeden UT handover, servisné profily, finálna párovaná matica a obnova |
| V0–V8 | Modulárne kontrakty a samostatné vrstvy geometrie, generického DVB, pozemného rádia, servisných alternatív, výsledkov a vydania |
| U0–U8 | Integrácia vrstiev do spoločnej cesty, premenné RSU, dynamický pool, RF/ISL parametre, servisný bridge, výsledky, ovládanie a release |
| U9 | Aktuálny editor, jednotlivé politiky zariadení, rozsah 2–120 s, mapa/glóbus a nové servisné udalostné jadro |
| F1–F4 | Pripnuté dráhy, časové a servisné cesty, anténne obálky a lokálne prostredie v novej U9 ceste |
| RF/F5 pracovná vrstva | Nový audítovateľný link-budget overlay; rozsah opísaný v kapitole 11 |
| `analyze_p5_matrix.py`, `analyze_u6_results.py`, `analyze_v7_results.py` | Analýzy vlastných výsledkových kontraktov; nepripisujú sa automaticky novému servisnému behu |
| `scripts/portable_*`, `pack_u9_portable.py` | Príprava čistého prenosného zdroja, oddeleného workspace a obnovy prostredia |
| `release/`, V8/U8 release skripty | Verzionované odovzdávacie a smoke postupy starších kontraktov |
| `patches/` | Projektové zásahy do upstream SNS-3, napríklad overlap/drop a single-UT handover; podstatné pre DVB reprodukciu |
| `data/inputs`, `data/orbits`, `data/derived` | Pôvodné scenáre, archivované dráhy a odvodené/cachované dáta |
| `results/`, `docs/experiments/` | Surové dôkazy a ich ľudský výklad; samotný starý súhrn nie je nový výsledok |
| `thesis/` | Rukopis bakalárskej práce; report ho automaticky neprepisuje |

Staršie servisné obaly U5/V6 modelujú IP alebo MO/MT na hranici služby a replay. Nový `u9-service-native.cc` na rozdiel od nich prijíma CAM callbacky priamo zo spoločného ns-3 behu. Historický service replay, nový servisný engine a generický DVB sú tri odlišné pojmy.

Externé knižnice v `vendor/` poskytujú rozsiahle vlastné modely. Tento report opisuje API a konkrétnu konfiguráciu, ktorú z nich náš projekt využíva. Netvrdí, že implementujeme všetky modely dostupné v ns-3, Vanetza alebo SNS-3.
