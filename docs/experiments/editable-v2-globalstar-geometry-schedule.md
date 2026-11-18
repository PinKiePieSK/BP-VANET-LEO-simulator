# Geometrický plán Globalstar proxy pre editovateľný v2 paketový pilot

**Stav:** izolovaný predvýpočet overený 22. 10. 2026 UTC. Sám **nesimuluje ani neposiela paket**. Pripravuje len časovo zhodný vstup pre prípadný otvorený ns-3 model `RSU → hypotetický UT → archívny objekt → mestská gateway proxy`: šesť vzoriek pri `t=20,0–22,5 s` po 0,5 s. Používa `rsu0` zo schváleného [v2 packet-subset scenára](editable-v2-cam-radio.md), jeho povinnú WGS84/ENU kotvu a archívny GP/OMM záznam. Globalstar komerčnú trasu ani protokol RM200M týmto nepredstavuje.

## Presný beh

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/prepare_editable_v2_globalstar_geometry_schedule.py \
  --scenario data/inputs/editable-road-v2/packet-subset.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --gateway-proxy nemea-city-proxy \
  --output-csv results/editable_v2_globalstar_geometry_schedule/positive.csv
.venv/bin/python tools/prepare_editable_v2_globalstar_geometry_schedule.py \
  --scenario data/inputs/editable-road-v2/packet-subset.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --gateway-proxy nemea-city-proxy --negative-gateway \
  --output-csv results/editable_v2_globalstar_geometry_schedule/negative-gateway.csv
