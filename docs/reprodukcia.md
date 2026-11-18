# Reprodukcia simulátora a historických experimentov

Aktuálne spustenie a kontrola prenosného simulátora sú v [odovzdávacom návode](simulator-odovzdanie.md). Príkazy starších míľnikov nižšie sú historický záznam. Ich sondy a pomocné skripty boli 3. 11. 2026 presunuté do `tools/legacy/`, `src/legacy/` a `scripts/legacy/`; na doslovnú reprodukciu starého behu použi zachovanú zdrojovú snímku v `archive/pre-cleanup-simulator-20261103/` a príslušný výsledkový manifest.

**Aktuálne U7:** spoločný editor, scenár, príkazy, checkery a limity sú v [návode a prijímacom dôkaze U7](experiments/u7-unified-control-2026-10-27.md). Nižšie uvedené V8 a staršie postupy zostávajú historicky platné v ich pôvodnom rozsahu.

**Stav 26. 10. 2026.** Koreňom je tento priečinok `obnova/Bakalarska praca/`; príkazy spúšťaj z neho. Jediný runtime je **ns-3.38/SNS-3 3.38** v `vendor/ns-3.38-ocb-eval`. Staré 3.48 a `/tmp/ns3-sns3-338-feasibility` nie sú zdrojovým checkoutom. Pôvodný návod s historickými príkazmi je zachovaný v [archíve](archive/reprodukcia-pred-p6-20261026.md).

**Odovzdávací postup V8:** [offline archív, kontrola hashov, čistá obnova a nový smoke beh](../release/README-V8.md). [Kontrakt jednotného CLI](decisions/v8-cli-release-contract.md) určuje `configure → validate → run → verify → analyze → verify-analysis` a rozlišuje generický DVB model od operátorských návrhov. [Prijímací denník](experiments/v8-release-2026-10-26.md) zaznamenáva výsledok z rozbaleného artefaktu. Nižšie zostávajú reprodukčné príkazy starších P5/P6 experimentov.

## 1. Obnova celého priečinka na Ubuntu

Prenes **celý** projekt vrátane ignorovaných `vendor/`, `build/`, `data/`, `results/`, `archive/` a patchov. Systémové balíky a pripnuté verzie uvádza [migračný návod](migracia-na-nativne-ubuntu.md). V novej kópii najprv spusti:

```bash
python3 scripts/check_migration.py
bash scripts/obnovit-native-ubuntu.sh
python3 scripts/check_migration.py
```

Obnovovací skript regeneruje `.venv` a lokálne CMake/ns-3 cache, preto patrí do **novej kópie**, nie do rozbehnutého experimentu. Zdrojové commity, patche, orbitálne gzip/OMM a pôvodné výsledky kontroluje `check_migration.py`. Skript nainštaluje aj pripnuté P5 analytické balíky vrátane kompatibilného NumPy a na záver spustí `pip check`.

## 2. Rýchly preflight a finálne dôkazy

```bash
.venv/bin/python -m unittest discover -s tools -p 'test_*.py'
.venv/bin/python tools/validate_bp_experiment_contract.py
.venv/bin/python tools/check_two_leo_roundtrip.py results/native_two_leo_roundtrip_p1_final_20261025
.venv/bin/python tools/check_p2_urban_load.py results/p2_urban_load_20261025
.venv/bin/python tools/check_p2_osm_pair.py results/p2_osm_pair_20261025
.venv/bin/python tools/check_p2_fault_hops.py results/p2_fault_hops_20261025
.venv/bin/python tools/check_p2_complete.py results/p2_complete_20261026
.venv/bin/python tools/check_p3_single_ut.py results/p3_single_ut_verified_20261026
.venv/bin/python tools/check_p4_service_profiles.py results/p4_service_profiles_20261026_v6
.venv/bin/python tools/check_p5_native_matrix.py results/p5_native_final_20261026
.venv/bin/python tools/check_p5_service_matrix.py results/p5_service_final_20261026
.venv/bin/python tools/check_p5_analysis.py results/p5_native_final_20261026 results/p5_service_final_20261026 results/p5_analysis_final_20261026
.venv/bin/python tools/check_p5_feedback_pairing.py results/p5_feedback_diagnostic_20261026
```

Každý checker číta raw stopy a pripnutý manifest. `verification.json` je výsledok kontroly, nie jej náhrada. P0–P5 dôkazy a obmedzenia sú v [pracovnom pláne](pracovny-plan-simulatora.md) a príslušných [denníkoch](experiments/p5-final-matrix-2026-10-26.md). Checkery odmietajú zmenené zdroje alebo obsah; po úmyselnom zásahu do zdroja sa historická stopa nemá vydávať za nový PASS.

