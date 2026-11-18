# U9: migrácia paketovej cesty do jedného ns-3 procesu — stav 2. 11. 2026

## Prijímacie brány

1. CAM/RSU → SNS-3 LEO → brána → odpoveď v **jednom** procese ns-3.38; raw bajty, čas a príjemca musia prejsť checkerom.
2. Ten istý proces musí zachovať pozemné tienenie a satelitný výhľad. Osobitne overiť LOS aj NLOS a satelit viditeľný aj zakrytý. Geometrický preflight nie je náhradou negatívneho paketového behu.
3. Spustiť a overiť natívny generický DVB paketový beh osobitne pre Starlink, Iridium NEXT a Globalstar. Názov konštelácie určuje orbitálne/topologické vstupy; výsledok nie je modem ani služba operátora.
4. Až potom presmerovať U9 editor, replay a ostatné režimy. Starý servisný model nesmie automaticky nahradiť neúspešný natívny prenos.

**Migrácia je dokončená podľa štyroch prijímacích brán uvedených nižšie.** Nové U9 scenáre so satelitnou vetvou zapisujú schému výsledku 7 a prijmú iba jeden natívny ns-3.38/SNS-3 3.38 paketový proces. Historické výsledky schémy 6 zostávajú čitateľné, ale nevydávajú sa za natívny prenos. Obmedzenia výberu topológie a vernosti sú uvedené na konci dokumentu.

## Brána 1: čerstvý natívny dôkaz — PASS

Nový pozemný vstup `config/u9-native-stage1-ground.json` používa 24 áut, 31 RSU, syntetické trasy a 20 vzoriek po 100 ms. V kópiách sveta a dopytu v `data/inputs/u9/native-stage1-*.json` je odstránená dnes vyradená voľba priameho terminálu auta; pôvodné dáta zostali zachované. Izolovaný beh `results/u9_native_migration_ground_b_20261102` prešiel `u9_check_ground.verify`: 177 CAM TX, 9 558 CAM RX.

Nový vstup `config/u9-native-stage1-u3.json` pripína tento baseline a štyri archivované objekty Iridium NEXT; `config/u9-native-stage1-u4.json` pripína U3 konfiguráciu. `run_u9_full_per_rsu.run` spustil `src/u9-full-integration-per-rsu.cc` ako **jeden** proces s OCB/Vanetza CAM, RSU reportom, vlastným UT každej RSU, SNS-3 DVB/ISL/IP/UDP a návratom. Experimentálny runner vyžaduje aj tri priame automobilové terminály; táto vetva nie je súčasťou aktuálneho editora a nemá sa tam vrátiť bez osobitného rozhodnutia.

`results/u9_native_migration_stage1_b_20261102` má manifest SHA-256 `667e319a5e42cc13cbf95da518b74f4fda4c1b07607f9a0e5abdc1305211e903`. Nezávislé druhé volanie `run_u9_full_per_rsu.verify` vrátilo **PASS**: 177 vytvorených RSU reportov, 76 prijatých na bráne, 74 odpovedí v autách; tri priame terminály 9 ponúk, 9 prijatí na bráne, 9 návratov, 18 raw ISL záznamov. Checker rekonštruuje CAM → report → IP/UDP/ISL → odpoveď a kontroluje bajty, identitu, časové poradie a správneho príjemcu. Rozdiel 76/74 je pozorovaný výsledok tohto krátkeho okna, nie skrytá oprava doručenia. Generický DVB, diagnostická anténa a hypotetická brána nepredstavujú Iridium modem.

Reprodukcia z koreňa projektu (vždy nový výstupný adresár):

```bash
PYTHONPATH=tools .venv/bin/python -c 'from pathlib import Path; import run_u9_full_per_rsu as r; print(r.run(Path("config/u9-native-stage1-u4.json"), Path("results/NOVE_ID"), ["bg00", "bg01", "bg02"])["status"])'
PYTHONPATH=tools .venv/bin/python -c 'from pathlib import Path; import run_u9_full_per_rsu as r; print(r.verify(Path("results/NOVE_ID"))["status"])'
```

## Brána 2: tienenie a výhľad — PASS pre experimentálny profil

Izolovaný pozemný vstup `config/u9-native-stage2-ground.json` a budova `data/inputs/u9/native-stage2-building.json` prešli skutočným behom a `u9_check_ground.verify` v `results/u9_native_migration_stage2_ground_b_20261102`: 177 CAM TX, 8 317 CAM RX a 125 tienených vzoriek auto–RSU. Budova je syntetická; prvý návrh zasiahol polohu auta a simulátor ho správne odmietol (`V5_ERROR=radio station entered synthetic building`).

