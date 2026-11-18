# Lokálny OSM výrez Slovenska — 2. 11. 2026

## Vstup a pravidlo výberu

Geofabrik `slovakia-261031.osm.pbf`, dátový čas `2026-10-31T21:23:06Z`, 347 439 321 B, SHA-256 `4af3affa32fdc294ade673b409a0dc7f5c6c908875776ff06530d7bd923a9185`. Stiahnutý súbor, oficiálny MD5 a polygón Slovenska sú mimo čistého balíka v `Desktop/BP-Simulator-Workspace/imports/osm/`. Oficiálny MD5 prešiel. Zdroj: https://download.geofabrik.de/europe/slovakia.html. Atribúcia: OpenStreetMap contributors, ODbL.

Import reálnej mapy používa tento PBF, iba ak je **celý požadovaný bbox** v polygóne Geofabriku bez dotyku hranice. `osmium extract --strategy complete_ways` vytvorí lokálny XML výrez a uloží ho do externej cache. PBF sa pri prvom použití procesu overí voči pripnutému SHA-256. Všetky ostatné výrezy prechádzajú pôvodným OSM API a jeho cache/rate-limit vetvou. Pri chýbajúcom lokálnom PBF ostáva pôvodné správanie. Setup prenosného balíka stiahne pripnutý PBF do workspace a doinštaluje `osmium-tool`.

Zdrojový záznam ciest i budov nesie `provider=geofabrik-slovakia-pbf`; cestný zdroj nesie tiež `dataset_sha256`. Historické scenáre s `provider=openstreetmap-api-v0.6` sa stále validujú. Podkladové mapové dlaždice OpenFreeMap, terénne HGT dáta a orbitálne vstupy ostávajú samostatné sieťové zdroje; táto zmena lokalizuje OSM import ciest a pôdorysov budov.

## Overenie

- `osmium fileinfo -e`: platný PBF, 37 134 038 uzlov, 4 505 179 ways.
- Skúšobný XML výrez Bratislavy prešiel existujúcim parserom: 1 410 cestných úsekov, 2 354 pôdorysov.
- Test výberu územia: Bratislava áno, Viedeň a Kittsee nie; konkávna hranica v jednotkovom teste správne odmieta výrez prechádzajúci mimo územia.
- Test lokálneho zdroja a fallbacku: štyri jednotkové testy `test_u9_slovakia_local_pbf.py` + `test_u9_osm_rate_cache.py` prešli. Pri lokálnom zdroji sa sieťový downloader nevolal; pri oblasti mimo územia sa volal pôvodný downloader.
- HTTP `POST /api/u9/editor/roads` nad Bratislavou, 2 km: 200, 1 696 cestných úsekov a 3 557 budov, obe vrstvy s lokálnym providerom; zopakovanie na bežiacom serveri približne 5 s.
- HTTP výrez 4 km: 200, 6 115 cestných úsekov, 11 855 budov, lokálny provider, 53,4 s prvé načítanie. OSM API sa na tento výrez nepoužilo.
- Prenosný priečinok: 11 457 zdrojových súborov a odkazov overených manifestom. ZIP `unzip -tq`: bez chyby; zmenené súbory sa v ZIP a priečinku zhodujú.

Import budov naďalej vynecháva building multipolygon relations, ktoré pôvodný parser nespracováva; nejde o novú regresiu. Hraničné výrezy používajú OSM API, aby sa nestratili objekty za okrajom slovenského PBF.
