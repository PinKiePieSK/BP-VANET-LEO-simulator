# Katalóg vstupov editora a ich účinku v simulácii

**Stav k 5. 11. 2026.** Čítaj spolu s [vysvetlením celého simulátora](studium-bp-ako-funguje-simulator.md). Toto je mapa **aktuálneho** vstupu, nie historických vetiev projektu. Najvyššia autorita pre povolené kľúče a rozsahy je [`bp_u9.preflight`](../tools/bp_u9.py), [`u9_editable_scenario.validate`](../tools/u9_editable_scenario.py) a pri prostredí [`validate_environment`](../tools/u9_local_environment.py). Keď zmeníš kód, skontroluj tabuľku znova.

Značky: **P** = zmení vykonávaný pohyb alebo pakety; **K** = kontrola, výber, pôvod dát alebo audit, bez samostatného paketu; **Z** = len editor či zobrazenie. „Predvolené“ znamená hodnotu doplnenú konkrétnou funkciou, nie všeobecné odporúčanie.

## 1. Tri súbory, ktoré editor uloží

[`u9_editor_api.save`](../tools/u9_editor_api.py) zapisuje `world.json`, `demand.json` a scenár v `config/scenarios/`. `world` určuje mapu, dopravný model a RSU; `demand` určuje konkrétne autá; scenár určuje sieť, udalosti a satelit. Pred behom [`bp_u9.preflight`](../tools/bp_u9.py) prepíše `world.vehicles` hodnotou `demand.vehicles`, takže pre konkrétny beh sú autá z **demand**. `world.flows` a `world.network_execution` sú deklaratívne údaje editora: `execution="not_implemented"` v nich nevytvára pakety. Tie vznikajú v aktívnom C++ engini podľa scenára.

Príklad čítania cesty v kóde: `scenario['radio']['tx_power_dbm']` = výkon pozemného vysielača; `world['rsus'][0]['x_m']` = lokálna súradnica prvej RSU. `[]` tu znamená „vyber položku“.

## 2. `world.json`: plocha, čas a súradnice

| Pole | Rozsah/jednotka a logický význam | Účinok a miesto v kóde |
| --- | --- | --- |
| `schema_version` | Presne `2`. | K; kontrola formátu v [`validate`](../tools/u9_editable_scenario.py). |
| `extent_m` | Voliteľné `2000` alebo `4000` m; štandardná štvorcová plocha. | P; hranice lokálnych objektov a výrez mapy. |
| `width_m`, `height_m` | Voliteľná dvojica celých čísel `500…4000` m; oba naraz; nahrádza rozmery z `extent_m`. | P; hranice súradníc a výrez prostredia. |
| `map_source` | `manual` alebo `osm_live`; predvolené `manual`. | P; `osm_live` volí odlišné nastavenie vstupnej rýchlosti a mapovanie kliknutej polohy na SUMO pruh v [`make_inputs` a `align_route_positions`](../tools/u9_editable_scenario.py). |
| `network_execution` | Presne `schema_only`. | K; starší world formát sám nemá sieťovú väzbu. Aktívny runner sieť spustí samostatne. |
| `simulation.duration_s` | World povoľuje `1…300` s, násobok kroku; aktuálny sieťový beh vyžaduje **celé `2…120` s**, pri satelite aspoň 6 s. | P; dĺžka dopravného a paketového okna. [`bp_u9.runtime_inputs`](../tools/bp_u9.py) pridá `0,3 s` na SUMO dobeh. |
| `simulation.step_s` | World `0,1…1` s; aktuálny beh nastaví **0,1 s**. | P; SUMO FCD a rádiové waypointy každých 100 ms. |
| `simulation.seed` | World `0…2³¹−1`; aktuálny beh ho prepíše scenárovým `seed`. | P; deterministické dopravné generovanie. |
| `simulation.utc_origin` | ISO 8601 UTC; aktuálny beh prepíše scenárovým `utc_origin`. | P; absolútny čas pre orbitu a DENM. |
| `georeference.frame` | Presne `WGS84_ENU`. | P; lokálne **x na východ, y na sever**, metre. |
| `georeference.anchor_x_m`, `anchor_y_m` | Lokálny bod v rámci šírky/výšky mapy. | P; tento bod zodpovedá zadanému zemepisnému bodu. |
| `georeference.latitude_deg`, `longitude_deg`, `height_m` | Zemepisná šírka `−90…90°`, dĺžka `−180…180°`, výška `−500…9000 m`. | P; referencia ENU↔WGS84 v [`simulator_coordinates.py`](../tools/simulator_coordinates.py); polohy terminálov a CAM. Lokálne `up=0` pri prevode auta **nie je digitálny model výšky vozovky**. |

