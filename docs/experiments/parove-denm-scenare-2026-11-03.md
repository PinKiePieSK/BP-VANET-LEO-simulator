# Párové scenáre doručenia DENM — 3. 11. 2026

## Účel a vstupy

Štyri uložené 60 s scenáre tvoria dve kontrolované dvojice. V rámci každej dvojice majú pozemný a satelitný variant **identické bajty** `world.json` a `demand.json`, teda rovnaké cesty, autá, rýchlosti, trasy, RSU, UTC, seed a jednu DENM výstrahu pri `t = 5 s`. Mení sa len aktivácia satelitného backhaulu pri dvoch RSU. V oboch variantoch sa zachováva pozemné ITS-G5 a CAM.

| Dvojica | Dopravná situácia | DENM |
| --- | --- | --- |
| `realna-d1-pozemna` / `realna-d1-satelit` | Šesť áut v dvoch protiidúcich prúdoch na skutočných smerovaných úsekoch D1 pri Bratislave. Zdrojová RSU je pri západnej skupine a cieľová pri východnej, vzdialené približne 2,6 km. OSM cesty a budovy pochádzajú z pripnutého slovenského Geofabrik extraktu. RSU a dopyt sú navrhnuté pre experiment; nie sú meranou infraštruktúrou ani dopravou. | Auto `car0`, polomer 1000 m, platnosť 45 s, bez opakovania. |
| `navrh-koridor-pozemna` / `navrh-koridor-satelit` | Päť áut na kreslenom hlavnom mestskom ťahu a odbočke do južnej štvrte. Zdrojová RSU leží pri hlavnom ťahu, cieľová pri južnej vetve, vzdialené približne 1,1 km. Celá geometria je modelový návrh. | Auto `car0`, polomer 600 m, platnosť 45 s, bez opakovania. |

Použitá konštelácia satelitných variantov je Iridium NEXT so skutočným pripnutým orbitálnym vstupom pre zvolený UTC okamih. Prenosový modem je **generický DVB model SNS-3**, nie modem Iridium. Brána a RSU sú experimentálne, nie doložená operátorská sieť. Zámerom je porovnať architektúru pozemná/satelitná vetva, nie predpovedať komerčnú dostupnosť.

## Skutočné behy a surové stopy

Každý scenár prešiel `run`, nezávislým `verify` a vytvorením replay. Súbory sú v `results/simulations/scenar-<id>-20261103/`. Replay má 60 s; polohy áut sú vzorkované od 0,0 do 59,9 s s krokom 0,1 s. V každom behu bolo prítomné každé auto od štartu a SUMO nezaznamenalo teleport.

| Scenár | CAM TX | Príjem DENM autami | Satelitná cesta |
| --- | ---: | --- | --- |
| `realna-d1-pozemna` | 1480 | `car1`, `car2` | vypnutá |
| `realna-d1-satelit` | 1480 | `car1`, `car2`, **`car3`, `car4`, `car5`** | `rsu0` → brána → `rsu1`; 3 vzdialené autá |
| `navrh-koridor-pozemna` | 876 | `car1` | vypnutá |
| `navrh-koridor-satelit` | 876 | `car1`, **`car3`, `car4`** | `rsu0` → brána → `rsu1`; 2 vzdialené autá |

Surové `trace.csv` potvrdzujú, že pôvodný DENM prijala `rsu0` pri t ≈ 5,000 s, brána ho prijala a `rsu1` vyslala nový pozemný broadcast pri t ≈ 5,135 s. V pozemných kontrolách cieľové autá DENM neprijali. Overovací kód kontroloval ASN.1 bajty, identitu stanice, uzly paketovej cesty a manifest. Oba satelitné replay obsahujú satelitné polohy a potvrdené paketové spojenia; pozemné replay neobsahujú satelitné paketové spojenia.

## Interpretácia

Tieto štyri konkrétne deterministické behy ukazujú, že za zvolených pozícií a fyzikálnych predpokladov sa výstraha dostala k viacerým autám so satelitným backhaulom. Rozdiel nie je štatistická PDR ani univerzálne zlepšenie. Pre záverečné experimenty treba neskôr dohodnúť s vedúcim opakovania cez rôzne seedy, časy, polohy, rušenie a výpadky; scénare teraz slúžia ako zrozumiteľné funkčné príklady a východisko merania.

## Skúška prenosného balíka

Finálny ZIP obsahuje presne štyri uložené scenáre a ich štyri dvojice vstupov; osobné a staré skúšobné vstupy do neho nevstupujú. Neobsahuje konštelácie vygenerované starými behmi. Kontrola manifestu a test integrity ZIP prešli. Čisté `setup.sh` na Ubuntu 24.04 zostavilo Vanetza a ns-3.38/SNS-3 3.38 a vykonalo skúšobný pozemný beh. Všetky štyri scenáre prešli preflightom z nového runtime. Následný beh `portable-realna-d1-satelit-20261103` a samostatný verifier potvrdili 1480 CAM TX, jeden DENM v bráne a tri vzdialené autá. Tým sa preukázalo aj opätovné vytvorenie natívnych satelitných vstupov z pripnutého archívu.

V prehliadači prenosného servera sa zobrazili presne štyri nové položky; reálny aj kreslený scenár sa načítali s očakávanými autami a RSU. Overený prenosný replay sa otvoril bez chyby a posuvník ukázal `60.00 / 60.00 s`.
