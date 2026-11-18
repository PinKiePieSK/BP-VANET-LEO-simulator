# Hypotetická priama geometria auto–Iridium NEXT na syntetickej ceste

## Otázka a rozsah

Ak by auto na syntetickej ceste pri Bratislave **malo vhodný satelitný terminál**, ako by sa pri pohybe menila jeho geometrická elevácia, priama vzdialenosť a minimálne jednosmerné vákuové oneskorenie voči jednej archivovanej družici? Tento experiment vypočítava len polohu a priamu viditeľnosť. **Neimplementuje terminál na aute, anténu, Iridium službu, frekvenciu, výkon, link budget, protokol, beam, gateway ani pakety.** Preto nič v tomto CSV nedokazuje, že auto dokáže satelit osloviť.

Vstup je [georeferencovaná syntetická trasa](sumo-georeference.md), nie skutočná cesta alebo meraná premávka. Počas 60 s obsahuje 236 bodov (car0: 120, car1: 116) a 120 jedinečných okamihov UTC, pričom posledná vzorka je v 59,5 s. Každé auto má osobitnú geodetickú polohu pre svoj okamih. Šírka/dĺžka/výška sú WGS84; približne 0,03–0,04 m výšky vzniká lokálnym dotykovým prevodom a **nie je výškou antény na aute**. Rýchlosť z SUMO sa uchováva pre audit, ale výpočet používa polohu v každom časovom bode; nepočíta Doppler ani dynamiku vozidlového rádiového kanála.

## Zdroje, čas a algoritmus

