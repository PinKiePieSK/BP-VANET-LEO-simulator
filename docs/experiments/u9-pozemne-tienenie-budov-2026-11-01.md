# U9: tienenie budov v pozemnom rádiu

**Stav 1. 11. 2026:** implementované a otestované pre komunikáciu auto–auto aj auto–RSU v spoločnom U9 behu. Výstražná aplikácia a kalibrácia dopravného dopytu zostávajú na neskôr.

## Vstup a mechanika

Pri scenári s reálnou mapou sa z pripnutého `satellite.environment` exportujú uzavreté OSM pôdorysy budov do `inputs/ground-obstructions.csv`. CSV je súčasťou výsledku a jeho obsah kontroluje verifier. Na výšku sa použije zvolený variant `low`, `central` alebo `high`; OSM hodnota výšky, odhad z počtu podlaží a lokálne imputovaná výška si zachovávajú svoj pôvod v pôvodnom scenári. Export sa robí aj pri vypnutej satelitnej vetve, pretože budovy potrebuje pozemné rádio.

Natívny ns-3.38 model `urban_osm_building` zisťuje v okamihu každého pozemného spojenia prienik priamej 3D spojnice medzi anténami s presným 2D polygónom budovy a jej zvolenou výškou. Nájdená prekážka nastaví kanál `NLOS`, inak `LOS`; na obe podmienky sa použije existujúci `ThreeGppV2vUrbanPropagationLossModel` pri 5,9 GHz. Rozhodnutie platí rovnako pre V2V, V2I aj spätný I2V prenos. Pohyb vozidiel mení polohu antény v tom istom ns-3 čase ako pakety. Prieskum sa obmedzuje priestorovým indexom po 100 m bunkách.

Anténa auta má v tomto modeli výšku 1,5 m. RSU mimo budovy je vo výške 5 m; ak je jej bod v pôdoryse budovy, explicitne predpokladáme strešnú montáž 2 m nad odhadnutou strechou. Tento predpoklad je dôležitý, lebo editor dnes nerozlišuje stĺp, fasádu a strechu. Staršie ručne zadané `urban_building`, `urban_los` a `urban_nlos` prípady zostávajú dostupné v nízkoúrovňovom testovacom rozhraní; bežný U9 import reálnej mapy volí nový režim automaticky.

## Prijímacie kontroly

| Kontrola | Výsledok |
| --- | --- |
| Samostatná geometria | Polygón tieni spojnicu pretínajúcu budovu; spojnicu v obalovom obdĺžniku, ale mimo skutočného polygónu, netieni; lúč nad strechou zostáva LOS. `test_ground_osm_geometry.cc` v pracovnom testovacom priečinku: PASS. |
| Párovaná pozemná kontrola, 3 autá + 1 RSU, rovnaké správy a poloha | Bez budovy 18/18 CAM príjmov. S jednou 8 m budovou 8/18; blokované sú odkazy auto–auto aj auto–RSU cez budovu, odkazy na rovnakej strane zostali funkčné. Oba výsledky prešli `u9_check_ground.verify`. |
| Reálny výrez Bratislavy, pozemný beh | 5 áut, 3 RSU a 4 722 OSM budov; 89 CAM vyslaní, 9 príjmov, bez teleportov. `bp_u9.py run` a samostatné `verify`: PASS. |
| Spoločný pozemný + Starlink servisný beh | Rovnaký reálny výrez; 89 CAM vyslaní, 9 príjmov, 27 servisných ponúk a 27 ACK. Vzdialená RSU dostala oznámenie, ale v tomto rozmiestnení sa k autu cez budovy nedostalo. Celý `bp_u9.py verify`: PASS. Ide o výsledok modelu, nie predikciu služby operátora. |
| Historický výsledok pred touto zmenou | `f5-heightbudget-starlink-20261101` sa naďalej overuje ako PASS so svojím pôvodným zdrojovým manifestom. |

Raw výsledky sú v projektových `results/ground-osm-clear-20261101`, `results/ground-osm-blocked-20261101`, `results/u9_runs/ground-osm-roof-20261101` a `results/u9_runs/ground-osm-service-20261101`. Pracovné logy a malý geometrický test sú v `~/Desktop/BP-Simulator-Workspace/tests/`. Žiadne zo starších výsledkov nebolo prepísané.

## Hranica vernosti

Pôdorysy pochádzajú z OSM, no OSM nie je úplný register budov: neúplné/multipolygonové objekty sa nepreberajú, výšky sú často odhadnuté a lokálne natočenie/montáž RSU nie sú merané. Pozemný rádiový model tu nepoužíva reliéf terénu, difrakciu na hrane, Fresnelovu zónu, materiál stien, vozidlá ako prekážky ani meranú miestnu kalibráciu. `NLOS` zvyšuje modelový útlm; nie je to tvrdenie, že každá budova vždy úplne zablokuje paket. PDR jedného krátkeho scenára nie je skutočná PDR Bratislavy. Pre obhajobu treba používať formuláciu **OSM geometricky podmienený 3GPP V2V Urban LOS/NLOS model**.
