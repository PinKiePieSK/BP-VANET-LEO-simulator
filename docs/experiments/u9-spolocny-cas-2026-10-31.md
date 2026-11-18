# U9: jeden experimentálny čas pre dopravu, satelity a pakety

## Kontrakt

Nové scenáre editora majú `schema_version: 5`, `mode: unified` a `time_policy: warmup_then_full_duration`. Jediné používateľské pole **Dĺžka simulácie** určuje logický interval `0..D` pre pohyb, orbitálny náhľad, paketový prenos a replay. Podporované celé sekundy sú 2–120 bez satelitnej vetvy a 6–120 so satelitom. Vzorkovanie mobility a spúšťanie CAM je každých 100 ms, teda `sample_count = 10 × D` a posledný CAM tick je `D − 0,1 s`. Pozície satelitov sa v replayi uvádzajú aj na hranici `D`.

Natívny ns-3.38/SNS-3 potrebuje pred prvým paketom 10 s inicializácie terminálov. Runner preto posunie odchody všetkých áut a prvú rádiovú vzorku na interné `t = 10 s`, potom ns-3 zastaví na internom `t = 10 + D s`. Replay odpočíta 10 s. Toto posunutie nemení fyzickú rýchlosť áut, dráhy ani latenciu paketov. Interný `utc_origin` kotví začiatok technického nábehu, takže logický čas 0 zodpovedá `utc_origin + 10 s`; treba to zohľadniť pri výbere orbitálneho snapshotu.

Každé auto musí byť prítomné pri prvom ticku; SUMO odložený odchod pri preplnenej ceste je chyba scenára. Krátke trasy vedú k stojacemu vozidlu do konca behu. Rádio nesmie po `D` pokračovať dobehom správ: včas nedoručený paket sa vykáže ako nedoručený. Vizualizácia pri veľkom počte vzoriek preriedi iba zobrazené polohy; surový výpočet a audit zachovávajú všetky vzorky.

## Opravy odkryté pri dlhšom behu

- Runner satelitnej vetvy už nepredpokladá presne 20 vzoriek pri priamom aute; kontroluje počet podľa scenára.
- Kontrolór spätnej/priamej ISL trasy RSU používa čas handoveru konkrétneho terminálu, preto nevyžaduje starú trasu druhej RSU po jej prepnutí.
- Nezávislý audit antény auta používa skutočný serving satelit v každom kroku; pri súbehu waypointu a handoveru rešpektuje poradie udalostí ns-3.
- Geometrický audit v novom časovom kontrakte končí na `D`; historické behy si ponechávajú pôvodný horizont a overujú sa cez presné zdrojové snapshoty.
- Limit čakania na dlhý natívny beh sa odvodzuje z počtu uzlov a vzoriek. Limity 1200 vzoriek sú v runneroch a oboch aktívnych C++ modeloch zhodné.

## Overenie

Výsledky testov a vstupy sú v `~/Desktop/BP-Simulator-Workspace/runtime/results/u9_runs/` a `~/Desktop/BP-Simulator-Workspace/runtime/config/u9-scenarios/`; pracovné logy sú o úroveň vyššie. Testovací balík neobsahuje výsledky. Úspešný beh má surové stopy, manifest so SHA-256 a samostatný `bp_u9.py verify`.

| Beh | Záťaž | Stav |
| --- | --- | --- |
| `clock-v2v-exact-20261031` | 5 áut, bez RSU a satelitu, D = 2 s | PASS, nezávislý checker; replay 0–2 s. |
| `clock-satellite-6s-final-20261031` | 5 áut, 3 RSU, 4 satelity, priamy terminál a alert, D = 6 s | PASS, nezávislý checker; posledná replay poloha satelitu 6,000 s a paketová udalosť pred 6 s. |
| `long-ground-120-20261031` | 5 áut, 3 RSU, bez satelitu, D = 120 s | PASS, nezávislý checker; 1200 vzoriek každého z 8 rádiových uzlov, posledná poloha 119,9 s a posledná paketová udalosť 119,904 s. |
| `long-sat-120-final-20261031` | 5 áut, 3 RSU, 3 satelity Iridium, priamy terminál auta a alert do druhej RSU, D = 120 s | PASS, finálny manifest aj samostatný `verify`; alert prijali 2 autá. Replay: posledná poloha auta 119,9 s, posledná paketová udalosť 119,904331 s, satelitná poloha 120,0 s. Prvý pokus narazil na pôvodný wall-clock timeout 180 s, ktorý je odstránený. |
| `fleet-200-sat-60-spread-20261031/ground` | 200 áut so zapnutým pozemným rádiom, 6 RSU, D = 60 s | PASS nezávislého auditu pozemných stôp: 200/200 áut v každom zo 600 tickov, 2 670 147 prijatých CAM, 0 kolízií a teleportov. Integrovaná vetva pri všetkých 200 aktívnych rádiách má výrazný výkonový limit; pokus je zachovaný ako diagnostika, nie ako úspešný koncový beh. |
| `fleet-200-mixed-sat-60-20261031` | 200 pohybujúcich sa áut, z nich 20 s aktívnym pozemným rádiom, 6 RSU, 3 satelity Starlink, D = 60 s | PASS integrovaného behu aj samostatného `verify`. 200/200 áut v každom zo 600 tickov; RSU vytvorili 1 449 správ, brána prijala 1 413 a 1 413 odpovedí prišlo k autám. Alert cez satelit do druhej RSU prijalo 8 áut. Replay: posledná poloha auta 59,9 s, paketová udalosť 59,919609 s, satelit 60,0 s. |

Neúspešný pôvodný 200-vozidlový spawn mal 11 odložených áut pri t = 0. V opravenej skúške sa tieto autá presunuli na voľné nadväzujúce úseky; surový SUMO FCD dokazuje spoločný štart. Tieto skúšky sú výskumné modely generického DVB a hypotetických terminálov, nie meranie komerčnej služby.

Plný 200-vozidlový pozemný rádiový audit prečítal 2 670 147 prijatí CAM a po indexovaní PCAP a obsadenia kanála trval približne 143 s. V integrovanom variante so satelitom a súčasným vysielaním všetkých 200 áut natívny model po približne troch minútach spracoval len 1,9 s experimentálneho času za nábehom; tento pokus bol zastavený a zostáva diagnostikou výkonovej hranice. Variant `fleet-200-mixed-sat-60-20261031` zachováva pohyb všetkých 200 áut a používa individuálnu politiku rádia: 20 áut vysiela, ostatné rádio majú vypnuté. To overuje veľkú mobilnú topológiu a spoločnú pozemno-satelitnú vetvu; výsledok nemožno vydávať za škálovací dôkaz 200 súčasne aktívnych rádií v integrovanom modeli.
