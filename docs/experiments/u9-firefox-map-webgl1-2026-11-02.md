# U9: reálna mapa vo Firefoxe bez WebGL 2

## Diagnóza

Používateľský screenshot z ikony simulátora na porte 8766 ukázal chýbajúci reálny podklad v oboch mapových plochách. Glóbus spadol do lokálneho záložného vykresľovania a zobrazil hlásenie `WebGL2 is required ... browser does not support WebGL2`. Cestný graf OSM sa pritom načítal správne: 5 779 úsekov a 12 977 budov. Príčinou chýbajúceho podkladu bol teda renderer MapLibre GL JS 6.16.0, ktorý podľa oficiálneho migračného návodu vyžaduje WebGL 2, nie import OSM.

## Oprava

MapLibre je pripnutý na verziu 5.24.0 z oficiálneho balíka npm `maplibre-gl`; stiahnutý tarball bol overený oproti registračnému SHA-512 integrity. Táto vetva zachováva glóbus a umožňuje WebGL 1. Oba pohľady používajú tú istú verziu a rovnaký reálny štýl OpenFreeMap. Staré nevyužité súbory v6 boli vyradené z aktívneho vieweru a allowlist serverov upravený na nové súbory. Orbitálna geometria, OSM cestný graf a model komunikácie sa nemenili.

## Overenie

- Samostatný test s vynúteným odmietnutím `canvas.getContext('webgl2')` vytvoril cez MapLibre 5 glóbus s reálnymi mapovými dlaždicami; stav `WebGL1 style loaded`, bez chýb konzoly.
- V celom editore na testovacom porte 8767 sa vykreslili reálne mapy v okne ciest aj na glóbuse. Priblíženie na Bratislavu zobrazilo budovy, cesty a miesto pokusu. Prepnutie prázdny svet → reálna mapa prešlo bez chyby konzoly.
- Po reštarte ikony skutočný Firefox používateľa načítal `maplibre-gl-5.24.0.js` a CSS s HTTP 200, cestný výrez s HTTP 200; používateľ následne potvrdil, že glóbus aj reálna mapa fungujú.
- Prenosný balík na ploche: manifest PASS pre 11 268 súborov a odkazov; `unzip -tq` PASS; ZIP SHA-256 `fbc0faf4d1c652188e96ce327f1a70e5567b090d21efbd219b28f3ad4cfd1707`. Zmenené súbory aktívneho runtime majú zhodný SHA-256 so zdrojom. Po reštarte boli staré súbory MapLibre 6 vyradené aj z runtime.

Podklad OpenFreeMap aj naďalej vyžaduje pripojenie k internetu a aspoň funkčné WebGL 1. Zdroj kompatibility: https://maplibre.org/maplibre-gl-js/docs/guides/v5-to-v6-migration-guide/ a https://maplibre.org/roadmap/maplibre-gl-js/globe-view/.
