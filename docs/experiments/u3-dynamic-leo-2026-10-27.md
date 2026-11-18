# U3 — dynamická generická LEO cesta a variabilný satelitný pool

**Dátum:** 27. 10. 2026. **Aktívny runtime:** výlučne ns-3.38/SNS-3 3.38 v `vendor/ns-3.38-ocb-eval`. **Rozsah tvrdenia:** natívne pakety v generickom DVB modeli s diagnostickým 17 dBi beamom, proxy bránou a archivovanými OMM prvkami skupiny Iridium NEXT. Nejde o emuláciu dostupnosti ani výkonu komerčnej služby.

## Jeden tok a nastaviteľná topológia

Nástupnícky `src/u3-dynamic-leo-backhaul.cc` zachováva U2 viacvysielačový CAM/DCC/OCB, výber prvého skutočne dekódujúceho RSU, ICB1, jediný spoločný UT, vzdialenú aplikáciu a GRA1/I2V1. Počet satelitov, ich katalogové ID, poradie, ISL hrany, počiatočný obslužný satelit, satelit brány a cieľ prepnutia určuje `config/u3-dynamic-matrix.json` cez `tools/run_u3_dynamic.py`. Pre súradnice UT sa používa skutočná poloha RSU z overeného V5 waypointu; brána je výslovne hypotetický bod. `tools/u3_model_inputs.py` rekonštruuje pinované OMM do vstupov SNS-3 a archivuje presné TLE/ISL/site/beam súbory vo výsledku. Katalogové ID nie je index satelitu: druhá epocha overuje počiatočný satelit aj GW s indexom 1 a prepnutie na index 0.

`tools/u3_preflight.py` nezávisle od paketového modelu propaguje archívny orbitálny snapshot pomocou SGP4/Astropy, kontroluje vek a hash zdroja, nadmorskú viditeľnosť UT a GW pri každej polsekundovej vzorke okna 10–13 s, priechodnosť každej deklarovanej ISL cez Zem a spojitosť celého grafu. Neplatný, starý alebo nespojený pool skončí ako `unsupported` ešte pred natívnym prípadom. Geometria predstavuje kandidáta, nie potvrdený beam, attach alebo službu.

Pri prepnutí sa jedno UT odpojí zo starého scheduleru/beamu, pripojí k novému, aktualizuje svoje PHY/MAC/LLC, mobility observer, timing advance a trasu. Identita UT IP/MAC zostáva rovnaká. Nové pripojenie potvrdí až reálny malý paket UT→GW a jeho návrat. Reporty prijaté počas `pending/await_probe` sa viditeľne označia `handover_pending`; nevytvorí sa fiktívna úspešná fronta. Dopredné ICB1 a spätné GRA1 prechádzajú skutočnými ISL zariadeniami. Pri `attach_failed` sa UT vráti na starý beam/scheduler a stará cesta pokračuje.

## Prijímací dôkaz

- Overený párovaný V5 základ: `results/u2_ground_one_20261026/cars03` a druhá UTC epocha `results/u3_ground_afternoon_20261027/cars03` (manifest SHA-256 `0c528903ed7bbd16ac07b618c1baa317aa42890049884097c3b19bf8cb8f57fc`). V oboch 3 autá, 1 RSU, 35 vyslaných CAM, 35 vytvorených ICB1. Nástupnícky engine ostáva podľa U2 scenárovej schémy použiteľný pre ďalší počet áut/RSU v jej deklarovaných limitoch; táto U3 matica cielene mení satelitnú topológiu.
- Deväťprípadová matica `config/u3-dynamic-matrix.json` → `results/u3_dynamic_full_20261027final/` (manifest SHA-256 `eea7daf52493641bec879c25dd23f23c7e7a1c44b2360f696f5c0f79e159ad8b`): 1, 2, 3 satelity; dve UTC epochy 22. 10. 2026 o 12:45 a 13:15 UTC; priame, jednostupňové a dvojstupňové ISL spojenie; `no_candidate`, `no_beam`, `no_attach`, `no_route` a `attach_failed`. Nezávislý checker **PASS**.
- Samostatná skúška `config/u3-four-sat-pilot.json` → `results/u3_four_sat_pool_20261027final/` (manifest SHA-256 `9f12040ddcc33ef27541a3ef9a766c6cd5bc20d6c7186ece1c02d0af9975bb67`): štvrtý satelit je orbitálny objekt v prepojenom ISL grafe, ale pri skúšanom UT/GW je pod horizontom. Checker **PASS**. Slúži na overenie rozdielu medzi **počtom objektov** a **počtom aktívne použitých satelitov**. Jeho účelom nie je tvrdiť väčšiu súčasne aktívnu konšteláciu.

Štvrtý objekt 43079 má pri 12:45:10 UTC vypočítanú eleváciu −3,58° pre UT a −10,49° pre GW; ISL 0–3 má v celom vzorkovanom okne minimálnu svetlú výšku 650,56 km. Natívny log ukazuje `SATELLITE_COUNT=4`, `GW=0 UT=0` na satelite 3 a 24/24 doručených reportov/návratov cez pôvodne kvalifikovanú trasu s prepnutím UT 0→2.

