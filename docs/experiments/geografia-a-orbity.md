# Geografia a aktuálne orbitálne elementy — pracovný míľnik (22. 10. 2026)

## Účel a oddelenie modelov

Tento míľnik plní prvý krok časti A v [hĺbkovej analýze](../hlbkova-analyza-komunikacie.md): zviditeľniť skutočné pozície uzlov v referenčnom SNS-3 behu, auditovať jeho geometriu a uložiť časovo blízke verejné orbitálne elementy troch skupín. Ide o **dva odlišné výpočty**. SNS-3 paketový scenár stále používa dve historické testovacie družice a DVB model; snímka Starlink/Iridium NEXT/Globalstar poháňa iba samostatný geometrický náhľad. Orbitálna viditeľnosť zo snímky zatiaľ neriadi paketové linky, rádiové chyby, handover ani brány.

## Referenčný paketový scenár: geografický audit

`src/vanet-sns3.cc` zapisuje `ground-positions.csv`: geodetickú polohu skutočného vybraného UT a všetkých brán SNS-3 spolu s ID uzla použitým v paketovej stope. `tools/geo_audit.py` prenesie lokálne súradnice SUMO `x` východ, `y` sever (m) na guľu SNS-3 s polomerom 6 378 137 m, s UT ako kotvou. Vypočíta eleváciu a šikmú vzdialenosť stanica–družica a najmenšiu vzdialenosť medzisatelitnej úsečky od zemského povrchu. Audit porovná identifikátory a horizont pre **každú doručenú** overenú fyzickú trasu `UT → SAT → [ISL] → SAT → GW`; pri rozpore beh odmietne. Začiatok v UTC berie z pevného `start_date.txt` a kontroluje jeho odstup od epochy historických TLE.

Vstupy: `scenario.json`, `sumo/waypoints.csv`, `run/ground-positions.csv`, `run/satellite-positions.csv`, `run/verification.json` a päť súborov referenčného scenára SNS-3. Výstupy: `run/ground-stations.csv`, `vehicle-geodetic.csv`, `visibility.csv`, `isl-geometry.csv`, `path-geometry.json`, `geography.json`, všetko v priečinku konkrétneho behu. Súradnice sú v stupňoch, výšky/vzdialenosti v metroch, elevácia v stupňoch a čas v sekundách od uloženého začiatku UTC. Pravidlo `elevácia > 0°` je iba geometrický horizont; **nie** servisná elevácia ani potvrdenie lúča. V tomto audite sa používa sféra SNS-3, zatiaľ čo nová orbitálna snímka nižšie používa WGS84. Prevody preto nie sú zameniteľné.

Tri integračné pokusy ostávajú ako neúspešné behy: `results/visual_runs/20261022T130000Zgeoaudit/` narazil na chybný parser názvového riadku TLE; `results/visual_runs/20261022T130500Zgeo2/` odhalil nesúlad medzi interným ID brány a ID uzla v `PacketTrace.log`. Po oprave mapovania `20261022T131500Zgeo3/` odhalil dôležitejší problém pôvodného scenára: všetkých osem doručených trás skončilo na bráne GW3 pri elevácii družice približne **−0,48° až −0,52°**, teda pod vypočítaným geometrickým horizontom. UT–SAT a ISL boli geometricky priechodné. Paketové stopy sa vytvorili, no reprodukčný reťazec sa správne zastavil pred označením behu za geograficky overený. Ide o nesúlad medzi paketovým doručením v testovacom scenári a nezávislou sférickou kontrolou; príčinu v internom modeli SNS-3 sme zatiaľ neidentifikovali.

Variant `data/scenarios/sns3-reference-geo/` je úplná miestna kópia pevne pripnutého dvojdružicového scenára SNS-3; jediný numerický vstupný rozdiel je posun druhej brány z `(15,93° N, 96,54° E)` na `(16,00° N, 100,00° E)`. Predbežný výpočet podľa historických vzoriek dáva pri prenose približne +2,5° elevácie satelitu 0. `tools/scenario_run.py` kopíruje tento variant do dát SNS-3 a pred behom overí úplnú zhodu súborov aj odkazu na anténny vzor. Originál v `vendor/` nemeníme; zmena je viditeľná, verzovaná a hashovaná ako vstup. Táto poloha je **syntetická opravná voľba**, nie skutočná komerčná brána. Po oprave treba pracovať až s behom, ktorý má `reproduce-command.txt` a úspešnú `geography.json`.

**Úspešný variant:** `results/visual_runs/20261022T133000Zgeo4/` prešiel koncovým overovačom, geografickým auditom a tvorbou prehrávania (`COMPLETE`, bez `failed.txt`). Pri seede 42/run 1, 60 s, bolo doručených V2V 50/50, V2I 8/25 a cez satelitný úsek 8/25 aplikačných správ. Osem paketových trás má skutočné PHY udalosti `UT4 → SAT1 → SAT0 → GW3`; všetkých osem vyhovelo geometrickému testu. Elevácia UT–SAT bola 5,676° až 5,986°, feeder SAT–GW 2,494° až 2,496° a minimálna rezerva ISL nad sférickou Zemou 341 425 až 341 489 m. Priemerné jednosmerné oneskorenie vzdialeného toku bolo 116,871 ms, jitter podľa zvolenej definície 0,804 ms a päťsekundová dostupnosť 0,4. Pozemný V2I dosah v tomto behu obmedzil počet vzdialených správ na rovnakých osem; 0,4 teda nie je dostupnosť LEO služby. Vstupných 20 SHA-256 odtlačkov sa po behu zhodovalo s aktuálnymi zdrojmi. Geometria >0° sama osebe ešte nedokazuje, že pozemná anténa a lúč obsluhujú uzol pri takto nízkej elevácii.

