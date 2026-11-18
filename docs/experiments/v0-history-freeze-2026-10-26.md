# V0 — zmrazenie historického dôkazu a mapa závislostí

**Stav:** HOTOVO 26. 10. 2026; brána V0 splnená. **Účel:** ponechať P0–P6 overiteľné aj po zmene zdrojového kódu univerzálneho enginu. Staré raw výsledky, manifesty a význam metrík sa nemenia.

## Nemenný zdrojový balík

- `archive/v0-source-20261026.tar.gz` obsahuje **464** zdrojových súborov alebo odkazov: `src`, `tools`, `scripts`, `config`, `patches`, `viewer`, `docs`, `thesis`, `scenarios`, malé `data/inputs`, `data/orbits`, `data/derived`, vstupné requirements a koreňové návody. Veľkosť: **3 046 307 B**; SHA-256: `58bde6846ba0777841e46e7ec40abec36894207e2231645adc034bdd56ef06c6`.
- `archive/v0-source-20261026.manifest.json` zaznamenáva hash každého bežného člena a cieľ symlinkov. Balík aj manifest majú režim iba na čítanie; ich bajtovú integritu znovu kontroluje `tools/v0_history.py validate`. Sú mimo hlavného Gitu, preto pri prenose treba **celý projektový priečinok** alebo obidva súbory samostatne priložiť.
- Veľké `results/`, `vendor/`, `build/`, `.venv/`, `archive/` a `data/additional-input/` nie sú duplicitne zabalené. Pri historickom audite sa pripoja zo súčasnej úplnej kópie; P6 kontroluje ich piny, patch, archívne dáta a raw/manifest hashe. Zdrojový balík bez týchto externých vstupov nie je samostatná kompletná reprodukčná kópia.
- **Jediný runtime zostáva ns-3.38/SNS-3 3.38.** Historická kontrola používa zdroje extrahované z balíka, nie aktuálny `src/`, `tools/`, `config/` alebo `scripts/`.
- `config/simulator_generation_registry.json` vyhradzuje `p0-p6-20261026` pre zmrazené výsledky a `universal-scenario-v3`/`results/v3_runs/` pre budúci engine. Nová schéma je zatiaľ **rezervovaná, nespustiteľná**; V1 zavedie jej validátor. Historický manifest sa nesmie vydávať za výstup v3.

Spustenie z koreňa projektu:

```bash
python3 tools/v0_history.py validate
python3 tools/v0_history.py verify results/NEW_UNIQUE_V0_AUDIT_ID
```

`verify` odmieta existujúci výstup. Výsledky pre kontrolu dočasne sprístupní v samostatnom koreni a samotný P6 preflight zapisuje prepočítané metriky iba do **dočasných kópií**. Pôvodné raw výstupy preto nie sú prepísané. Nové behy univerzálnej platformy budú mať inú schému a adresárovú rodinu.

## Mapa vykonania a pôvodu výsledkov

| Fáza | Vstup a hlavný kód | Výstup a kontrola |
| --- | --- | --- |
| 1. Protokol | `config/p5_final_matrix.json`, `config/bp_experiment_contract_v1.json`, `tools/run_p5_native_matrix.py` | seed × UTC × skupina × S0/S1/S2, kontrola schémy a vstupných hashov |
| 2. Doprava | `data/inputs/editable-road-v2/packet-subset.json`, `tools/run_p2_urban_load.py`, `tools/editable_scenario_v2.py`, SUMO | `scenario.json`, `sumo/fcd.xml`, metadáta geografie a FCD hash |
| 3. CAM vzorky | `tools/prepare_editable_v2_cam.py` | `waypoints.csv`, CAM časy a bajtové/geografické vstupy |
| 4. LEO referencia | `tools/run_two_leo_isl_reference.py`, archívne OMM/EOP, `vendor/ns-3.38-ocb-eval`, patche | pripnuté TLE/scenario/anténne vstupy, piny SNS-3 a Vanetza |
| 5. Natívny paketový beh | `src/p5-urban-matrix.cc` zostavený v runneri | `trace.csv`, OCB/LAN PCAP, SNS-3 `PacketTrace.log`, `delivery.csv` |
| 6. Natívny audit | `tools/check_p5_native_matrix.py` a importované P2 checkery | `native-metrics.csv`, `verification.json`; presné ICB1/GRA1, lokálne PCAP a negatívne vetvy |
| 7. Servisné obaly | `config/p4_service_profiles.json`, `tools/p5_service_geometry.py`, `tools/run_p4_service_profiles.py`, `tools/run_p5_service_matrix.py` | geometrickí kandidáti a trace troch profilov z tých istých S0 RSU ICB1 |
| 8. Servisný audit | `tools/check_p5_service_matrix.py` | `service-metrics.csv`, profilová topológia, rozmery správ, checksums, čas a hash |
| 9. Analýza | `tools/analyze_p5_matrix.py`, `requirements-p5-analysis.txt` | `summary.csv`, `local.csv`, PNG/PDF grafy a manifest |
| 10. Reprodukcia výsledku | `tools/check_p5_analysis.py`, `scripts/p6_final_preflight.py` | analýza z raw metrík, bajtovo rovnaké grafy, P0–P5 audit vrátane 69 Python testov |

