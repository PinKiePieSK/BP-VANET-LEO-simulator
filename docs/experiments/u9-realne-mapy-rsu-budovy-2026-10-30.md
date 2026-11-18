# U9: glóbus, reálne mapy, RSU a tienenie budov — 30. 10. 2026

**Aktualizácia:** Nižšie je pôvodná analýza pred realizáciou reálnej mapy. Skutočný stav glóbusu, lokálneho výrezu, importu jedného cestného úseku, prenosného balíka a otvorenej brány budov je v [prijímacom zázname mapového celku](u9-zem-a-realna-mapa-2026-10-30.md). Starší hash ZIP v tomto denníku je historický.

## Vykonaná úprava glóbusu

Pôvodné ručné orezávanie pobrežia na horizonte vytváralo nepresné spojnice. Pobrežie a zemepisná sieť teraz používajú ortografickú projekciu D3 s orezaním na horizonte. Skripty D3 sú uložené lokálne v `viewer/lib/`, takže vykreslenie nevyžaduje pripojenie k CDN. Odvrátené satelity sa už nepremietajú cez viditeľnú pologuľu: to fyzicky prekrývalo kontinenty a bolo vizuálne zavádzajúce. Celý **časovo platný** katalóg ostáva v pamäti náhľadu; otočenie Zeme ukáže druhú stranu. UI uvádza počet v katalógu, na viditeľnej pologuli a po otočení. Konštelácia v tomto zmysle nie je počet paketových uzlov: do natívneho DVB modelu vstupuje vybraný aktívny podgraf.

Pri epoche 22. 10. 2026 12:45 UTC má archív Iridium 80 záznamov, z toho 79 platných; Globalstar 30/30; Starlink 11 121/10 627. Neplatné/staré OMM sa zámerne nekreslia, lebo ich poloha v zvolenom čase nie je dôveryhodná. Na glóbuse sú satelity zobrazené v subsatelitnom smere na povrchu Zeme; ich skutočná výška nie je mierkou zakreslená. Náhľad pohybu používa SGP4/TEME→ITRS a pripnuté EOP; rámce sú medzi vzorkami graficky interpolované.

V bežiacom editore sa Iridium vykreslilo ako 38 objektov na viditeľnej pologuli a 41 po otočení. Starlink načítal 10 627 platných objektov, z nich 5 260 na viditeľnej pologuli a 5 367 po otočení. Údaj „412 nad miestom“ pri výbere Starlinku je počet stabilne viditeľných počas výberového okna; údaj „416 geometricky nad maskou“ na glóbuse je okamžitý stav v 10. sekunde. Snímka opraveného glóbusu je v `/home/samuel-petrik/Desktop/BP-Simulator-Workspace/u9-globe-orthographic-20261030.png`. HTML, obidve lokálne D3 knižnice, pobrežie a JS majú na porte 8765 HTTP 200; syntax Python/JavaScript prešla. Tieto kontroly nemenia výsledky paketovej simulácie.

Prenosný priečinok `/home/samuel-petrik/Desktop/BP-Simulator` a ZIP `/home/samuel-petrik/Desktop/BP-Simulator.zip` boli obnovené z finálneho zdroja. Kontrola manifestu prešla pre 11 520 súborov a odkazov; SHA-256 ZIP je `69ee4d3d1cf9321522d825d588881ab5f2b27c6ea529075d3004b095d3a203c9`. Bežiaci editor na porte 8765 číta rovnaký JS ako zdroj i prenosný balík.

## Reálna mapa a úsek cesty: uskutočniteľná architektúra

