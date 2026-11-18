# U2 — viac aktívnych RSU, deduplikácia a párovaný backhaul

**Ohraničená matica prijatá:** 26. 10. 2026. **Nástupnícke rozšírenie:** [variabilný počet áut/RSU](u2-variable-rsu-2026-10-26.md). **Runtime:** projektový ns-3.38/SNS-3 3.38. **Úroveň tvrdenia:** `model_only`; satelitná cesta je generický výskumný DVB model, nie predikcia služby operátora.

## Prijaté vstupy a raw dôkazy

- Scenáre 1/2 RSU × 3/12/24 áut: `config/u2-ground-one-rsu.json`, `config/u2-ground-two-rsu.json`; matica a fronty: `config/u2-integrated-matrix.json`. Všetky používajú syntetické SUMO cesty, 30 polohových vzoriek v okne 10–12,9 s, LOS a DCC vypnuté. V dvoch RSU sú aktívne `rsu0` a `rsu1`, obe viazané na pevný `ut0`.
- Izolované V5 pozemné baselines: `results/u2_ground_one_20261026/` (manifest SHA-256 `f9b23041f87af91e1bb2fdaebaa546a3f50e014bd494e55264f5c18d9f0d9dd3`) a `results/u2_ground_two_20261026/` (`ab6d3d0cc1ddca8dfc524202ba7b6d8e1f4b1a33365c9d53ad1e06dd71a80da2`); oba prešli `tools/check_v5_ground.py`.
- Prijatý integrovaný beh: `results/u2_integrated_20261026final/`, manifest SHA-256 `c31ba7b29c7fbb169f9bb5721a2b00ad45fbf7fd00705d6e15fb7d41694d5e0a`. Má šesť prípadov a **23 vetiev**: lokálny, pozemný a satelitný režim v každom prípade, plus päť poruchových vetiev pri dvoch RSU a 24 autách. `tools/check_u2_integrated.py` nad kompletným raw výsledkom **PASS**. Šesť mutácií reálnych raw stôp checker odmietol: rozhodnutie RSU, parent reportu, príjemcu návratu, bajt ISL, príčinu dropu v doprednej a návratovej fronte.
- Regresia `.venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: **91 testov, OK**; `py_compile` nových Python súborov a `git diff --check`: **PASS**.

```bash
.venv/bin/python tools/check_v5_ground.py results/u2_ground_one_20261026
.venv/bin/python tools/check_v5_ground.py results/u2_ground_two_20261026
.venv/bin/python tools/check_u2_integrated.py results/u2_integrated_20261026final
.venv/bin/python tools/test_u2_integrated_mutation.py results/u2_integrated_20261026final

