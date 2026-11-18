# F4 — lokálne prekážky pri výhľade na satelit

**Stav:** geometrická časť dokončená a overená 1. 11. 2026. Zodpovedné zdroje: `tools/u9_local_environment.py`, `tools/u9_dynamic_service.py`, `tools/u9_osm_road_graph.py`, `tools/u9_service_native.py`. Vegetácia a počasie sú v scenári oddelené štatistické vrstvy s explicitne neznámym útlmom; ich dB účinok na obojsmerný link budget patrí do F5.

## Vstupy a rozhodnutie o výhľade

- Reálna mapa v editore načíta 2 km cestný výrez a z **rovnakých pripnutých OSM XML dlaždíc** uzavreté pôdorysy budov. Pri každej budove sa ukladá OSM way ID, pôdorys v lokálnom ENU a pôvod výšky. `height` sa berie ako hodnota mapového tagu, nie ako meranie; `building:levels` dáva predpoklad 2,5–4 m na podlažie; bez tagu zostáva citlivostný interval 3–30 m. Tieto intervaly sú scenárové predpoklady, nie empirický model mesta. OSM dokumentuje jednotky `height` a význam `building:levels` [tu](https://wiki.openstreetmap.org/wiki/Height) a [tu](https://wiki.openstreetmap.org/wiki/Key:building:levels).
- Holý terén sa importuje z [AWS Terrain Tiles Skadi HGT](https://registry.opendata.aws/terrain-tiles/) a po 30 m sa vkladá do scenára spolu s SHA-256 každej stiahnutej dlaždice. Lokálna dráha sa porovnáva iba s **relatívnym rozdielom výšok** v tom istom rastri; zmiešaný vertikálny dátum zdroja sa preto nepoužíva ako absolútna výška satelitu. Orbitálna poloha zostáva z pripnutého OMM/SGP4.
- Pre každé auto a RSU, každý 0,5 s servisný čas a každého anténne prípustného satelita sa testuje zorný lúč proti terénu a budovám. Auto má deklarovanú výšku antény 1,5 m nad terénom, RSU 3 m; ide o predpoklady tohto scenára, kým sa nezadá skutočná montáž. Ak lúč prechádza pod minimálnou výškou budovy, spoj sa zablokuje. Ak závisí od neznámej výšky, trasa zostáva optimisticky možná, ale `serving_obstruction_status=uncertain`; počty zaručených, neistých a zablokovaných kandidátov sú vo `routes.json`. Paketový backend skutočne používa len zostávajúce trasy.
- Rastlinstvo a počasie sa **neprisudzujú budove ani terénu**. V `statistical_layers` sú samostatné záznamy pre [ITU-R P.833-10](https://www.itu.int/rec/R-REC-P.833) a [ITU-R P.618-14](https://www.itu.int/rec/R-REC-P.618). Bez hĺbky a druhu porastu, lokálneho dažďového podnebia a frekvencie je útlm `null`. Ak používateľ neskôr vloží `[min,max]` dB, musí mať `status=scenario_assumption_not_ITU_prediction`; F4 ho len uchová, F5 ho použije pri link budgete.

## Overenie a čísla

| Kontrola | Výsledok |
| --- | --- |
| Reálny výrez Bratislava, 48,1486° N, 17,1077° E | 2 007 jazdných úsekov, **4 722** uzavretých budov, 75×75 DEM buniek; OSM digest `dcc69bd5…`, HGT N48E017 digest `a28d1c66…`; import 20,4 s vrátane stiahnutia. 2 492 budov nemalo výšku, 2 184 malo len počet podlaží, 46 malo `height`. |
| `f4-terrain-building-starlink-20261101` | `run` a nezávislý `verify` PASS; 68/68 paketov k proxy bráne. Prvá obslužná trasa auta bola bez lokálnej prekážky, v ďalších kandidátoch sa objavili blokované aj neisté smery. |
| `f4-terrain-building-iridium-v2-20261101` | `run`/`verify` PASS; 61/68 paketov k bráne, 7 explicitných dropov, výstraha cieľovej RSU a autu. Zmena trasy presne na konci 6 s je zaznamenaná ako koncový stav, nie ako paket mimo experimentu. Prvý pokus s prísnym verifierom zostal uchovaný pod `f4-terrain-building-iridium-20261101` ako neúspešný, nie ako dôkaz. |
| `f4-terrain-building-globalstar-20261101` | `run`/`verify` PASS; 55/68 paketov k bráne, 15 dropov, Globalstar bez ISL, výstraha doručená. |
| Negatívna kontrola | Plochý terén: RSU0 má trasu vo všetkých 13 vzorkách. Štyri 500 m syntetické steny okolo tej istej RSU: **0/13** trás. Výsledok je v `results/f4-validation-20261101/negative-control.json`. |
| Jednotkové hrany | 11 kontrol prostredia, existujúceho plánovača, antény a mapovej polohy PASS; vysoká/nízka budova, neistý interval, terénny hrebeň, neplatná georeferencia. |

Všetky tri výsledky obsahujú pôvodné OSM/HGT hashe v scenári, zdrojový hash modelu, orbitálny snapshot, surovú ns-3 stopu a nezávislé prepočítanie servisnej trasy. Zachované staršie výsledky sa overujú cez presné zdrojové snapshoty. Zmena importovaného scenára alebo stopy musí zlyhať.

Po aktualizácii prenosného runtime sa znovu nezávisle overilo **7/7** historických servisných behov F2c/F3. Celá séria `test_u9_*.py` prešla **41/41** kontrol. Server na `127.0.0.1:8765` vrátil HTTP 200 pre editor, nový OSM/DEM import (2 007 ciest, 4 722 budov) a 1,83 MB satelitný preflight. Prenosný priečinok overil 11 431 súborov a odkazov; ZIP test bez poškodeného člena, SHA-256 `e2f6cc40d5f10f9ccad7f779da5a3b4a166be51b3670c9ad8b1792bc6419ca8e`.

Kópia všetkých F4 výsledkov vrátane neúspešného diagnostického pokusu a negatívnej kontroly je na ploche v `~/Desktop/BP-Simulator-Workspace/runtime/results/f4-local-environment-20261101/`. Pôvodné overiteľné adresáre v projektovom `results/u9_runs/` zostávajú nedotknuté, keďže manifesty obsahujú presné projektové cesty.

## Hranice presnosti

1. OSM XML API nemusí obsahovať všetky budovy a nie je geodetickým meraním. Parser zatiaľ berie uzavreté building ways; 157 budovových multipolygon relácií a tri neúplné ways v tomto výreze sú **výslovne mimo geometrie**. Toto je konkrétny zostávajúci zdroj optimistického výhľadu, ktorý treba zohľadniť pri výbere pokusu alebo doplniť import relácií.
2. Výškové tagy nemajú garantovanú presnosť. HGT/30 m vzorkovanie môže prehliadnuť úzky val alebo násyp. Výška 1,5/3 m je predpoklad a nie model karosérie, stožiara či sklonu vozidla. Kreslenie budov na prázdnej mape a objektový výber multipolygonov nie sú súčasťou F4.
3. Zablokovanie je geometrický LOS test. Neistý smer sa **nesmie** interpretovať ako garantovaná dostupnosť. Priamy útlm dažďa, listov, stien, Fresnelova zóna, difrakcia, aktivácia lúča, modem, kapacita a operátorský gateway zostávajú otvorené pre F5/F6 alebo pre externé merania.

**Záver:** F4 už ovplyvňuje skutočné paketové výsledky lokálnym terénom a budovami, ale výsledok je len fyzikálne možná alebo neistá geometrická cesta. Ďalší celok F5 musí spracovať obojsmerný link budget a štatistické útlmy bez predstierania skutočnej služby operátora.

**Nadväzujúce spresnenie 1. 11. 2026:** [F5](f5-odhad-vysok-a-link-budget-2026-11-01.md) zaviedlo lokálny medián pre chýbajúce výšky a tri opakovateľné citlivostné voľby. Čísla a správanie uložených behov F4 vyššie sú historické a nemenia sa; nové behy sú označené `f5-*`.
