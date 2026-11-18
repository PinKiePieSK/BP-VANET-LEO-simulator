# Tri skupiny GP objektov: vzorkovaná geometria nad Bratislavou

**Stav:** 22. 10. 2026 UTC. **Kód:** [`tools/multi_constellation_geometry.py`](../../tools/multi_constellation_geometry.py), kontrola [`tools/check_multi_constellation_geometry.py`](../../tools/check_multi_constellation_geometry.py). **Výstupy:** [`bratislava-20261022T124500Z.csv`](../../data/derived/multi-constellation/bratislava-20261022T124500Z.csv) a [metadáta](../../data/derived/multi-constellation/bratislava-20261022T124500Z.metadata.json).

## Účel, vstupy a hypotéza

Pre pevnú polohu potenciálneho terminálu pri RSU `48,1486° N, 17,1077° E, WGS84 výška 0 m` sa z archivovanej [snímky GP/OMM](../../data/orbits/20261022T124815Z-retlector/manifest.json) vypočíta geometrická viditeľnosť skupín `starlink`, `iridium-NEXT`, `globalstar`. Počiatok je **2026-10-22 12:45:00 UTC**, dĺžka 360 s, krok 30 s a zvolená minimálna elevácia 10°. Hypotéza: počet geometrických kandidátov a objekt s najvyššou eleváciou sa v krátkom okne môže meniť, preto statický jediný satelit nemusí byť reprezentatívny. Kontrolou je [samostatne vypočítaná dráha katalógového objektu 43253](../../data/derived/orbit-geometry/iridium-43253-bratislava-20261022.csv). Sú to **sledované katalógové objekty**, nie potvrdený prevádzkový zoznam operátorov.

Archív pochádza z označenej cache ReTLEctor s údajmi označenými ako CelesTrak GP. Stav cache Iridium NEXT a Globalstar bol pri získaní `Stale`; presné časy, pôvodné URL, počty a SHA-256 sú v manifeste. Skript pred výpočtom overí SHA-256 komprimovaných aj dekomprimovaných dát a počet objektov. Každý element musí mať epochu najneskôr na začiatku okna a najviac **48 h veku na konci okna**. Všetky staršie či budúce elementy sa odmietnu; skupina bez aktuálneho elementu spôsobí chybu bez výstupu. Prešlo 10 627 z 11 121 Starlink, 79 z 80 Iridium NEXT a 30 z 36 Globalstar; zamietnuté sú 494, 1 a 6 elementov.

Dodatočný pokus o priamy čerstvý download cez `python3 tools/fetch_orbits.py --provider celestrak` dňa 22. 10. 2026 o 14:09 UTC skončil odpoveďou HTTP 403 na prvom dopyte. Vznikol len prázdny pracovný priečinok, ktorý bol odstránený; archivovaná snímka a odvodené výsledky sa nemenili. Cache pôvod a jej vek preto zostávajú explicitným obmedzením tohto experimentu.

## Algoritmus, jednotky a predpoklady

Každý prijatý OMM záznam inicializuje `sgp4` s gravitačnými konštantami WGS72 pre GP; `SatrecArray` vypočíta TEME polohy. `astropy` prevedie TEME→ITRS s vypnutým sieťovým sťahovaním EOP a s hashovanou lokálnou tabuľkou IERS. WGS84 poloha stanice sa zmení na ITRS. Z vektora satelit mínus stanica sa počíta topocentrická elevácia, azimut a priama vzdialenosť. Použité verzie: `sgp4 2.27`, `astropy 7.1.1`, `astropy_iers_data 0.2026.10.19.0.52.1`, `erfa 2.0.1.5`, `numpy 1.26.4`; odtlačok EOP tabuľky je `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`. Presné verzie a zdrojové hashe sú tiež vo výstupných metadátach.

V **každej** vzorke sa ako kandidáti počítajú vekovo prípustné objekty s eleváciou nad geometrickým horizontom a aspoň 10°. Vybraný je najvyššie položený podľa *nezaokrúhlenej* elevácie; pri zhode rozhodne menšie číselné katalógové ID. Výber sa nanovo prepočíta v každej vzorke, nejde o realizovaný handover. Ak nie je kandidát, ID, parametre a `r/c` sú prázdne. `r/c` je šikmá vzdialenosť delená `299 792,458 km/s`: **jednosmerný čas vo vákuu pre úsek stanica→daný objekt**, nie RTT, gateway či celá satelitná cesta.