| Prípad | Vzdialené ICB1 / návraty do auta | Zmena cesty |
| --- | ---: | --- |
| 1 satelit, priamy | 35 / 35 | Bez ISL. |
| 2 satelity | 35 / 35 | UT 0 → ISL → GW 1; každý smer po jednej hrane. |
| 3 satelity, prepnutie na poludnie | 24 / 24; 11 explicitných pending dropov | Pred prepnutím 0→1, potom 2→0→1; späť opačne. |
| 3 satelity, prepnutie popoludní | 24 / 24; 11 pending dropov | Počiatočný UT/GW 1, potom UT 0→ISL→GW 1. |
| Štyri zamietnutia prechodu | každé 35 / 35 | Vyžiadaný gate je v raw stope 0; pôvodná cesta zostane aktívna. |
| Neúspešný attach s rollbackom | 24 / 24; 11 pending dropov | Probe nemá odpoveď, UT sa vráti a ďalšie pakety idú starou cestou. |

`tools/check_u3_dynamic.py` znovu vypočíta geometriu zo zdroja, overí vstupy TLE/ISL/site/diagnostický beam, OCB a LAN PCAP, id/parent väzbu CAM→ICB1→GRA1→I2V1, presné aplikačné bajty, checksumy ISL IPv4/UDP, poradie hrán v oboch smeroch, časy hopov, stav jediného UT, dôvody strát a všetky menovatele. `tools/test_u3_dynamic_mutation.py` mení parent ID, výber RSU, návratové bajty, ISL hranu, pending dôvod, kapacitu fronty a neplatné orbitálne/trasové vstupy; zmeny sú odmietnuté. U2 pôvodná 26-vetvová matica bola znova skontrolovaná pôvodným checkerom.

Strojové kontrolné súhrny sú v `results/u3_acceptance_20261027/full-check.json`, `four-check.json`, `mutations.json` a `u2-regression.json`. **Šesť sémantických raw mutácií a päť neplatných orbitálnych/trasových vstupov bolo odmietnutých; širšia Python regresia 91/91 OK.**

**Poznámka k nájdenému okraju:** prvá sondáž štvrtého úplne izolovaného orbitálneho objektu skončila internou chybou SNS-3 pri neplatnom beam ID ešte pred simuláciou. Surový neúspešný pokus zostal v `results/u3_four_sat_pool_20261027/`. Preflight teraz taký graf odmieta ako `unsupported`; vhodne prepojený štvrtý objekt je skúšaný samostatne.

## Reprodukcia

```bash
.venv/bin/python tools/check_v5_ground.py results/u3_ground_afternoon_20261027
.venv/bin/python tools/check_u3_dynamic.py results/u3_dynamic_full_20261027final
.venv/bin/python tools/test_u3_dynamic_mutation.py results/u3_dynamic_full_20261027final
.venv/bin/python tools/check_u3_dynamic.py results/u3_four_sat_pool_20261027final --allow-filter
.venv/bin/python tools/check_u2_variable.py results/u2_variable_full_20261026

# Nový natívny beh: vždy nové ID výsledku, aby sa zachovala raw stopa.
.venv/bin/python tools/run_u3_dynamic.py --config config/u3-dynamic-matrix.json --output results/u3_dynamic_NEW_ID
```

## Presné obmedzenia

- Jeden spoločný, v RSU fixovaný UT a jedna proxy GW; počet UT/GW ani ich mobilita nie sú U3 parametrizované. Automobily a RSU sa riadia U2/V5 limitmi, satelitné ID sú konfigurovateľné v rámci vstupov SNS-3 a pamäte. V tomto dôkaze sú otestované pooly 1–4, nie veľká prevádzková konštelácia ani škálovateľnostný limit. Graf musí byť spojený a jeho deklarované ISL geometricky priechodné v okne paketov.
- Preflight využíva 0,5° modelovú masku, archívne Iridium NEXT OMM, proxy súradnice a diagnostický beam. To nie sú reálne operátorské brány, servisný attach, scheduler ani prevádzková dostupnosť. Kandidát/beam/attach/route poruchy sú **riadené injekcie** na inak geometricky kvalifikovanom páre, nie pozorované zlyhania Iridia.
- Orbitálny snapshot bol archivovaný 22. 10. 2026 o 12:48 UTC; poludňajší beh o 12:45 UTC je preto retrospektívna geometrická rekonštrukcia z prvkov s prípustnou vnútornou epochou, nie prospektívna predpoveď vykonaná v danom okamihu.
- RF, výkon, fronty/kapacity a záťaž intersat linky zostávajú parametrizačným predmetom U4. U3 potvrzuje vykonanú trasu, identitu jedného UT a reálne pakety pri tejto referenčnej konfigurácii; nemeria reálnu PDR, handover duration ani dostupnosť komerčnej siete.