Príklad: kotva `(2000,2000)` na zemepisnom bode a auto `(2100,2000)` znamenajú približne 100 m na východ. Pri kreslení plátno prevracia y; JSON nie. FCD po spracovaní cez `netconvert` môže mať inú polohu než pôvodné kliknutie, hlavne v križovatke. [Prevod FCD na waypointy](../tools/u9_prepare_cam.py).

### Model jedného typu auta: `simulation.vehicle_model`

Celý objekt je voliteľný; ak chýba, [`make_inputs`](../tools/u9_editable_scenario.py) použije `accel=2`, `decel=4,5`, `sigma=0`, `length=5`, `width=1,8`, `minGap=2,5`, `speedFactor=1`, `manual_max_speed=40` v jednotkách nižšie. Ak objekt uvedieš, potrebuje **všetkých osem** kľúčov.

| Pole | Povolené | Ako sa použije |
| --- | --- | --- |
| `accel_mps2` | `0,1…10 m/s²` | P; SUMO `vType.accel`, schopnosť zrýchľovať. |
| `decel_mps2` | `0,1…15 m/s²` | P; SUMO `decel`, bežné spomalenie. |
| `sigma` | `0…1` | P; variabilita správania predvoleného SUMO car following modelu. |
| `length_m`, `width_m` | `1…20 m`, `0,5…3 m` | P; rozmery vozidla v SUMO; následne polia CAM. |
| `min_gap_m` | `0…10 m` | P; minimálny odstup v SUMO. |
| `speed_factor` | `0,1…2` | P; násobiteľ želanej rýchlosti v SUMO. |
| `manual_max_speed_mps` | `0,1…60 m/s` | P; maximálna rýchlosť spoločného `vType` len v `manual`; pri `osm_live` sa maxSpeed vytvorí osobitne z `depart_speed_mps` auta. |