Chýbajúci natívny vstup budov a LOS stopa boli opravené v spoločnom procese. `results/u9_native_migration_stage2_native_b_20261102` prešiel raw verifierom: 177 vytvorených reportov, 76 prijatých bránou a 76 návratov do áut. Stará neúspešná kópia zostáva diagnostická. Pozemné budovy sa nepreberajú z iného procesu do prijatého výsledku.

SNS-3 3.38 neaplikoval minimálnu eleváciu pri príjme. Do `SatChannel::ScheduleRx` bol preto vložený nastaviteľný výškový filter a raw trace `EarthOccultationDrop`; patch je `patches/sns3-338-native-elevation-mask.patch`. `results/u9_native_migration_stage2_mask_positive_20261102` pri 0,5° maske prešiel: 76 prijatých reportov a 76 návratov. `results/u9_native_migration_stage2_mask_negative_20261102` pri kontrolnej 90° maske zachoval 177 pozemných CAM, 125 tienených vzoriek, 97 satelitných ponúk, 454 odmietnutých príjmov v SNS-3 kanáli a nulový príjem na bráne. Tento záporný test používa umelo vysokú masku; samostatný dôkaz satelitu skutočne pod zemským horizontom by bol ďalším testom. Obe kontroly sú v natívnom procese, nie v aplikačnom zahadzovaní.

## Brána 3: tri orbitálne vstupy a natívne pakety — PASS v uvedenom rozsahu

U4 runner bol rozšírený na kvalifikovaný `stay` prípad s jedinou družicou a nulovým ISL. Nezávislý checker v takom prípade vyžaduje nulové ISL stopy, kompletnú surovú cestu CAM/RSU/IP/UDP/GRA1/I2V1 a skutočné pripojenie brány v SNS-3. Výsledky:

| Orbitálny profil a topológia | Natívny raw výsledok |
| --- | --- |
| Iridium NEXT, 4 družice, ISL/handover | `results/u9_native_migration_stage1_b_20261102`: PASS; 76 reportov na bráne, 74 odpovedí v autách. |
| Starlink, 2 družice, ISL/handover | `results/u9_native_migration_stage3_starlink_isl_20261102`: PASS; 98 odoslaných reportov, 77 na bráne, 77 v autách, 175 kontrolovaných ISL hopov. |
| Globalstar, 1 družica, bez ISL | `results/u9_native_migration_stage3_globalstar_full_20261102`: PASS; 177 odoslaných reportov, 162 na bráne, 154 v autách, nulové ISL hopy. |

Starlink má aj jednosatelitnú kontrolu `results/u9_native_migration_stage3_starlink_solo_20261102` s PASS 175/175/175. Pokusy s dvojicou, kde deklarovaný feeder nezodpovedal skutočnému pripojeniu brány SNS-3, zostávajú zamietnuté v `results/u9_native_migration_stage3_starlink_20261102`, `..._feeder0_20261102`, `..._gw_sat1_20261102` a `..._reordered_20261102`. Nejde o dôkaz úspešného ISL. Každý prijatý profil používa iba generický DVB paketový model a archivované orbitálne vstupy; nejde o modem alebo dostupnosť operátora.

## Brána 4: editor, ostatné režimy a replay — PASS v overenom rozsahu

`tools/u9_native_editor.py` pripravuje pohyb SUMO bez oddeleného pozemného ns-3 behu. `tools/bp_u9.py` pre nové satelitné scenáre spúšťa jeden proces `src/u9-full-integration-per-rsu.cc`, ktorý obsahuje OCB CAM, RSU aplikáciu, samostatný UT každej RSU a skutočné SNS-3 IP/UDP/DVB/ISL pakety. Schéma 7 vyžaduje nezávislý `tools/u9_check_native_editor.py`: kontroluje odtlačok binárky/knižnice, pripnutý OMM vstup, raw PCAP, PacketTrace v oboch smeroch, CAM/ICB1/GRA1/I2V1 bajty, príjemcu a časovú následnosť. Natívny výsledok explicitne odmieta adresár `service-model`. Pri neúspechu sa nespustí servisná náhrada.

Tri celé editorové behy s rovnakými piatimi autami a tromi RSU prešli samostatným volaním `bp_u9.py verify`:

| Konštelácia | Výsledok schémy 7 | CAM / brána / návrat |
| --- | --- | --- |
| Starlink | `results/u9_runs/native-editor-gate4-20261102` | 93 / 91 / 91 |
| Iridium NEXT | `results/u9_runs/native-editor-iridium-gate4-20261102` | 93 / 91 / 91 |
| Globalstar | `results/u9_runs/native-editor-globalstar-gate4-20261102` | 93 / 91 / 91 |

Explicitná dvojdružicová topológia Starlink s ISL/handoverom prešla v `results/u9_runs/native-editor-starlink-isl-20261102`: 93 vytvorených reportov, 78 satelitných ponúk, 76 návratov a surové ISL bajty. Tým je doložené, že editorový backend zvládne aj viac než jednu družicu, keď je topológia zadaná a overená.

