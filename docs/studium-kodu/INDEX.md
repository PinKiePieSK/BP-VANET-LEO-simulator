# Komentovaný aktívny kód

Táto kópia slúži na štúdium. Spustiteľný zdroj aj prenosný ZIP zostávajú čisté. Generátor vkladá len bežné komentáre medzi nezmenené riadky pôvodného kódu.

Po každej úprave aktívneho kódu spusti `python3 scripts/refresh_study_code.py`; príkaz `--check` skontroluje, či študijná kópia nezaostáva.

## [spustac/import.sh](komentovany-zdroj/spustac/import.sh)

Voliteľný vstup pre import vlastných súborov do pracovného priečinka. Cesty z balíka a pracovného priečinka drží oddelene, aby sa výsledky nemiešali so zdrojmi.

Pôvodný SHA-256: `49a23cef45d4…`

## [spustac/install_shortcut.py](komentovany-zdroj/spustac/install_shortcut.py)

Vytvorí desktopovú ikonu smerujúcu na prenosný spúšťač. Nemení simulačný model ani parametre pokusu.

Orientácia v súbore: `desktop()`, `quoted()`, `install()`.

Pôvodný SHA-256: `f8e6b9917a09…`

## [spustac/launch.py](komentovany-zdroj/spustac/launch.py)

Spúšťa lokálny server a samostatné okno prehliadača. Kontroluje identitu balíka, aby pracovný runtime nebol omylom použitý s inou verziou zdrojov, a po zavretí okna server ukončí.

Orientácia v súbore: `Stopped()`, `desktop()`, `tell()`, `on_signal()`, `stop()`, `browser_command()`, `ready_runtime()`, `start_server()`, `launch()`.

Pôvodný SHA-256: `4d035f282082…`

## [spustac/run.sh](komentovany-zdroj/spustac/run.sh)

Príkazový vstup pre preflight, beh a nezávislé overenie. Všetky tri príkazy deleguje na jeden aktuálny Python runner v pracovnom runtime.

Pôvodný SHA-256: `bacf37c21f0c…`

## [spustac/setup.sh](komentovany-zdroj/spustac/setup.sh)

Pripraví systémové závislosti, Python prostredie, Vanetza a ns-3.38/SNS-3. Ukladá zostavený runtime mimo prenosného zdrojového priečinka a vykonáva krátku kontrolu spustiteľnosti.

Pôvodný SHA-256: `f247f0d2a3dd…`

## [spustac/verify.py](komentovany-zdroj/spustac/verify.py)

Overí integritu prenosného balíka podľa manifestu SHA-256. Táto kontrola sa týka súborov balíka, nie správnosti výsledku konkrétnej simulácie.

Pôvodný SHA-256: `ebae7f80727f…`

## [src/cam-decoder.cc](komentovany-zdroj/src/cam-decoder.cc)

Pomocný dekóder CAM cez pripnutú knižnicu Vanetza. Používa sa pri čítaní potvrdených polí z reálnych bajtov paketu; nezúčastňuje sa vysielania.

Pôvodný SHA-256: `20e7c7ed08ae…`

## [src/denm-decoder.cc](komentovany-zdroj/src/denm-decoder.cc)

Pomocný dekóder DENM cez Vanetza. Overuje význam polí v zakódovanej výstrahe; nejde o druhú simulačnú vetvu.

Pôvodný SHA-256: `67c959044166…`

## [src/ground-building-condition.h](komentovany-zdroj/src/ground-building-condition.h)

Pozemné tienenie budov medzi vysielačom a prijímačom. Na základe geometrie budov rozhoduje o dodatočnom útlme alebo blokovaní v rádiovom modeli.

Orientácia v súbore: `Point`, `Building`, `OSMBuildingCondition`.

Pôvodný SHA-256: `c2b1eb620388…`

## [src/rsu-radio-config.h](komentovany-zdroj/src/rsu-radio-config.h)

Načíta presný CSV profil každej RSU pre pozemnú 802.11p PHY v oboch natívnych enginoch. Nepovolené rozsahy a cudzie ID zastavia beh pred vysielaním.

Orientácia v súbore: `Profile`.

Pôvodný SHA-256: `7cfb87855bcd…`