P5 servisný checker navyše číta natívny manifest a RSU raw reporty; analytický checker používa aj P3 `verification.json`. Preto historický dôkaz nie je iba samotný C++ súbor a tri CSV. Zmrazenie zahŕňa celý kódový reťazec aj malé zdrojové vstupy.

## Register pevných hodnôt, ktoré V1–V4 nemajú potichu dediť

| Terajší pin | Miesto | Význam pre nový engine |
| --- | --- | --- |
| Dve UTC epochy 22. 10. 2026, obmedzenie 12:00–14:00 | `prepare_editable_v2_cam.py`, `run_p5_native_matrix.py`, `p5-urban-matrix.cc` | Historická kvalifikácia modelu, nie všeobecný rozsah UTC. Nový scenár musí dostať vlastný orbitálny preflight. |
| Presne 6 CAM v čase 20,0–22,5 s po 0,5 s | `prepare_editable_v2_cam.py`, `p5-urban-matrix.cc`, P5 checkery | Fixture a štatistická jednotka P5; počet/časy musia byť v novej schéme parametre. |
| `car0`, `rsu0`, jeden primárny vysielač a jedno RSU | `p5-urban-matrix.cc`, P5 checker | V2 oddelí identitu uzla, aplikačnú rolu a politiku RSU. |
| Objekty 43253/43258, dve družice, pevné beam 30/43, 10° maska | `run_two_leo_isl_reference.py`, `p5-urban-matrix.cc`, `p5_service_geometry.py` | V3 kvalifikuje topológiu pre každý čas/miesto; geometria nie je attach. |
| 17 dBi diagnostická mapa, 1 Gbit/s ISL, proxy gateway | `run_two_leo_isl_reference.py`, `p5-urban-matrix.cc`, satelitné scenáre | V4 zdrojuje alebo explicitne označí citlivostné parametre. |
| 20 dBm, 6 Mb/s, 7 dB NF, shadowing off | `p5-urban-matrix.cc` | V5 pomenúva zariadenie/model, neistotu a validáciu. |
| 60 s deadline | `bp_experiment_contract_v1.json`, P5 checkery | Aplikačný výskumný prah; nový kontrakt ho deklaruje s významom správy. |
| Servisný delay/loss/queue | `p4_service_profiles.json` | Hypotetická citlivosť bez nezávislej validácie; V6 nesmie zmeniť štítok na meranie služby. |

## Prijímací dôkaz V0

1. `python3 tools/v0_history.py validate` prečíta celý archív a porovná každého člena s manifestom.
2. Audit extrahovaného balíka spustí historický P6 preflight nad jeho vlastnými zdrojmi. Očakáva sa **15/15** kontrol, historické raw hashe sa nezmenia.
3. Pri dočasnej nefunkčnej zmene aktívneho `src/p5-urban-matrix.cc` má dnešný P5 checker odmietnuť starý manifest, zatiaľ čo checker zo zmrazeného balíka má stále prejsť. Aktívny zdroj sa po skúške bajtovo obnoví a overí SHA-256.

**Skutočný výsledok:** archívny audit v `results/v0_historical_audit_20261026_v2/manifest.json` prešiel **15/15** P6 kontrol nad extrahovaným zdrojovým balíkom. Prvý vývojový pokus `results/v0_historical_audit_20261026` zlyhal ešte pred kontrolami na bezpečnostnom pravidle P6 pre lokálne dokumentačné odkazy: symlink výsledkov smeroval mimo extrahovaného koreňa. Opravený wrapper vytvoril v dočasnom koreni hardlinky raw súborov; P6 nad nimi naďalej pracoval len cez svoje dočasné kópie. Neúspešný pokus je zachovaný, nie vydávaný za dôkaz.

Mutačná skúška `results/v0_historical_audit_mutation_20261026/mutation-test.json` dočasne zmenila aktívny `src/p5-urban-matrix.cc`. Aktuálny P5 checker skončil chybou `P5 source pin mismatch: source_sha256`; zmrazený audit opäť prešiel **15/15**. SHA-256 aktívneho C++ súboru pred aj po obnove je `500b00a6359b695a5612f5ba5b0a14672ea4c53a4631408699a01895698dac81`. Pôvodné výsledky podľa P6 preflightu zostali bajtovo nezmenené.

Tieto body overujú **kontinuitu dôkazu**, nie presnosť komerčných sietí ani všeobecnú konfigurovateľnosť. V1 je nasledujúci samostatný celok.
