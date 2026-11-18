# Explicitná WGS84/ENU kotva editovateľného scenára v2

## Účel a hranica

Voľne kreslené cesty v scenári v2 majú lokálne kartézske súradnice v metroch. Aby sa ich poloha dala použiť v CAM alebo budúcej geometrii satelitného spojenia, každý vstupný JSON teraz **povinne** obsahuje geografickú kotvu. Tá odstraňuje skrytú bratislavskú konštantu z `tools/prepare_editable_v2_cam.py`. Kotva je modelový vstup, nie dôkaz existencie cesty, vozidiel ani rádiovej služby na zvolenom mieste.

```json
"georeference": {
  "frame": "WGS84_ENU",
  "anchor_x_m": 800.0,
  "anchor_y_m": 675.0,
  "latitude_deg": 48.1486,
  "longitude_deg": 17.1077,
  "height_m": 0.0
}
```

`anchor_x_m` a `anchor_y_m` sú súradnice bodu v lokálnom cestnom grafe; uvedená šírka, dĺžka a výška sú WGS84 poloha **toho istého bodu**. Lokálne `+x` smeruje na východ, `+y` na sever. Zemepisné uhly sú v stupňoch; `height_m` je **elipsoidická**, nie nadmorská výška. Povolené intervaly: x/y `0..2000 m`, šírka `−90..90°`, dĺžka `−180..180°`, výška `−500..9000 m`. Všetky čísla musia byť konečné a nesmú byť text alebo booleovská hodnota. `frame` musí byť presne `WGS84_ENU`; neznáme alebo chýbajúce polia sa odmietnu. Rovnaké limity vynucuje Python validátor aj editor v prehliadači. Editor zobrazuje predvolený demonštračný bod Bratislavy, ktorý možno zmeniť.

## Algoritmus a dáta

SUMO generátor stále vytvára a simuluje lokálnu sieť v metroch. Jeho `fcd.xml` obsahuje polohy vozidiel v lokálnom grafe a čas od začiatku simulácie. Paketový prípravný krok načíta **kotvu zo vstupného JSON**; pre každú FCD polohu vypočíta `east = x_m − anchor_x_m`, `north = y_m − anchor_y_m` a `up = 0`. Pomocou `astropy.coordinates.EarthLocation` prevedie WGS84 geodetickú kotvu na geocentrické XYZ, pridá ENU posun po otočení do zemského rámca a výsledok prevedie späť na WGS84 šírku, dĺžku a elipsoidickú výšku. Výstup zaokrúhli pre CAM na `latitude_e7`/`longitude_e7` v `10⁻⁷°` a `altitude_cm` v cm. Prípravný krok zároveň zachová lokálne x/y a UTC z `simulation.utc_origin`. Použitá kotva je zapísaná v `waypoints.metadata.json` a v dopravnom manifeste.

[Astropy EarthLocation](https://docs.astropy.org/en/stable/api/astropy.coordinates.EarthLocation.html) dokumentuje prevody geodetických a geocentrických súradníc vrátane WGS84 elipsoidu. [Oficiálna dokumentácia SUMO FCD](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html) určuje význam polohy, rýchlosti a smeru vo výstupe FCD. V tomto scenári nevzniká geograficky referencovaná SUMO cestná sieť; WGS84 vznikne až v explicitnom adaptéri.

Tangentný model je určený pre malý lokálny graf do `2 km × 2 km`. `up=0` znamená nulový ENU posun od kotvy, nie konštantnú výslednú elipsoidickú výšku: vzhľadom na zakrivenie elipsoidu sa výstupná výška mierne mení. Model nepoužíva digitálny terén, skutočnú výšku vozidla či RSU antény, geoid, meranú GNSS chybu, zatienenie ani šírenie RF. Pre orbitálnu viditeľnosť je nutné pridať výšky a anténne masky a osobitne overiť geometriu/čas; samotná kotva to nerobí.

## Migrácia a dôkaz

`data/inputs/editable-road-v2/scenario.json` aj `packet-subset.json` obsahujú explicitný pôvodný bod `(800 m, 675 m) ↔ (48.1486°, 17.1077°, 0 m)`. Tak sa starý paketový fixture zachová bez implicitného fallbacku. `tools/test_editable_v2_anchor.py` spustí SUMO a prípravný krok z migrovaného `packet-subset.json`: SHA-256 všetkých 24 waypoint riadkov vrátane hlavičky ostáva `77dce47be845e6ca8c303696302449627a0719e3da927c40ca77553ab7d9f0d7`, teda presne ako pred migráciou. Potom zmení **iba** dĺžku kotvy o `+0.1°` a nad tým istým FCD opakuje prevod: lokálne x/y, čas a rýchlosť zostanú rovnaké, WGS84 dĺžka a SHA výstupu sa zmenia. Sedem nových negatívnych kontrol overuje chýbajúcu kotvu, chybný rámec, x/y mimo grafu, šírku/dĺžku mimo platného intervalu a text namiesto výšky. Celý test schémy má 18 negatívnych prípadov.

Z koreňa repozitára:

```bash
python3 tools/test_editable_scenario_v2.py
python3 tools/test_editable_v2_anchor.py
/home/ubuntu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check viewer/draft-editor.js
```

Výsledok v tejto VM: všetky tri príkazy prešli; SUMO test mal štyri vložené a dorazené vozidlá, nulové kolízie a teleporty. Samostatný paketový runner ďalej používa rovnaké CAM a lokálny rádiový model; táto zmena nemení jeho RF parametre ani neimplementuje orbitálny spoj.
