# U2 rozšírenie — počet áut a aktívnych RSU zo scenára

**Práca a overenie:** 26.–27. 10. 2026. **Runtime:** ns-3.38/SNS-3 3.38. **Tvrdenie:** parametrizovaná výskumná cesta v súčasnom otestovanom rozsahu; satelitná vetva je stále dvojobjektový generický DVB model.

## Prečo vzniklo rozšírenie

Pôvodný [U2 prijímací beh](u2-multi-rsu-backhaul-2026-10-26.md) preukázal 1/2 RSU a 3/12/24 áut, ale engine odmietal tretie RSU a runner/checker poznali len pevné názvy šiestich prípadov. Používateľ požaduje scenárom voliteľný počet áut, RSU a satelitov. Pôvodný zdroj, checker a 23 vetiev ostali nedotknuté, aby sa zachoval ich manifest a raw dôkaz. Nástupnícky `src/u2-variable-rsu-backhaul.cc`, `tools/run_u2_variable.py` a `tools/check_u2_variable.py` odstránili pevný dvojRSU guard a zoznam pomenovaných prípadov; variabilný orbitálny pool a routing zostávajú záväznou bránou U3 podľa [kontraktu mierky](../decisions/variable-topology-contract-2026-10-26.md).

## Nová mimomatričná skúška

- Vstup: `data/inputs/u2/base-world-three-rsu.json`, `data/inputs/u2/synthetic-05-trips.json`, `config/u2-ground-three-rsu.json`. Päť vozidiel `bg00`–`bg04`, tri aktívne RSU `rsu0/rsu1/rsu2`, 30 vzoriek po 100 ms, syntetická LOS premávka, DCC vypnuté.
- Pozemný V5 baseline: `results/u2_ground_three_20261026b/`, manifest SHA-256 `f93f7970500b41416867a19d4e5950b205d82f001905e70730f3988f567c2991`; nezávislý `tools/check_v5_ground.py` **PASS**.
- Finálny nový 8-vetvový beh: `results/u2_variable_three05_20261026final/`, manifest SHA-256 `f6371f02e140f287d041c0a946e42c38563382d506c8d14d454487fcca147198`; `tools/check_u2_variable.py` **PASS**. `tools/test_u2_variable_mutation.py` odmietol šesť sémantických mutácií (`selection`, `report_parent`, `return_recipient`, `isl_bytes`, oba smerové queue dôvody). Python regresia: 91 testov, OK.
- Spoločná prijímacia matica: `config/u2-variable-full-matrix.json` → `results/u2_variable_full_20261026/`, manifest SHA-256 `398edc47a8c3d4a2e0dcc111c53b684af912b16f69b84906febe1182efbd3d7a`. Jeden runner a checker **PASS** nad 7 prípadmi a **26 vetvami**: 1/2/3 RSU, 3/5/12/24 áut, tri párované režimy a päť poruchových kontrol. Pripnuté SHA-256 zdroja, runnera aj checkera súhlasia so súčasnými súbormi. Šesť mutácií v 3‑RSU kontrolnom prípade bolo odmietnutých aj v spoločnej matici.

| Vetva | CAM TX | RSU RX / duplicity | Vytvorené reporty | Ponuka / dopredný drop | Vzdialená aplikácia | Návratový drop / auto RX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `local` | 60 | 180 / 120 | 60 | 60 / 0 | 60 | 0 / 60 |
| `ground` | 60 | 180 / 120 | 60 | 60 / 0 | 60 | 0 / 60 |
| `satellite` | 60 | 180 / 120 | 60 | 60 / 0 | 58 | 0 / 58 |
| `blocked` / `no_isl` | 60 | 180 / 120 | 60 | 60 / 0 | 0 | 0 / 0 |
| `no_return_route` | 60 | 180 / 120 | 60 | 60 / 0 | 58 | 0 / 0 |
| `queue_overload` | 60 | 180 / 120 | 60 | 7 / 53 | 7 | 0 / 7 |
| `reverse_queue_overload` | 60 | 180 / 120 | 60 | 60 / 0 | 58 | 51 / 7 |

Všetky tri RSU reálne vyhrali politiku prvého dekódovania: `rsu1` 38×, `rsu2` 20×, `rsu0` 2×. Tá istá množina 60 originálnych CAM ID je v lokálnej, pozemnej a satelitnej vetve. Duplicity nie sú pridané do menovateľa jedinečných reportov. Satelitných 58/60 je výsledok tejto pripnutej modelovej zostavy, nie dostupnosť komerčnej služby.

## Reprodukcia

```bash
.venv/bin/python tools/check_v5_ground.py results/u2_ground_three_20261026b
.venv/bin/python tools/check_u2_variable.py results/u2_variable_three05_20261026final
.venv/bin/python tools/test_u2_variable_mutation.py results/u2_variable_three05_20261026final
.venv/bin/python tools/check_u2_variable.py results/u2_variable_full_20261026
.venv/bin/python tools/test_u2_variable_mutation.py results/u2_variable_full_20261026

# Nový beh: zvoľ nové ID, aby sa neprepisovali raw výsledky.
.venv/bin/python tools/run_u2_variable.py --config config/u2-variable-full-matrix.json --output results/u2_variable_NEW_ID
.venv/bin/python tools/check_u2_variable.py results/u2_variable_NEW_ID
```

`config/u2-variable-full-matrix.json` je verzia 2 s mapou `ground_baselines`. Každá položka obsahuje overený V5 výsledok, pôvodnú konfiguráciu a jej SHA-256; mená prípadov sa odvodia z položiek `cases`. Pre ďalší počet vozidiel alebo RSU treba pripraviť nový world/demand, spustiť V5 baseline a jeho checker, pridať položku do **novej kópie** matice a potom spustiť spoločný runner. Pevné číselné názvy v kóde runnera ani checkera nie sú. `config/u2-variable-matrix.json` zachováva menší izolovaný 3‑RSU test.

**Zostávajúci rozsah:** V5 vstup zatiaľ povoľuje 2–49 áut a najviac 50 rádiových účastníkov celkom; editorový world najviac 20 RSU. V novom jednom runneri sú otestované 1/2/3 RSU a 3/5/12/24 áut. Spoločný UT je pevný; satelitná cesta má stále presne dva orbitálne objekty a manuálnu ISL. Neobmedzený počet uzlov sa netvrdí.