## [src/satellite-link-condition.h](komentovany-zdroj/src/satellite-link-condition.h)

Model fyzikálnych podmienok satelitného terminálu vložený do natívneho kanála. Kontroluje viditeľnosť, Dopplerovu toleranciu, smerovanie antény a lokálne prekážky; nejde o skutočnú politiku komerčného operátora.

Orientácia v súbore: `Profile`, `Condition`.

Pôvodný SHA-256: `8733a60ddc85…`

## [src/vanet-ground-network.cc](komentovany-zdroj/src/vanet-ground-network.cc)

Pozemný paketový engine používa pre CAM a výšku antény hodnoty odovzdané scenárom; rozhodnutia ostávajú v raw DCC stope.

Orientácia v súbore: `Runtime`, `Sample`, `DenmEvent`, `BoxInput`, `Interval`, `DccPolicy`, `Station`.

Pôvodný SHA-256: `de252a507366…`

## [src/vanet-leo-network.cc](komentovany-zdroj/src/vanet-leo-network.cc)

Jednotný ns-3/SNS-3 engine používa ten istý profil CAM a antén ako pozemný engine, aby porovnanie nemenilo skryté nastavenia.

Orientácia v súbore: `SimulatorRuntime`, `Waypoint`, `DenmEvent`, `BuildingBox`, `Station`.

Pôvodný SHA-256: `bb85988fa45c…`

## [tools/fetch_orbits.py](komentovany-zdroj/tools/fetch_orbits.py)

Stiahne a uloží pripnutý orbitálny archív. Archív je vstupom pre SGP4 polohy a musí mať pôvod a hash, aby sa beh dal zopakovať.

Orientácia v súbore: `NoRedirect()`, `verify_snapshot()`, `recent_snapshot()`, `fetch()`.

Pôvodný SHA-256: `8561e4127656…`

## [tools/simulator_antenna_envelope.py](komentovany-zdroj/tools/simulator_antenna_envelope.py)

Validuje náklon a azimut terminálu proti zvolenému fyzikálnemu profilu. Tieto predpoklady opisujú výskumný model, nie skutočnú anténu operátora.

Orientácia v súbore: `validate_mounts()`, `angles_deg()`, `starlink_fov_mask()`.

Pôvodný SHA-256: `278064c20da7…`

## [tools/simulator_build.py](komentovany-zdroj/tools/simulator_build.py)

Zostavenie spoločného natívneho paketového programu z vlastného C++ zdroja a knižníc ns-3, SNS-3 a Vanetza.

Orientácia v súbore: `compile_packet_engine()`.

Pôvodný SHA-256: `1feaae143678…`

## [tools/simulator_cam_decode.py](komentovany-zdroj/tools/simulator_cam_decode.py)

Volá pripnutý C++ dekóder CAM a prevádza jeho overené ASN.1 polia do čitateľnej podoby. Používa sa pre detail paketu a verifier.

Orientácia v súbore: `binary()`, `decode_cam()`, `enrich()`.

Pôvodný SHA-256: `8138ddca28dd…`

## [tools/simulator_car_radio.py](komentovany-zdroj/tools/simulator_car_radio.py)

Vstup a kontrola individuálneho pozemného rádia áut v zjednotenom simulátore.

Orientácia v súbore: `render()`, `write()`.

Pôvodný SHA-256: `c2eb3eb9ebb6…`

## [tools/simulator_cli.py](komentovany-zdroj/tools/simulator_cli.py)

Preflight akceptuje voliteľný profil enginu a overuje ho pred vytvorením nemenných vstupov behu.

Orientácia v súbore: `full_duration()`, `runtime_inputs()`, `experiment_clock()`, `need()`, `native_satellite()`, `unified_policy()`, `load()`, `write()`, `template()`, `orbit_group()`, `preflight()`, `run()`, `verify()`.

Pôvodný SHA-256: `e2b97914f674…`

## [tools/simulator_clock.py](komentovany-zdroj/tools/simulator_clock.py)

Spoločný časový kontrakt aktuálneho simulátora. Experiment začína v UTC určenom scenárom pri t = 0; všetky uzly musia byť pripravené ešte pred vykonaním prvého kroku ns-3.

