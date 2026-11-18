# Dve statické používateľské PHY cesty k rozdielnym LEO objektom

**Stav 22. 10. 2026 UTC: prešlo.** Cieľom je po [jedinej SAT0→ISL→SAT1 ceste](two-leo-isl-packet-reference.md) vytvoriť druhý fyzický používateľský spoj v tom istom ns-3.38/SNS-3 3.38 čase. Ide o **dva samostatné, rovnako umiestnené terminály** pri jednej hypotetickej RSU, nie o handover jedného terminálu. Satelitné rádiá sú generický DVB-S2/RCS2 model, nie Iridium Certus.

## Hypotéza a kontrola

Pri rovnakých archivovaných GP/OMM dráhach objektov 43253 a 43258, UTC počiatku, polohe terminálov a brány, anténnom predpoklade a semene má prvý 16 B UDP paket z UT0 prejsť cez user PHY SAT0, modelový ISL a feeder PHY SAT1. Druhý, odlišný 16 B paket z UT1 má použiť user PHY SAT1 a jeho feeder cestu. V kontrolnom variante sa odstráni **len** ISL hrana: prvý paket sa nemá dostať k bráne, druhý má zostať doručiteľný. Kontrola tak odlíši dve fyzické cesty od premenovania toho istého proxy kanála.

## Implementácia a vstupy

V pripnutom SNS-3 `SatHelper::CreateConstellationScenario` sa UT pri konštrukcii automaticky priraďuje k družici podľa `GetClosestSat(position)`. Pre rovnako umiestnené UT by preto oba vybrali ten istý satelit. Verzovaný [úzky patch](../../patches/sns3-338-static-ut-sat-id.patch) číta voliteľný `ut_sat_ids.txt` v adresári konštelácie, po jednom ID v poradí riadkov `ut_positions.txt`. V tomto pokuse obsahuje `0` a `1`; parser odmieta nesúlad počtu UT, nečíselné a neexistujúce ID. Pri chýbajúcom súbore ostáva pôvodné SNS-3 priraďovanie. Patch sa aplikuje na SNS-3 commit `739a10dbe1db02fd2c4064501e4a48994e0b79f3`; nejde o úpravu operátorského protokolu ani dynamický handover.

[`two-leo-isl-reference.cc`](../../src/two-leo-isl-reference.cc) v režime `--dualUt=1` vytvorí dva samostatné UDP sockety na dvoch UT user uzloch. Pakety sa líšia celým aplikačným identifikátorom `LEOGEO1`/`LEOGEO2` a koncovými bajtmi. Prvý sa odošle v 1 s, druhý v 2 s. [`run_two_leo_isl_reference.py`](../../tools/run_two_leo_isl_reference.py) pripína OMM archív, pre každý variant vytvára dvojicu identických súradníc `48,1486° N, 17,1077° E, 0 m`, jediný hypotetický bod GW `37,8167° N, 22,6667° E, 0 m`, archívne TLE rekonštruované z OMM a 17 dBi konštantnú anténnu mapu. Kladný a kontrolný vstup sa líšia iba `isls.txt`. Čas simulácie je štyri sekundy, seed 314159 a run 1.

`run-manifest.json` ukladá SHA-256 zdroja, patchu, binárnych vstupov a surových stôp. [`check_two_leo_dual_ut_reference.py`](../../tools/check_two_leo_dual_ut_reference.py) kontroluje zhodu týchto hashov, text topológie pre UT0/SAT0 a UT1/SAT1, celých 44 B IPv4/UDP paketov na ISL vrátane checksumov, obsah oboch prijatých paketov, časy a modelový `PacketTrace` pre každé ID. Vykoná aj jednobajtovú mutáciu, ktorá musí zlyhať na UDP checksume. Skyfield z rovnakého GP nezávisle kontroluje topocentrickú geometriu druhej user cesty; nezávislosť sa týka súradnicovej transformácie, nie zdrojovej orbity.

## Výsledok a interpretácia

