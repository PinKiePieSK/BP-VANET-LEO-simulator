# U9 · samostatná stránka technických parametrov

## Rozsah

Editor `/u9-simulator.html` otvára `/u9-parameters.html` v ďalšej karte. Technická stránka má odkaz späť do simulátora. Živý náhľad získava z otvoreného editora cez `BroadcastChannel` a neukladá scenár pri samotnom zobrazení. Bez editora možno vybrať uložený scenár cez existujúci zdrojový endpoint.

Sedem častí rozlišuje čas a náhodnosť, mapu a prostredie, mobilitu, pozemné rádio, satelitnú geometriu, servisný prenos a hranice modelu. Hodnoty scenára sú oddelené od pevných hodnôt, odvodených hodnôt, zdrojových údajov a výskumných predpokladov. Priamo sa dajú meniť seed, číslo ns-3 behu, zvolený pozemný model, výkon a šumové číslo. Ostatné nastavenia sa menia v editore. Ak sú prítomné budovy, stránka osobitne ukazuje účinný model `urban_osm_building`; samotná voľba `urban_los`/`friis` nie je vtedy účinným modelom. DCC je označené ako vypnuté a operátorské lúče/modem ako nemodelované.

## Overenie

- `python3 -m py_compile tools/u9_server.py` prešlo.
- HTTP 200 pre obe stránky, skripty a `/api/u9/technical-model`; profil má Iridium NEXT, Globalstar aj Starlink a interný nábeh je 10 s.
- V prehliadači technická karta dostala živý neuložený scenár z editora. Zmena modelu rádia aj seedu sa premietla späť do editora. Uložený scenár `service-native-iridium-final-20261101` sa načítal v režime len na čítanie. Odkaz späť otvoril simulátor.
- Prenosný balík `BP-Simulator` má aktualizovaných šesť súborov a 11 453 záznamov v manifeste; `verify.py` prešiel. ZIP prešiel `unzip -tq`; SHA-256 `9e49b8f64df32b3878296bfdb3282321c6e011d6663577e31768577048fbab03`.

Táto zmena nepridáva nový fyzikálny model ani nový experimentálny beh. Stránka je čitateľný audit aktuálneho scenára a implementovaných konštánt; zo servisného profilu sa nesmie vyvodzovať meraná dostupnosť operátora.