Pôvodný SHA-256: `6d521c310843…`

## [tools/simulator_constellation.py](komentovany-zdroj/tools/simulator_constellation.py)

Počíta náhľad konštelácie a polohy pre glóbus. Prehľad môže zobraziť viac kandidátov než skutočný paketový beh; rozhodujúci výber pri behu robí simulator_satellite_runner.py.

Orientácia v súbore: `preview()`, `motion()`.

Pôvodný SHA-256: `140d4d4185e9…`

## [tools/simulator_coordinates.py](komentovany-zdroj/tools/simulator_coordinates.py)

Prevod lokálnych metrov editora na WGS84 pomocou tečnej roviny ENU a knižnice Astropy.

Orientácia v súbore: `enu_to_wgs84()`.

Pôvodný SHA-256: `bc1366bf50a6…`

## [tools/simulator_denm_decode.py](komentovany-zdroj/tools/simulator_denm_decode.py)

Volá pripnutý C++ dekóder DENM a formátuje význam zakódovaných polí. Pomáha čitateľnému rozboru jedného výstražného paketu.

Orientácia v súbore: `binary()`, `decode_denm()`.

Pôvodný SHA-256: `596dd5698d5f…`

## [tools/simulator_editor_api.py](komentovany-zdroj/tools/simulator_editor_api.py)

Nový návrh ukladá úplný profil enginu, aby boli aj pôvodne pevné vedecké predpoklady súčasťou reprodukovateľného scenára.

Orientácia v súbore: `_file_state()`, `_run_state()`, `verified_run()`, `read()`, `new_draft()`, `source()`, `save()`, `check()`, `_rows()`, `_folder()`, `_satellites()`, `_packet_event_index()`, `_packet_timeline()`, `packet_events()`, `_visible_trace_events()`, `_replay_links()`, `replay()`, `physical_audit()`, `packet()`.

Pôvodný SHA-256: `c408c275479f…`

## [tools/simulator_engine_controls.py](komentovany-zdroj/tools/simulator_engine_controls.py)

Spoločný register scenárových premenných pre natívny engine. Staršie scenáre dedia pôvodné hodnoty; hranice bránia neplatným kombináciám prahov, frontov a RF predpokladov.

Orientácia v súbore: `effective()`.

Pôvodný SHA-256: `dc2f914a0a59…`

## [tools/simulator_ground_obstructions.py](komentovany-zdroj/tools/simulator_ground_obstructions.py)

Premení geometriu budov z editora/OSM na textový vstup pozemného C++ kanála. Rovnaký zdroj prekážok sa potom porovnáva vo verifieri.

Orientácia v súbore: `export_bytes()`, `write()`.

Pôvodný SHA-256: `b5e14b9b94f3…`

## [tools/simulator_ground_runner.py](komentovany-zdroj/tools/simulator_ground_runner.py)

Pozemný runner odovzdáva účinné CAM a anténne parametre natívnemu ns-3 programu a zaznamenáva zdroj ich validácie.

Orientácia v súbore: `digest()`, `root_file()`, `compile_source()`, `validate_config()`, `traffic_metrics()`, `run()`.

Pôvodný SHA-256: `dae71df59f4d…`

## [tools/simulator_ground_verifier.py](komentovany-zdroj/tools/simulator_ground_verifier.py)

Nezávislý overovač prepočítava CAM rozhodnutia z parametrov uložených v JSON, nie z pôvodných pevných prahov.

Orientácia v súbore: `require()`, `digest()`, `rows()`, `segment_hits_box()`, `load_case()`, `verify()`.

Pôvodný SHA-256: `542a28ea7424…`

## [tools/simulator_inputs.py](komentovany-zdroj/tools/simulator_inputs.py)

Premenné DCC, fázy a CAM/antén sa prenášajú zo scenára do pozemného JSON, z ktorého vznikajú argumenty ns-3.

Orientácia v súbore: `project_input()`, `ground_config()`.

Pôvodný SHA-256: `aa0778930eb0…`

## [tools/simulator_inventory.py](komentovany-zdroj/tools/simulator_inventory.py)

Inventár povoľuje nový RSU panel cez server a prenosný balík; bez toho by sa v pracovnej ikone nenačítal.

