# U9: jeden editor a automatický satelitný výber, 31. 10. 2026

## Zmena ovládania a kontraktu

Stránka `viewer/u9-simulator.html` sa otvára s prázdnym návrhom. Úvodný výber šiestich skúšobných scén a výber technického profilu boli odstránené. Naďalej možno načítať vlastný uložený scenár; staršie konfiguračné súbory ostávajú historickými vstupmi pre reprodukciu. Nové návrhy používajú `mode: unified`; od zjednotenia časovania používajú `schema_version: 5`. Pri každom aute sa samostatne nastavuje pozemné ITS-G5 (`autá aj RSU`, `iba autá`, `vypnuté`) a priamy satelitný terminál. Pri každej RSU sa samostatne nastavuje pozemné rádio a satelitný backhaul. Zdrojová a cieľová RSU sa odvodia zo zapnutých zariadení. Celá pozemná a vyžiadaná satelitná vetva beží v jednom U9 scenári; nevyberá sa profil behu.

Výber počtu paketových satelitov je odstránený. Po zmene konštelácie alebo polohy editor preskúma vekovo platný archív OMM, viditeľnosť nad maskou, cestu k proxy bráne a zostaví feeder–serving–handover strom pre aktuálne terminály. Glóbus stále vykresľuje celú platnú konšteláciu. Zobrazuje samostatné počty viditeľných, s bránou spojených a v paketovom strome použitých satelitov. Údaj pri výbere podgrafu znamená stabilnú viditeľnosť počas komunikačného okna; počet na glóbuse je okamžitý a môže byť vyšší. Viditeľný satelit nemusí niesť paket: terminály sa pripájajú na konkrétny serving uzol a jeden overený handover cieľ. Nie je to automatické smerovanie každého viditeľného satelitu ani predikcia dostupnosti služby operátora. Šesťmiestne katalógové ID sa v súčasnom natívnom SNS-3 vstupe neakceptuje a editor počet vylúčených objektov uvádza.

Tento odsek zachytáva pôvodný stav pred zjednotením časovania. Aktuálny editor používa jedinú dĺžku pre pohyb, orbitálny náhľad aj paketový beh; podrobnosti a nové skúšky sú v [zázname spoločného času](u9-spolocny-cas-2026-10-31.md). Priame auto–satelit bez akejkoľvek satelitnej RSU zatiaľ nemá spoločný natívny packet engine; preflight to odmietne s konkrétnym dôvodom. Jedna satelitná RSU bez priameho auta a bez cieľovej RSU už podporovaná je. Toto je technická hranica, nie skrytá náhrada iným profilom.

## Prijímacie testy

Raw vstupy a výsledky sú mimo zdrojového balíka v `/home/samuel-petrik/Desktop/BP-Simulator-Workspace/runtime/config/u9-scenarios/` a `.../runtime/results/u9_runs/`. Každý úspešný beh vytvoril `run-manifest.json`, skutočné ns-3.38/SNS-3 3.38 stopy a prešiel `bp_u9.py verify`; adresáre sa neprepisovali. Neúspešné prvé pokusy zostávajú v pracovnom priečinku ako diagnostika, úspešné opravené behy majú odlišné ID.

| Beh | Vetva | Výsledok |
| --- | --- | --- |
| `unified-ground-2cars-v2-20261031` | 2 autá, 0 RSU, 0 satelitov | PASS; 12 CAM TX, 12 RX, bez teleportu |
| `unified-ground-policies-20261031` | 5 áut, 3 RSU, individuálne vypnuté rádio a cars-only | PASS; 22 CAM TX, 41 RX |
| `unified-one-rsu-satellite-v2-20261031` | 5 áut, 1 RSU, bez priameho auta a cieľovej RSU | PASS; natívny RSU report a návrat, nulové nepovolené vetvy |
| `unified-two-rsu-direct-20261031` | 5 áut, 2 RSU, jedno priame auto, upozornenie medzi RSU | PASS; 3/3 priamych prijatí a návratov, upozornenie dvom autám, 2 terminálové handovery |
| `unified-auto-iridium-20261031` | Automatický výber Iridium, 4 viditeľné a 3 paketové uzly | PASS; úplný natívny beh a checker |
| `unified-auto-globalstar-20261031` | Automatický výber Globalstar, 2 viditeľné a 2 paketové uzly | PASS; úplný natívny beh a checker |
| `unified-auto-starlink-20261031` | Automatický výber Starlink, 412 viditeľných a 3 paketové uzly | PASS; úplný natívny beh a checker |

Príkaz `PYTHONPATH=tools .venv/bin/python -m unittest tools.test_u9_capabilities tools.test_unified_contract` prešiel: 16 testov. Syntax `viewer/u9-simulator.js` prešla kontrolou Node `--check`. Negatívne kontroly odmietli nesúlad satelitného príznaku, chýbajúcu politiku auta a vypnuté rádio zdroja. Skryté browserové testovanie overilo prázdny štart, načítanie uloženého scenára, nastavenia `car4` a `rsu1`, automatické prepočítanie Globalstar na 2 aktívne uzly bez tlačidla na ručný výber a načítanie Starlink na živom serveri 8765. Konkrétne výstupné manifesty sú rozhodujúcim dôkazom; samotná grafika glóbusu nedokazuje doručenie paketu.