`results/u9_runs/native-editor-30s-20261102` po samostatnom verifieri prešiel s 443 CAM, 440 reportmi na bráne a 440 návratmi. `u9_editor_api.replay` ukázal 30 s, satelitné polohy aj na konci 30 s a 1 990 paketových spojníc. `results/u9_runs/native-editor-osm-gate4-20261102` overil spoločnú budovu: `building_los.csv` obsahuje 180 tienených a 720 voľných dvojíc auto–RSU; vzniklo 55 reportov oproti 93 bez budovy a všetkých 55 dorazilo cez natívne SNS-3. Pozemný režim bez satelitu zostáva natívny ns-3 ITS-G5; `results/u9_runs/native-migration-ground-only-20261102` prešiel s 880 vyslanými CAM a 3 853 prijatými CAM. Replay berie polohy, udalosti a raw paketové spojnice z výsledku natívneho behu, nie zo servisných udalostí. Fyzikálny audit schémy 7 teraz počíta ponuky, príjem brány a ACK z natívnej `trace.csv`; terminály zapnuté v SNS-3 sa už nezobrazujú ako vypnuté. Nulový explicitný počet strát neznamená nulovú stratu prenosu bez príčiny v raw stope.

Náhľad glóbusu už neukladá starý proxy podgraf do paketového scenára. Zobrazuje orbitálny katalóg; natívny výber prebehne pred spustením. Editorové technické parametre odlišujú SNS-3 od historického servisného modelu. Cesta `editor/check` → `editor/save` → `runs` bola overená aj cez HTTP API pracovného runtime: `results/u9_runs/20261102t014814z32ff0be5` prešiel natívnym verifierom s 93 CAM, 91 reportmi na bráne a 91 návratmi. Server generuje ID malými písmenami, ako vyžaduje identita natívneho procesu. Prvý API pokus `20261102T014715Zadef1493` s veľkými písmenami skončil pred paketovým prenosom; zostáva diagnostický.

### Presná hranica tvrdenia

Automatický výber aktuálne vyberie **jednu** družicu, ktorá udrží súčasný výhľad na všetky zapnuté RSU a modelovú bránu počas celého okna. Pripnutý archív môže mať tisíce družíc, ale neznamená to tisíce inštancií v paketovom behu. Ak taká družica neexistuje, beh sa odmietne. Explicitná pripojená viacdružicová topológia a ISL je podporovaná; automatické prepínanie každého RSU terminálu pri strate výhľadu ešte nie je implementované. To je **obmedzenie našej integrácie**, nie preukázaný limit samotného SNS-3. V súčasnom natívnom zdroji sa handover týka prvého terminálu.

SNS-3 poskytuje generický DVB satelitný kanál. Neimplementuje prevádzkové modemy, aktívne lúče, autentizáciu, plánovanie kapacity ani skutočné spojenie Starlink/Iridium NEXT/Globalstar. Zisk 17 dBi, vysielací výkon, ISL kapacita a modelové umiestnenie brány sú scenárové predpoklady. Verejná elevácia a zorný uhol sa používajú na výber a výškovú masku; montáž terminálu, smerovanie antény, Dopplerova tolerancia a jemný link budget z historického servisného modelu sa v tomto natívnom backend-e zatiaľ neuplatňujú. Sú to **aktuálne medzery integrácie/fyzikálneho modelu**; nesmú sa zamieňať za potvrdenú dostupnosť operátora ani za limit, ktorý SNS-3 nevyhnutne má. Výstup schémy 7 dokazuje skutočný prenos generických paketov v deklarovanej topológii.

Reprodukcia: `.venv/bin/python tools/bp_u9.py verify results/u9_runs/native-editor-globalstar-gate4-20261102` (analogicky ostatné adresáre). Pre nový beh použite `run config/u9-native-editor-gate4.json results/u9_runs/UNIKATNE_ID`; výsledok možno prijať až po opakovanom `verify`.

**Nadväzujúca etapa 2. 11. 2026:** [handover všetkých RSU a natívne RF podmienky](u9-native-rsu-handover-rf-2026-11-02.md) nahradili uvedený handover iba prvého UT a doplnili montáž/smerovanie, Dopplerovu toleranciu a miestne budovy priamo do SNS-3 user kanála. Zvyšné obmedzenia vrátane automatickej voľby jedinej družice a neznámeho operátorského modemu sú v nadväzujúcom zázname. Historický text vyššie zachytáva stav pred touto etapou.

Neúspešné priečinky `results/u9_native_migration_ground_20261102`, `results/u9_native_migration_stage2_ground_20261102` a čiastočný `results/u9_native_migration_stage2_native_20261102` sú ponechané na diagnostiku; nesmú sa citovať ako PASS.