Celý čítací audit vrátane integrity aktívnych lokálnych dokumentačných odkazov spustí aj jediný príkaz. Použi nové ID, pretože výstupný adresár sa nesmie prepisovať:

```bash
.venv/bin/python scripts/p6_final_preflight.py results/p6_final_preflight_NEW_ID
```

`manifest.json` a jednotlivé logy zaznamenajú stav každej kontroly a SHA-256 finálnych overení a grafov. Tento audit nenahrádza čisté zostavenie v oddelenej kópii projektu.

## 3. Nový kompletný beh P5

Zvoľ nové jedinečné ID. Natívny C++ parser vyžaduje pri výstupe cestu bez medzier, preto sa najprv pracuje v `/tmp`; projektová kópia sa potom overí znovu. Výstupné priečinky sa neprepisujú.

```bash
.venv/bin/python tools/run_p5_native_matrix.py config/p5_final_matrix.json vendor/ns-3.38-ocb-eval /tmp/p5_native_NEW_ID --workers 4
cp -a /tmp/p5_native_NEW_ID results/p5_native_NEW_ID
.venv/bin/python tools/check_p5_native_matrix.py results/p5_native_NEW_ID
.venv/bin/python tools/run_p5_service_matrix.py results/p5_native_NEW_ID results/p5_service_NEW_ID
.venv/bin/python tools/check_p5_service_matrix.py results/p5_service_NEW_ID
.venv/bin/python tools/analyze_p5_matrix.py results/p5_native_NEW_ID results/p5_service_NEW_ID results/p5_analysis_NEW_ID
.venv/bin/python tools/check_p5_analysis.py results/p5_native_NEW_ID results/p5_service_NEW_ID results/p5_analysis_NEW_ID
```

Tento protokol obsahuje 6 seedov, 2 UTC epochy vzdialené 92 s, riedku/hustú dopravu, nízku/vysokú lokálnu CAM záťaž a S0/S1/S2 natívne vetvy. P4 servisné obaly sa prehrávajú z **rovnakých RSU ICB1 bajtov a časov** vo vetve S0. Grafy sú v `results/p5_analysis_*/`; vytvárajú sa zo `summary.csv` a `local.csv` z raw odvodených metrík.

## 4. Cesta od grafu k paketu

1. Otvor `results/p5_analysis_final_20261026/p5_service_sensitivity.png` a jeho `manifest.json`. `products_sha256` identifikuje graf, `service_metrics_sha256` súhrnný zdroj a `protocol_sha256` vopred určený plán.
2. V `summary.csv` vyber `group`, `transport`, `variant`, menovateľ `created`, počet `delivered`, 95 % interval a rozsah párovaných jednotiek. `local.csv` má samostatný menovateľ párov CAM–auto.
3. V `results/p5_service_final_20261026/service-metrics.csv` nájdi konkrétny `block_id`, `group`, `profile`, `variant` a `event_id`. `run-manifest.json` ukáže príslušný raw `trace.csv`, jeho SHA-256 a natívny zdroj.
4. `results/p5_native_final_20261026/<block_id>/<group>_s0/trace.csv` obsahuje presný `RSU_REPORT_CREATED` ICB1; súvisiaci prípad obsahuje OCB/LAN PCAP, `PacketTrace.log`, SUMO FCD, waypointy a modelové vstupy. Natívny checker porovnáva obsah, kontrolné súčty, časové poradie a záporné vetvy.

**Konkrétna kontrola:** V grafe servisnej citlivosti vyber `sparse_low`, `starlink`, `sensitivity_high`. Súhrn má 66/72 včasných doručení. V `service-metrics.csv` nájdi blok `seed314171_124500` a `event_id=ca00000000005a88`. Servisný `run-manifest.json` pre tento blok/skupinu/profil/variant pripína `starlink_sensitivity_high.csv` so SHA-256 `9a14ac77f1a2c751ebc2566a8c174a7dc3ae938deac5c212b87b370bb5f8c482`. Jeho `RSU_REPORT_CREATED` má 96 B pri 20 000 220 µs; presne tie isté raw bajty sú v natívnom `seed314171_124500/sparse_low_s0/trace.csv`. SHA-256 týchto 96 B je `78d96f241f7e8aefb652fffcaa2a99c23695ce95dd2a3d80979ae4e3048b587c`. Servisná stopa následne ukazuje `UL_IP_TX`, `REMOTE_APP_RX`, `DL_IP_TX` a `RSU_RECEIPT_RX`. Reťaz sa dá opäť nezávisle prejsť vyššie uvedenými P5 checkermi.

