# Geometrická brána jednej družice Iridium NEXT — pracovný pilot

## Hypotéza a význam scenára

Pre pevnú polohu RSU v Bratislave s **osobitným hypotetickým satelitným používateľským terminálom** sa geometrická priama viditeľnosť jednej archivovanej družice Iridium NEXT mení s časom. Keď elevácia klesne pod vopred zvolených 10°, geometrická brána ju zamietne; keď klesne pod 0°, priama dráha prechádza Zemou a nesmie mať vypočítané použiteľné jednosmerné rádiové oneskorenie. Kontrolným variantom sú vzorky z tej istej dráhy a polohy nad 10° na začiatku intervalu. Toto je iba predvýpočet vstupu pre budúcu paketovú skúšku, nie model prevádzkovej služby Iridium.

## Zdroj a presná konfigurácia

- Uložený GP/OMM snapshot: `data/orbits/20261022T124815Z-retlector/`, poskytovateľ cache **ReTLEctor**, deklarovaný pôvod **CelesTrak GP**. Skupina `iridium-NEXT`, NORAD katalógové ID **43253**, názov v zdroji **IRIDIUM 145**. Snímka obsahuje sledované objekty skupiny, nie potvrdený zoznam aktívnych satelitov.
- Epocha vybraných elementov: **2026-10-21 02:59:35,421792 UTC**. Pri prvom kroku 2026-10-22 12:45 UTC majú **33,756827 h**, pri poslednom 33,856827 h. Skript odmieta interval, v ktorom vek elementov prekročí 48 h. Snapshot bol získaný **2026-10-22 12:49:43,719531 UTC**, teda po začiatku modelovaného intervalu: ide o **retrospektívne prehratie**, nie dôkaz, že by boli elementy v čase 12:45 dostupné online.
- Stanica WGS84: **48,1486° N, 17,1077° E, 0 m**. Je to modelová kotva RSU+UT, nie overené umiestnenie skutočného terminálu alebo pokrytia. Začiatok **2026-10-22 12:45:00 UTC**, trvanie **360 s**, krok **30 s**, minimálna elevácia **10°**. Tento uhol je skúšobná geometrická hranica, nie zdokumentovaná prevádzková maska konkrétneho terminálu Iridium.
- Odtlačky: manifest SHA-256 `d28ad3618304780d3cd118e83e8e8a2e88c14d015fa022c3082ba7b2f624d826`, surová skupina SHA-256 `059f731d2f8d98e2d60cb43b2a1d4ae7b88e91cf2740dffd2b772a09a8b33388`, kanonický OMM záznam SHA-256 `a5b9bf888ecc4db479692ffac29fefa778dae1a52eeb1b5204b2ccee8c3c18d1`.

[CelesTrak opis GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php) uvádza implicitné `REF_FRAME=TEME`, `TIME_SYSTEM=UTC`, `MEAN_ELEMENT_THEORY=SGP4` pri JSON/CSV. Tieto hodnoty nie sú pri každom zázname vypísané. Zdroj aj jeho čas/odtlačky sú v sprievodnom metadátovom JSON.

## Algoritmus, výstupy a jednotky