CSV má 39 riadkov (13 časov × 3 skupiny). Čas je UTC a sekundy od počiatku, elevácia/azimut v stupňoch, vzdialenosť v km, `r/c` v ms a vek epochy v hodinách. Uvádza vekovo prípustný počet, počet kandidátov nad prahom, vybrané ID/názov, eleváciu/azimut/vzdialenosť/`r/c`, epochu a SHA-256 konkrétneho OMM záznamu. Metadáta majú SHA-256 CSV, kódu, manifestu, gzip aj surového vstupu pre každú skupinu a EOP súboru. Vzorka môže skryť prechod cez prah medzi dvoma časmi; nie je garanciou spojitej viditeľnosti.

## Reprodukcia a skúšky

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/multi_constellation_geometry.py \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --at 2026-10-22T12:45:00Z --lat 48.1486 --lon 17.1077 \
  --height-m 0 --duration-s 360 --step-s 30 \
  --min-elevation-deg 10 --max-age-h 48 \
  --output-csv data/derived/multi-constellation/bratislava-20261022T124500Z.csv
.venv/bin/python tools/check_multi_constellation_geometry.py
```

Kontrola vykoná dva nezávislé výpočty a porovná CSV aj JSON **bajt po bajte** s archivovanými výstupmi; tri počiatočné vzorky Iridium 43253 porovná s oddelene vytvoreným [jednoobjektovým výpočtom](../../data/derived/orbit-geometry/iridium-43253-bratislava-20261022.csv) vrátane elevácie, azimutu, vzdialenosti a odtlačku OMM. Úvodné počty `206 / 1 / 2` sa zhodujú aj so skôr uloženým Skyfield náhľadom v [geografickom míľniku](geografia-a-orbity.md). Negatívny test s limitom veku 1 h odmietne celý archív ešte pred vytvorením výstupu; samostatný test poškodí bajt gzip archívu a očakáva chybu SHA-256. Všetky testy prešli; odtlačok finálneho CSV je `ea0af7d113bb40b4a96e8adf0bcf5f49799aad934996a9555b56a0cd7054b278`.

| Čas od začiatku | Skupina | Kandidáti ≥10° | Vybrané ID | Elevácia | Vzdialenosť | Jediný `r/c` úsek |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 s | Starlink | 206 | 64434 | 78,930919° | 491,049666 km | 1,637965377 ms |
| 0 s | Iridium NEXT | 1 | 43253 | 29,436714° | 1 389,928028 km | 4,636300850 ms |
| 0 s | Globalstar | 2 | 37190 | 26,339695° | 2 470,515034 km | 8,240751119 ms |
| 150 s | Starlink | 199 | 52134 | 83,650662° | 470,151995 km | 1,568258249 ms |
| 150 s | Iridium NEXT | 2 | 43258 | 17,815867° | 1 840,466313 km | 6,139134804 ms |
| 150 s | Globalstar | 2 | 37190 | 27,596933° | 2 411,382043 km | 8,043504692 ms |
| 360 s | Starlink | 193 | 48301 | 75,775783° | 475,968384 km | 1,587659633 ms |
| 360 s | Iridium NEXT | 1 | 43258 | 75,026623° | 808,060721 km | 2,695400434 ms |
| 360 s | Globalstar | 2 | 37190 | 18,788162° | 2 870,451155 km | 9,574794423 ms |

**Interpretácia:** V geometrii sa mení počet objektov nad zvoleným prahom aj objekt s najvyššou eleváciou. Nie je z toho možné odvodiť operátorský attach, aktívny lúč, skutočnú frekvenciu, typ terminálu, komerčné pokrytie, satelitné medzispoje, gateway, RF budget ani doručenie paketu. V tejto úlohe nebol žiadny výstup pripojený k sieťovej simulácii. Ďalší krok je oddelená validačná brána pre konkrétnu službu a úplnú cestu; až po nej možno z geometrického výberu vytvoriť podmienky paketového experimentu.
