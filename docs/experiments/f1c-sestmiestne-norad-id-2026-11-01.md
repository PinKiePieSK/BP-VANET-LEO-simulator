# F1c — šesťmiestne NORAD ID v aktívnom U9

**Dátum:** 1. 11. 2026. Uzavretá tretia brána [plánu fyzikálnej vernosti](../plan-fyzikalna-vernost-2026-11-01.md).

## Dôvod adaptéra

SNS-3 3.38 v `satellite-sgp4io.cc` číta päť znakov TLE katalógového poľa ako desiatkové číslo (`%5ld`), takže štandardný Alpha-5 zápis šesťmiestneho verejného ID nie je v tomto runtime použiteľný. `tools/u9_tle_catalog.py` ponecháva každé verejné ID 1–99 999 bez zmeny. Pre ID 100 000–999 999 prideľuje deterministický voľný päťmiestny interný alias bez kolízie s už vybranými ID. OMM sa s týmto číslom znovu inicializuje do TLE; orbitálna geometria zostáva kontrolovaná proti pôvodnému OMM s toleranciou 2 m. Verejné ID zostáva v topológii, `CATALOG` hlavičke TLE, manifeste `native_tle_aliases` a replay `catalog_id`. Interné ID je iba vstupom SNS-3.

Rozsah a unikátnosť kontrolujú U3 preflight, generátor aj nezávislé natívne verifikátory. Výber aktívneho podgrafu už šesťmiestne ID nevynecháva. Overovač z pôvodného archívu rekonštruuje celé TLE aj mapu aliasov. Staršie manifesty a zdrojové hashe zostávajú overiteľné cez presné nezmenené snímky v `tools/legacy/`.

## Pozitívny beh

`~/Desktop/BP-Simulator-Workspace/runtime/config/u9-scenarios/f1c-six-digit-starlink-20261101.json` používa hashovaný CelesTrak archív `20261101T113716Z-celestrak`, UTC 2026-11-01T11:37:16Z a verejnú topológiu **[48577, 46063, 100050]**. Satelit 100050 je v druhom ramene handoveru, jeho elevácia 42,9–43,6° a najmenší odstup ISL od Zeme 403 km v predletovej kontrole. V natívnom TLE má alias **00001** a manifest uvádza `{"100050": 1}`. Celý šesťsekundový beh s piatimi autami, tromi RSU, priamym terminálom a satelitným prenosom medzi RSU skončil `PASS`; 13 z 13 priamych správ dorazilo do brány a späť, dve terminálové handovery boli potvrdené. Samostatné `bp_u9 verify` vrátilo `PASS`. Replay má 183 satelitných záznamov v čase 0–6 s a pre všetky tri satelity zachováva verejné `catalog_id` vrátane 100050.

## Negatívne a regresné kontroly

- Spustenie scenára s duplicitným verejným ID `[48577,100050,100050]` sa zastavilo v preflighte pred vytvorením výsledku: `invalid orbit pool, ISL graph or route indices`.
- V izolovanej kópii natívneho výsledku zmenená mapa `100050 → 46063` vyvolala `public NORAD to native TLE ID map changed`; pôvodný výsledok ostal nedotknutý.
- Jednotkové testy overili deterministické aliasy pri kolízii s existujúcimi ID, duplicity/rozsah a obnovu skutočného šesťmiestneho OMM do TLE. Celá sada: **128 testov OK**.
- Po zmenách prešli opätovne všetky štyri natívne výsledky F1b: `combined_advanced`, `native_generic_dvb`, `combined_full` a `unified`.

Logy negatívnych kontrol a testov sú v `~/Desktop/BP-Simulator-Workspace/physical-f1c-20261101/`; úplný pozitívny beh je v `~/Desktop/BP-Simulator-Workspace/runtime/results/u9_runs/f1c-six-digit-starlink-20261101/`. Prenosný `~/Desktop/BP-Simulator` prešiel overením **11 398 súborov a odkazov**, ZIP má SHA-256 `3ae9b2ae427f0ac3b4bccc3c7b3ab28748aef9f6b95c62a3cde4a697b68a4e8c`; predošlý balík je odložený v `~/Desktop/BP-Simulator-Workspace/package-pre-f1c-20261101/`. Editor na porte 8765 po reštarte vracia HTTP 200.

## Hranica tvrdenia

F1c rieši verejnú identitu v **aktívnom U9** a technickú kompatibilitu so SNS-3. Staršie samostatné nástroje V3/U3 používajú svoje historické päťmiestne rozhranie. Táto zmena nemení prevádzkovú dostupnosť Starlinku, aktívne lúče ani operátorské smerovanie. Ďalšia brána F2 rieši časovo sa meniaci výber fyzikálne možných satelitov pre jednotlivé terminály.