`tools/orbit_geometry_gate.py` najprv overí SHA-256 archivovaných gzip a surových OMM dát a vyberie **presne jeden** objekt. SGP4 2.27 s konštantami WGS72 vypočíta polohu TEME pre každý okamih UTC. Astropy 7.1.1 prevedie TEME → ITRS a WGS84 stanice → ECEF; následne rozloží vektor družica–stanica do lokálnych osí východ/sever/hore a vypočíta azimut, eleváciu a euklidovskú vzdialenosť. Tento postup nadväzuje na [metódu Astropy pre družice](https://docs.astropy.org/en/stable/coordinates/satellites.html) a na našu [nezávislú kontrolu transformácie](orbit-validation.md).

CSV `data/derived/orbit-geometry/iridium-43253-bratislava-20261022.csv` má jeden riadok na čas UTC. Čas je v ISO 8601 UTC s mikrosekundami, poloha stanice v stupňoch a metroch, elevácia/azimut v stupňoch, priama geometrická vzdialenosť v km, vek elementov v hodinách a parametre rotácie Zeme v sekundách/uhlovej sekunde. `above_geometric_horizon=1` znamená eleváciu >0°, `passes_minimum_elevation=1` znamená navyše eleváciu ≥10°. Vzorka pod horizontom si ponecháva **čisto geometrickú vzdialenosť** pre audit, ale `one_way_vacuum_delay_ms_if_los` je prázdne. Nad horizontom je táto hodnota **len** `vzdialenosť / c` v milisekundách, kde presne `c = 299 792,458 km/s` podľa [definície SI od BIPM](https://www.bipm.org/en/si-base-units/metre). Neobsahuje atmosféru, modem, MAC, spracovanie, frontu, gateway ani spiatočnú cestu. Šesť desatinných miest CSV je formát zápisu, nie tvrdenie o milimetrovej fyzikálnej presnosti.

Súbor `data/derived/orbit-geometry/iridium-43253-bratislava-20261022.metadata.json` uchováva parametre, vek, všetky vstupné SHA-256, verzie knižníc, SHA-256 samotného CSV a generátora, ako aj počty stavov. Zabalená tabuľka orientácie Zeme `finals2000A.all` z `astropy-iers-data 0.2026.10.19.0.52.1` má SHA-256 `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`. V celom intervale bol jej status **IERS-A predikcia (2)**, nie finálne meranie. Sieťové sťahovanie EOP je pri behu vypnuté.

## Meranie a kontrolné body

| UTC 22. 10. 2026 | Offset | Elevácia | Priama vzdialenosť | Vákuové oneskorenie jedného úseku | Stav pri 10° |
| --- | ---: | ---: | ---: | ---: | --- |
| 12:45:00 | 0 s | +29,436714° | 1 389,928028 km | 4,636301 ms | prijaté geometriou |
| 12:47:30 | 150 s | +10,265132° | 2 322,058929 km | 7,745555 ms | prijaté geometriou |
| 12:48:00 | 180 s | +7,757501° | 2 517,894182 km | 8,398791 ms | nad horizontom, pod zvolenou maskou |
| 12:50:00 | 300 s | −0,352559° | 3 309,553412 km | prázdne | pod horizontom, zamietnuté |
| 12:51:00 | 360 s | −3,680353° | 3 706,311704 km | prázdne | pod horizontom, zamietnuté |

Z **13** vzoriek je **6** nad skúšobnou hranicou 10°, ďalšie **4** medzi 0° a 10° a **3** pod horizontom. Podhorizontálny bod je negatívna kontrola. Hranica medzi susednými 30 s vzorkami je iba intervalom, nie presne vypočítaným okamihom prechodu. CSV SHA-256 je `fb8c995cee050eb4697238bd5700c939e4c44059bc17a76697f59955b65db359`.

## Presná reprodukcia a skúšky

Na Ubuntu 24.04 / CPython 3.12 / x86_64 s pripraveným `.venv` podľa `requirements-orbits.txt` a `requirements-orbit-validation.txt`:

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/orbit_geometry_gate.py \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --group iridium-NEXT --catalog-id 43253 \
  --lat 48.1486 --lon 17.1077 --height-m 0 \
  --at 2026-10-22T12:45:00Z --duration-s 360 --step-s 30 \
  --min-elevation-deg 10 \
  --output-csv data/derived/orbit-geometry/iridium-43253-bratislava-20261022.csv
sha256sum data/derived/orbit-geometry/iridium-43253-bratislava-20261022.csv
```

Druhý beh do `results/orbits/` vytvoril **bitovo totožné CSV**. Automatická kontrola overila 13 presných 30 s krokov, SHA-256 CSV, 6 úspešných a 3 podhorizontálne vzorky, prázdne oneskorenie pod horizontom a výpočet `r/c` nad ním. Negatívny test s časom 24. 10. 2026 bol správne odmietnutý pre vek elementov >48 h. `py_compile` a `pip check` prešli.

## Obmedzenia a ďalší krok

Tento súbor **nepotvrdzuje**, že satelit 43253 vtedy niesol použiteľnú službu, že RSU má certifikovaný terminál, že mu patril lúč alebo brána, ani že by paket došiel. Nezahrňuje terén, atmosférickú refrakciu, link budget, zisk antén, tienenie vozidlom, Doppler, handover, ISL ani core sieť. Vek OMM približne 34 h a predikčné EOP limitujú polohovú vierohodnosť; publikovaný zdroj nedáva dôkaz o konkrétnom operátorovom plánovaní ani o okamžitej prevádzke objektu. Pred napojením na SNS-3 sa musí zvoliť konkrétny podporovaný terminál/služba, reálna cesta `vozidlo ↔ RSU ↔ UT ↔ satelit ↔ gateway` a linkové parametre. Záporná elevácia má byť tvrdá blokovacia podmienka; 10° je zatiaľ iba experimentálna hranica.
