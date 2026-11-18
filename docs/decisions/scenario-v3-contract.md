# Scenárový kontrakt v3 — brána V1

**Verzia:** `scenario_v3`, schéma 3; výstupná schéma 2. **Účel:** jeden deklaratívny vstup pre budúci univerzálny engine a samostatný preflight pred buildom. V1 vykoná validáciu a geometrický výpočet, **nevytvorí žiadny sieťový paket**. `execution_state=preflight_only_no_packets` a `packet_trace_count=0` sú povinnou súčasťou výstupu. V3 výsledok sa nesmie označiť ako P5/P6 experiment ani ako meranie operátora.

## Vstup a rozsah

Šablóny sú v `config/scenario_v3_reference.json`, `scenario_v3_iridium.json`, `scenario_v3_globalstar.json` a `scenario_v3_starlink.json`. Kľúče sú uzavreté: neznámy alebo chýbajúci kľúč sa odmietne; JSON s duplicitným kľúčom sa odmietne. **Žiadne tiché defaulty.** Všetky časy sú od `clock.utc_origin` v sekundách a každý dátum je explicitne UTC. Číselné jednotky sú v názve kľúča alebo v nasledujúcom kontrakte.

| Časť | Povinné položky a prípustný rozsah V1 |
| --- | --- |
| Identita | `schema_version=3`; `scenario_id` má 3–64 malých písmen, číslic, `_` alebo `-` a začína písmenom. |
| `world` | `kind=editable_v2`; `source={path,sha256}` je súbor vo vnútri projektu; `traffic_evidence=synthetic`. V2 svet musí prejsť pôvodným validátorom a mať **práve jeden** ITS-G5 CAM broadcast zo zvoleného vozidla. Súradnice WGS84/ENU, cesta a doprava sú v pripnutom V2 svete; preflight ich nemení okrem simulácie/času/seed. Syntetická doprava nie je kalibrácia Bratislavy. |
| `clock` | `utc_origin` ISO 8601 UTC; `duration_s` 1–300; `step_s` 0,1–1 a musí deliť trvanie; `warmup_s` 0–duration; `measurement_start_s` ≥ warm-up; `measurement_end_s` > start a ≤ duration. |
| `agents` | `cam_source_id` existujúce vozidlo s ITS-G5; `rsu_id` RSU s ITS-G5 aj IP backhaul; `terminal_host_id=rsu_id`; `local_receiver_ids` je zoznam jedinečných iných ITS-G5 vozidiel. |
| `applications` | CAM: `mode=fixed_interval`, `first_tx_s` v meracom okne, `interval_s` 0,1–10 a celočíselný násobok `step_s`, `count` 1–1000; posledný CAM ≤ koniec okna. Report: `format=ICB1`, `payload_bytes=96`, `deadline_s` 0,001–3600. Návrat: explicitné bool `enabled`, `format=GRA1_I2V1`. Podpora iného flow sa **nepredpokladá**. |
| `profiles`/`ground_radio_profile` | Súbor profilov je SHA-256 pripnutý. Podporované Friis alebo mestský 3GPP V2V LOS/NLOS výskumný model; 5850–5925 MHz, 10 MHz, sadzba zo súborom uvedeného 802.11p rozsahu 3–27 Mb/s, výkon −20–33 dBm, noise figure 0–30 dB, explicitné shadowing bool. Konkrétne hodnoty a ich pôvod sú v profiloch a registri. |
| `backhaul` | `profile_id` zo súboru profilov, `orbit_snapshot={path,manifest_sha256}`, `gateway_site` s WGS84 stupňami/`height_m` −500–9000 a `status=proxy` alebo `null` iba pri Iridiu, `geometry_mask_deg` 0–89, `max_element_age_h` 0,1–168. Archív OMM/GP a surové aj komprimované hashe sú kontrolované. DVB referencia má dva určité NORAD objekty a model ISL; Globalstar/Starlink vyžadujú ten istý geometrický objekt viditeľný UT aj proxy bráne; Iridium kontroluje len UT kandidáta. |
| `experiment` | `seed` a `ns3_run` celé 1–2³¹−1; `repetitions` celé 1–64, ďalší seed/run je základ + poradové číslo − 1 bez pretečenia; `branches` jedinečné `positive`, `blocked`, pre DVB navyše `no_isl`; `metrics` jedinečné podporované ID s povinným menovateľom, úspechom a oneskorením; `metric_contract={path,sha256}` pripína definície P0; `require_geometry_candidate` bool. Sú to **plánované** vetvy/opakovania/metriky, nie vykonané behy. |
| `provenance` | `purpose` neprázdny; `claim_level=model_only` pre DVB alebo `sensitivity` pre operátorské profily; pripnutý `parameter_register`; `calibration_evidence` a `independent_validation_evidence` sú vo V1 `null`. Nepodložené tvrdenie o kalibrácii/validácii sa odmietne. |

