# Pohybujúce sa autá a pevné RSU voči trom skupinám GP: geometrický experiment

## Hypotéza a reálny význam scenára

Hypotéza je úzka: pri tom istom UTC a tých istých archivovaných GP elementoch vytvorí poloha pohybujúceho sa auta mierne odlišnú eleváciu, vzdialenosť a počet geometrických kandidátov oproti pevnému RSU. Scenár predstavuje syntetickú cestu v lokálnych metroch, ukotvenú na WGS84 pri Bratislave, a dve autá zo SUMO. Pevné RSU je kontrolný variant. Priame **auto → satelit** by vo svete vyžadovalo vlastný vhodný terminál, anténu, výhľad a oprávnenie k službe; žiadna z týchto vecí tu nie je modelovaná. Výsledok preto nehovorí o rádiovom spojení, prevádzkovom pokrytí, doručení správy ani o konkrétnom mobilnom produkte Starlink, Iridium či Globalstar.

## Vstupy, pravidlá a algoritmus

Použité sú archivované georeferencované polohy `data/derived/georeference/bratislava-synthetic-road-20261022.csv` (SHA-256 `81ae33f307311b2e13c32837d409cb292852a54bfb44a7b2826f7ec8e6abdd33`), pôvodný pevný RSU rad `data/derived/multi-constellation/bratislava-20261022T124500Z.csv` (SHA-256 `ea0af7d113bb40b4a96e8adf0bcf5f49799aad934996a9555b56a0cd7054b278`) a GP snapshot `data/orbits/20261022T124815Z-retlector/manifest.json` (SHA-256 `d28ad3618304780d3cd118e83e8a2e88c14d015fa022c3082ba7b2f624d826`). Metadáta oboch CSV sa hashujú a kontrolujú. Snapshot je **retrospektívny**: začiatok hodnoteného úseku je `2026-10-22T12:45:00Z`, kým čas získania v manifeste je `12:49:43.719531Z`. Nešlo o elementy dostupné terminálu na začiatku úseku.

Zhodne s pôvodným RSU výpočtom sa ponechávajú iba elementy s epochou najneskôr na začiatku a vekom najviac 48 h **aj na konci pôvodného 360 s referenčného okna**. Tak vznikne pevná množina 10 627 objektov v skupine Starlink, 79 Iridium NEXT a 30 Globalstar. To sú objekty v sledovanej GP skupine, nie overený súpis aktívnej konštelácie. Každý element sa inicializuje cez `sgp4`/WGS72. Na každom čase s krokom **0,5 s** v úseku `[0,60] s` sa všetky prijaté elementy propagujú **raz**; vektorový prevod Astropy TEME→ITRS s lokálnou EOP tabuľkou potom slúži pre RSU a dostupné polohy oboch áut. Súradnice auta sa neinterpolujú: používa sa presne 236 uložených bodov (car0 120, car1 116; druhé auto začína v 2 s). Pri 60 s majú autá poslednú polohu v 59,5 s, preto je tam len RSU.

