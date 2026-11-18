# U9: samostatné RSU terminály v jednom spoločnom čase

## Účel a hranica

Overiť, či spoločný proces ns-3.38/SNS-3 dokáže naraz prevádzkovať OCB/Vanetza CAM, jednu satelitnú LAN/UT na každú RSU, priame terminály vybraných áut, generickú DVB/ISL cestu a návrat I2V správnemu autu. Terminál RSU má vlastnú WGS84 polohu, IP adresu, používateľský uzol a SNS-3 UT. Auto bez explicitného výberu v `direct_cars` nemá priamy satelitný terminál.

## Reprodukcia a výsledky

Z koreňa projektu:

```bash
.venv/bin/python tools/bp_u9.py preflight config/u9-full-24cars-31rsu-4sat.json
.venv/bin/python tools/bp_u9.py run config/u9-full-24cars-31rsu-4sat.json results/u9_runs/NOVE_ID
.venv/bin/python tools/bp_u9.py verify results/u9_runs/NOVE_ID
```

Výstup musí dostať nové ID. Pripnuté raw behy:

| Beh | Uzly a vetvy | Paketový výsledok |
| --- | --- | --- |
| `results/u9_runs/u9_full_per_rsu_24cars_31rsu_20261028` | 24 áut, 31 RSU/UT, 4 orbitálne objekty, 3 priame autá | 182 RSU reportov, 78 prijatých na bráne a 78 vrátených autám; priame CAM 9/9 návratov. |
| `results/u9_runs/u9_full_per_rsu_52cars_verified_20261028` | 52 áut, 31 RSU/UT, 4 objekty, 3 priame autá | 290 RSU reportov, 122 prijatých na bráne, 116 vrátených autám; 6 satelitných ACK do konca okna nepozorovaných; priame CAM 11/11 návratov. |
| `results/u9_per_rsu_noisl_20261028` | 24 áut, 31 RSU/UT, 3 priame autá, 100 % ISL receive loss | 99 satelitných ponúk RSU, 9 priamych CAM, 0 vzdialených prijatí; 182 pozemných CAM pokračovalo, ten istý primárny UT sa vrátil po neúspešnom handovere. |

Natívny manifest pripína C++ zdroj, vstupy, binárku a raw súbory. Vonkajší manifest pripína runner, packetový checker, patch SNS-3, hash zostavenej satelitnej knižnice a geometrický audit. `tools/u9_check_u4_per_rsu.py` samostatne overuje identitu každého reportu/odpovede, raw bajty LAN/OCB/ISL, poradie skutočných hopov, trasu primárneho UT po handovere a príjemcu auta. Rozlišuje reporty na bráne od návratov a odpovede bez pozorovaného príjmu do konca okna. Mutácia vlastníka RSU terminálu v raw logu bola odmietnutá aj po prepočítaní SHA-256.

`tools/u9_full_geometry.py` kontroluje 25 bodov do 21,9 s pre všetky RSU, tri priame UT, bránu a všetky ISL hrany. Pri veľkom behu je minimum 9,25° pre RSU, 25,545° pre priame autá, 19,891° pre bránu a 482,981 km pre ISL rezervu nad Zemou. Kontrola je iba geometrická; aktívny beam, PHY úspech či servis operátora z nej nevyplýva.

## Zistená chyba SNS-3

Pred patchom `SatPhyRxCarrier::StartRx` ukončil proces pri druhom súbežnom príchode vyhradeného DA rámca. Pri 31 vlastných RSU UT to nastalo približne v čase 11,006 s, aj po časovom rozložení aplikačných reportov. Patch `patches/sns3-338-da-overlap-drop.patch` ponechá signál zaregistrovaný ako interferenciu a druhý rámec nedekóduje. Prvé dve neúspešné skúšky sú zachované v `results/u9_per_rsu_prototype_20261028` a `results/u9_per_rsu_staggered_20261028`; výsledky po patchi sa od nich nezamieňajú. Preflight `scripts/check_migration.py` kontroluje presný diff patchu na lokálnom SNS-3 3.38.

## Stále nepodporované

Handover vykonáva primárna RSU; ostatné RSU UT a priame autá zostávajú na prvom satelite. Priame auto UT má polohové vzorky, ale nulovú rýchlosť mobility triedy, takže Doppler a smerovanie antény nie sú modelované. Graf ISL je feeder-rooted strom a vstup používa archívne OMM/TLE, generický DVB/diagnostickú anténu a hypotetickú bránu. Aplikačná distribúcia informácie z brány na inú RSU a jej autá, servisná kalibrácia a offline U9 vydanie zostávajú otvorené. Čistý scenár bez RSU je odteraz podporený **oddeleným režimom `v2v_only`**, nie týmto spoločným satelitným behom. Úspechy 9/9 alebo 11/11 sú len výsledky týchto konkrétnych konfigurácií a semien.
