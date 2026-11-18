# Bratislavská OSM cesta: prvý dopravný smoke test

Stav 22. 10. 2026 UTC. Toto je nový **dopravný vstup**, nie ešte spoločný beh OSM–CAM–ns-3–satelit. Účel je nahradiť ručne kreslenú geometriu cesty overiteľným výrezom OpenStreetMap a overiť import, trasovanie a súradnice. Hypotéza: ohraničená motorová cestná sieť z verejného zdroja umožní aspoň jeden deterministický 60 s SUMO beh s WGS84 FCD a bez kolízie alebo teleportácie.

## Vstup, licencia a výber

`map.osm` je odpoveď OSM API 0.6 z 22. 10. 2026 14:30:23 UTC pre `bbox=17.101,48.145,17.115,48.153`, URL `https://api.openstreetmap.org/api/0.6/map?bbox=17.101,48.145,17.115,48.153`; SHA-256 `59d94d0a52c2a7d326b1343f7fa830e32736954455d059397af03bf573fe5e39`. © OpenStreetMap contributors, ODbL 1.0; atribúcia a licencia sú aj v XML. Pôvodné uzly/ways majú vlastné metadáta vrátane individuálnych časov úprav. Dátum stiahnutia nie je dátum zamerania ani záruka úplnosti.

Priamy import celého BBOX do `netconvert` skončil s návratovým kódom 134 a interným zlyhaním `NBNodesEdgesSorter::edge_by_junction_angle_sorter::getConvAngle` pri konverzii. Vstup obsahoval aj neúplné relácie na hranici BBOX. Tento neúspešný pokus je zaznamenaný; nevyvodzujeme z neho neplatnosť celej mapy. Reprodukovateľný prípravný skript ponechá triedy `secondary`, `secondary_link`, `tertiary`, `residential`, `unclassified`, `living_street`, `service`, ich referencované uzly a pôvodnú OSM atribúciu, odstráni ostatné ways a relácie. Výsledok má 510 ways a 1696 uzlov, SHA-256 `a4b7c90d41ea87d45e6e0740d971d863ee9cde4c7a9c8089ef0000ded9640dd5`. Filter nie je odborne validovaný výber všetkých prejazdných ulíc; napríklad `service` zahŕňa rôzne areály a neoverujeme obmedzenia prístupu. Výsledok sa nesmie vydávať za úplnú, kalibrovanú sieť Bratislavy.

## Presný postup

Spúšťať z koreňa Git projektu, SUMO 1.18.0, Python 3.12:

```bash
python3 tools/prepare_osm_road_subset.py \
  --input data/inputs/bratislava-osm/map.osm \
  --output data/inputs/bratislava-osm/road-only.osm
netconvert --osm-files data/inputs/bratislava-osm/road-only.osm \
  --geometry.remove --junctions.join --tls.guess-signals \
  --tls.discard-simple --tls.join --tls.default-type actuated \
  -o data/inputs/bratislava-osm/road.net.xml
SUMO_HOME=/usr/share/sumo python3 /usr/share/sumo/tools/randomTrips.py \
  -n data/inputs/bratislava-osm/road.net.xml \
  -r data/derived/bratislava-osm-pilot/routes.rou.xml \
  -o data/derived/bratislava-osm-pilot/trips.trips.xml \
  -b 0 -e 60 -p 10 -s 314159 --validate
sumo -n data/inputs/bratislava-osm/road.net.xml \
  -r data/derived/bratislava-osm-pilot/routes.rou.xml -b 0 -e 60 \
  --fcd-output data/derived/bratislava-osm-pilot/fcd-geo.xml \
  --fcd-output.geo true \
  --summary-output data/derived/bratislava-osm-pilot/summary-geo.xml \
  --collision.action warn
python3 tools/check_bratislava_osm_pilot.py
```

`netconvert` pri filtrovanom vstupe skončil s exit 0, ale vypísal varovania o zlučovaní križovatiek, signáloch a ostrých odbočeniach. Pred fyzikálnou/prevádzkovou interpretáciou treba tie miesta skontrolovať v mape. SUMO sieť má UTM zónu 33 a uloženú transformáciu `netOffset`, výstup `--fcd-output.geo` priamo obsahuje zemepisnú dĺžku `x` a šírku `y` vo WGS84. Konverzia sa kontroluje voči `origBoundary` siete.

## Pozorovanie a limity

Kontrola prešla: 4 validované náhodné trasy z pevného semena 314159, 60 krokov po 1 s, 151 georeferencovaných záznamov pre vozidlá 0, 1, 2, 4, všetky v hranici siete, 0 kolízií a 0 teleportácií. Do konca 60 s dorazilo jedno vozidlo a tri ešte jazdili. To je **funkčný import a reprodukovateľný pohyb**, nie reálny dopravný dopyt alebo kalibrácia dopravného toku. Nepoznám reálne intenzity, semaforové plány, jazdné pruhy ani polohu antény RSU. Bez ich validácie nesmú z tohto behu vzniknúť tvrdenia o reálnej Bratislave. Následný [izolovaný OSM→CAM→RSU experiment](osm-ba-cam-rsu.md) už použil päť súvislých FCD bodov na paketový beh; kvalita križovatiek, dopytu a rádia zostáva osobitnou validačnou bránou.