Bez prepisu uloženého behu zopakuj rovnaký vstup pod novým identifikátorom:

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
mkdir -p results/visual_runs/20261022T133000Zgeo5
cp results/visual_runs/20261022T133000Zgeo4/scenario.json \
   results/visual_runs/20261022T133000Zgeo5/scenario.json
python3 tools/scenario_run.py 20261022T133000Zgeo5
```

## Verejné GP/OMM elementy a propagácia

`tools/fetch_orbits.py` ukladá surovú odpoveď pre skupiny `starlink`, `iridium-NEXT`, `globalstar` ako deterministické gzip súbory a manifest s adresou zdroja, časom stiahnutia, časovým rozsahom epoch, počtom sledovaných objektov a SHA-256 surových i gzip bajtov. Dňa 22. 10. 2026 bola priamo zo servera CelesTrak prijatá skupina Starlink, ďalšia požiadavka však dostala HTTP 403. Skript nereaguje opakovanými pokusmi. Kompletná snímka preto pochádza z **nezávisle označenej cache ReTLEctor**, ktorá podľa svojho statusu uchováva CelesTrak dáta; pre Iridium NEXT a Globalstar vtedy hlásila stav `Stale`, približne 18 a 16 hodín od aktualizácie cache. Snímka je `data/orbits/20261022T124815Z-retlector/` a pozostáva z 11 121, 80 a 36 katalógových objektov v daných skupinách. To **nie je počet prevádzkovaných satelitov**. Jednotlivé elementy majú rôzny vek; pri výpočte sa každý starší ako 48 hodín zamietne. Skupiny aj ich stav je potrebné obnoviť pre neskoršie experimenty, s dodržaním [politiky CelesTrak](https://celestrak.org/usage-policy.php).

`tools/orbit_preview.py` overí oba SHA-256 odtlačky, načíta OMM, propaguje každý prijatý objekt SGP4 s WGS72 gravitačnými konštantami pre GP, prevedie geocentrický výsledok cez Skyfield na zemepisnú WGS84 polohu a pre zadanú WGS84 stanicu vypočíta eleváciu, azimut a šikmú vzdialenosť. Vstupmi sú snímka, UTC okamih, šírka/dĺžka/výška, trvanie, krok, minimálna elevácia a vekový limit elementov. Výstup JSON nesie každú vzorku s časom UTC, katalógovým ID, epochou elementu, polohou (°, km), eleváciou/azimutom (°), šikmou vzdialenosťou (km) a veľkosťou rýchlosti (km/s). Všetky výpočty sú geometrické. Použitá vstavaná časová škála Skyfield neťahá priebežne aktualizované parametre rotácie Zeme; pred kvantitatívnou analýzou pokrytia treba nezávislú kontrolu vybraných dráh, času a súradníc.

Pripnuté knižnice sú v `requirements-orbits.txt` s SHA-256 pre Ubuntu 24.04, CPython 3.12, x86_64. Príklad bez ďalšieho sieťového prenosu:

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-orbits.txt
.venv/bin/python tools/orbit_preview.py \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --at 2026-10-22T12:45:00Z --lat 48.1486 --lon 17.1077 \
  --duration-s 60 --step-s 10 --min-elevation-deg 10 \
  --output results/orbits/bratislava-20261022T124500Z.json
python3 tools/scenario_server.py --port 8765
```

V overenom príklade Bratislava, 12:45 UTC, prešlo filtrom veku 10 627 elementov Starlink, 79 Iridium NEXT a 30 Globalstar; vo vzorke `t=0` bolo nad **zvolenou** hranicou 10° 206, 1 a 2 objekty. Sú to iba počty geometricky viditeľných sledovaných objektov; nezaručujú službu, aktívny lúč, terminál, bránu, spoj satelit–satelit ani doručenie správy. Konkrétne `results/orbits/*.json` vznikajú z uložených vstupov a sú ignorované Gitom kvôli veľkosti; príkaz vyššie ich presne vytvorí znova.

Lokálny editor má oddelený formulár s výberom skupiny, WGS84 kotvou cesty a UTC začiatkom. Server spúšťa predvýpočet na pozadí a uložených 60 sekúnd možno prehrávať pri 0,25× až 8×. Počiatok nakreslenej cesty má zadanú geografickú kotvu, ale pohyb vozidiel sa v tomto orbitálnom režime zatiaľ **nepoužíva** na sieťový výpočet. Test cez UI potvrdil dokončenie predvýpočtu, zobrazenie počtu objektov a posun času pri prehrávaní.

## Ďalšie validačné brány

1. Dokončiť úspešný geografický audit historickej paketovej trasy a archivovať výsledok aj neúspešné pokusy.
2. Nezávisle porovnať vzorky súradníc/elevácie s iným propagátorom a overiť časovú škálu; až potom používať viditeľnosť ako kvantitatívny vstup.
3. Vybrať konkrétny terminál, službu, región, gateway a minimálnu eleváciu; iba pre taký profil prepojiť aktuálne orbity s paketovým modelom. Zaviesť podmienky lúča, link budget a dôvody nedoručenia.
4. Nahradiť diagnostické 300 B UDP payloady štandardnými správami a pridať overiteľný lokálny C-ITS zásobník podľa hĺbkovej analýzy.
