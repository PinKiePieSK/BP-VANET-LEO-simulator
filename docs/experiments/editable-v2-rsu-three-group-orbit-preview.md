# Geometrický náhľad troch archívnych skupín nad RSU editora v2

**Stav:** samostatný deterministický CLI predvýpočet overený 22. 10. 2026 UTC. Nepripája satelitnú sieť k editoru ani k pozemnému paketovému behu. Jeho cieľ je ukázať, že používateľom vytvorená a **výslovne WGS84 ukotvená** cesta môže dostať časovo zladený náhľad archívnej geometrie Starlink, Iridium NEXT a Globalstar pre každú RSU. Katalógový objekt nad maskou **nie je výber aktívneho operátorského satelitu, RF link, servisné pokrytie ani doručený paket**.

## Reprodukcia

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/editable_v2_rsu_orbit_preview.py \
  --scenario data/inputs/editable-road-v2/scenario.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --min-elevation-deg 10 \
  --output-csv results/editable_v2_rsu_orbit_preview/preview.csv
.venv/bin/python tools/test_editable_v2_rsu_orbit_preview.py -v
sha256sum results/editable_v2_rsu_orbit_preview/preview.csv
```

Výstup: `results/editable_v2_rsu_orbit_preview/preview.csv` SHA-256 `6d26e0266652d683626b022a17bcb287964ec35e172065f1fc3da2623a664aa4` a susedný `preview.metadata.json` SHA-256 `4a38e6c560fa0267c16e1904a963f4d04855217c5f6322b2ba3c457e8549d4dc`. Tri testy prešli: plný 36-riadkový regresný výsledok s pripnutým hashom a číslami, odmietnutie chýbajúcej/chybnej kotvy a zmena zemepisnej polohy po zmene kotvy. Na tejto VM beh trval približne **2,4 s**, maximum RSS **184 MB**; bez kompilácie alebo sieťového fetchu.

Vstupný `scenario.json` má SHA-256 `dbaa76dbfe6c369a4ec8316e6a804deb7c0661c1cead3683ac2e58dfbd62484d` a musí prejsť celou `editable_scenario_v2.validate`: schéma 2, `WGS84_ENU` s povinnou kotvou a UTC, čas dopravného kroku 0,5 s. Pilot berie šesť časov `t=20,0; 20,5; 21,0; 21,5; 22,0; 22,5 s` od `2026-10-22T12:45:00Z`, identických s [editable CAM pilotom](editable-v2-cam-radio.md). Každú z dvoch RSU (`rsu0`, `rsu1`) prevádza existujúcou [WGS84/ENU transformáciou](editable-v2-wgs84-enu-anchor.md). Je to **syntetická** cestná sieť posadená blízko Bratislavy; poloha ulice, výška terénu ani antén nie sú geodeticky overené. `rsu0` deklaruje `ip_backhaul`, `rsu1` `satellite_terminal`; **geometria sa zobrazuje pre obe** bez ohľadu na deklarovaný terminál, pretože deklarácia nevytvára skutočný hardvér ani službu.

Archívny manifest ReTLEctor/CelesTrak GP má SHA-256 `d28ad3618304780d3cd118e83e8e8a2e88c14d015fa022c3082ba7b2f624d826`. Snímka bola získaná `2026-10-22T12:49:43.719531Z`, teda po prehrávaných 12:45:20–22,5 UTC: ide o **retrospektívny náhľad**, nie v tom čase dostupnú predpoveď. [CelesTrak dokumentuje](https://celestrak.org/NORAD/documentation/gp-data-formats.php) význam GP/OMM a SGP4. Nástroj používa existujúci `checked_groups` z `multi_constellation_geometry.py`: kontroluje hash komprimovaných i surových OMM skupín, unikátne katalógové ID a maximálny vek elementu 48 h cez poslednú vzorku. Do výpočtu prijíma 10 627 z 11 121 záznamov Starlink, 79 z 80 Iridium NEXT, 30 z 36 Globalstar. Sú to *vekom oprávnené záznamy* v tejto snímke; počet neznamená počet zapnutých ani prenášajúcich družíc.

Na každom UTC okamihu sa každá skupina propaguje SGP4/WGS72 pomocou `SatrecArray`, rámec TEME sa prevedie na zemský ITRS cez Astropy 7.1.1 so zabudovanou IERS tabuľkou (SHA-256 `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`; sieťové sťahovanie EOP je vypnuté). Pre každú RSU sa WGS84 poloha prevedie na ECEF, rozdiel k objektu na lokálne ENU. Elevácia je `asin(up/r)`, azimut `atan2(east,north)` v stupňoch, `r` je šikmá vzdialenosť v km. Jednosmerný vákuový čas je `r/299792,458 km/s` v ms. Kandidát má `elevácia > 0°` **a zároveň** `≥ 10°`; 10° je výlučne **výskumná maska**. Zo spĺňajúcich objektov sa zapíše najvyššia nezaokrúhlená elevácia, pri rovnosti najmenšie numerické katalógové ID. Ak niet kandidáta, ID a geometrické polia zostanú prázdne. Výpočet je diskrétny; prechod medzi 0,5 s vzorkami sa neinterpoluje.

## Výsledok tohto konkrétneho archívu

| RSU | WGS84 odvodené z ENU | Počet kandidátov Starlink / Iridium NEXT / Globalstar pri t=20,0 s | Najvyššie ID pri t=20,0 s |
| --- | --- | --- | --- |
| `rsu0` | 48,148060323° N; 17,103533981° E; 0,007802 m | 204 / 1 / 2 | 64434 / 43253 / 37190 |
| `rsu1` | 48,148555027° N; 17,106490499° E; 0,000636 m | 204 / 1 / 2 | 64434 / 43253 / 37190 |

Všetkých šesť polsekundových vzoriek má pri `rsu0` počty Starlink **204, 204, 205, 205, 205, 205**; Iridium NEXT **1** a Globalstar **2** v každej vzorke. Vybrané ID zostávajú v tomto 2,5 s okne rovnaké. CSV zapisuje pre každý riadok presný UTC, katalógové ID, názov, eleváciu/azimut v °, vzdialenosť v km, jednosmerné `r/c` v ms, epochu a vek vybraného OMM záznamu a jeho SHA-256. Napríklad pri `rsu0`, t=20,0 s je najvyšší Starlink 64434 s epochou `2026-10-21T05:09:16.997184Z`, eleváciou 80,699556°, dosahom 488,814471 km a vákuovým `r/c=1,630509568 ms`; Iridium 43253 má eleváciu 25,861331° a Globalstar 37190 26,942994°. Tieto hodnoty **neobsahujú** gateway ani druhú komunikačnú vetvu, preto ich nemožno sčítať do end-to-end latencie bez ďalšej topológie.

`metadata.json` pinne SHA scenára, manifestu a každej skupiny, WGS84 súradnice RSU, UTC, verzie `sgp4=2.27`, `astropy=7.1.1`, `astropy-iers-data=0.2026.10.19.0.52.1`, masku, pravidlo výberu a SHA výsledku. Nebola vykonaná nezávislá validácia skutočnej orbity; ide o opätovné použitie [už overenej Astropy cesty](orbit-validation.md), ktorá zdieľa SGP4 jadro s ďalšími kontrolami.

## Hranica tvrdenia

Náhľad nepozná aktívny stav satelitov, operátorské beam/UT priradenie, skutočný terén a tienenie, anténny horizont/zisk, dopplerovský alebo atmosférický útlm, RF/MAC, gateway, ISL, paketový obsah, fronty ani servisné oprávnenie. Používateľova voľba Starlink/Iridium/Globalstar v budúcom UI smie zatiaľ zmeniť **iba zobrazenú skupinu geometrických kandidátov**. Pri Globalstar by paketová služba vyžadovala spoločnú viditeľnosť *toho istého* objektu z vhodnej reálnej gateway; tento náhľad počíta len RSU→objekt. Pri Starlink a Iridium z GP nemožno vyvodiť skutočnú ISL/gateway trasu. Dokumentovaný [operátorský fail-closed kontrakt](../decisions/operator-path-fidelity-contract.md) je oddelený krok pred akýmkoľvek servisným tvrdením.
