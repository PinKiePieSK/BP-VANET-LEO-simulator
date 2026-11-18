# Obnova na natívnom Ubuntu — 25. 10. 2026

## Konečný stav: zjednotené na ns-3.38

Na výslovnú požiadavku používateľa bol všetok aktívny runtime zjednotený na `vendor/ns-3.38-ocb-eval`. **Checkout `vendor/ns-3.48` bol po úspešných testoch odstránený**, vrátane knižníc, build cache a jeho vnorených Git metadát. V build programoch nezostala závislosť na `ns3.48` ani RPATH do odstráneného adresára. Systémový ns-3.41 sa už na zostavovanie pilotu nepoužíva.

Spoločné pôvodné anténne/kanálové dáta sú presunuté z vyradeného checkoutu do samostatného `data/additional-input` (adresár, nie odkaz na 3.48). Historické výsledky, text práce, pôvodný prenosový archív a historické čísla verzií zostali zachované.

### Zmeny

- Presmerované všetky aktívne runnery, linker názvy, piny, editor, obnova a preflight na ns-3.38/SNS-3 3.38; nové staršie sondy zapisujú do výsledkových rodín s príponou `_ns338`.
- Pôvodný vizuálny `vanet-sns3.cc` portovaný z API `SatTopology`/`LoadScenario` na `SatHelper`, `SatUserHelper` a konfiguráciu konštelácie 3.38. Geometrické vstupy, UTC a presunutá anténna mapa zostali explicitné.
- Build skript doplnený o WAVE/Wi-Fi, CSMA, buildings a vizuálny pilot. C++17 a numerický MHz kompatibilný typ zachovávajú staršie zdrojové adaptéry.
- Checkery vyhodnocujú chýbajúci alebo validný prázdny PCAP ako nulový príjem; neakceptujú poškodený súbor či rámec.
- Pôvodné projektové zdroje a SHA-256 sú v `archive/pre-ns338-migration-20261025`. Historický replay môže overiť presné archivované zdrojové bajty; surové dáta nikdy nesmú použiť takýto fallback. Pridané negatívne testy.

### Nové overené behy

| Beh | Výsledok |
| --- | --- |
| `results/native_pilot338_20261025` | SUMO, ground/nominal/outage a kontrola účinku výpadku PASS; graf vygenerovaný. |
| `results/visual_runs/native338final20261025` | Celý 60 s pôvodný vizuálny pilot, raw paketový audit, geografický audit a replay COMPLETE. V2V 50/50, V2I 8/25, satelitný tok 8/25, osem kontrolovaných modelových ISL priechodov. Nejde o prevádzkovú PDR služby. |
| `results/sns3_integrated/runs/20261025T135355Z-34490` | Nový plný shellový SNS-3 pilot a jeho checker úspešné. |
| `results/native_roundtrip338_final_20261025` | Roundtrip PASS: odpovede RSU 2/1/1 pre positive/no_isl/no_confirm, overené celé IP/UDP bajty a trasy. |
| `results/native_two_leo_icb1_20261025` | SUMO/CAM/ICB1 cez dve LEO: 6 TX, 18 pozemných príjmov, brána 6/0/0; checker PASS. |
| `results/native_cam_radio338_final_20261025`, `results/native_ocb338_20261025` | Oba nové rádiové piloty: 6 TX, 18 RX, záporná kontrola 0 RX. |
| `results/editable_leo_runs/20261025T135120Z16b1b79e` | Nový beh spustený tlačidlom v editore: 6 CAM, 18 RX, brána 6, blokovaná 0; paketový prehrávač a geometria overené v prehliadači. |
| `results/v2v_urban_radio_ns338` | LOS 4/4, vynútené NLOS a budova 0/4; analytická kontrola útlmu PASS. |

Všetky presmerované shellové sondy boli zostavené a vykonané: káblový GN/BTP/CAM, Wi-Fi CAM, integrated CAM backhaul, moving CAM, moving V2V, moving Iridium gate, OSM CAM RSU, párový OSM backhaul, geometrický LEO proxy. Navyše Certus E2E podlimitná/záťažová/integritná/geometrická kontrola prešla. C++ syntax audit všetkých 31 projektových C++ zdrojov proti 3.38 prešiel bez chýb.

Automatická sada po zmenách: **39 testov OK**. Po odstránení 3.48 znovu spustené preflight, Python testy a LEO/OSM replay kontroly. Podrobné logy, zoznam Python balíkov, pôvodné piny vyradeného checkoutu a UI snímka sú v `results/native_validation_20261025`.

Počas migrácie boli zachytené a opravené: chýbajúci WAVE build v pôvodnom obnovovacom skripte; rozdiel SNS-3 API; nesprávna predvolená anténna mapa pri prvom porte; C++20 nekompatibilita starých ns-3.38 hlavičiek; predpoklad neexistujúceho prázdneho PCAP. Tieto zlyhania neboli použité ako úspešné vedecké experimenty. Vývojový adresár `native33820261025` uchováva značku prvého zlyhania a API ho odmieta HTTP 409; finálny beh `native338final20261025` vznikol pod novým ID a jeho replay aj editorové/OSM API vrátili HTTP 200. Runner odmieta opätovné použitie existujúceho ID.