Pôvodný SHA-256: `96d2bb738aff…`

## [tools/simulator_link_budget.py](komentovany-zdroj/tools/simulator_link_budget.py)

Diagnostický výpočet orientačného link budgetu. Je oddelený od natívneho paketového kanála; číslo z tohto súboru samo nepredpovedá doručenie.

Orientácia v súbore: `_interval()`, `validate_assumptions()`, `fspl_db()`, `_radial_speed()`, `_budget()`, `evaluate()`.

Pôvodný SHA-256: `9beaccd12247…`

## [tools/simulator_link_policy_defaults.py](komentovany-zdroj/tools/simulator_link_policy_defaults.py)

Predvolené výskumné hodnoty RF, Dopplera a smerovania terminálu. V scenári ich možno explicitne nahradiť a verifier kontroluje, čo bolo odovzdané behu.

Pôvodný SHA-256: `3c72fb914a78…`

## [tools/simulator_local_environment.py](komentovany-zdroj/tools/simulator_local_environment.py)

Načíta budovy a terén, odhadne chýbajúce výšky a validuje miestne prostredie. Výškový odhad je označený ako predpoklad a dá sa skúmať nízkym/stredným/vysokým variantom.

Orientácia v súbore: `terrain_side()`, `_height()`, `_building_class()`, `impute_building_heights()`, `buildings_from_xml()`, `_tile_key()`, `_hgt()`, `_xy_to_geo()`, `terrain_for()`, `import_environment()`, `validate_environment()`, `LocalObstructions()`.

Pôvodný SHA-256: `0f6f3103c10d…`

## [tools/simulator_message_verifier.py](komentovany-zdroj/tools/simulator_message_verifier.py)

Nezávislý audit CAM a DENM: identita, surové bajty, poradie udalostí a doručenie cez RSU/bránu. Toto čítaj pri obhajobe dôveryhodnosti výsledkov.

Orientácia v súbore: `need()`, `rows()`, `verify()`.

Pôvodný SHA-256: `bfacaaa483d0…`

## [tools/simulator_mobility_export.py](komentovany-zdroj/tools/simulator_mobility_export.py)

Spojí SUMO FCD polohy s identitou staníc a vytvorí waypoints.csv pre C++ paketový engine. Dôležitý most medzi pohybom vozidiel a časmi odoslania CAM.

Orientácia v súbore: `prepare()`.

Pôvodný SHA-256: `ab0a59fde5e2…`

## [tools/simulator_node_policy.py](komentovany-zdroj/tools/simulator_node_policy.py)

Preloží nastavenie rádia každého auta a RSU na presné prepínače pre natívny program. Vypnutý uzol tak nemôže náhodou komunikovať iba preto, že geometricky vidí druhý uzol.

Orientácia v súbore: `environment()`.

Pôvodný SHA-256: `9cb4ed66edb5…`

## [tools/simulator_orbit_source.py](komentovany-zdroj/tools/simulator_orbit_source.py)

Kontroluje pripnutý orbitálny archív, jeho hash a časovú platnosť. Z neho stavia konfiguráciu, ktorú používa glóbus, výber topológie aj fyzikálny audit.

Orientácia v súbore: `validate_pin()`, `config_for()`, `snapshots()`, `newest_default()`.

Pôvodný SHA-256: `7c825f703262…`

## [tools/simulator_orbits.py](komentovany-zdroj/tools/simulator_orbits.py)

Načítanie pripnutého orbitálneho archívu, výpočet polohy družíc a kontrola geometrického výhľadu.

Orientácia v súbore: `digest()`, `utc()`, `stamp()`, `site()`, `load_orbits()`, `clearance()`, `pinned_eop()`, `sample()`, `station_vectors()`, `view()`, `sat_ecef()`, `site_ecef()`, `ns3_sphere_position()`.

Pôvodný SHA-256: `3177e7f93283…`

## [tools/simulator_osm_local_extract.py](komentovany-zdroj/tools/simulator_osm_local_extract.py)

Číta lokálny výrez OpenStreetMap zo stiahnutého PBF, keď je k dispozícii. Chráni editor pred limitmi verejného OSM API pri slovenských lokalitách.

