# F1a — čerstvý orbitálny archív troch skupín

**Dátum:** 1. 11. 2026. Prvá dokončená brána [plánu fyzikálnej vernosti](../plan-fyzikalna-vernost-2026-11-01.md). Vstup je priamo z CelesTrak GP/OMM, nie z predchádzajúcej cache ReTLEctor. Ide o sledované katalógové objekty, nie o potvrdený zoznam prevádzkových satelitov.

## Oprava importu a kontrola integrity

`tools/fetch_orbits.py` teraz zapisuje správnu hodnotu `upstream=CelesTrak GP`, takže nový manifest prijme existujúci `v3_leo_topology.load_orbits`. Pred uložením gzip súboru vyžaduje platný OMM zoznam bez duplicitných ID a aspoň jeden element každej skupiny vo veku do 48 hodín. Opätovné použitie dvojhodinovej lokálnej cache kontroluje SHA-256 všetkých troch gzip aj surových JSON súborov a počty objektov; poškodený súbor sa odmietne. Rozpracovaný adresár bez manifestu sa nikdy nevracia ako hotový snapshot. Historický archív z 22. 10. zostal nezmenený (manifest SHA-256 `d28ad3618304780d3cd118e83e8e8a2e88c14d015fa022c3082ba7b2f624d826`).

Nová snímka: `data/orbits/20261101T113716Z-celestrak`, manifest SHA-256 `067b9f58d9cf14ffb16730535226cbb1cbcef0289c5fa7119a440bad8f013556`. Všetky tri skupiny boli stiahnuté jednou sekvenciou priamych požiadaviek; následné volanie vrátilo `cached` bez nového downloadu.

| Skupina | Všetky záznamy | Epochy do 48 h pri stiahnutí | Katalógové ID nad 99999 |
| --- | ---: | ---: | ---: |
| Iridium NEXT | 80 | 80 | 0 |
| Globalstar | 36 | 33 | 8 |
| Starlink | 11 156 | 11 140 | 527 |

Pri epoche `2026-11-01T11:38:00Z`, 30 s okne a 10 s kroku prešli pôvodným OMM→SGP4→ITRS vzorkovaním všetky tri skupiny: Iridium 80 platných objektov, Globalstar 33, Starlink 11 140. Z nich bolo šesťmiestnych Globalstar 6 a Starlink 524. Surový audit so SHA-256 orbitálnych vstupov a EOP je v `~/Desktop/BP-Simulator-Workspace/physical-f1a-20261101/propagation-audit.json`.

Negatívna skúška zmenila jeden gzip súbor po vytvorení manifestu; `verify_snapshot` odmietol poškodený archív. Prázdny download nevytvoril manifest ani gzip. Test overil aj celý starý trojskupinový archív. Syntax Python/shell prešla. Automatická regresia: **125 testov OK**; log je v pracovnom priečinku na ploche.

Prenosný balík obsahuje obnovovací nástroj a `bash run.sh refresh-orbits` pre obnovenie GP po rozbalení na podporovanom Ubuntu. Príkaz sa overil v pracovnom runtime: vrátil lokálne `cached` bez nového sieťového volania. Adresár `~/Desktop/BP-Simulator` prešiel integritnou kontrolou **11 376 súborov a odkazov**; ZIP SHA-256 je `281ef596ad447101e6dd7c7dd90d5b07bfd70c4f76e62cd5a6d297c0fe872326`. Predošlý balík je zachovaný v `~/Desktop/BP-Simulator-Workspace/package-pre-f1a-20261101`.

Nové bajty v archíve sú nemenný vstup; **aktuálny U9 scenár ich ešte nevyberá**. F1b preto musí pripojiť presný snapshot a hash k scenáru, náhľadu, preflightu a packet behu naraz. Kým F1b nie je hotové, editor na porte 8765 naďalej používa pripnutý historický archív z 22. 10.; nedáva zmysel nastavovať dátum 1. 11. a očakávať použiteľný satelitný beh.

Zdroj a formát: [CelesTrak GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php), [politika sťahovania](https://celestrak.org/usage-policy.php).