Táto migrácia nemení rozsah modelu: generický DVB, hypotetické antény/GW a dve existujúce UT nie sú implementáciou služby operátora ani handoverom jedného rádia.

---

Nasleduje záznam priebežnej obnovy pred doinštalovaním závislostí; jeho otvorené body sú vyriešené vyššie.

## Umiestnenie a integrita

Pracovný projekt: `/home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca`.
Pôvodné štyri archívne časti ostávajú v nadradenom `BP-prenos-2026-10-25`.
Rozbalené do samostatného cieľa, aby sa vnorená história nezmiešala s pôvodným nadradeným Git repozitárom.

- `sha256sum -c SHA256SUMS`: všetky 4 časti OK.
- Úplné zstd/tar rozbalenie: návratový kód 0; približne 11 GB.
- `python3 scripts/check_migration.py`: PASS, piny, patch, dátové odkazy, orbitálne a legacy archívy sú v poriadku.
- Zachované existujúce necommitnuté zmeny README, scenárov operátorov, scenario_server a prenosové dokumenty.

## Prostredie

Ubuntu 24.04.5 LTS, Python 3.12.3, RAM 39 GiB. OpenSSL runtime `3.0.13-0ubuntu3.16` zodpovedá pinu.
Stará prenesená `.venv` bola vyčistená a obnovená. Systémové ensurepip chýba, preto bol pip bootstrapovaný z PyPI wheelu s overeným SHA-256 podľa PyPI metadata do novej `.venv` (pip 26.2.2).
`requirements-orbits.txt` nainštalované s `--require-hashes`, následne `requirements-orbit-validation.txt`; `pip check` bez chýb.

## Vykonané kontroly

- `.venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: 36 testov, OK. Discovery nevolá samostatné skripty s funkciou main.
- `tools/check_bratislava_osm_pilot.py`: PASS; 510 ways, 4 vozidlá, 151 geo FCD bodov, bez kolízií/teleportov v zachovanom behu.
- Čítacie volania `audit`/`verify` troch checkerov bez ich zapisujúcich CLI: `two_leo_isl_icb1` PASS (GW 6/0/0); `two_leo_icb1_rsu_policy_verified_v2` PASS (GW 4/2/2); `two_leo_dual_ut_roundtrip_verified_v2` PASS (odpovede RSU 2/1/1). Kontrolované surové stopy, bajty, checksumy, manifesty a geometria, nie iba existujúci verification.json.
- `tools/test_editable_v2_cam_radio.py`: PASS; 6 TX, 18 RX, záporná kontrola 0 RX, disektor a poškodené rámce. Pôvodne zlyhal na zastaranej očakávanej podreťazcovej hláške `UTC origin`; test upravený na aktuálne `verified UTC pilot origins`. Produkčný validator nezmenený.
- `tools/test_osm_leo_hop_replay.py`: PASS, API 200 a odmietnutie poškodenia 409.
- `tools/check_osm_paired_viewer.py`: PASS, dva varianty po 65 fáz, API a odmietnutie poškodenia.
- Skutočný štart `tools/scenario_server.py --port 8765`: HTTP 200 pre `/`, `/draft-editor.html`, `/certus-packet.html`, `/i2v-packet.html`, `/api/runs`. Smoke server po skúške ukončený. Grafické ovládanie v prehliadači zatiaľ nebolo preskúšané.

## Pôvodné otvorené podmienky pred dokončením (historický záznam)

**Plná spustiteľnosť nových simulácií zatiaľ nepotvrdená.** Chýbajú build nástroje, SUMO a systémové vývojové knižnice. `sudo -n true` vyžaduje heslo; používateľ dostal príkaz z migračného návodu na ich inštaláciu. Heslo sa nemá posielať do chatu.

Po inštalácii pokračovať:

1. `bash scripts/obnovit-native-ubuntu.sh` (predvolený limit 2 build úlohy); regenerovať Vanetza a ns-3.38/3.48 cache, nepoužiť prenesené binárky ako dôkaz.
2. Nový izolovaný roundtrip do nového adresára: `.venv/bin/python tools/run_two_leo_dual_ut_roundtrip.py vendor/ns-3.38-ocb-eval results/native_roundtrip_20261025` a príslušný checker.
3. SUMO/editorové samostatné testy a jeden nový spoločný CAM/ICB1/LEO beh do nového adresára, potom jeho checker a UI kontrola.
4. Doplniť tento denník o skutočné build/smoke výsledky.

Kontext: načítané AGENTS, README, migračný návod, stav a ďalší postup, zadanie, hĺbková analýza, pracovný text, návod a matica vernosti/kontrakt jedného UT. Plán z druhého chatu je stále prázdny. Zatiaľ žiadne tvrdenie o komerčnej sieti ani funkčnom handovere jedného UT; historické úspechy predstavujú generický DVB a dve samostatné UT.