Orientácia v súbore: `_ring()`, `_inside()`, `_boundary_touches()`, `covers()`, `_source()`, `_osmium()`, `extract()`.

Pôvodný SHA-256: `e859c3704923…`

## [tools/simulator_osm_road_graph.py](komentovany-zdroj/tools/simulator_osm_road_graph.py)

Načíta jazdné cesty z OSM do pracovného výrezu, zachová ich topológiu, smerové hodnoty a jednoduché zákazy odbočenia. Časové značky sa do cestných záznamov ani SUMO vstupov nezahrnú.

Orientácia v súbore: `OsmRateLimit()`, `_tile_paths()`, `_cached()`, `_store()`, `_tile_lock()`, `_retry_seconds()`, `finite()`, `basis()`, `local()`, `dimensions()`, `bbox_for()`, `download()`, `point_near_square()`, `speed()`, `directional_speed()`, `speed_source()`, `directional_lanes()`, `lanes_source()`, `passenger_access()`, `graph_from_xml()`, `_build()`, `load()`.

Pôvodný SHA-256: `cf9cd7ddff3c…`

## [tools/simulator_packet_trace.py](komentovany-zdroj/tools/simulator_packet_trace.py)

Nezávislé čítanie PCAP a kontrola úplných IPv4/UDP bajtov na satelitných ISL skokoch.

Orientácia v súbore: `require()`, `pcap_packets()`, `ones_complement_valid()`, `decode_isl()`, `hops()`.

Pôvodný SHA-256: `118dc9d5bafb…`

## [tools/simulator_physical_coverage.py](komentovany-zdroj/tools/simulator_physical_coverage.py)

Verejne doložené minimálne elevácie a ďalšie fyzikálne profily Starlinku, Iridia a Globalstaru. Výsledkom je kandidátska geometrická obálka, nie potvrdená dostupnosť služby operátora.

Orientácia v súbore: `profile()`, `direct_link_policy()`, `site_ecef_km()`, `assess()`, `assess_pair()`.

Pôvodný SHA-256: `1a1ea61697d9…`

## [tools/simulator_physical_report.py](komentovany-zdroj/tools/simulator_physical_report.py)

Spája geometrické vzorky a natívne paketové udalosti do časovej správy o fyzikálnom stave. Odlišuje výhľad na satelit od prijatia paketu v bráne.

Orientácia v súbore: `digest()`, `horizon_counts()`, `packet_counts()`, `native_packet_counts()`, `native_analyze()`, `margin_status()`, `classify()`, `analyze()`, `csv_text()`, `export()`, `verify_export()`.

Pôvodný SHA-256: `0f970821aa49…`

## [tools/simulator_platform.py](komentovany-zdroj/tools/simulator_platform.py)

Spoločné cesty k projektu a runtime, kontrolné súčty súborov, bezpečný zápis generovaných vstupov a poloha terminálu RSU.

Orientácia v súbore: `sha()`, `put_exact()`, `ut_site()`.

Pôvodný SHA-256: `e460512c767f…`

## [tools/simulator_rsu_radio.py](komentovany-zdroj/tools/simulator_rsu_radio.py)

Vytvorí presný účinný rádiový profil každej RSU zo spoločného nastavenia scenára a individuálnych prepísaní. Rovnaké bajty kontrolujú nezávislé verifiery.

Orientácia v súbore: `render()`, `write()`.

Pôvodný SHA-256: `4362cad29e73…`

## [tools/simulator_rsu_reference.py](komentovany-zdroj/tools/simulator_rsu_reference.py)

Voliteľný referenčný zdroj polôh RSU na mape s označeným pôvodom. Nepodsúva zobrazené referenčné objekty automaticky do simulácie.

Orientácia v súbore: `_value()`, `fetch()`.

Pôvodný SHA-256: `f52825d48cab…`

## [tools/simulator_satellite_inputs.py](komentovany-zdroj/tools/simulator_satellite_inputs.py)

Tvorba natívnych súborov SNS-3 pre vybrané družice, ISL, terminály a diagnostický anténny vzor.

Orientácia v súbore: `generate()`.

Pôvodný SHA-256: `2b1aa5c54245…`