- Georeferencovaný CSV SHA-256 `81ae33f307311b2e13c32837d409cb292852a54bfb44a7b2826f7ec8e6abdd33`; metadáta SHA-256 `a168fc53c1c8fede4d25798313e2394b0b8e74759a461adcc85be7663f673512`. Nástroj kontroluje oba a pri každom riadku overuje `UTC = 2026-10-22 12:45:00 + time_s`, rast času pre každé auto a intervaly WGS84.
- Archivovaná skupina GP/OMM `iridium-NEXT` zo snapshotu `20261022T124815Z-retlector`, objekt **IRIDIUM 145 / 43253**, epocha **2026-10-21 02:59:35,421792 UTC**. Manifest SHA-256 `d28ad3618304780d3cd118e83e8e8a2e88c14d015fa022c3082ba7b2f624d826`; kanonický OMM záznam SHA-256 `a5b9bf888ecc4db479692ffac29fefa778dae1a52eeb1b5204b2ccee8c3c18d1`. Vek elementov je **33,756827–33,773355 h**; nástroj odmieta body mimo okna 0–48 h. Snapshot bol získaný **22. 10. 2026 o 12:49:43,719531 UTC**, teda po modelovanom začiatku: ide o retrospektívne prehratie, nie online znalosť dráhy v čase 12:45.
- CelesTrak pre GP JSON opisuje implicitné `TEME`, `UTC` a `SGP4` v [dokumentácii formátu](https://celestrak.org/NORAD/documentation/gp-data-formats.php). `sgp4 2.27` s konštantami WGS72 propaguje vybraný záznam raz pre každý z 120 časov. `Astropy 7.1.1` vykoná TEME → ITRS a WGS84 → ECEF; lokálne osi východ/sever/hore dávajú eleváciu, azimut a priamu vzdialenosť. Postup transformácie vychádza z [dokumentácie Astropy pre družice](https://docs.astropy.org/en/stable/coordinates/satellites.html) a bol porovnaný s druhou knižnicou v [orbitálnej validácii](orbit-validation.md).
- Zabalená tabuľka orientácie Zeme `astropy-iers-data 0.2026.10.19.0.52.1` má SHA-256 `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`. Pri všetkých bodoch bol status EOP **IERS-A predikcia (2)**. Nástroj vypína sieťové sťahovanie EOP. Finálne hodnoty a skutočné dráhy neboli použité.

## Polia a jednotky

Výstup `data/derived/vehicle-orbit/bratislava-cars-iridium-43253-20261022.csv` obsahuje ID auta, `time_s` a UTC, jeho syntetické lokálne súradnice v **m**, rýchlosť v **m/s**, WGS84 šírku/dĺžku v **°** a výšku v **m**; potom ID/epochu družice, vek elementov v **h**, jej WGS84 polohu (**°, km**), eleváciu a azimut v **°**, priamu euklidovskú vzdialenosť v **km** a jednosmerné oneskorenie v **ms**. `above_geometric_horizon=1` znamená eleváciu >0°. `passes_experimental_mask=1` znamená navyše eleváciu ≥**10°**. Táto hranica je čisto skúšobná a nie je prevádzkovým parametrom Iridium. Pri elevácii ≤0° by pole `one_way_vacuum_delay_ms_if_los` ostalo prázdne; pri viditeľnosti je `r/c` s presnou SI hodnotou `c=299 792,458 km/s`. Ide iba o vákuové oneskorenie **jedného** geometrického úseku, nie o RTT ani doručenie správy. Zdroj hodnoty `c`: [BIPM](https://www.bipm.org/en/si-base-units/metre).

Sprievodný `...metadata.json` obsahuje SHA-256 vstupov, manifestu, OMM záznamu, EOP tabuľky, oboch použitých skriptov a výsledného CSV, verzie knižníc, časový rozsah a počty bodov. Výstupný CSV SHA-256 je **`44b8de3a819f3ef2739e0ab10cb4f0515fe3a7ff0822bcf13fe99c436477a011`**. Desatinné miesta výstupu sú formát, nie tvrdenie o zodpovedajúcej fyzikálnej presnosti.

## Namerané body a kontroly

| Auto, UTC 22. 10. 2026 | Poloha auta WGS84 | Elevácia | Vzdialenosť | Vákuové oneskorenie |
| --- | --- | ---: | ---: | ---: |
| car0, 12:45:00 | 48,147910730° N; 17,098361426° E | 29,430586° | 1 390,110557 km | 4,636910 ms |
| car0, 12:45:59,5 | 48,148534071° N; 17,116892472° E | 19,987313° | 1 745,264144 km | 5,821575 ms |
| car1, 12:45:59,5 | 48,148580239° N; 17,116478696° E | 19,987322° | 1 745,263734 km | 5,821573 ms |

Všetkých **236/236** bodov vyšlo nad geometrickým horizontom aj nad skúšobnou maskou 10°. U car0 sa v zvolenom úseku elevácia pohybovala **19,987313°–29,430586°** a vzdialenosť **1 390,110557–1 745,264144 km**; u car1 **19,987322°–29,051843°** a **1 401,530839–1 745,263734 km**. Z tohto krátkeho úseku nemožno vyvodiť trvalé pokrytie. Pri štyroch kontrolných bodoch sa elevácia a vzdialenosť nezávisle prepočítali cez Skyfield na tom istom OMM; odchýlka elevácie bola najviac **0,000144°**, vzdialenosti **4,285 m**. Propagátor SGP4 a elementy sú v oboch cestách spoločné, takže nejde o nezávislé overenie skutočnej dráhy.

Samostatné testy pravidla viditeľnosti potvrdili, že pri elevácii −0,1° aj presne 0° je LoS nepravdivé a oneskorenie prázdne; pri 9,999° je skúšobná 10° maska zamietnutá, pri 10,000° prijatá. Tieto záporné body sú **testy algoritmu**, nie vzorky z 60-sekundovej trasy. Po zmene vstupného UTC, šírky na 91° a posune všetkých časov o tri dni (s konzistentne prepočítaným hashom testovacieho CSV) kontroly príslušne odmietli nekonzistentný čas, neplatnú WGS84 polohu a OMM starší než 48 h. Opakovaný celý beh vytvoril bitovo totožné CSV. `pip check` a `py_compile` prešli.

## Reprodukcia

Na Ubuntu 24.04 / CPython 3.12 / x86_64 s `.venv` podľa `requirements-orbits.txt` a `requirements-orbit-validation.txt`:

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/moving_vehicle_orbit_geometry.py \
  --waypoints-csv data/derived/georeference/bratislava-synthetic-road-20261022.csv \
  --waypoints-metadata data/derived/georeference/bratislava-synthetic-road-20261022.metadata.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --group iridium-NEXT --catalog-id 43253 --min-elevation-deg 10 \
  --output-csv data/derived/vehicle-orbit/bratislava-cars-iridium-43253-20261022.csv
sha256sum data/derived/vehicle-orbit/bratislava-cars-iridium-43253-20261022.csv
```

## Výklad a ďalší krok

Výstup je geograficky a časovo konzistentná **hypotetická geometria** auta a jednej družice v retrospektívnom syntetickom scenári. Bez špecifikovaného vozidlového satelitného terminálu, vhodnej služby, antény, link budgetu, terénu, tienenia karosériou, Dopplera, gateway a paketového protokolu nesmie byť premenený na tvrdenie o komunikácii auto–satelit. Pre prípadný budúci paketový model treba najprv vybrať podporovaný typ terminálu a službu Iridium, získať zdrojované parametre a otestovať celý úsek vrátane dôvodov zamietnutia. Tento experiment nevyužíva ani neopravuje historický SNS-3 satelitný pilot.
