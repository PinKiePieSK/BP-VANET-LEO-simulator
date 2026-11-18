# U0: jeden kontrakt, štyri pravdivé režimy

**Verzia 1, 26. 10. 2026.** Tento dokument je mapa fungovania aktuálneho systému a hranica pre U1. U0 **nespája V5 a V8 do jedného paketového behu**. Zdrojový stav a prijatie sú v [denníku U0](../experiments/u0-unified-contract-2026-10-26.md); poradie ďalšej práce v [pláne U0–U8](../plan-zjednoteny-simulator-2026-10-26.md).

## Ako prejde jedna informácia

1. Vstupný JSON v `config/unified_examples/` označí režim a **hashom** pripne existujúci konkrétny scenár. `tools/unified_contract.py` najprv skontroluje obal, verziu, známu schopnosť a hash vstupu, potom zavolá existujúci preflight príslušnej vrstvy. Z normalizácie uloží spoločný blok `common` a podrobný blok `details`: čas, uzly, aplikáciu, pozemné rádio, backhaul, experiment, pôvod dát a skutočné hranice vykonania. Presné polia a výslovný význam `null` sú v `config/unified_scenario_contract_v1.json`.
2. `ground`: V5 SUMO/FCD → viac vozidiel s Vanetza CAM → ns-3.38 ITS-G5 OCB/DCC → lokálne autá a RSU. Končí sa na pozemnom prijatí. Kód: `tools/run_v5_ground.py`, `src/v5-ground-cam-dcc.cc`; checker: `tools/check_v5_ground.py`.
3. `native_generic_dvb`: V8 SUMO/FCD → CAM z jedného vybraného auta → OCB/RSU → nový 96 B ICB1 → UT/SNS-3 DVB/SAT0/ISL/SAT1/GW → GRA1/I2V1 odpoveď. Kód: `tools/bp_v8.py`, `tools/run_scenario_v3_native.py`, `src/v3-native-cam-leo.cc`; checker: `tools/check_scenario_v3_native.py`. V8 zatiaľ nepoužíva V5 súbežný CAM/DCC mechanizmus.
4. `service_boundary_replay`: V6 zoberie šesť historických, natívne overených ICB1 od RSU a vykoná model IP alebo MO/MT hranice služby. Kód: `tools/run_v6_services.py`; checker: `tools/check_v6_services.py`. Replay nie je proprietárne satelitné RF/MAC a zatiaľ nepreberá čerstvú ľubovoľnú dávku z V8.
5. `geometry_only`: V3 načíta archivované dráhy, EOP a vypočíta výhľad/trasového kandidáta cez `tools/v3_leo_topology.py`. Kandidát nepreukazuje aktívny lúč, pripojenie, servis ani doručenie. V3/V4 samostatné paketové experimenty ostávajú osobitné, kým U3/U4 neprenesú ich mechanizmy do spoločného enginu.

Všetky štyri režimy používajú len **ns-3.38/SNS-3 3.38** tam, kde sú potrebné sieťové pakety. `config/unified_capabilities_v1.json` obsahuje aktuálny stav, príslušný runner/checker a hranicu tvrdenia. U0 CLI vie `preflight`, `plan` a `verify`; **nespúšťa simulačné pakety**. Preto výstup každého plánu nesie `execution_in_this_cli=preflight_only_no_packets` a `integrated_end_to_end=false`.

## Identita, čas, obsah a metriky

`CAM.generationDeltaTime` je 16-bitové modulo časové pole, nie unikátne ID. Nový kontrakt v `tools/unified_events.py` vytvára 64-bitové ID z doménovo oddeleného SHA-256 nad `scenario_id`, `run_id`, `station_id`, sekvenciou, absolútnym simulačným `time_us` a wire `generationDeltaTime`. Register odmieta opätovné použitie sekvencie toho istého vysielača a každú kolíziu výsledného 64-bit ID. ICB1/report ID sa odvodí z parent CAM ID a RSU; odpoveď z parent report ID a príjemcu. Dva vysielače v rovnakom milisekundovom čase preto majú odlišnú identitu; historické V8 ID sa bez prepisu raw výsledkov nemenia. Prenos tejto mapy do C++ a ICB1 formátu je prijímacia úloha U1.

Každý budúci raw riadok má explicitný `run_id`, vetvu, režim, `event_id`, parent, vysielača/príjemcu, fázu, čas v µs, hash/dĺžku skutočných wire bajtov, stav, dôvod, vernosť a presný zdrojový riadok. `config/unified_event_contract_v1.json` a `validate_event` určujú povinné polia a drop dôvody. Chýbajúca fáza **nie je** automaticky `phy_drop`; keď príčinu nepoznáme, dôvod je `unknown`. Metrika má ID, hodnotu/jednotku, explicitný čitateľ/menovateľ, zoznam unikátnych event ID, vernosť a dôvod potlačenia. `validate_metric` odmieta napríklad úspech pri nulovom menovateli. U6 spojí tieto schémy so skutočnými raw stopami; U0 nimi definuje budúcu kompatibilitu.

**Rozdiel medzi výsledkami:** počet vytvorených CAM, ponúknutých CAM, skutočných MAC TX, unikátne dekódovaných CAM v RSU, vytvorených ICB1, včas prijatých reportov a odpovedí sú samostatné veličiny. Primárny deadline sa počíta od vopred určenej udalosti, nie automaticky od príjmu v RSU. Výsledok geometrie ani servisného replay nemôže dostať štítok `native_generic_dvb`.

## Opakovateľný U0 postup

```bash
.venv/bin/python tools/unified_contract.py preflight config/unified_examples/native-reference.json
.venv/bin/python tools/unified_contract.py plan config/unified_examples/native-reference.json results/NEPOUZITE_U0_ID
.venv/bin/python tools/unified_contract.py verify results/NEPOUZITE_U0_ID
.venv/bin/python -m unittest discover -s tools -p 'test_unified_contract.py'
```

`plan` nikdy neprepisuje existujúce ID. Uloží `normalized.json`, `capability-plan.json` a `manifest.json`. `verify` znovu spustí preflight nad pripnutými vstupmi, porovná presné kanonické bajty a hashe; upravený plán neprejde ani po prepočte jeho vlastného hashového poľa. Toto je dôkaz **kontraktu**, nie dôkaz nového natívneho doručenia. V U1 sa naň naviaže prvý skutočný jednotný paketový engine a nový raw checker.