Topocentrická elevácia a azimut sú v stupňoch, priama vzdialenosť v kilometroch. Kandidát je objekt s eleváciou **>0° a ≥10°**. Hranica 10° je **experimentálna geometrická maska**, nie prah konkrétneho operátora alebo terminálu. Pri každom pozorovateľovi a čase sa vyberie kandidát s najvyššou nezaokrúhlenou eleváciou, pri zhode najnižšie číselné katalógové ID. Počet kandidátov ani vybrané ID nie sú prihlásenie, handover či dostupná kapacita. Pre vybraný objekt sa zapisuje len jednosmerný vákuový čas `r/c` v ms, kde `c = 299 792,458 km/s` podľa [definície metra BIPM](https://www.bipm.org/en/si-base-units/metre). Nezahŕňa atmosféru, modem, MAC, frontu, spracovanie, gateway ani spätnú cestu. Formát CSV na šesť desatinných miest nie je odhad fyzikálnej presnosti dráhy. Metóda GP/TEME a transformácia sú uvedené v [CelesTrak GP dokumentácii](https://celestrak.org/NORAD/documentation/gp-data-formats.php) a [Astropy návode pre družice](https://docs.astropy.org/en/stable/coordinates/satellites.html); hranice nezávislého overenia sú v [orbitálnej validácii](orbit-validation.md).

## Výsledok a interpretácia

CSV `data/derived/vehicle-orbit/bratislava-cars-rsu-three-groups-20261022.csv` má **1 071 riadkov**: v každej skupine 121 RSU, 120 car0 a 116 car1. SHA-256 výstupu je `d5623466356f935abfc651cd41e0d9ff1118a67ce4aebf97081c43af6f8fe5ed`. Metadáta obsahujú presné verzie (`sgp4 2.27`, `Astropy 7.1.1`, `numpy 1.26.4`), hash EOP `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`, skupinové hashe OMM, čas získania, pravidlo výberu a negatívne vzorky.

| Polia CSV | Jednotky a význam |
| --- | --- |
| `utc`, `elapsed_s`, `group`, `observer_id` | ISO 8601 UTC, sekundy od začiatku, zdrojová GP skupina, `rsu`/`car0`/`car1` |
| `observer_latitude_deg`, `observer_longitude_deg`, `observer_height_m` | WGS84 stupne a metre; uložené polohy automobilov alebo pevné RSU |
| `age_eligible_objects`, `geometric_candidates_above_experimental_mask`, `negative_elevation_objects` | počty GP elementov po vekovom filtri, nad 10° a pod 0° |
| `selected_catalog_id`, `selected_object_name`, `selected_omm_record_sha256`, `selected_element_epoch_utc` | identita a pôvod najvyššieho geometrického kandidáta; prázdne bez kandidáta |
| `selected_elevation_deg`, `selected_azimuth_deg`, `selected_range_km`, `selected_one_way_vacuum_ms` | stupne, stupne, kilometre a ms jednosmerného vákuového `r/c`; prázdne bez kandidáta |

| Skupina | Počet kandidátov RSU v 0,5 s vzorkách | Vybraný objekt | Rozsah elevácie car0 | Rozsah elevácie car1 |
| --- | ---: | --- | ---: | ---: |
| Starlink GP skupina | 202–211 | `64434`, potom `49762` | 68,050957°–84,811609° | 68,048661°–84,807046° |
| Iridium NEXT GP skupina | 1 | `43253` | 19,987313°–29,430586° | 19,987322°–29,051843° |
| Globalstar GP skupina | 2 | `37190` | 26,352800°–27,746117° | 26,417532°–27,746600° |

Vybrané ID sa medzi autom a RSU v týchto 60 s vzorkách nelíši. Starlink GP počet kandidátov sa medzi autom a RSU líši najviac o jeden objekt; pri ďalších dvoch skupinách je v tomto úseku rovnaký. Ide o výsledok tejto syntetickej trasy a daného času, nie všeobecný záver o sieti. Ani 0,5 s vzorkovanie nedokazuje nepretržitú viditeľnosť medzi vzorkami.

## Testy a denník behov

Príkazy z koreňa projektu:

```bash
OPENBLAS_NUM_THREADS=1 /usr/bin/time -v \
  -o results/orbits/moving-three-groups-20261022-singlethread.profile.txt \
  .venv/bin/python tools/moving_multi_constellation_geometry.py \
  --waypoints-csv data/derived/georeference/bratislava-synthetic-road-20261022.csv \
  --waypoints-metadata data/derived/georeference/bratislava-synthetic-road-20261022.metadata.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --reference-csv data/derived/multi-constellation/bratislava-20261022T124500Z.csv \
  --reference-metadata data/derived/multi-constellation/bratislava-20261022T124500Z.metadata.json \
  --output-csv data/derived/vehicle-orbit/bratislava-cars-rsu-three-groups-20261022.csv
OPENBLAS_NUM_THREADS=1 .venv/bin/python tools/check_moving_multi_constellation_geometry.py
```

Skutočný profil odporúčaného behu s jedným BLAS vláknom je v [uloženom logu](logs/moving-three-groups-20261022-singlethread.profile.txt): **4,03 s** wall, **192 440 KiB RSS**, bez major page fault, návratový kód 0. [Profil bez obmedzenia BLAS vlákien](logs/moving-three-groups-20261022.profile.txt) mal pri opakovaní 4,08 s wall, 192 456 KiB RSS, ale vyšší súčet CPU času; prvý beh mal 5,47 s wall a 192 360 KiB RSS. Obmedzenie na jedno BLAS vlákno je preto primerané pri súbežnej práci na 4-vCPU VM a nezmenilo CSV hash. Nebol potrebný redší raster; výpočtová pamäť je výrazne pod 8 GB VM. Profil nie je deterministický benchmark zariadenia, preto jeho čas nie je kritérium zhody výsledkov.

Kontrolný RSU výsledok v čase 0/30/60 s sa pre všetky tri skupiny **presne** zhoduje s predchádzajúcim archivovaným CSV v počte, vybranom ID, elevácii, azimute, vzdialenosti a `r/c`. Všetkých **236** automobilových hodnôt Iridium `43253` sa číselne v zápise zhoduje s predchádzajúcou jednoobjektovou sondou. Test `tools/check_moving_multi_constellation_geometry.py` znovu zostaví identický CSV v pamäti, overí zdrojové hashe, počty a tieto krížové kontroly. Test hraníc potvrdzuje `−0,1°` a `0°` bez LoS, `9,999999°` pod maskou, `10,000000°` nad maskou. V reálnych hodnotených objektoch je negatívnym príkladom Iridium NEXT `41917` voči RSU pri `t=0`: elevácia `−30,192157°`, a teda bez kandidátskeho spojenia. Záporné príklady sú v metadátach aj pre ďalšie dve skupiny. Posledný test vrátil `PASS` a rovnaký SHA-256 výstupu; `py_compile` a `pip check` tiež prešli. Žiadny neúspešný beh tohto výpočtu nenastal; negatívne testy sú plánované zamietnutia geometrických podmienok, nie zlyhania simulátora.

## Obmedzenie pre prácu

Toto je výpočet geometrických možností hypotetického priameho terminálu na aute. Syntetická cesta nemá reliéf, výškové prekážky, zatienenie karosériou, polohu antény, konštrukciu terminálu ani jeho podporu pre jednotlivých operátorov. Skript nevyberá aktívny lúč a nezachytáva RF, MAC, sieťové pakety, medzisatelitné spojenie ani E2E oneskorenie. Ak sa tento scenár stane paketovým experimentom, tieto vrstvy sa musia špecifikovať a overiť zvlášť; samotná geometria nepreukazuje službu.