.venv/bin/python tools/test_editable_v2_globalstar_geometry_schedule.py -v
```

Testy **3/3**: jeden objekt na oboch koncoch po celé okno, presná schéma/UTC/časy/delays a hash; syntetická negatívna brána zachová všetky ostatné geometrické polia, ale zablokuje 6/6; chýbajúca explicitná brána sa odmietne a umelo príliš vysoká maska uzavrie všetkých šesť riadkov **bez dosadenia náhradného satelitu**. Žiadny zdroj reportov ani packet fixture sa nečíta.

Kladný `positive.csv` má SHA-256 `7d45936c115a1b208a916daa6bc8b26ffc3edcad750463cbea1e4cb96fe7fd74`, sprievodný `positive.metadata.json` `2817f80eab3fa8d67342eb04baf93b9bfbf821ef5fb14cd26e88338d663c0664`. Záporný CSV má SHA-256 `d8ecd353627d1f9a049f2dc1b6d2c54d9919faabf6d38535d3a6addb1b0ad68f`, jeho metadata `3902a3669332345fe1958dffaa0f979fb6221a54141585d60b43a76bfc46f692`. Každý CSV obsahuje **presne šesť dátových riadkov** a presne túto hlavičku:

```text
time_us,utc,catalog_id,omm_sha256,ut_elevation_deg,gw_elevation_deg,ut_delay_ns,gw_delay_ns,enabled
```

`time_us` je mikrosekunda od počiatku scenára `2026-10-22T12:45:00Z`; `utc` je absolútny UTC, `*_elevation_deg` sú topocentrické stupne, `*_delay_ns` sú **jednosmerné vákuové** nanosekundy `round(slant_range_km/299792,458 km/s × 10⁹)`. `enabled=1` je **iba geometrická brána v jednom vzorkovanom okamihu**. Prázdne ID/hash/delays a `enabled=0` znamenajú, že niet jedného spoločného objektu nad maskou pre **celé** šesťvzorkové okno; ďalšia vrstva musí taký plán odmietnuť alebo modelovať ako nedostupný, nie doplniť odhadom.

## Vstup, transformácia a výber

`packet-subset.json` SHA-256 `ac1b242cc750205a62683f6799af68603051cc8bddb1573aa9427f4370825f3c` prechádza celým validátorom v2. Jeho lokálny bod RSU `(490, 615) m` a ukotvenie `(800, 675) m ↔ (48,1486° N, 17,1077° E, 0 m)` dávajú cez už overený `enu_to_wgs84` bod RSU `48,148060323° N; 17,103533981° E; 0,007802 m`. Hodnota výšky je len dôsledok tangentnej WGS84 transformácie `up=0`, **nie výška reálnej antény**. `rsu0` deklaruje `its_g5` a `ip_backhaul`, **nie satelitný terminál**. Tento plán je hypotetický proxy variant; nasadenie by vyžadovalo terminál, anténu, napájanie a službu.

Proxy Nemea je **centrum mesta** `37,8167° N; 22,6667° E; 0 m`, nie súradnica skutočnej antény. [Globalstar oznámil pozemnú stanicu v Nemea](https://investors.globalstar.com/news-releases/news-release-details/globalstar-completes-expansion-greece-ground-station-marking-key), ale v oznámení z 21. 9. 2026 bolo rozšírenie ešte v uvádzaní do prevádzky. Z toho nemožno odvodiť stav/priradenie tejto konkrétnej služby a objektu. [Verejný opis Globalstar](https://www.globalstar.com/en-us/about/our-technology) podporuje transparentnú cestu používateľ–satelit–vhodná pozemná brána, a preto testujeme **to isté katalógové ID na oboch koncoch**. Maska **10° je výskumné nastavenie**, nie publikovaná anténna maska.

Snímka `20261022T124815Z-retlector` má manifest SHA-256 `d28ad3618304780d3cd118e83e8e8a2e88c14d015fa022c3082ba7b2f624d826`, surovú Globalstar skupinu SHA-256 `99844314d711a0028cd03a045f13699a6f6460039d8a859cb03e62ff972f17af` a 30 z 36 vekom prijatých GP objektov. Archív bol získaný až `2026-10-22T12:49:43.719531Z`, **po** 12:45:20–22,5 prehrávanom okne; výstup je retrospektívny, nie vstup skutočne dostupný terminálu v čase TX. Reuse existujúceho `globalstar_two_endpoint_geometry.py` načíta a hashom overí OMM, ponechá len epochy pred počiatkom a vek najviac 48 h dokonca cez 360 s horizont do 12:51 UTC. Nový adaptér používa tie isté WGS84/ECEF, lokálne topocentrické vektory a Astropy TEME→ITRS so SGP4/WGS72 a offline IERS/EOP tabuľkou SHA-256 `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`. Presné verzie knižníc sú v metadata; nové RF ani orbitálne fyzikálne pravidlá sa nepridávajú.

Zo 30 vekom prijatých objektov musí **jeden objekt počas všetkých šiestich okamihov** spĺňať eleváciu `>0°` a `≥10°` pri RSU aj proxy. Spomedzi takých sa volí najväčšia *najhoršia* elevácia zo všetkých dvanástich koncových meraní, pri zhode najmenšie číselné ID. Ide o konzervatívny pevný geometrický kandidát bez vymysleného handoveru. Výsledkom je **ID 37741 vo všetkých šiestich riadkoch**, OMM record SHA-256 `64a1f3de50a39556c1d94d33d7369589ee0b6ea3a3624af70c80796c661311aa`, epocha `2026-10-21T06:54:00.067392Z`. Výber v žiadnom prípade nedokazuje, že operátor používal tento satelit alebo gateway.

| t od počiatku | Elevácia RSU / Nemea proxy | `r/c` RSU→objekt / objekt→proxy | `enabled` |
| --- | --- | --- | ---: |
| 20,0 s | 20,413631° / 21,399020° | 9,276983 / 9,087401 ms | 1 |
| 22,5 s | 20,256858° / 21,172884° | 9,307490 / 9,129825 ms | 1 |
| 20,0–22,5 s, syntetická záporná brána | skutočná vypočítaná RSU elevácia / **−1,000000° dosadené iba v kontrole** | skutočné vypočítané vzdialenosti sú ponechané | **0/6** |

Metadáta nesú hash scenára, výsledku, skriptu, archívu, Globalstar gzip/raw, EOP, presné WGS84 body, vybrané epochy pre každý UTC, pravidlo výberu a označenie záporného zásahu. Súčet dvoch uvedených `r/c` je iba dolná hranica šírenia vo vákuu; neobsahuje serializáciu, prístup k médiu, opakovanie, frontu, spracovanie ani pozemný core. Pri budúcom paketovom behu treba bránu aplikovať v čase TX a výslovne povedať, či sa mení počas letu. CSV **neobsahuje payload** a teraz sa neviaže na žiadne report/PCAP bajty.

**Hranica platnosti:** žiadny overený používateľský terminál, skutočná poloha alebo aktivita antény Nemea, beam, operátorské riadenie, RF/MAC, RM200M správy, ISL, zákryty terénom, dostupnosť služby ani doručenie. [Fail-closed operátorský kontrakt](../decisions/operator-path-fidelity-contract.md) bráni povýšeniu takejto geometrie na servisné tvrdenie.