Modelové profily Starlinku, Iridia a Globalstaru **nie sú** nezávisle validované komerčné služby. Krátke UTC okno, retrospektívne orbitálne vstupy, proxy brány, hypotetické straty/oneskorenia a generický DVB limitujú závery. Preto neodvodzuj prevádzkové PDR, dostupnosť, p99 ani poradie operátorov. Presné čísla a hashe sú v [denníku P5](experiments/p5-final-matrix-2026-10-26.md).

## 4. U1 spoločný CAM/DCC/LEO engine

Prijatý deväťvetvový U1 beh a výsledky checkera sú v [denníku U1](experiments/u1-integrated-cam-leo-2026-10-26.md). Overenie existujúcich dôkazov:

```bash
.venv/bin/python tools/check_v5_ground.py results/u1_ground_baseline_20261026b
.venv/bin/python tools/check_u1_integrated.py results/u1_integrated_20261026final
.venv/bin/python tools/test_u1_integrated_mutation.py results/u1_integrated_20261026final
```

Pre nové výsledky zvoľ nové ID, pretože oba runnery odmietajú prepis:

```bash
.venv/bin/python tools/run_v5_ground.py --config config/u1-ground-pilot.json --output results/u1_ground_NEW_ID
.venv/bin/python tools/check_v5_ground.py results/u1_ground_NEW_ID
.venv/bin/python tools/run_u1_integrated.py --baseline results/u1_ground_NEW_ID --output results/u1_integrated_NEW_ID
.venv/bin/python tools/check_u1_integrated.py results/u1_integrated_NEW_ID
```

U1 má zatiaľ jeden aktívny RSU/UT, syntetické SUMO dopyty a pripnutú generickú DVB referenciu. Jeho `identity.csv` a `trace.csv` sú základom pre vysvetlenie jednej správy a nezávislé prepočítanie bajtov; [kontrakt](decisions/u1-integrated-engine-contract.md) rozlišuje skutočne vykonanú cestu od ďalších etáp.

## 5. U2 viac RSU a párovaný lokálny/pozemný/satelitný backhaul

Prijatých 23 vetiev, presné počty, manifestové hashe a hranice modelu sú v [denníku U2](experiments/u2-multi-rsu-backhaul-2026-10-26.md). Kontrola pôvodných dôkazov:

```bash
.venv/bin/python tools/check_v5_ground.py results/u2_ground_one_20261026
.venv/bin/python tools/check_v5_ground.py results/u2_ground_two_20261026
.venv/bin/python tools/check_u2_integrated.py results/u2_integrated_20261026final
.venv/bin/python tools/test_u2_integrated_mutation.py results/u2_integrated_20261026final
```

Pre nový beh najprv vytvor dve nové V5 baseline pomocou `tools/run_v5_ground.py` a over ich. V **novej kópii** `config/u2-integrated-matrix.json` nastav obe nové `result_path`, `config_path` a `config_sha256`; potom spusti `tools/run_u2_integrated.py --config <nová_matica> --output results/u2_integrated_NEW_ID` a `tools/check_u2_integrated.py` nad novým výsledkom. Runner odmieta prepísanie výsledkov. U2 stále používa pevný spoločný UT a generickú DVB referenciu; dynamická LEO cesta je etapa U3.

**Nástupnícky variabilný U2:** [denník škálovania](experiments/u2-variable-rsu-2026-10-26.md) má spoločnú 26‑vetvovú maticu pre 1/2/3 RSU a 3/5/12/24 áut. Overenie:

```bash
.venv/bin/python tools/check_v5_ground.py results/u2_ground_three_20261026b
.venv/bin/python tools/check_u2_variable.py results/u2_variable_full_20261026
.venv/bin/python tools/test_u2_variable_mutation.py results/u2_variable_full_20261026

# Po príprave nových overených V5 baseline a novej matice, nikdy nie do existujúceho adresára:
.venv/bin/python tools/run_u2_variable.py --config config/u2-variable-full-matrix.json --output results/u2_variable_NEW_ID
.venv/bin/python tools/check_u2_variable.py results/u2_variable_NEW_ID
```

Položky `ground_baselines` v matici určujú svet, dopyt, počet áut a RSU; runner/checker odvodzujú prípady z ich overených manifestov. Počet satelitov ešte nie je takto parametrický: U2 obsahuje pripnutú dvojicu a U3 musí doplniť orbitálny pool, ISL graf a obojsmernú trasu. [Kontrakt mierky](decisions/variable-topology-contract-2026-10-26.md) uvádza presné dnešné kapacitné hranice.