„GPS mapa“ tu znamená georeferencované dáta WGS84 a mapový podklad; GPS samotné neposkytuje cesty ani budovy. Pre vizualizáciu je vhodný [MapLibre GL JS](https://maplibre.org/maplibre-gl-js/docs/): má glóbus, 2D mapu, vlastné vrstvy GeoJSON, mierku, 3D extrúzie budov aj terén. Môže zobrazovať lokálne uložené údaje a štýly. Súčasný ľahký glóbus môže zostať orbitálnym pohľadom; MapLibre má zmysel najmä pre detailnú cestnú mapu. Ak sa neskôr prejde na jeho glóbus, polohy satelitov sa majú kresliť ako georeferencovaná vrstva nad **tou istou UTC časovou osou**, nie vypočítavať z mapového podkladu.

Geometrickým zdrojom ciest a budov môže byť OpenStreetMap. [SUMO vie importovať OSM](https://sumo.dlr.de/docs/Networks/Import/OpenStreetMap.html) priamo cez `netconvert --osm-files`; [osmGet](https://sumo.dlr.de/docs/Tools/Import/OSM.html) podporuje výrez podľa geografického obdĺžnika. OSM WGS84 sa pri importe do SUMO premieta do lokálnych súradníc. Reálny postup pre používateľa: vybrať miesto na glóbuse → na detailnej mape zvoliť ohraničený úsek alebo trasu → stiahnuť/otvoriť **pripnutý** OSM výrez → vytvoriť SUMO sieť → zobraziť reálne cesty v editore → doplniť autá a RSU → spustiť rovnaký paketový model. Výrez, dátum, hash, licencia a atribúcia musia byť uložené spolu so scenárom. Cestná topológia, smerovosť, križovatky a rýchlosti sa musia validovať, nie iba vizuálne prekresliť.

Súčasný editovateľný svet má lokálny WGS84 ENU rámec 0–2000 m, najviac 100 cestných uzlov a 100 úsekov, a každý úsek považuje za obojsmerný. Teda **ľubovoľný OSM výrez zatiaľ nemožno korektne importovať**. Prvý inkrement môže byť úzky koridor v týchto limitoch; pre mestskú sieť treba verziovať schému, zväčšiť hranice a zachovať jednosmernosť, pruhy a napojenie. Existujúci lokálny bratislavský OSM súbor `data/inputs/bratislava-osm/map.osm` a jeho SUMO sieť poskytujú reprodukovateľný pilot; cestný filter má 510 motorových ways a 1 696 uzlov, nie však hotový univerzálny import do U9.

Verejný server `tile.openstreetmap.org` **nesmie slúžiť na hromadné sťahovanie alebo offline prednačítavanie**; vyžaduje atribúciu, identifikáciu aplikácie a cache podľa [politiky OSMF](https://operations.osmfoundation.org/policies/tiles/). Prenosný simulátor má používať legálne lokálne vektorové dáta alebo poskytovateľa s povoleným offline balíkom. MapLibre je renderer, nie zdroj dát a nie rádiový model.

## Reálne polohy RSU

Najkonkrétnejší overený verejný zdroj je [geografická vrstva U.S. Department of Transportation](https://geo.dot.gov/server/rest/services/Hosted/V2X_Deployment_Map_ULS_Licenses_and_V2X_RSUs_Updated_8_11_26_WFL1/FeatureServer/2) s názvom **8 401 Active RSU Locations at Signalized Intersections – July 2026**. Poskytuje body a GeoJSON dotazy; server vracia maximálne 2 000 záznamov na stránku a podporuje stránkovanie. Skúšobný GeoJSON dotaz skutočne vrátil polohy a identifikátory, napr. bod pri 40.78141667° N, −73.55727778° E s prevádzkovateľom New York State Department of Transportation. Vrstva však nemá výšku (`HasZ: false`) a samotný bod nedokazuje aktuálnu dostupnosť rádia, výkon, anténu ani prístup k sieti. Dátum snímky sa musí zachovať.

Použitie v U9: dotaz len pre vybranú oblasť, uložiť odpoveď a hash, preniesť WGS84 polohy do toho istého ENU rámca ako cesty, označiť RSU ako `reported_location` a technické parametre antény/služby ako samostatné `unknown` alebo zdôvodnený odhad. Mimo pokrytia tejto vrstvy zostávajú ručne vložené RSU výslovne hypotetické. V dostupných verejných zdrojoch som nenašiel overiteľný strojovo čitateľný zoznam presných slovenských RSU; to nie je dôkaz, že neexistuje.

## Budovy a rádiové tienenie

Lokálny bratislavský OSM výrez obsahuje 936 ways s tagom `building`, ale iba 4 s priamym `height` a 408 s `building:levels`. Pôdorysy sú použiteľné ako geometrický vstup; výšky sú vo väčšine prípadov neznáme alebo len odhadované. [OSM `height`](https://wiki.openstreetmap.org/wiki/Key:height) a [`building:levels`](https://wiki.openstreetmap.org/wiki/Key:building:levels) majú rôzny význam; prevod podlaží na metre treba vo výsledkoch označiť ako modelový odhad.

[ns-3 Buildings module](https://www.nsnam.org/docs/models/html/buildings-design.html) podporuje budovy a kanálové podmienky LOS/NLOS vrátane V2V Urban. Súčasný spoločný U9 beh však používa pozemný OCB/Friis; existujúca mestská sonda je oddelená a používa syntetickú budovu. Kreslenie budov na mape **samo o sebe nemení prijímanie paketov**. Integrácia musí previesť OSM pôdorysy a výšku do lokálneho 2.5D modelu, pri každom páre auto–auto/auto–RSU určiť priesečník spojnice s budovou v relevantnej výške antén, potom tento stav pripojiť k zvolenému ns-3.38 kanálu a overiť párovými behmi s rovnakým pohybom a seed. Jednoduchý binárny blokovaný/neblokovaný test môže byť prvým citlivostným variantom; absolútna PDR bez meranej kalibrácie nebude predikciou mesta. Pri satelite treba oddeliť blokovanie miestneho výhľadu antény budovou od operátorského RF/link budgetu.

## Odporúčané poradie implementácie

1. **Mapový podklad a súradnice:** pripnutý malý OSM výrez, MapLibre detailná mapa, jednotný WGS84↔ENU prevod, atribúcia a offline režim. Overiť, že bod na glóbuse, rovnaký bod na mape a SUMO sieť sú totožné.
2. **Výber reálnej trasy:** najprv koridor v súčasných limitoch; potom schéma pre jednosmerky, viac ako 100 úsekov a križovatky. Porovnať vozidlové stopy so SUMO sieťou.
3. **RSU dáta:** adaptér na verejnú USDOT vrstvu s regionálnym výrezom, cache, provenienciou a explicitne neznámymi RF parametrami. Nepriraďovať týmto bodom automaticky aktivované satelitné terminály.
4. **Budovy:** OSM pôdorysy, triedy kvality výšky, vizuálne zobrazenie, následne LOS/NLOS v jednom integrovanom pozemnom behu a párové kontroly. Až potom tvrdiť, že budovy ovplyvňujú komunikáciu.

## Brána na tvrdenie „reálne mesto“

Pred takým tvrdením musia prejsť kontroly rovnakého CRS a UTC, smerovosti ciest, stôp áut, polohy RSU, výšok antén/budov, reprodukovateľného dátového výrezu, a rozdielu v paketových výsledkoch pri zapnutom a vypnutom tienení. Doterajší glóbus je presná orbitálna geometria v medziach archívu, nie realistická 3D mapa či kalibrovaný rádiový model mestskej zástavby.
