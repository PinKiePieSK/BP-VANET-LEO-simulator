# Zdroje, navigácia a overenie reportu

Tento register dopĺňa dve čitateľské časti. Opisuje pracovný projekt, nie všetky externé knižnice riadok po riadku. Absolútne odkazy smerujú na skutočné lokálne zdroje; čísla riadkov platia pre zachytený stav. Pri ďalšom vývoji sa môžu posunúť. SHA-256 a čas uzavretia inventára sú v `audit-zdrojov.json`.

## Čo bolo urobené pri príprave reportu

- Prečítané projektové AGENTS, migračný denník, pôvodný report a aktuálne U9/F dokumenty; rozhodujúce tvrdenia porovnané s implementáciou.
- Prečítaný hlavný runner, server, editovanie, mobilita, servisný C++ model, dynamické trasy, antény, lokálne prostredie, nový RF overlay a vybrané historické DVB integračné body.
- Spustených 39 existujúcich testov kontraktu, času, plánovača, prostredia, antén, fyzikálnej obálky, katalógu, replay, cache a mapového zarovnania: všetky OK. Ďalšie 3 existujúce testy RF overlay: všetky OK.
- Osobitne znovu spustený `u9_service_native.verify` nad troma existujúcimi novými servisnými podadresármi. Je to audit servisnej vrstvy, nie nové vykonanie simulácie ani tvrdenie o novom úplnom hlavnom `bp_u9.verify`.
- Pôvodný report, rukopis, výsledky a implementácia neboli touto úlohou prepísané. Nové sú len súbory tohto reportu.

Pracovné zdroje sa počas čítania vyvíjali: pribudol RF overlay a nadväzné integračné zmeny. Text preto uvádza jeho konkrétny prečítaný účinok a nevyhlasuje iba podľa názvu plánu, že celá F5 je dokončená. Neskoršie zmeny treba porovnať s inventárom.

## Znovu overené servisné výsledky

| Existujúci beh | Ponuky | Brána | ACK terminálu | Upozornené autá | Drop udalosti | Audit servisnej vrstvy |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| f5-heightbudget-starlink-20261101 | 68 | 68 | 68 | 1 | 0 | PASS |
| f5-heightbudget-iridium-20261101 | 68 | 49 | 49 | 1 | 19 | PASS |
| f5-heightbudget-globalstar-20261101 | 68 | 53 | 51 | 1 | 17 | PASS |

Každý z týchto behov doručil výstrahu cieľovej RSU. Počty patria konkrétnym uloženým syntetickým konfiguráciám. Nie sú nezávislé meranie výkonu operátorov ani párované štatistické poradie. Drop môže patriť odpovedi alebo ďalšej vetve; nie je automaticky doplnkom počtu ponúk do počtu doručení.

## Príkazy vykonané pri overení

Z aktívneho projektového koreňa:

```bash
PYTHONPATH=tools .venv/bin/python -m unittest tools.test_u9_capabilities tools.test_u9_full_duration_clock tools.test_u9_dynamic_service tools.test_u9_local_environment tools.test_u9_antenna_envelope tools.test_u9_physical_coverage tools.test_u9_time_visibility tools.test_u9_tle_catalog tools.test_u9_replay_bounded tools.test_u9_verify_cache tools.test_u9_real_map_position_alignment
PYTHONPATH=tools .venv/bin/python -m unittest tools.test_u9_link_budget
```

Servisné podadresáre boli auditované priamym volaním `u9_service_native.verify(Path(.../service-model))`. Verifier prepočítava trasy a integritu; nie je to spustenie nového merania. Pre vlastný nový beh používaj nové ID a hlavné `bp_u9.py preflight`, `run`, `verify`, prípadne webový editor.

## Mapa prečítaných zdrojov