`PrintTopology` v oboch behoch hlási dva UT **na tej istej polohe**: `UT 3 → SAT0/beam 30` a `UT 5 → SAT1/beam 30`. Každý je odlišný SNS-3 rádiový terminál. Pri kladnom behu sa prvý obsah `LEOGEO1` odoslal v **1,000000 s**, na prijímacom ISL zariadení SAT1 sa zachytil celý 44 B IPv4/UDP paket v **1,114815 s** a brána prijala identických 16 B v **1,126182 s**. Druhý obsah `LEOGEO2` sa odoslal z UT1 v **2,000000 s** a brána ho prijala v **2,106142 s**. `PacketTrace` priradil prvému skúšobnému paketu interné ID 18, potvrdil `UT3 PHY→SAT0 ND→SAT1 feeder PHY→GW ND`; druhému ID 53 a `UT5 PHY→SAT1 ND→SAT1 feeder PHY→GW ND`. Na ISL bol len prvý aplikačný paket, so správnym IPv4/UDP checksumom a bajtmi.

V párovanej kontrole bez ISL zostali oba UT aj oba ich satelitné user PHY, rovnaké vstupné polohy a aplikačné obsahy. SAT0 stále prijala paket prvého UT, no GW ho neprijala. Druhý paket z UT1 prešiel cez SAT1 user PHY a GW ho prijala v **2,113156 s**. Skóre sa zmenilo **2/2 → 1/2** presne podľa odstránenej hrany; druhá cesta zostala fyzicky aktívna. Skyfield vypočítal pri odoslaní druhého paketu eleváciu UT→SAT1 **13,7537°** a vzdialenosť **2 070,073 km**, nad experimentálnou 10° maskou. Geometriu SAT0→ISL→SAT1 checker znovu preveril zo spoločných OMM; nejde o nezávislé meranie družicovej polohy.

## Reprodukcia a surové výsledky

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
git -C /tmp/ns3-sns3-338-feasibility/contrib/satellite apply \
  '/home/ubuntu/Documents/ChatGPT/Bakalarska praca/patches/sns3-338-static-ut-sat-id.patch'
ninja -C /tmp/ns3-sns3-338-feasibility/cmake-cache -j2 libns3.38-satellite-debug.so
.venv/bin/python tools/run_two_leo_isl_reference.py \
  /tmp/ns3-sns3-338-feasibility results/two_leo_static_ut_repeat --dual-ut
.venv/bin/python tools/check_two_leo_dual_ut_reference.py results/two_leo_static_ut_repeat
```

Patch aplikuj **iba raz** na čistý pripnutý SNS-3 checkout; v aktuálnom pracovnom checkoute už aplikovaný je. Runner vyžaduje, aby skutočný `git diff` presne súhlasil s uloženým patchom; výstupný priečinok musí byť nový alebo prázdny. Overené surové stopy a manifest sú v ignorovanom `results/two_leo_static_ut_verified/`. Pôvodný jedno-UT runner a checker sa po tejto úprave znova spustili a prešli s výsledkom 1/1 s ISL a 0/1 bez ISL. Aj úplný [SUMO→CAM→RSU→ICB1→dve LEO družice](two-leo-isl-icb1-e2e.md) scenár bez voliteľného súboru sa znovu spustil: checker v `results/two_leo_isl_icb1_static_patch_regression/` potvrdil **6** paketov na ISL, **6/6** GW v kladnom, **0/6** bez ISL a **0/6** pri blokovanom UT.

Prvý dual-UT pokus zlyhal pred paketovým behom: pôvodná diagnostická anténna mriežka sa pri SAT1 končila na 80° zemepisnej šírky a `GetBestBeamId` vrátil `NaN`. Zisk ani error model sa nenastavovali podľa výsledku. V samostatnom vstupnom anténnom adresári sa **konštantná výskumná mapa 17 dBi** rozšírila na zemepisné šírky −90 až +90°; následný beh vytvoril oba user PHY a doručil uvedené pakety. Prvé dva neúspešné štarty skončili tým istým `NaN`, druhý ich chybu vypísal do diagnostiky; nepočítajú sa ako paketové výsledky.

## Hranice

Tento scenár vytvára **dve rádiové zariadenia**, nie jeden UT meniaci družicu. Ani po úspechu ním nemožno dokázať attach, odovzdanie signalizácie, presun MAC stavu, frontov či IP smerovania jedného terminálu. Manually inserted ISL, všesmerová 17 dBi mapa, proxy GW a generický DVB model nie sú parametre Iridia. Ďalší krok je riadený prechod jedného logického RSU toku medzi týmito fyzickými cestami s potvrdením, jasnou politikou paketov počas výpadku a až potom výskumný single-radio handover, ak ho SNS-3 možno implementovať bez falošných operátorských tvrdení.
