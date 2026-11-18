# Čistenie OSM ciest a oprava križovatky — 11. 11. 2026

**Historický pokus.** Automatické spájanie a skrývanie úsekov aj formulár manuálneho spojenia sú teraz pozastavené. Aktuálny stav a dôkaz sú v [overení verného importu OSM](simulator-osm-faithful-import-2026-11-11.md).

## Zmena

Pri vytvorení pracovného výrezu sa z lokálneho cestného grafu odstránia slepé vedľajšie úseky kratšie ako 30 m a odpojené skupiny s celkovou dĺžkou kratšou ako 100 m. Väčšie samostatné cestné skupiny zostávajú. Voľné konce odlišných komponentov sa automaticky spoja iba do 5 m, ak majú rovnakú triedu, nadväzujúci smer a jediného kandidáta. Úseky použité na trase auta alebo zahrnuté do manuálnej opravy zostávajú zachované. Ide o spracovanie grafu pre editor a následný vstup do SUMO, nie o zmenu podkladovej OSM databázy.

Pre väčšiu medzeru medzi koncom a stredom druhej cesty pribudol v paneli reálnej cesty nástroj „Opraviť chýbajúce napojenie“. Používateľ vyberie voľný koniec a cieľovú cestu do 50 m po overení, že ide o križovatku v rovnakej úrovni. Editor premiestni koniec, podľa potreby rozdelí cieľovú cestu a vytvorí spoločný grafový uzol. Novú WGS84 geometriu ukladá do `map_objects.roads`; voliteľné `manual_joins` uchováva ID, koniec, cieľ, bod a vzdialenosť zásahu. Samotný SUMO vstup vzniká z aktualizovaných `roads.nodes` a `roads.segments`. Koniec orezaný hranou mapy a cestu používanú existujúcim autom nástroj odmietne.

## Overenie na bežiacom runtime

- Živý server `127.0.0.1:8766` vrátil nové verziované HTML, CSS a JS; test prebehol v oddelenom headless Firefox, používateľská karta ani server sa nereštartovali.
- V 4 km výreze Bratislavy zostalo 4 898 ciest. Panel uviedol 881 skrytých krátkych úsekov a jedno automaticky spojené malé prerušenie. Toto číslo je kontrola konkrétneho výrezu, nie univerzálna miera kvality OSM.
- Syntetické prípady v skutočnom mapovom module potvrdili spojenie dvoch zarovnaných koncov vzdialených 4 m, odstránenie krátkeho slepého úseku a zachovanie rovnakého úseku, ak je chránený trasou auta.
- Vložený dvojcestný prípad overil panel: spojenie konca `roadA` s bodom uprostred `roadB` vzdialeným 10 m vytvorilo `roadB_j1`, tri cesty zdieľajú jeden uzol stupňa 3 a záznam `manual_joins` nesie presné súradnice a vzdialenosť. Scenár zostal neuložený.
- Zdrojový aj U9 runtime Python validator prijali správny záznam opravy a odmietli vzdialenosť nad 50 m.
- Uložený scenár `realna-d1-pozemna` sa v oddelenej karte načítal so všetkými 6 autami; po čistení bol označený ako zmenený a `/api/simulator/editor/check` vrátil HTTP 200 s plánom pre 6 áut. Žiadne používateľské dáta sa neprepísali.
- `python3 scripts/refresh_study_code.py --check`: PASS, 64 aktívnych súborov.

## Hranice

Automatika nevie z dvojrozmernej OSM geometrie určiť výškovú úroveň križovania. Väčšiu medzeru pri koľajach alebo nadjazde preto nespojí sama. Oprava konkrétnej križovatky z obrázka bude v scenári existovať až po výbere dvoch ciest a potvrdení v editore. Čistenie sa týka ciest odovzdaných simulácii; podkladová mapa môže naďalej kresliť vlastné referenčné čiary.
