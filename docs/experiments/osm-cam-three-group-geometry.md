# OSM CAM scenár: porovnateľný geometrický vstup troch GP skupín

**Stav 22. 10. 2026 UTC:** izolovaný a overený geometrický predvýpočet pre budúci spoločný paketový runner. [Generátor](../../tools/osm_cam_three_group_geometry.py), [kontrola](../../tools/check_osm_cam_three_group_geometry.py), [CSV](../../data/derived/osm-cam-geometry/bratislava-20261022T124500Z.csv) a [metadáta](../../data/derived/osm-cam-geometry/bratislava-20261022T124500Z.metadata.json). **Nejde o ďalší sieťový beh ani o pokrytie operátora.**

## Hypotéza, vstup a čas

Hypotéza: pre *tie isté* WGS84 polohy a UTC časy OSM→CAM scenára možno deterministicky porovnať geometrických kandidátov Starlink, Iridium NEXT a Globalstar bez zámeny s kvalitou alebo existenciou paketového spojenia. Zápornou kontrolou je objekt so zápornou eleváciou, ktorý nesmie prejsť maskou 10°. Kontrolou integrity je zmenený bajt waypoint CSV; generátor ho musí odmietnuť pred orbitálnym výpočtom.

Vstup [OSM→CAM→RSU pilotu](osm-ba-cam-rsu.md) je generované, Gitom ignorované `build/osm-ba-cam-waypoints.csv`, SHA-256 `1b89eaf70b81f5f8935307969169c498af7b5e6f3728792d4328fca0094e12e1`, s `build/osm-ba-cam-waypoints.metadata.json`, SHA-256 `6827841074dcc42180dcf6660495f709c76ae245eda2001c0cc48a6d08edfe19`. Oba súbory sa reprodukujú z verzovaného FCD a skriptu prvým príkazom nižšie. CSV obsahuje päť bodov auta `car0` v čase **12:45:05–12:45:09 UTC**, po 1 s, z archívneho 60 s SUMO behu nad ohraničeným OSM výrezom Bratislavy. RSU je **hypoteticky** umiestnená asi 12 m napravo od smeru vozidla v bode t=7 s; jej približná WGS84 poloha po zaokrúhlení waypointov je **48,1482681° N, 17,1085885° E, 0 m**. Výška 0 m je predpoklad, nie topografické meranie. Dopyt `randomTrips` so semenom 314159 nie je meraná premávka.