Projekt explicitne neurčuje názov SUMO `carFollowModel`; platí model predvolený v použitej verzii SUMO. Vlastné sú hodnoty `vType` a generovanie XML, fyziku pohybu počíta SUMO. [SUMO car following](https://sumo.dlr.de/docs/Car-Following-Models.html).

## 3. `world.roads`, `demand.vehicles` a `world.rsus`

| Pole | Jednotky a význam | Účinok |
| --- | --- | --- |
| `roads.nodes[]` | `2…30000` križovatkových/koncových uzlov. Každý má `id`, `x_m`, `y_m` v rámci plochy. | P; [`make_inputs`](../tools/u9_editable_scenario.py) píše `road.nod.xml`. |
| `roads.segments[]` | `1…30000` cestných úsekov; `id`, `from`, `to` sú ID uzlov. | P; orientovaný graf pre trasy. |
| `segments[].shape` | `2…30` bodov `[x_m,y_m]`, prvý/posledný sú príslušné uzly s toleranciou 0,01 m; každý diel aspoň 1 m, celok aspoň 2 m. | P; geometria SUMO hrany, potom jazdná poloha a rádio. |
| `segments[].speed_limit_mps` | `1…40 m/s`. | P; SUMO `edge.speed`; obmedzenie cestnej rýchlosti. |
| `segments[].lanes_each_direction` | Celé `1…3`. | P; počet pruhov **v každom povolenom smere**. |
| `segments[].oneway` | Voliteľné bool, predvolené `false`. | P; pri `true` nevznikne `reverse` SUMO hrana, trasa v protismere sa odmietne. |
| `segments[].osm_way_id`, `name`, `road_class` | Voliteľné OSM ID ako desiatkové číslice v texte, meno do 120 znakov, trieda do 40. | K/Z; pôvod a označenie cesty, samotný paketový engine z nich nerozhoduje. |
| `vehicles[]` | V aktuálnom behu `demand.vehicles`; aspoň **dve** autá. | P; každé sa stane SUMO autom a ITS rádiovým uzlom. |
| `vehicles[].id` | Jedinečné ID, aj vo výsledných stopách. | P/K; viaže waypointy a stanice. |
| `vehicles[].depart_s` | World `0…duration−step`; aktuálny beh vyžaduje **0 s**. | P; všetky rádiá sú pripravené na začiatku komunikačného okna. |
| `vehicles[].depart_speed_mps` | `0…40 m/s`. | P; v manuálnej mape počiatočná rýchlosť; pri `osm_live` `vType.maxSpeed` a `departSpeed="max"`, takže skutočnú vstupnú rýchlosť upraví SUMO podľa pruhu. |
| `vehicles[].route[]` | `1…200` nadväzujúcich krokov `{segment,direction}`; smer `forward/reverse`. | P; poradie SUMO hrán. Nepripojené úseky a jazda proti `oneway` sa odmietnu. |
| `vehicles[].depart_pos_m` | Voliteľná vzdialenosť od začiatku prvej hrany; predvolené 0; najviac dĺžka prvého úseku mínus 20 m. | P; kliknutá východisková poloha, pri OSM sa premietne na skutočný SUMO pruh. |
| `vehicles[].arrival_pos_m` | Voliteľná vzdialenosť na poslednej hrane; v rámci jej dĺžky. | P; koncová poloha. Po príchode sa auto do konca rádiového okna drží zastavené. |
| `vehicles[].technologies` | Neprázdny zoznam unikátnych hodnôt z `its_g5`, `cellular_v2x`, `ip_backhaul`, `satellite_terminal`; auto nesmie mať `satellite_terminal`, aktuálny beh vyžaduje `its_g5`. | K; deklarované schopnosti. Samotný záznam `cellular_v2x` **nespustí C-V2X**; aktuálna rádiová cesta je ITS-G5. Účinné zapnutie určuje `node_policy`. |
| `rsus[]` | `0…512` v aktívnom behu. | P; pevné cestné jednotky. Satelitný beh potrebuje aspoň jednu s backhaulom. |
| `rsus[].id`, `x_m`, `y_m` | Jedinečné ID; lokálne metre v rámci mapy. | P; poloha pozemného rádia a prípadného satelitného UT. |
| `rsus[].technologies` | Rovnaký deklaratívny zoznam; aktuálny beh vyžaduje `its_g5`. | K; `satellite_terminal` tu ešte samo osebe nezapína prevádzku, rozhoduje `node_policy.rsus[id].satellite_backhaul`. |

`netconvert` zostrojí sieť; `sumo` vypíše FCD. [`u9_prepare_cam.py`](../tools/u9_prepare_cam.py) z FCD pripraví per auto čas, lokálne `x/y`, WGS84 `lat/lon`, rýchlosť, smer, zrýchlenie, yaw, svetlá a rozmery. Tieto údaje **sa menia v čase podľa SUMO**, nie podľa stálej hodnoty `depart_speed_mps`. [Význam FCD podľa SUMO](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html).

### `demand.json`

| Pole | Význam |
| --- | --- |
| `schema_version` | Presne `1` (K). |
| `kind` | `synthetic_trips` alebo `measured_trips` (K). Merané trasy vyžadujú odkaz na zdroj; editorom vygenerované trasy sú syntetické. |
| `provenance` | Neprázdny text; pri `measured_trips` sa musí začínať `https://` (K). |
| `vehicles` | Tie isté polia áut z tabuľky vyššie; **tento zoznam vstupuje do aktuálneho behu** (P). |

### `world.flows[]`: opis zámeru, nie vykonávané smerovanie

World vyžaduje `1…100` záznamov. Každý obsahuje `id`, `source`, `target` (ID uzla alebo `broadcast`), `technology`, `message_type` (`CAM`, `DENM`, `IP_REPORT`, `CUSTOM`) a `execution="not_implemented"`. Validátor kontroluje existenciu uzlov a deklarovanú technológiu; pre CAM/DENM povoľuje iba pozemné V2X technológie. **Žiadna z týchto hodnôt sama neurčuje adresáta satelitného mosta ani nevysiela správu.** Aktívne správanie tvorí `scenario.denm_events`, `source_id`, `rsu_id`, `alert_target_rsu`, `node_policy` a C++ aplikácia. [`validate`](../tools/u9_editable_scenario.py), [`u9-full-integration-per-rsu.cc`](../src/u9-full-integration-per-rsu.cc).

## 4. Globálna OSM vrstva `world.map_objects` a UI

`map_objects` je voliteľný objekt verzie `1`, ktorý udržiava editovateľné **pôvodné WGS84** body pri `osm_live`. Cestný `roads[]` má `id`, `coordinates` ako 2…30 dvojíc **`[longitude,latitude]`**, `speed_limit_mps`, `lanes_each_direction` a voliteľné `oneway`, `osm_way_id`, `name`, `road_class`. Auto `cars[]` má `id`, `longitude_deg`, `latitude_deg`, `road_id`, `depart_s`, `depart_speed_mps`, `direction`, `technologies`, `ground_mode`, `source`; môže mať `route[]` a `arrival_pos_m`. RSU `rsus[]` má `id`, zemepisnú dĺžku/šírku, `technologies`, booleany `ground`, `satellite_backhaul`, `primary`, `alert_target`. `sources[]` nesie pôvod OSM výrezu: `bbox`, `retrieved_at`, `sha256`, `provider`, `tiles`, `ways`, `roads`, voliteľný `dataset_sha256`. Pozri [presnú kontrolu globálnych objektov](../tools/u9_editable_scenario.py) a [prevod OSM grafu](../tools/u9_osm_road_graph.py).

Toto je **zdroj editovania a pôvodu**. Skutočný SUMO a ns-3 beh používa projekciu do `world.roads`, `demand.vehicles`, `world.rsus` a účinnú `node_policy`. Pri rozpore treba sledovať uložené súbory v `results/simulations/<run_id>/inputs/`, nie iba ikonu na mape.

Ovládacie prvky `spawn_count` a `traffic_trip_percent` v [`technical-parameters-bridge.js`](../viewer/technical-parameters-bridge.js) menia **budúce generovanie áut/trás**; už vytvorenému behu nič spätne nepridajú. Priblíženie, zvolená vrstva, glóbus a kruh okolo RSU sú vizualizácia. Napríklad kruh 300 m v [`viewer/simulator.js`](../viewer/simulator.js) **nie je dosah odvodený z rádiového modelu**.

## 5. `scenario.json`: voľba behu, pozemné rádio a politika

Scenár má **presne** horné kľúče v tabuľke; ďalšie nie sú povolené. Verzia je `7`. [Úplný `preflight`](../tools/bp_u9.py).

| Pole | Povolené/význam | Účinok |
| --- | --- | --- |
| `schema_version` | `7`. | K; správna aktívna schéma. |
| `scenario_id` | Malé písmeno na začiatku, potom malé písmená/číslice/pomlčky, 3…48 znakov. | K; identita behu. |
| `world_template`, `demand` | Projektové cesty **pod `data/inputs/`**, bez `..`. | P; načítanie konkrétneho sveta a vozidiel cez [`simulator_inputs.project_input`](../tools/simulator_inputs.py). |
| `source_id` | ID existujúceho auta s aktívnym pozemným rádiom. | P; primárna stanica a predvolený zdroj DENM. |
| `rsu_id` | ID zdrojovej RSU; `""` iba ak RSU nie sú. | P; jednotka, z ktorej môže začať most. |
| `alert_target_rsu` | Text; pri satelitnom cieli iná aktívna RSU. | P; vzdialená RSU pre opätovné miestne vyslanie DENM. |
| `seed`, `ns3_run` | Každé celé `1…2³¹−1`. | P; deterministické zdroje náhodnosti SUMO/ns-3; číslo behu umožní opakovanie. |
| `utc_origin` | Presne `YYYY-MM-DDTHH:MM:SSZ`. | P; absolútny čas orbitalnej geometrie a časových polí správ. |
| `sample_count` | `20…1200`, presne `duration_s × 10`. | P; počet 100 ms vzoriek. |
| `mode`, `time_policy` | Presne `unified`, `ready_at_t0_full_duration`. | K/P; aktuálna vetva a spoločné časové okno; autá majú `depart_s=0`. |
| `satellite_enabled` | Bool, presne zodpovedá tomu, či niektorá RSU má `satellite_backhaul=true`. | P; volí pozemný alebo integrovaný ns-3/SNS-3 beh. |
| `radio`, `link_policy`, `satellite`, `node_policy`, `denm_events` | Vnorené objekty nižšie. | P/K podľa konkrétneho poľa. |

### `radio`

| Pole | Jednotky, rozsah | Kto a ako ho používa |
| --- | --- | --- |
| `mode` | `friis` alebo `urban_los`. | P; [`simulator_inputs.ground_config`](../tools/simulator_inputs.py) vyberie model útlmu ns-3. Ak existujú budovy, [`bp_u9.template`](../tools/bp_u9.py) účinne prepne na `urban_osm_building`. |
| `tx_power_dbm` | `0…33 dBm`. | P; výkon ITS-G5 vysielača v ns-3. |
| `noise_figure_db` | `0…20 dB`. | P; šum prijímača v ns-3. |
| `rate_mbps` | Voliteľné `3/6/12/24 Mbit/s`, predvolené 6. | P; modulácia/dátová rýchlosť 10 MHz 802.11p PHY. |
| `channel_number` | Voliteľné `172,174,…,184`, predvolené 180. | P; stredová frekvencia `5000+5×channel_number` MHz a kanál. |
| `tx_gain_dbi`, `rx_gain_dbi` | Voliteľné `−20…20 dBi`, predvolené 0. | P; anténne zisky pri pozemnom linku. |
| `shadowing` | Voliteľné bool, predvolené `false`; s `friis` musí byť `false`. | P; dodatočná náhodná zložka podporovaného urban modelu. Samotná voľba nie je 3D stavba. |

Účinná cesta je `radio` → [`ground_config`](../tools/simulator_inputs.py) → [`u9_run_ground.py`](../tools/u9_run_ground.py) alebo [`u9_native_editor.py`](../tools/u9_native_editor.py) → C++ `WifiPhy`/propagation model. **Naša aplikácia volí parametre a model; ns-3 rieši MAC/PHY prenos a pravdepodobnosť príjmu.**

### `node_policy`

| Pole | Význam v aktívnom engini |
| --- | --- |
| `cars[id].ground="all"` | Auto komunikuje s autami aj RSU cez ITS-G5. Povinné pre zdroj satelitnej DENM. |
| `cars[id].ground="cars"` | Povolená komunikácia s autami; RSU aplikačne ignoruje príjem z tohto auta. Fyzické zariadenie môže byť vytvorené. |
| `cars[id].ground="off"` | Auto sa aplikačne nevysiela ako aktívna stanica; nesmie byť zdrojom DENM. |
| `rsus[id].ground` | Bool, povolenie miestnej ITS-G5 činnosti RSU. |
| `rsus[id].satellite_backhaul` | Bool, vyžaduje `ground=true`; povoľuje aplikačný satelitný most danej RSU. V natívnom modeli môže topológia vytvoriť UT/LAN aj pre neaktívnu RSU; filter zabraňuje aplikácii použiť ho. |

Objekt musí mať **presne** mapy `cars` a `rsus`, po jednom zázname pre každé ID. [`unified_policy`](../tools/bp_u9.py), [filtre v C++](../src/u9-full-integration-per-rsu.cc).

### `denm_events[]`

Najviac 64 udalostí. Každá má **presne** šesť povinných polí a voliteľné `source_id`. [Validácia životného cyklu](../tools/bp_u9.py), [tvorba správy](../src/u9-full-integration-per-rsu.cc).

| Pole | Jednotky/význam | Skutočné rozhodnutie |
| --- | --- | --- |
| `source_id` | Voliteľné ID auta; inak scenárové `source_id`. | P; ktorá stanica vytvorí DENM. |
| `at_s` | Reálne číslo `0 ≤ t < duration_s`. | P; kedy aplikácia vyvolá `new/update/cancel`, nie výsledok detekcie zo SUMO. |
| `sequence` | Celé `0…65535`. | P; s ID zdroja identifikuje akciu `actionId`. |
| `operation` | `new`, `update`, `cancel`. | P; `new` vytvorí akciu, `update` mení ešte platnú, `cancel` ju ukončí. Poradie a platnosť kontroluje preflight. |
| `validity_s` | Celé `1…86400 s`. | P; ako dlho je správa platná, používa sa pri tvorbe a príjme. |
| `radius_m` | Celé `1…1780 m`. | P; polomer kruhu GeoBroadcast vo Vanetze. **Nie** maximálny dosah vysielača; fyzický príjem počíta ns-3. |
| `repetition_ms` | `0` alebo celé `100…60000 ms`. | P; náš C++ rozvrh opakovaní; `0` znamená bez opakovania. |

Náš kód používa modelový typ udalosti `trafficCondition/trafficJam`, pozíciu auta a plánovaný čas. Vanetza ju UPER zakóduje, vloží do BTP portu 2002 a GeoNetworking GBC s najviac 3 skokmi; ns-3 pošle skutočné rádiové rámce. Prijímacia RSU mostuje iba vyhovujúcu prijatú správu podľa `node_policy`, deduplikácie a cieľa. [ETSI DENM](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.03.01_60/ts_103831v020301p.pdf).

## 6. Satelitné polia a čo znamená „dostupné“

Pri `satellite_enabled=true` je povinný objekt `satellite` s `orbit_group`, `orbit_snapshot`, `dynamic_physical=true`, `gateway` a `mask_deg`. Povolené sú iba nižšie uvedené ďalšie polia. [Preflight](../tools/bp_u9.py), [výber topológie](../tools/u9_native_editor.py), [orbity](../tools/simulator_orbits.py).

| Pole | Jednotky/význam | Účinok |
| --- | --- | --- |
| `orbit_group` | `iridium-NEXT`, `globalstar`, `starlink`. | P/K; profil frekvencií, elevácie, antény a prípustnej topológie. |
| `orbit_snapshot.path`, `manifest_sha256` | Cesta `data/orbits/<archív>` a 64 hex znakov SHA-256 manifestu. | P/K; pripnuté OMM dráhy pre konkrétny UTC čas; hash bráni tichej výmene vstupu. [`validate_pin`](../tools/u9_orbit_source.py). |
| `dynamic_physical` | Presne `true`. | K/P; podmienka natívneho integrovaného behu. |
| `gateway` | `[latitude_deg,longitude_deg,height_m]`; šírka `−90…90°`, dĺžka `−180…180°`; editor pri výške povoľuje `−500…9000 m`. | P; **modelová** brána pre feeder link a SNS-3, nie dôkaz umiestnenia operátorskej GW. |
| `mask_deg` | `0 ≤ uhol < 90°`. | P; minimálna elevácia; účinné minimum je maximum masky a profilu služby/antény. |
| `catalog_ids` | Voliteľný zoznam NORAD ID. Prázdny zoznam znamená automatický výber **jednej** družice pre aktívne RSU a GW počas celého okna. | P; explicitný viacdružicový výber musí prejsť geometriou a topológiou. |
| `isls` | Dvojice indexov do `catalog_ids`; pre Globalstar ISL nepovolené. | P; hrany modelovej medzisatelitnej siete SNS-3. |
| `initial_serving_sat`, `handover_target_sat`, `feeder_sat` | Indexy družíc v explicitnom `catalog_ids`. | P; počiatočné pripojenie UT, cieľ handoveru a družica pri feeder/GW. |
| `beam_gain_dbi` | Diagnostický/modelový zisk anténnej predlohy. Editor povoľuje `−10…60 dBi`, ale [`simulator_satellite_inputs.generate`](../tools/simulator_satellite_inputs.py) odmietne hodnotu **nad 50 dBi**. | P; vstup do SNS-3 predlohy, **nie** overený aktívny operátorský lúč. Rozsah 50…60 v UI je aktuálny nesúlad, beh s ním nevznikne. |
| `ut_power_dbw` | Výkon UT `−50…20 dBW`. | P; parameter natívneho satelitného vysielača. |
| `forward_isl_bps`, `reverse_isl_bps` | Celé `100…10¹⁰ bit/s`. | P; rýchlosti modelového ISL, ak sa používa. |
| `forward_queue_packets`, `reverse_queue_packets` | Celé `1…10000` paketov. | P; veľkosť modelových ISL front. |
| `antenna_model` | Ak je uvedený, presne `public-v1`. | K/P; profil verejných terminálových obálok. |
| `terminal_mounts` | Mapa aktívnych RSU → `{tilt_deg,azimuth_deg,frame}`. | P; iba pre Starlink a `antenna_model=public-v1`; `tilt 0…180°`, `azimuth 0…<360°`; pre RSU `frame="north"`. Chýbajúci záznam znamená predvolenú montáž nahor. [`validate_mounts`](../tools/u9_antenna_envelope.py). |
| `environment`, `link_budget` | Objekty rozpísané nižšie. | P/K; budovy majú účinok na natívny user link a pozemný LOS; terén a štatistické útlmy sú najmä fyzikálny audit. |

Pri explicitnom `catalog_ids` hodnoty topológie kontrolujú [`_select_topology`](../tools/u9_native_editor.py) a [`simulator_satellite_inputs.generate`](../tools/simulator_satellite_inputs.py). Pri automatike sa najskôr hľadá vhodná jedna družica. Prázdny kandidátsky zoznam, nedostatočná geometria alebo nevyhovujúca konfigurácia vedú k odmietnutiu prípravy; nejde o „nulové pakety“ skrytého behu.

### `link_policy`: presne šesť kľúčov

| Pole | Rozsah a význam v natívnom filtri |
| --- | --- |
| `rf_hz` | `1×10⁹…5×10¹⁰ Hz`; frekvencia pre výpočet Dopplera. |
| `compensation` | `0…1`; podiel kompenzovaného Dopplera; zvyšok `abs(doppler)×(1−compensation)`. |
| `doppler_tolerance_hz` | `0…1×10⁷ Hz`; ak zvyšok prevýši toleranciu, user link je odmietnutý. |
| `zenith_cone_deg` | `0…90°`; montážny smerový limit. |
| `steering_rate_deg_s` | `0…360°/s`; limit rýchlosti smerovania. |
| `beam_half_angle_deg` | `0…90°`; polovičný uhol lúča. |

[`u9_native_editor.py`](../tools/u9_native_editor.py) zapíše tieto čísla do natívneho CSV, ktoré číta [`u9-native-satellite-condition.h`](../src/u9-native-satellite-condition.h). Pri **Iridiu/Globalstare** natívny kód smerové limity nastaví na všesmerové hodnoty `180/360/180°`, keďže pre daný terminál nie je doložená inštalovaná smerová krivka. Frekvencia a Doppler sa stále uplatňujú. Pri Starlinku sa uplatní verejné FOV a montážny predpoklad. Tento filter môže user link odmietnuť; ak ho prijme, o ďalšom PHY/MAC osude rozhoduje SNS-3.

### `satellite.environment`: budovy, terén a odhad

Objekt verzie `1` má `georeference` presne rovnakú ako `world`, `extent_m` alebo dvojicu `width_m,height_m`, `buildings`, `terrain`, `height_case`, `uncertain_route_policy`, `statistical_layers`, `sources`. Kontrola je v [`validate_environment`](../tools/u9_local_environment.py). Rozmery sa musia rovnať svetu.

| Pole | Význam a účinok |
| --- | --- |
| `buildings[]` | Najviac 50 000 budov. Každá potrebuje `polygon_xy_m` (3…150 lokálnych bodov), `height_min_m`, `height_max_m` (`0…500 m`) a text `height_source`. Záznamy môžu mať `id`, `height_central_m`, `height_reference`, `building_class`. OSM `height` je neoverený tag; `building:levels` sa mení pomocou predpokladu 2,5…4 m na podlažie; neznáma výška tvorí interval, nie presný bod. |
| `height_case` | `interval`, `low`, `central`, `high`. Natívny export pre `low/high` vyberie minimum/maximum; pre `central/interval` centrálny odhad, prípadne stred intervalu, ak chýba. Pre voľby `low/central/high` validátor vyžaduje `height_central_m` každej budovy. Samostatný audit pri `interval` zachová neistotu. [`u9_ground_obstructions.py`](../tools/u9_ground_obstructions.py). |
| `terrain.origin_xy_m`, `step_m`, `width`, `height`, `elevation_m` | Mriežka HGT: začiatok `[-120,-120]`, krok 30 m, rozmery z výrezu, výšky `−500…9000 m`. **Používa ju samostatný fyzikálny náhľad/audit lúča**, nie plný výškový model pre každý pozemný paket v ns-3. |
| `uncertain_route_policy` | Presne `optimistic_with_uncertainty_flag`; neistota sa nesmie predstierať ako potvrdené doručenie. |
| `statistical_layers.weather`, `.vegetation` | Každá vrstva má `recommendation`, `status`, `assumed_loss_db_interval` alebo `null`; pri číselnom intervale `0…100 dB` a stav `scenario_assumption_not_ITU_prediction`. Ide o výslovný odhad pre fyzikálny link budget, **nie natívny paketový filter dažďa/vegetácie**. |
| `sources.osm`, `.terrain` | Pôvod podkladov pre audit a opakovateľnosť. |

Budova v pozemnej vetve: náš [`OSMBuildingCondition`](../src/u9-osm-ground-condition.h) zisťuje prienik 3D úsečky medzi vozidlovými/RSU anténami s pôdorysom vytiahnutým do vybranej výšky. Oznámi LOS/NLOS **ns-3 3GPP V2V modelu útlmu**; ten s 802.11p PHY určí výsledok príjmu. Budova v satelitnej vetve: náš [`NativeSatelliteCondition`](../src/u9-native-satellite-condition.h) môže priamo odmietnuť miestny **user link** podľa prieniku 3D lúča, Dopplera a montáže. Miestne budovy nepredstavujú model vzdialeného feeder linku.

### `satellite.link_budget`: len audit predpokladov

Voliteľné vetvy `user_uplink`, `user_downlink`, `feeder_uplink`, `feeder_downlink`. Každá môže mať intervaly `eirp_dbw_interval`, `rx_gt_db_per_k_interval`, `required_cn0_dbhz_interval`, `other_loss_db_interval`; voliteľne `pointing_loss_db_at_70deg_interval`, `environment_loss_db_interval`. Feeder navyše potrebuje explicitné `frequency_hz` v `10⁸…10¹¹ Hz`; user frekvencia je z profilu. Interval je dvojica `[minimum,maximum]`, ostatné straty `0…100 dB`. Ak niečo potrebné chýba, výsledok auditu zostane `unknown_missing_…`. Ak predpoklady stačia, [`u9_link_budget.py`](../tools/u9_link_budget.py) spočíta FSPL, interval C/N0 a rezervy. **Tieto odhadové intervaly samy nenastavujú satelitný modem ani neprikazujú SNS-3 doručiť paket.**

## 7. Hodnoty, ktoré editor v aktuálnej vetve neponúka ako voľbu

| Hodnota | Kde vzniká a čo znamená |
| --- | --- |
| **100 ms** | [`bp_u9.py`](../tools/bp_u9.py) vynúti krok 0,1 s a `sample_count=duration×10`; z tohto rytmu vznikajú waypointy a kontroly CAM. |
| **CAM BTP 2001, DENM BTP 2002; DENM max. 3 GN skoky** | Nastavenie nášho C++ [odosielania](../src/u9-full-integration-per-rsu.cc); Vanetza realizuje príslušný cestný zásobník. |
| **CAM pohyb >4 m / >0,5 m/s / >4°** | Podmienky nášho `Station::check`; `>` znamená, že rovná hodnota ešte pohybový spúšťač nevyvolá. [`Station::check`](../src/u9-full-integration-per-rsu.cc). |
| **DCC prahy CBR 0,004 a 0,012; minimá 100/250/500 ms** | Scenárová výskumná politika z [`u2-ground-one-rsu.json`](../config/u2-ground-one-rsu.json) používaná v C++ pri `dcc=1`. |
| **10 MHz OCB** | Pevná šírka 802.11p kanála. Výber `channel_number` a `rate_mbps` zostáva editovateľný. [`u9-full-integration-per-rsu.cc`](../src/u9-full-integration-per-rsu.cc). |
| **Auto 1,5 m; RSU `max(5 m, strecha+2 m)`** | Model výšky pozemných antén v C++ `radio_height`. Nie je to presná montáž skutočného zariadenia. |
| **RSU↔UT LAN 100 Mbit/s, 100 µs** | Modelový lokálny IP úsek v integrovanom C++ engini. |
| **Pozemný aplikačný front 512 paketov a obsluha 1 µs** | Argumenty v [`u9_native_editor.py`](../tools/u9_native_editor.py); ide o front pred satelitnou trasou, odlišný od editovateľného **ISL** frontu. |

## 8. Päť otázok pri ľubovoľnom výsledku

1. **Aký je uložený vstup?** Otvor `results/simulations/<run_id>/inputs/scenario.json`, `world.json`, `demand.json`; vypadni z predstavy, že zobrazený kruh alebo formulár je definitívna hodnota.
2. **Bol vstup len deklarácia?** `flows`, technologický štítok alebo `map_objects` ešte nie je paket. Hľadaj prevod do SUMO XML, `ground.json`, natívneho CSV alebo C++ argumentu.
3. **Kto rozhodoval?** Pozícia = SUMO; tvorba CAM/DENM a most = náš C++; GN/BTP/ASN.1 = Vanetza; 802.11p MAC/PHY = ns-3; satelitný DVB paketový prenos = SNS-3; výber orbitálnej geometrie a user-link filter = náš kód.
4. **Čo je tvrdenie o dostupnosti?** OMM existencia, geometrická viditeľnosť, zorné pole, prijatie filtrom, prijatie na PHY a aplikačné prijatie sú rôzne dôkazy. Nevyvodzuj komerčnú službu z posledného modelového kroku.
5. **Kde sú bajty?** Pri pozemnom behu čítaj [`u9_check_ground.py`](../tools/u9_check_ground.py); pri satelitnom [`u9_check_cam_denm.py`](../tools/u9_check_cam_denm.py) a natívny `PacketTrace.log`. `PASS` znamená, že konkrétny beh spĺňa definované kontroly, nie automaticky že každá naplánovaná DENM prišla každému autu.