| Súbor | Riadkov pri uzavretí inventára | Úloha |
| --- | ---: | --- |
| [tools/bp_u9.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py>) | 729 | Runner, výpočet alebo kontrola |
| [tools/u9_server.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_server.py>) | 210 | Runner, výpočet alebo kontrola |
| [tools/u9_editor_api.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py>) | 573 | Runner, výpočet alebo kontrola |
| [tools/u9_editable_scenario.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editable_scenario.py>) | 498 | Runner, výpočet alebo kontrola |
| [tools/u9_run_ground.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_run_ground.py>) | 274 | Runner, výpočet alebo kontrola |
| [tools/u9_prepare_cam.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_prepare_cam.py>) | 96 | Runner, výpočet alebo kontrola |
| [tools/u9_node_policy.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_node_policy.py>) | 45 | Runner, výpočet alebo kontrola |
| [tools/u9_osm_road_graph.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_osm_road_graph.py>) | 202 | Runner, výpočet alebo kontrola |
| [tools/u9_orbit_source.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_orbit_source.py>) | 77 | Runner, výpočet alebo kontrola |
| [tools/fetch_orbits.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/fetch_orbits.py>) | 157 | Runner, výpočet alebo kontrola |
| [tools/v3_leo_topology.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/v3_leo_topology.py>) | 302 | Runner, výpočet alebo kontrola |
| [tools/u9_time_visibility.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_time_visibility.py>) | 185 | Runner, výpočet alebo kontrola |
| [tools/u9_dynamic_service.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_dynamic_service.py>) | 337 | Runner, výpočet alebo kontrola |
| [tools/u9_physical_coverage.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_physical_coverage.py>) | 133 | Runner, výpočet alebo kontrola |
| [tools/u9_antenna_envelope.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_antenna_envelope.py>) | 90 | Runner, výpočet alebo kontrola |
| [tools/u9_local_environment.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_local_environment.py>) | 441 | Runner, výpočet alebo kontrola |
| [tools/u9_link_budget.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_link_budget.py>) | 176 | Runner, výpočet alebo kontrola |
| [tools/u9_service_native.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py>) | 363 | Runner, výpočet alebo kontrola |
| [src/u9-service-native.cc](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc>) | 676 | C++ model |
| [src/u9-ground-cam-dcc.cc](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-ground-cam-dcc.cc>) | 409 | C++ model |
| [src/u9-full-advanced.cc](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-full-advanced.cc>) | 2175 | C++ model |
| [src/u9-full-direct-advanced.h](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-full-direct-advanced.h>) | 100 | C++ model |
| [src/u9-full-integration-per-rsu.cc](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-full-integration-per-rsu.cc>) | 1889 | C++ model |
| [src/u9-parametric-leo-backhaul.cc](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-parametric-leo-backhaul.cc>) | 1839 | C++ model |
| [tools/run_u9_advanced.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/run_u9_advanced.py>) | 151 | Runner, výpočet alebo kontrola |
| [tools/check_u9_advanced.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/check_u9_advanced.py>) | 247 | Runner, výpočet alebo kontrola |
| [tools/bp_u7.py](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u7.py>) | 545 | Runner, výpočet alebo kontrola |
| [viewer/u9-simulator.js](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/viewer/u9-simulator.js>) | 257 | Webové ovládanie/zobrazenie |
| [viewer/u9-earth-map.js](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/viewer/u9-earth-map.js>) | 557 | Webové ovládanie/zobrazenie |
| [viewer/u9-route-planner.js](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/viewer/u9-route-planner.js>) | 246 | Webové ovládanie/zobrazenie |
| [viewer/u9-traffic-spawner.js](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/viewer/u9-traffic-spawner.js>) | 86 | Webové ovládanie/zobrazenie |
| [viewer/u9-globe.js](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/viewer/u9-globe.js>) | 248 | Webové ovládanie/zobrazenie |
| [scripts/obnovit-native-ubuntu.sh](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/scripts/obnovit-native-ubuntu.sh>) | 78 | Obnova |

## Funkcie a triedy, ktoré sa oplatí otvoriť