`config/scenario_v3_profiles.json` drží pomenované voľby rádia a servisnej topológie. `config/scenario_v3_parameter_register.json` páruje každú aktívnu profilovú hodnotu s presnou jednotkou, stavom dôkazu a súborom zdroja. Preflight kontroluje doslovnú zhodu registra s vybraným profilom a hash dôkazu. Nový profil sa teda nepridáva iba názvom: vyžaduje zodpovedajúcu položku registra a schválený modelový typ v validátore. Obe konfigurácie nesú SHA-256 a všetky závislé projektové súbory, vrátane troch importovaných modulov výpočtu, vstupujú do `input_sha256`.

Metriky v pláne sú `unique_icb1_created` (jedinečné RSU reporty z prijatého CAM; menovateľ), `unique_icb1_before_deadline` (presná identita a hash na vzdialenej aplikácii pred deklarovaným deadline; čitateľ), `e2e_delay_s_delivered` (sekundy iba úspešne doručených), voliteľne `local_cam_receiver_pairs` (oprávnené páry CAM–príjemca), `return_to_rsu_count` (GRA1 s pôvodnou identitou), `geometry_candidate_count` (len geometria) a `drop_reason_counts` (počty podľa fázy, neznáma príčina zostáva `unknown`). Sémantiku a počiatok deadline definuje SHA-pripnutý `config/bp_experiment_contract_v1.json`. V1 iba deklaruje ich budúce meranie; skutočný menovateľ a trace audit musí vykonať V2.

## Reprodukovateľné použitie

Z koreňa obnoveného projektu:

```bash
.venv/bin/python tools/scenario_v3.py validate config/scenario_v3_reference.json results/v3_runs/MOJE_NOVE_ID
.venv/bin/python tools/scenario_v3.py verify results/v3_runs/MOJE_NOVE_ID
```

`validate` odmietne existujúci výstup a zapisuje iba do `results/v3_runs/`. Vytvorí `scenario.normalized.json` s rozriešenými profilmi a hashmi, `world.staged-v2.json` s deklarovaným UTC/krokom/seed, `plan.json` s presným zoznamom plánovaných kombinácií opakovanie × vetva, metrík a geometrických vzoriek a `run-manifest.json` s hashmi všetkých výstupov, vstupov a validátora. `verify` prepočíta výsledok zo zdrojového scenára a odmietne zmenu obsahu, kódu či vstupu. Po zmene validátora sa starý vývojový preflight nevyhlasuje za aktuálny; má svoj pôvodný hash a nové ID sa vytvorí znovu.

Manifest pripína tiež verzie Pythonu, NumPy, Astropy, `astropy-iers-data` a SGP4. Inventár obsahuje hash súborov `requirements-orbits.txt` a `requirements-orbit-validation.txt`, aby sa dal rozdiel prostredia rozpoznať pri opakovaní geometrie.

Prísny prevod existujúceho editora:

```bash
.venv/bin/python tools/scenario_v3.py convert-v2 data/inputs/editable-road-v2/packet-subset.json config/scenario_v3_reference.json config/MOJ_ADAPTOVANY_SCENAR.json
```

Adaptér doplní deklaráciu sveta, čas, seed a roly, potom spustí ten istý preflight. Prijme iba jediný ITS-G5 CAM broadcast; napríklad DENM, viac flow alebo neurčené RSU odmietne. Uložený konfiguračný súbor sám o sebe nie je paketový výsledok.

## Hranica fyzikálneho preflightu

Geometria používa SHA-pripnutý historický CelesTrak OMM/GP archív, SGP4, EOP a vzorky pri prvom/poslednom CAM a konci merania. Kontroluje vek orbitálnych elementov po **celé trvanie scenára**, chybu SGP4, eleváciu a pri referenčnom ISL nepriesečník so Zemou. `require_geometry_candidate=true` odmietne nulový počet kandidátov na vzorkách; `false` umožní explicitnú štúdiu výpadku. Výber najlepšieho kandidáta je iba geometrická diagnostika. Neoveruje medzi vzorkami spojité pokrytie, aktívny lúč, výkon linky, pripojenie terminálu, pridelenie gateway, routovanie ani úroveň komerčnej služby. Brána V3 rozšíri časové a pripájacie modelovanie; V2 pridá prvý skutočný paketový runner.
