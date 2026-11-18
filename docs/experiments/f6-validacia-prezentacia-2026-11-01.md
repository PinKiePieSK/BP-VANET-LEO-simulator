# F6 — časový audit fyzikálne možnej satelitnej cesty

**Stav:** dokončené 1. 11. 2026 v rozsahu verejne doložiteľnej geometrie a deklarovaných RF predpokladov. Tento audit **nepotvrdzuje dostupnosť komerčnej služby**. Meranie rovnakého modelu terminálu v rovnakej lokalite a čase nebolo dodané, preto empirické porovnanie nemá stav PASS.

## Čo zobrazuje prehrávač

Pri otvorení overeného satelitného behu panel **Fyzikálna cesta vybraného uzla** vyhodnotí každé auto/RSU osobitne v kroku 0,5 s. Výber uzla a posun času prehrávania zobrazia šesť oddelených vrstiev: (1) družice nad čistým horizontom 0°, (2) družice vo verejne modelovanej obálke služby, (3) terminálovú anténu alebo jej neznámy ziskový vzor, (4) geometrický výhľad a budovy/terén, (5) interval rezervy každého zo štyroch smerov user/feeder a (6) zaznamenané ponuky, prijatia bránou, straty a ACK v paketovej proxy vrstve. Farebné prstence na pozemnej mape sa dajú vypnúť v **Vrstvách mapy**. JSON a CSV tlačidlá exportujú uzlové časové riadky.

Základom je ten istý pripnutý OMM snapshot a SUMO/WGS84 waypointy ako v overenom behu. Čistý horizont sa dopočíta nezávisle, ostatné vrstvy sa spájajú z uložených `physical-timeline.json`, `service-model/link-budget.json` a `service_packets.csv`. Nový endpoint `/api/u9/runs/<ID>/physical-audit` najprv overí beh a až potom vráti audit. Export do samostatného adresára obsahuje `audit.json`, `audit.csv` a `manifest.json`; overovač znovu načíta a overí pôvodný beh, prepočíta audit a porovná presné bajty. Historické F5 behy sa neupravovali.

**Výklad:** „nad horizontom“ nie je „v lúči“; „možná anténa“ pri Iridium/Globalstar znamená neznámy detailný ziskový vzor; kladný RF interval je len výsledkom zadaných predpokladov; paketový úspech je úspech modelu ns-3, nie potvrdený attach k operátorovi. RF interval sa nezamieňa za tvrdú bránu paketového backendu. Aktívne lúče, operátorská kapacita, reálny modemový prah a komerčná dostupnosť zostávajú `unverified`.

## Integrované kontroly

Použité sú tri pripnuté F5 behy, každý 5 áut, 3 RSU, 6 s a 13 časových snímok na uzol. Audit má v každom prípade **104 riadkov**. Samostatne exportované a opäť overené sú v `~/Desktop/BP-Simulator-Workspace/runtime/results/f6-physical-audit-20261101/{globalstar,iridium,starlink}/`.

| Služba | Horizont > obálka | Snímky s aspoň jedným kandidátom v obálke | Snímky s tieneným kandidátom | RF stav pri zapnutom termináli |
| --- | ---: | ---: | ---: | --- |
| Globalstar | 0/104 | 104/104 | 38/104 | 30 intervalov pretína nulu; 9 bez cesty. Ide o výslovne hypotetické vstupné RF intervaly. |
| Iridium NEXT | 0/104 | 104/104 | 39/104 | 29 neznámych RF vstupov; 10 bez cesty. |
| Starlink | 104/104 | 104/104 | 39/104 | 39 neznámych RF vstupov; zvyšných 65 má vypnutý terminál. |

Kladný predpokladaný RF margin sa v týchto integrovaných scenároch **nevyskytol**. V 65/104 riadkoch každého behu je satelitný terminál vypnutý; fyzikálna obálka sa eviduje, ale nie je tým autorizovaný prenos. Paketové stavy a RF stavy sa zámerne neodvodzujú jeden z druhého. Zobrazenie na skúšobnom serveri bolo overené pre Globalstar: panel ukázal 2 družice nad horizontom, 2 v obálke, 1 voľnú a 1 tienenú, hypotetický interval RF rezervy a skutočné servisné udalosti v prvom polsekundovom okne. Dĺžka prehrávania bola 6,00/6,00 s podľa behu.

## Negatívne a citlivostné kontroly

- `test_u9_physical_report.py` overuje, že čistý horizont sám nevytvorí aktívny terminál alebo dostupnú službu, publikačná obálka nemôže presiahnuť čistý horizont, zorné pole môže vyradiť kandidáta, tienenie, RF margin a paketový výsledok ostávajú nezávislé a udalosti sa priradia pôvodnému vysielajúcemu uzlu.
- Chýbajúce RF vstupy zostávajú `unknown_rf_inputs` a neznámy ISL rozpočet zostáva `unknown_isl_budget`; presne špecifikovaný hypotetický interval môže byť kladný, záporný alebo pretínať nulu. Tieto stavy nepremieňajú generický packet trace na dôkaz služby.
- Nízke/stredné/vysoké odhady výšky na rovnakých dráhach a waypointoch z F5 dali **467/679/1074** tienených kandidátov; úplná možná trasa v danom pokuse zostala 39/39 snímok pre všetky tri odhady. Táto citlivosť je vlastnosťou odhadu výšok, nie pozorovaná spoľahlivosť siete.
- Poškodenie jedného bajtu exportovaného CSV bolo nezávislým `verify_export` odmietnuté. Neexistujúce ID behu endpoint odmietol HTTP 409. Celá sada `test_u9_*.py` prešla **49/49**, syntax troch dotknutých JS súborov prešla.

Finálny prenosný priečinok `~/Desktop/BP-Simulator/` overil **11 443** súborov/odkazov, nový JS auditu aj Python modul sú v manifeste a testovacie súbory v balíku nie sú. ZIP prešiel `unzip -t`, SHA-256 `b12a11ff5a8df6946b6bc61e2d94229abeeff9fcdeb8b341664898f79a845770`. Runtime na `127.0.0.1:8765` vrátil HTTP 200 pre editor, skripty auditu a vytvorenie nového návrhu. Skúšobný server na porte 8766 a všetky simulačné procesy boli po kontrole ukončené; beží iba používateľský runtime na 8765.

## Reprodukcia a hranica ďalšej práce

Z koreňa projektu spusti `./.venv/bin/python tools/u9_physical_report.py export results/u9_runs/<overený-satelitný-beh> <nový-prázdny-adresár>` a následne `./.venv/bin/python tools/u9_physical_report.py verify <nový-prázdny-adresár>`. Export vyžaduje uzavretý a overiteľný beh s fyzikálnou časovou osou; cieľový adresár nesmie existovať.

Na empirickú validáciu treba súčasné GPS/polohy auta, model a montáž antény, časový záznam viditeľnosti/attachu, log RSRP/SNR alebo ekvivalent a paketové úspechy konkrétneho terminálu. Potom možno pridať porovnanie po 0,5 s podľa UTC a rozlíšiť chybu dráhy, obálky, tienenia a RF. Kým také dáta chýbajú, F6 uzatvára **prezentáciu a internú konzistenciu modelu**, nie kalibráciu reálnej dostupnosti.