## [tools/simulator_satellite_runner.py](komentovany-zdroj/tools/simulator_satellite_runner.py)

Spoločný satelitný runner odovzdáva fronty, DVB parametre, DCC, CAM a výšky antén ako pomenované argumenty jedného ns-3/SNS-3 procesu.

Orientácia v súbore: `_orbit_positions()`, `_select_topology()`, `_model()`, `run()`.

Pôvodný SHA-256: `2e8b08425110…`

## [tools/simulator_satellite_trace.py](komentovany-zdroj/tools/simulator_satellite_trace.py)

Číta natívny PacketTrace.log SNS-3 a pripája iba tie vrstvové kroky, ktorých ns-3 packet UID bol pri vysielaní preukázateľne spojený s konkrétnym DENM. Riadiaca premávka SNS-3 sa do cesty výstrahy nepridáva.

Orientácia v súbore: `_joined()`, `load()`, `by_event()`.

Pôvodný SHA-256: `6b6453775adb…`

## [tools/simulator_satellite_verifier.py](komentovany-zdroj/tools/simulator_satellite_verifier.py)

Overí integrovaný ns-3/SNS-3 beh: zdrojovú binárku, satelitnú knižnicu, raw stopy, bajty a cestu DENM do brány a vzdialených áut. Neakceptuje náhradný servisný model.

Orientácia v súbore: `_rows()`, `_need()`, `verify()`.

Pôvodný SHA-256: `2ed04f34e523…`

## [tools/simulator_server.py](komentovany-zdroj/tools/simulator_server.py)

Technický model posiela rozhraniu aktuálne predvolené hodnoty enginu, aby sa neodvodzovali z popisného textu.

Orientácia v súbore: `canonical_route()`, `running()`, `Handler()`.

Pôvodný SHA-256: `11989667cdcd…`

## [tools/simulator_sumo.py](komentovany-zdroj/tools/simulator_sumo.py)

Schéma mapy a áut, validácia geometrie, tvorba SUMO XML a spustenie mobility. Tu sa rozhoduje, po ktorých úsekoch a ako dlho sa autá pohybujú; prijaté správy zatiaľ nemenia ich jazdu.

Orientácia v súbore: `only_keys()`, `number()`, `validate_car_model()`, `validate_rsu_radio()`, `validate_car_radio()`, `point()`, `node_id()`, `technologies()`, `validate_map_objects()`, `validate()`, `write_xml()`, `make_inputs()`, `verify_net_connections()`, `hold_vehicles_for_radio_window()`, `align_route_positions()`, `run()`.

Pôvodný SHA-256: `de2509f069ab…`

## [tools/simulator_time_visibility.py](komentovany-zdroj/tools/simulator_time_visibility.py)

Počas celého pokusu sleduje satelity nad fyzikálnou maskou pre každý terminál. Kontroluje tiež, či skutočné natívne paketové ponuky neporušili časovú geometriu.

Orientácia v súbore: `_tracks()`, `_site()`, `_elevation()`, `calculate()`, `audit_packet_geometry()`.

Pôvodný SHA-256: `e36898cee371…`

## [tools/simulator_tle_catalog.py](komentovany-zdroj/tools/simulator_tle_catalog.py)

Mapuje verejné orbitálne ID na identifikátory a TLE formát, ktorý prijíma SNS-3 3.38. Pôvodné verejné ID sa zachováva v manifeste.

Orientácia v súbore: `native_ids()`, `tle_lines()`, `manifest_mapping()`, `expected_tle()`.

Pôvodný SHA-256: `3bfe9803a57f…`

## [viewer/earth-map.js](komentovany-zdroj/viewer/earth-map.js)

Reálna mapa umožňuje kliknutím vybrať importovaný pôdorys budovy na zmenu účinných výšok a vrcholov.