# Nové výsledky vždy do nových adresárov; runner odmieta prepis.
.venv/bin/python tools/run_v5_ground.py --config config/u2-ground-one-rsu.json --output results/u2_ground_one_NEW_ID
.venv/bin/python tools/run_v5_ground.py --config config/u2-ground-two-rsu.json --output results/u2_ground_two_NEW_ID
# Do novej matice pripni obe nové baseline cesty, ich konfigurácie a hashe.
.venv/bin/python tools/run_u2_integrated.py --config config/u2-integrated-matrix_NEW_ID.json --output results/u2_integrated_NEW_ID
.venv/bin/python tools/check_u2_integrated.py results/u2_integrated_NEW_ID
```

## Výsledok

Každá riadna trojica `local/ground/satellite` zdieľa identickú množinu originálnych CAM ID. Pri 1 RSU sa každý dekódovaný CAM stane jedným reportom; pri 2 RSU sa počet fyzických prijatí zdvojnásobí, ale druhý príjem toho istého CAM je zapísaný ako duplicita, nie nový report. Politika `first_actual_decode` vybrala v dvoch RSU pri 3 autách `rsu1` 25× a `rsu0` 10×, pri 12 autách 61×/59× a pri 24 autách 61×/195×.

| Prípad | CAM TX | RSU prijímacie páry | Duplicity | Reporty | Lokálne / pozemné odpovede v aute | Satelitné prijatie / odpoveď v aute |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 RSU, 3 autá | 35 | 35 | 0 | 35 | 35 / 35 | 35 / 35 |
| 1 RSU, 12 áut | 120 | 120 | 0 | 120 | 120 / 120 | 113 / 113 |
| 1 RSU, 24 áut | 256 | 256 | 0 | 256 | 256 / 256 | 249 / 249 |
| 2 RSU, 3 autá | 35 | 70 | 35 | 35 | 35 / 35 | 35 / 35 |
| 2 RSU, 12 áut | 120 | 240 | 120 | 120 | 120 / 120 | 113 / 113 |
| 2 RSU, 24 áut | 256 | 512 | 256 | 256 | 256 / 256 | 249 / 249 |

Čísla `113/120` a `249/256` sú výsledkom tohto pripnutého generického DVB behu, nie mierou reálnej satelitnej služby. V každom prípade sa reporty odvodzujú od *jedinečných dekódovaných* CAM; checker zároveň ponechá menovateľ všetkých vygenerovaných CAM aj RSU prijímacích párov, takže duplicita ani strata nemôže potichu zmenšiť populáciu.

| Dva RSU, 24 áut: kontrola | Vytvorené ICB1 | Dopredná ponuka / drop fronty | Brána prijala | Vytvorené GRA1 / drop návratovej fronty | I2V1 v aute |
| --- | ---: | ---: | ---: | ---: | ---: |
| `blocked` | 256 | 256 / 0 | 0 | 0 / 0 | 0 |
| `no_isl` | 256 | 256 / 0 | 0 | 0 / 0 | 0 |
| `no_return_route` | 256 | 256 / 0 | 249 | 0 / 0 | 0 |
| `queue_overload` | 256 | 7 / 249 | 7 | 7 / 0 | 7 |
| `reverse_queue_overload` | 256 | 256 / 0 | 249 | 249 / 242 | 7 |

Každá z týchto kontrol si ponecháva 256 CAM TX, 512 RSU prijímacích párov, 256 deduplikovaných reportov a rovnakú množinu originálnych CAM ID. `no_isl` blokuje doprednú ISL pred bránou; `no_return_route` prijme 249 reportov, ale explicitne nevytvorí odpovede. Obe fronty sú aplikáciové FIFO: nominálne 512 miest/1 ms, kontrolované preťaženie 2 miesta/500 ms.

## Jedna overiteľná správa

V `two_cars03/satellite` vyslalo `car0` CAM `1b33dad277301ce5` v 10 001 000 µs. Oba RSU ho dekódovali v 10 001 222 µs; `selection.csv` zvolil `rsu1` ako prvý skutočný callback a `rsu0` označil za duplicitu. `rsu1` vytvoril 98 B ICB1 `8c1f8c442ff8e0a7`, ktorý je v `identity.csv` previazaný s pôvodným CAM. Cez vlastný RSU→UT spoj a generické DVB dorazil report bráne v 10 130 740 µs. GRA1 sa vrátil na vybraný `rsu1`; ten vyslal I2V1 a pôvodné `car0` ho prijalo v 10 166 541 µs. Checker overuje bajty reportu a odpovede, rodičovské ID, časové poradie, OCB/LAN PCAP a ISL IPv4/UDP payload.

## Metóda a hranice

Checker opätovne odvodí CAM/ICB1/GRA1/I2V1 identitu a bajty, nezávisle skontroluje V5 FCD/CAM/CBR/OCB, výber z každého RSU callbacku, FIFO obsadenosť a servisné časy, smerové IP/ISL bajty, menovatele a príčiny dropov. FCD časové kroky pre 1 a 2 RSU sú zhodné; odlišný RSU mení výber, nie vozidlá. Mutačný test volá sémantický audit priamo nad zmenenými raw súbormi, takže zlyhanie nespôsobí iba neplatný manifestový hash.

Obe RSU zatiaľ používajú **jeden pevný UT**; ich 100 Mbps/100 µs káblové linky a pozemný bypass sú referenčné nastavenia. Výber podľa prvého príjmu nie je optimalizovaný handover. `no_return_route` je riadená poruchová brána aplikácie a nevytvorená spätná SNS-3 trasa, nie dôkaz zlyhania reálneho routovacieho protokolu. Fronty nemodelujú proprietárny DVB scheduler. Dynamický výber LEO/beam/attach/route a handover terminálu zostáva U3, parametrická RF/kapacita U4. [Kontrakt U2](../decisions/u2-multi-rsu-backhaul-contract.md) uvádza presné vrstvy a názvoslovie.
