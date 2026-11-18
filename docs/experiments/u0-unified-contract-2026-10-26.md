# U0: prijatie spoločného kontraktu a integračnej kostry

**Dátum:** 26. 10. 2026. **Stav:** dokončená U0; žiadny nový zjednotený paketový beh. Ďalšia etapa je U1. Kontrakt a vysvetlenie fungovania: [U0 architektúra](../decisions/u0-unified-architecture-contract.md), pracovné poradie: [U0–U8](../plan-zjednoteny-simulator-2026-10-26.md).

## Zafixovaný východiskový stav

[Manifest SHA-256](u0-baseline-sha256.json) uvádza 32 konkrétnych súborov: historický V0 zdrojový register, V8 vydanie, štyri C++ modely, runnery/analyzátor, nový U0 kontrakt a príklady, manifesty štyroch referenčných výsledkov a štyroch finálnych U0 plánov. Pôvodné P/V raw stopy sa nemenili. Read-only checkery nad existujúcimi výsledkami 26. 10. vrátili:

Obnoviteľná kópia týchto 32 súborov aj manifestu je `archive/u0-unified-source-20261026.tar.gz` s vlastným `.sha256`. `sha256sum -c` prešiel; po rozbalení do dočasného priečinka prešlo všetkých 32 obsahových hashov. Veľké historické raw výsledky sú zachované na pôvodných miestach a vo V8 prijímacom archíve, nie zdvojené v U0 kópii.

| Historický dôkaz | Výsledok |
| --- | --- |
| `results/v3_runs/v8_three_parameters_20261026` | V8 natívne `PASS`, 1 opakovanie × 3 vetvy. |
| `results/v5-ground-2026-10-26-r9` | V5 pozemné `PASS`, 9 prípadov. |
| `results/v6_service_architectures_20261026` | V6 servisné `PASS`, 17 prípadov; kontrola s `--skip-p4-reaudit`, samotné V6 raw a pôvod sa kontrolovali. |
| `results/v3_leo_native_v3_bratislava_20261026` | V3 jeden UT `PASS`, 51 geometrických vzoriek, 119 per-event záznamov. |

## Nové vykonané artefakty

- `config/unified_scenario_contract_v1.json`: presný obal scenára, štyri výberové schémy a rovnaký `common` blok pre každý režim; režimovo špecifické údaje sú v `details`. Žiadne skryté defaulty. Zdroj je projektová relatívna cesta s SHA-256.
- `config/unified_capabilities_v1.json`: štyri režimy s presným stavom, runnerom/checkerom, vernosťou a hranicou. `integrated_end_to_end=false` je výslovný.
- `config/unified_event_contract_v1.json` a `tools/unified_events.py`: budúca 64-bit identita CAM/report/odpoveď, spoločný event a metric schema, kontrola kolízií, duplicitných sekvencií, drop dôvodov, menovateľov a zhodnosti zlomku. Historické event ID neboli zmenené.
- `tools/unified_contract.py`: `preflight`, neprepisujúce `plan` a read-only `verify`; adaptuje existujúce V5, V8, V6 a V3 validátory. Nevykonáva pakety. Pri servisnom režime kontroluje presne šesť historických ICB1 vrátane bajtov/ID/času a pôvodného V6 manifestu; pri geometrii vykoná kandidátny výpočet bez tvrdenia o službe.
- Štyri vzory v `config/unified_examples/`. Finálne plány sú v `results/u0_unified_contract_20261026/{ground,native,service,geometry}/`; každý má `normalized.json`, `capability-plan.json`, `manifest.json` a opakované `verify: PASS`. Skorší vývojový variant sa zachoval pod `results/u0_unified_contract_20261026_draft/` a **nie je** prijímacím artefaktom.

## Prijímacie kontroly

`python -m unittest discover -s tools -p 'test_unified_contract.py'`: 5/5 testov. Pokrývajú štyri pravdivé režimy, neprípustný operátorský RF mód, neznáme pole, zmenený hash zdroja, zlý case/profil, pokus zameniť geometrický režim za paketový, reprodukovateľný plán, semanticky sfalšovaný plan po prepočte hashov, rovnaký CAM `generationDeltaTime` u dvoch áut, opakovaný 16-bit čas v neskoršej epoche, duplicitnú sekvenciu, vynútenú 64-bit kolíziu, falošný drop a zlý menovateľ. Celá projektová sada po zmene: **91 testov, OK**.

Štyri finálne plány boli vytvorené samostatne a každý prešiel týmto príkazom (s vlastným koncovým priečinkom):

```bash
.venv/bin/python tools/unified_contract.py verify results/u0_unified_contract_20261026/native
.venv/bin/python tools/unified_contract.py verify results/u0_unified_contract_20261026/ground
.venv/bin/python tools/unified_contract.py verify results/u0_unified_contract_20261026/service
.venv/bin/python tools/unified_contract.py verify results/u0_unified_contract_20261026/geometry
```

**Hranica U0:** toto je kontrakt, schopnostná matica a overiteľný preflight. V5 viacvysielačový CAM/DCC a V8 satelitné pakety ešte nie sú jedným procesom ani jedným časom; nový event schema sa ešte neemituje z C++. V6 stále prehráva historických šesť reportov. U1 musí ako nový celok dodať spoločný natívny beh, skutočné nové event ID v raw stopách, byte checker a záporné kontroly. U0 ich úspech netvrdí.