Orientácia v súbore: `basis`, `localToGeo`, `geoToLocal`, `category`, `rememberStyle`, `applyBaseLayers`, `syncGround`, `initializeGround`, `addOverlay`, `setSource`, `referenceEnabled`, `drawReferenceRsus`, `loadReferenceRsus`, `editorFeatures`, `renderSky`, `renderPacketLinks`, `location`, `render`, `updateNote`, `setMode`, `clipSegment`, `roadLines`, `featureRoadPath`, `hideShortDetachedComponents`, `cleanRealRoadGraph`, `roadJoinCandidates`, `joinRoadEnd`, `renderRoadJoinControls`, `globalStore`, `globalCounts`, `upsert`, `syncActiveGlobal`, `nearestOnShape`, `projectGlobalToCurrentSite`, `endpoint`, `initializeGlobal`, `siteCovered`, `fetchRoadNetwork`, `loadRoadNetwork`, `ensureRoad`, `roadAtScreenPoint`, `mapClick`.

Pôvodný SHA-256: `0c09ab34cec4…`

## [viewer/globe.js](komentovany-zdroj/viewer/globe.js)

Glóbus, orbitálny náhľad a synchronizácia pohybu satelitov s replay. Vizualizuje archív konštelácie; sám nerozhoduje, ktorý satelit prijal paket.

Orientácia v súbore: `globeBasis`, `dot`, `globeSize`, `globeUnit`, `envelopeFootprint`, `project`, `projectLonLat`, `siteEcef`, `motionFrame`, `replaySatelliteXyz`, `drawLand`, `drawGraticule`, `drawGlobe`, `collect`, `updateSite`, `globePointer`, `loadGlobeMotion`, `orbitTick`.

Pôvodný SHA-256: `b6c1692d3680…`

## [viewer/manual-buildings.js](komentovany-zdroj/viewer/manual-buildings.js)

Panel budovy upravuje pôdorys a tri výšky v scenári; tento objekt vstupuje do tienenia pozemného rádia aj satelitného výhľadu.

Orientácia v súbore: `ensure`, `setRectangle`, `add`, `render`, `renderInspector`.

Pôvodný SHA-256: `321a5a74654e…`

## [viewer/packet-inspector.js](komentovany-zdroj/viewer/packet-inspector.js)

Zobrazuje vybraný paket ako surové bajty a dekódované polia CAM/DENM či IP/UDP. Je to čítačka výstupu verifiera, nie nová simulácia komunikácie.

Orientácia v súbore: `cam`, `denm`, `groups`, `hexdump`, `render`.

Pôvodný SHA-256: `a5e4f2c767fe…`

## [viewer/physical-audit.js](komentovany-zdroj/viewer/physical-audit.js)

Ovládanie grafického pohľadu na časovú fyzikálnu dostupnosť a výsledky paketového behu. Odlišuje geometrického kandidáta od skutočne prijatého paketu.

Orientácia v súbore: `rowFor`, `color`, `selected`, `stage`, `interval`, `render`, `draw`, `clear`, `load`, `download`.

Pôvodný SHA-256: `a4fa8d51a06f…`

## [viewer/route-planner.js](komentovany-zdroj/viewer/route-planner.js)

Plánovanie ciest pre jedno auto alebo vybranú skupinu áut na grafe vozoviek. Vygenerovaná trasa sa uloží do scenára pred spustením SUMO.

Orientácia v súbore: `graph`, `Heap`, `tree`, `pathTo`, `legal`, `startOptions`, `apply`, `randomSeed`, `random`, `travelSpeed`, `targetTravelSeconds`, `estimatedSeconds`, `durationNotice`, `randomWalk`, `destination`, `candidate`, `planToPoint`, `planGroup`, `assign`, `clickDestination`, `sliceShape`, `geometry`, `renderControls`, `toggleGroup`, `renderGroupControls`.

Pôvodný SHA-256: `5269bcd4633f…`

## [viewer/rsu-inputs.js](komentovany-zdroj/viewer/rsu-inputs.js)

Panel RSU oddeľuje polohu a pozemné rádio od satelitnej roly, terminálu a cieľovej aplikácie.

Orientácia v súbore: `render`.

Pôvodný SHA-256: `ca24f305fb77…`

## [viewer/simulator.css](komentovany-zdroj/viewer/simulator.css)

Posuvný zoznam vrcholov veľkej OSM budovy zostáva vo vnútri objektového panelu bez zmeny rolovania celej stránky.

Pôvodný SHA-256: `b788f7add9ae…`

## [viewer/simulator.html](komentovany-zdroj/viewer/simulator.html)