GP/OMM vstup je archivovaná snímka `data/orbits/20261022T124815Z-retlector`, manifest SHA-256 `d28ad3618304780d3cd118e83e8e8a2e88c14d015fa022c3082ba7b2f624d826`. Jej poskytovateľ `retlector` je tretia strana so zrkadlom [CelesTrak GP](https://celestrak.org/NORAD/elements/); manifest uvádza získanie **12:49:43.719531 UTC**, teda **po** začiatku scenára. Toto je retrospektívna geometrická rekonštrukcia. Zdroj EOP Astropy má SHA-256 `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`. Generátor overuje hashe waypointov, metadát, manifestu, komprimovaných aj dekomprimovaných OMM skupín a zhodu EOP s [referenčnou RSU geometriou](multi-constellation-geometry.md). Sťahovanie nového GP sa nespúšťa.

## Metóda a jednotky

Rovnaký súbor vekovo prijateľných OMM elementov ako v referencii: epocha nesmie byť po začiatku a vek nesmie prekročiť **48 h až do t=360 s**. Tento pevný kohortový filter udržuje rovnaké objekty naprieč výpočtami; nie je pravidlom operátora. Každá skupina sa v piatich UTC časoch propaguje cez SGP4/WGS72 → TEME → ITRS s pripnutým EOP. Polohy auta a RSU sa posudzujú vo WGS84. V každej vzorke sú kandidátmi objekty s eleváciou **≥10°** a nad geometrickým horizontom. Maska 10° je **experimentálna**. Vyberie sa najvyššia elevácia, pri zhode nižšie katalógové ID. Neinterpoluje sa medzi sekundami a netvrdí sa pretrvávajúca viditeľnosť.

CSV má 30 riadkov: päť časov × dva body (`car0`, `rsu`) × tri skupiny. `time_us` sú mikrosekundy od UTC kotvy 12:45:00, `elapsed_s` sekundy, zemepisné súradnice stupne, výška metre, elevácia/azimut stupne, `selected_range_km` kilometre a `selected_one_way_vacuum_ms = selected_range_km / 299792,458 km/s × 1000` iba jednosmerná doba vo vákuu. Polia pre vybraný objekt sú prázdne, ak nad maskou nie je kandidát; záporná elevácia nikdy nedáva použiteľné `r/c` vybraného spojenia.

Pre skupinu Globalstar sa osobitne počíta prienik **toho istého** objektu nad 10° z auta či RSU a z `nemea_city_proxy` (**37,8167° N, 22,6667° E, predpoklad 0 m**). Výber spoločného objektu maximalizuje slabšiu z dvoch elevácií; pri zhode nižšie ID. V stĺpci `shared_two_legs_vacuum_ms_only` je súčet dvoch geometrických `r/c`. [Globalstar opisuje transparentnú architektúru so zemskými bránami](https://www.globalstar.com/en-us/about/our-technology), ale poloha mesta Nemea je len citlivostný proxy z [predchádzajúcej dvojkoncovej sondy](globalstar-two-endpoint-geometry.md). Nie je to potvrdená poloha antény, aktivita gateway, pridelenie terminálu ani paketové oneskorenie. **Vybraný lokálne najvyšší objekt a najlepší spoločný objekt môžu byť odlišné.**

## Reprodukcia a zistenia

Z koreňa projektu bez `sudo`:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python tools/prepare_osm_ba_cam_waypoints.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python tools/osm_cam_three_group_geometry.py \
  --waypoints build/osm-ba-cam-waypoints.csv \
  --waypoints-metadata build/osm-ba-cam-waypoints.metadata.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --reference-metadata data/derived/multi-constellation/bratislava-20261022T124500Z.metadata.json \
  --output data/derived/osm-cam-geometry/bratislava-20261022T124500Z.csv
OPENBLAS_NUM_THREADS=1 .venv/bin/python tools/check_osm_cam_three_group_geometry.py
```

CSV SHA-256: `f7c2a1280c4f1a005971cc9ab5ab2c20e053422b4083dca3c0a84fd09edc59c3`. Kontrola prešla (`PASS`, 30 riadkov, 10 riadkov s kladným spoločným prienikom Globalstar) a dvakrát v pamäti vygenerovala **bitovo totožný** CSV. Explicitne odmietla zmenený waypoint bajt; testy `-1°`, `9,999999°`, `10°` kontrolujú horizont a hranicu masky. Opakované samostatné spustenie dalo rovnaký SHA; s `OPENBLAS_NUM_THREADS=1` trvalo približne **3,7 s** a maximum RSS bolo **183 584 KiB** v tejto VM.

| t=5 s, pozorovateľ | Skupina | Kandidáti ≥10° | Vybraný objekt | Elevácia | Vzdialenosť | Jednosmerné `r/c` |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| car0 | Starlink | 206 | 64434 | 82,505311° | 486,495538 km | 1,622774440 ms |
| car0 | Iridium NEXT | 1 | 43253 | 28,497908° | 1418,598938 km | 4,731936711 ms |
| car0 | Globalstar | 2 | 37190 | 26,499097° | 2463,058231 km | 8,215877904 ms |
| RSU | Globalstar | 2 | 37190 | 26,498534° | 2463,084260 km | 8,215964727 ms |

V tejto vzorke je pri Globalstar **2** spoločných geometrických kandidátov s mestským proxy; ako dvojkoncovo najlepší sa vyberie **37741**, nie lokálne najvyšší **37190**. Súčet dvoch vákuových dôb pre auto a proxy je **17,931187387 ms**. To nie je predikcia RTT ani merané oneskorenie RM200M. Počet Starlink kandidátov sa v okne zmení z 206 na 207, Iridium ostáva 1 a Globalstar 2; tento päťsekundový výrez neumožňuje záver o dlhodobej dostupnosti.

## Hranica pre budúci paketový runner

CSV je časovo zladený **vstup** a kontrola rovnakých polôh pre tri skupiny. Samotné GP katalógové objekty nemusia byť aktívne, obsluhovať danú lokalitu alebo patriť overenej aktuálnej prevádzkovej množine. Auto nemá modelovaný kompatibilný satelitný terminál; RSU nemá modelovaný terminál, anténu ani tienenie. Chýbajú RF/MAC, atmosféra, terén a mestské prekážky, lúče, frekvencie, link budget, handover, ISL, gateway priradenie, signalizácia a protokoly operátora. `r/c` nie je koncové sieťové oneskorenie. Porovnateľnosť budúceho **paketového** experimentu vznikne až vtedy, keď všetky varianty použijú totožný OSM pohyb, CAM bajty, pozemnú sieť, záťaž a časy, s výslovne zvoleným a odôvodneným modelom servisného úseku.
