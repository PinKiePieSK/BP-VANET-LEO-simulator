# Časové a zemepisné ukotvenie syntetickej cesty SUMO

**Stav:** 22. 10. 2026. **Účel:** pripraviť spoločné WGS84/UTC súradnice auta a hypotetickej RSU+satellitného terminálu pre budúci orbitálny paketový experiment. Tento prevod ešte **nie je** v satelitnom behu použitý a neznamená, že nakreslená cesta existuje v Bratislave.

## Vstupy, algoritmus a jednotky

`tools/sumo_georeference.py` načíta [archivované FCD body](../../data/inputs/bratislava-synthetic-road/waypoints.csv) z úspešného SUMO behu `20261022T144000Zp2pfix`: `time_s` v sekundách od štartu, ID auta, `x_m/y_m` v lokálnych metroch a `speed_mps`. [Konfigurácia editora](../../data/inputs/bratislava-synthetic-road/scenario.json) je uložená vedľa nich. V konkrétnej testovacej konfigurácii je stred RSU `(800 m, 675 m)` hypoteticky položený na **48,1486° N, 17,1077° E, 0 m WGS84** a `t=0` je **2026-10-22 12:45:00 UTC**. Os `+x` smeruje na východ, `+y` na sever. Miesto RSU, orientácia aj čas sú experimentálne voľby, nie údaje o skutočnej ulici alebo termináli.

Pole `constellation` v archivovanej konfigurácii patrí k pôvodnému diagnostickému SNS-3 behu; georeferenčný skript z nej preberá **iba trajektórie**. Nový orbitálny výpočet používa osobitný archivovaný OMM objekt Iridium NEXT 43253 a nesmie si tieto dva satelitné scenáre zamieňať.

Pre každý bod sa vypočíta rozdiel `(x − 800, y − 675)` vo vodorovnej lokálnej ENU rovine. Pomocou elipsoidu WGS84 ([Astropy `EarthLocation`](https://docs.astropy.org/en/stable/api/astropy.coordinates.EarthLocation.html)) sa poloha kotvy prevedie na ECEF metre; ENU rozdiel sa otočí do ECEF a výsledok sa prevedie späť na zemepisnú šírku, dĺžku a výšku. Lokálne `up=0` je výpočtový predpoklad. Preto sa pri vzdialenejšom bode môže vypočítaná elipsoidická výška mierne zmeniť zakrivením Zeme; **nie je to model reliéfu ani výšky antény**. Čas každého bodu je `UTC začiatok + time_s`. Vstupné hodnoty, monotónnosť času každého auta a rozsahy kotvy sa kontrolujú.

Výstup [CSV](../../data/derived/georeference/bratislava-synthetic-road-20261022.csv) pridáva `utc`, `latitude_deg`, `longitude_deg`, `height_m` k nezmeneným pôvodným stĺpcom. [Metadáta](../../data/derived/georeference/bratislava-synthetic-road-20261022.metadata.json) nesú kotvu, osi, verziu Astropy, počet bodov a SHA-256 vstupu, výstupu a generátora. Tento výstup je potrebný, aby sa neskôr mohol testovať výhľad satelitu **z pohybujúceho sa auta**, no samotný dnešný geometrický pilot počíta iba pevnú RSU.

## Reprodukcia a kontrola

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/sumo_georeference.py \
  --waypoints data/inputs/bratislava-synthetic-road/waypoints.csv \
  --output-csv data/derived/georeference/bratislava-synthetic-road-20261022.csv \
  --start-utc 2026-10-22T12:45:00Z \
  --anchor-x-m 800 --anchor-y-m 675 \
  --anchor-lat-deg 48.1486 --anchor-lon-deg 17.1077 --anchor-height-m 0
sha256sum data/derived/georeference/bratislava-synthetic-road-20261022.csv
.venv/bin/python tools/test_sumo_georeference.py
```

Výsledok: **236 bodov**, `car0` a `car1`, UTC rozsah 12:45:00 až 12:45:59,5. Opakovanie do iného výstupného adresára vytvorilo bitovo rovnaký CSV (`81ae33f307311b2e13c32837d409cb292852a54bfb44a7b2826f7ec8e6abdd33`). Spätná projekcia všetkých zaokrúhlených zemepisných súradníc do ENU mala maximálny rozdiel **0,0000662 m** voči vstupnému `(x,y)`; táto hodnota je iba numerická kontrola transformácie a zápisu, nie geodetická presnosť reálnej polohy. Oba SHA-256 metadát sa zhodujú s uloženým vstupom a výstupom.

Jednotkový test pre štyri ENU body vrátane kotvy skontroloval spätný rozdiel pod 1 µm pri nezaokrúhlených súradniciach; druhý test odmietol `nan` a čas bez časovej zóny. Oba testy prešli.

Negatívna kontrola s `x_m=nan` skončila výnimkou `ValueError: x_m must be finite` ešte pred vytvorením súradnicového výstupu.

## Obmedzenia a ďalšia brána

Vstupný SUMO scenár je vytvorený používateľským editorom, nie importom overenej mapy OpenStreetMap. Nezodpovedá automaticky bratislavskej cestnej geometrii, výškovému profilu, pravidlám premávky alebo skutočnému dopytu. Pre názov „reálny úsek Bratislavy“ bude potrebná skutočná mapová sieť, správny `netOffset/projParameter`, pozemné súradnice RSU a kontrola porovnateľnej dopravnej prevádzky. Aktuálne odvodené body smú slúžiť iba ako **syntetická, konzistentne georeferencovaná trajektória**. Ich vloženie do orbitálneho modelu musí ešte prejsť kontrolou časového prekrytia elementov, zemského zákrytu a konkrétnej antény/terminálu.