Načítava aktuálne zjednotené panely objektov vrátane RSU a nové verzie skriptov, aby refresh zobrazil zmeny.

Pôvodný SHA-256: `8c330dae49a7…`

## [viewer/simulator.js](komentovany-zdroj/viewer/simulator.js)

Inšpektor objektov zjednocuje panely podľa účinku na jednotlivé simulácie a posiela RSU do samostatného editora.

Orientácia v súbore: `svg`, `fmt`, `error`, `status`, `api`, `post`, `svgPoint`, `worldPoint`, `unitsPerPixel`, `sy`, `viewRatio`, `fullView`, `clampView`, `setView`, `zoom`, `fit`, `renderGrid`, `segment`, `shapeLength`, `pointAt`, `carPosition`, `nearestRoad`, `entityAt`, `replayCar`, `linkVisualKind`, `linkKey`, `activePacketLinks`, `selectPacketLink`, `groundPosition`, `renderGroundPacketLinks`, `markDirty`, `nextId`, `rebuildObjectPicker`, `focusSelected`, `removeRoadFromDraft`, `addRoadPoint`, `undoRoadPoint`, `redoRoadPoint`, `clearRoadDraft`, `finishRoad`, `end`, `addCar`, `addRsu`, `updateTool`, `satelliteCount`, `renderRoads`, `renderSumoInputs`, `render`, `ensureNodePolicy`, `renderPerNodeControls`, `renderAntennaControls`, `validateRoadPointEdit`, `updateRoadPoint`, `renderRoadControls`, `updateLaneRows`, `renderInspector`, `field`, `choose`, `checkbox`, `renderCatalog`, `orbitControls`, `loadOrbitSnapshots`, `syncOrbitSnapshotPicker`, `refreshOrbits`, `renderOrbit`, `loadMapConstellation`, `durationLimits`, `renderDenmControls`, `renderCarDenmControls`, `renderDurationControls`, `commitDurationInput`, `mapDraftSnapshot`, `restoreMapDraft`, `applyMapModeUI`, `syncHeightCase`, `clearMapFor`, `clearRealSite`, `commitAreaSize`, `newMap`, `switchMapMode`.

Pôvodný SHA-256: `198ee90f00cc…`

## [viewer/technical-parameters-bridge.js](komentovany-zdroj/viewer/technical-parameters-bridge.js)

Most prijíma iba ohraničené zmeny parametrov a hneď aktualizuje rozpracovaný scenár v hlavnom editore.

Orientácia v súbore: `snapshot`, `send`, `numeric`, `choice`, `byId`, `patch`.

Pôvodný SHA-256: `9eea4641f751…`

## [viewer/technical-parameters.css](komentovany-zdroj/viewer/technical-parameters.css)

Samostatné vrstvy technických parametrov sú bloky cez šírku stránky, každá s vlastnou dvojstĺpcovou mriežkou.

Pôvodný SHA-256: `b2ca9203c7ef…`

## [viewer/technical-parameters.html](komentovany-zdroj/viewer/technical-parameters.html)

Technická stránka načítava aktuálnu podobu skupín a štýlov pre kontrolu všetkých scenárových vrstiev.

Pôvodný SHA-256: `2fc324b12b73…`

## [viewer/technical-parameters.js](komentovany-zdroj/viewer/technical-parameters.js)

Technická stránka má oddelené skupiny SUMO, ns-3, SNS-3 a aplikačnej komunikácie; upraviteľné hodnoty čerpá zo scenára.

Orientácia v súbore: `get`, `request`, `group`, `section`, `row`, `detail`, `catalogue`, `roadStats`, `enabled`, `render`, `saved`, `download`.

Pôvodný SHA-256: `b811cb1e2733…`

## [viewer/traffic-spawner.js](komentovany-zdroj/viewer/traffic-spawner.js)

Generuje syntetickú premávku na dostupnom cestnom grafe. Výber hlavného ťahu, odbočiek, rýchlostí a dĺžky trasy prebehne pred simuláciou; vozidlá potom riadi SUMO.

Orientácia v súbore: `roadPriorities`, `extend`, `spawn`.

Pôvodný SHA-256: `8ae6ca6318ca…`