| Miesto | Vysvetlenie v reporte |
| --- | --- |
| [bp_u9.py · def service_primary(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:81>) | Druhá časť, kapitola 1 |
| [bp_u9.py · def preflight(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:133>) | Druhá časť, kapitola 2 |
| [bp_u9.py · def unified_policy(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:85>) | Druhá časť, kapitola 2 |
| [u9_server.py · class Handler(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_server.py:52>) | Druhá časť, kapitola 3 |
| [u9_editor_api.py · def save(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:130>) | Druhá časť, kapitola 3 |
| [bp_u9.py · def run(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:278>) | Druhá časť, kapitola 3 |
| [u9-route-planner.js · function tree(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/viewer/u9-route-planner.js:22>) | Druhá časť, kapitola 4 |
| [u9_editable_scenario.py · def make_inputs(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editable_scenario.py:296>) | Druhá časť, kapitola 4 |
| [u9_editable_scenario.py · def run(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editable_scenario.py:431>) | Druhá časť, kapitola 4 |
| [bp_u9.py · def runtime_inputs(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:46>) | Druhá časť, kapitola 5 |
| [u9_prepare_cam.py · def prepare(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_prepare_cam.py:19>) | Druhá časť, kapitola 5 |
| [u9-service-native.cc · class Runtime ](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:48>) | Druhá časť, kapitola 6 |
| [u9-service-native.cc · class Station ](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:168>) | Druhá časť, kapitola 6 |
| [u9-service-native.cc · void check(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:212>) | Druhá časť, kapitola 6 |
| [u9-service-native.cc · void indicate(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:275>) | Druhá časť, kapitola 6 |
| [u9_orbit_source.py · def validate_pin(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_orbit_source.py:21>) | Druhá časť, kapitola 7 |
| [v3_leo_topology.py · def load_orbits(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/v3_leo_topology.py:106>) | Druhá časť, kapitola 7 |
| [v3_leo_topology.py · def sample(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/v3_leo_topology.py:151>) | Druhá časť, kapitola 7 |
| [u9_antenna_envelope.py · def angles_deg(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_antenna_envelope.py:63>) | Druhá časť, kapitola 8 |
| [u9_local_environment.py · def impute_building_heights(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_local_environment.py:61>) | Druhá časť, kapitola 8 |
| [u9_local_environment.py · class LocalObstructions:](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_local_environment.py:313>) | Druhá časť, kapitola 8 |
| [u9_dynamic_service.py · def plan(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_dynamic_service.py:82>) | Druhá časť, kapitola 9 |
| [u9_dynamic_service.py · def _path(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_dynamic_service.py:57>) | Druhá časť, kapitola 9 |
| [u9-service-native.cc · struct ServiceRoute ](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:304>) | Druhá časť, kapitola 10 |
| [u9-service-native.cc · class ServiceModel ](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:309>) | Druhá časť, kapitola 10 |
| [u9-service-native.cc · void hop(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:432>) | Druhá časť, kapitola 10 |
| [u9-service-native.cc · void offer(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-service-native.cc:466>) | Druhá časť, kapitola 10 |
| [u9_link_budget.py · def evaluate(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_link_budget.py:114>) | Druhá časť, kapitola 11 |
| [u9_link_budget.py · def _budget(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_link_budget.py:77>) | Druhá časť, kapitola 11 |
| [u9_service_native.py · write_json(output/'link-budget.json'](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:132>) | Druhá časť, kapitola 11 |
| [u9-full-advanced.cc · class SimulatorRuntime ](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/src/u9-full-advanced.cc:56>) | Druhá časť, kapitola 12 |
| [run_u9_advanced.py · def run(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/run_u9_advanced.py:23>) | Druhá časť, kapitola 12 |
| [check_u9_advanced.py · def ](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/check_u9_advanced.py:14>) | Druhá časť, kapitola 12 |
| [u9_service_native.py · def run(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:104>) | Druhá časť, kapitola 13 |
| [u9_service_native.py · def verify(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:204>) | Druhá časť, kapitola 14 |
| [bp_u9.py · def verify(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/bp_u9.py:365>) | Druhá časť, kapitola 15 |
| [u9_service_native.py · def verify(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_service_native.py:204>) | Druhá časť, kapitola 15 |
| [u9_editor_api.py · def verified_run(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:52>) | Druhá časť, kapitola 16 |
| [u9_editor_api.py · def replay(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:453>) | Druhá časť, kapitola 16 |
| [u9_editor_api.py · def packet(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_editor_api.py:529>) | Druhá časť, kapitola 16 |
| [u9_run_ground.py · def compile_source(](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/tools/u9_run_ground.py:45>) | Druhá časť, kapitola 17 |

## Projektové metodické podklady

- [docs/experiments/obnova-native-2026-10-25.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/experiments/obnova-native-2026-10-25.md>)
- [docs/decisions/u9-service-packet-backend-contract.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/decisions/u9-service-packet-backend-contract.md>)
- [docs/experiments/f2c-servisny-paketovy-backend-2026-11-01.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/experiments/f2c-servisny-paketovy-backend-2026-11-01.md>)
- [docs/experiments/f3-antenny-profil-montaz-2026-11-01.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/experiments/f3-antenny-profil-montaz-2026-11-01.md>)
- [docs/experiments/f4-lokalne-prekazky-prostredie-2026-11-01.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/experiments/f4-lokalne-prekazky-prostredie-2026-11-01.md>)
- [docs/plan-fyzikalna-vernost-2026-11-01.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/plan-fyzikalna-vernost-2026-11-01.md>)
- [docs/navod-na-pouzitie.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/navod-na-pouzitie.md>)
- [docs/reprodukcia.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/reprodukcia.md>)
- [docs/technicky-report-simulatora-2026-10-28.md](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/technicky-report-simulatora-2026-10-28.md>)

Externé produktové hodnoty report opisuje ako konštanty a hranice aktuálnej implementácie. Nevykonával sa nový webový audit produktov; projektové F dokumenty a zdrojové profily zachovávajú odkazy na pôvodné podklady. V tomto reporte sa teda neposkytuje nové tvrdenie o aktuálnej obchodnej ponuke operátorov.
