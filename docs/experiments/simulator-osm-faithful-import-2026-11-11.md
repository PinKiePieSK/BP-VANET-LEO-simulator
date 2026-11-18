# Verný import ciest z OSM — 11. 11. 2026

## Príčina prerušenia

V pripnutom slovenskom OSM PBF (`dataset_sha256` `4af3affa32fdc294ade673b409a0dc7f5c6c908875776ff06530d7bd923a9185`) sú pri Pribinovej tri nadväzujúce OSM ways: `563753753` → `954672373` → `204438875`. Stredný úsek má 1,335 m a v OSM spája uzly `3048592615` a `2144379418`. Starý import odmietal každú časť kratšiu ako 2 m; v uloženom pracovnom grafe preto medzi susednými koncami zostala medzera 1,334 m. Súradnicový prevod posunul konce iba o 0,01–0,06 m. OSM teda tieto súradnice a spojenie dodalo; stratili sa u nás.

Rovnaký dôvod vyradil 1,615 m spojku `992945452` a 0,815 m spojku `902086841`. V oblasti `17.121–17.132° E`, `48.139–48.143° N` malo pôvodné OSM 167 spoločných uzlov jazdných ciest. Starý import nepredstavoval tri z nich pre dve krátke spojky; nový import zachoval všetkých 167. Samostatné blízke slepé konce bez spoločného OSM uzla sa za križovatku nepovažujú.

## Zmena

- Import, lokálne orezanie a SUMO schéma prijímajú platné cestné časti od 0,5 m. Malé úseky už nezmiznú len kvôli minimálnej celkovej dĺžke. `netconvert` a SUMO v kontrolovaných prípadoch prijali hrany 0,5 m, 0,8 m a 1,335 m; FCD obsahovalo prejazd krátkou hranou.
- Globálne OSM cesty uchovávajú ID pôvodného way a oboch koncových OSM uzlov. Pracovný graf spája cesty podľa zhodného OSM uzla; rovnaká poloha dvoch rôznych uzlov nie je automaticky križovatkou. Konce vytvorené orezaním na hranici pracovnej mapy zostávajú samostatné.
- Miestna geometria používa centimetrové zaokrúhlenie a ponecháva pôvodné lomové body od 0,5 m. Existujúce scenáre po načítaní dostanú nový import verzie 3. K už známym cestám sa doplní identita uzlov pri nezmenených zemepisných koncoch, pričom ručne nastavená rýchlosť, pruhy a smer ostávajú.
- Na žiadosť používateľa sú vypnuté heuristiky automatického spájania medzier a skrývania slepých alebo odpojených úsekov. Formulár manuálneho spájania sa v paneli nezobrazuje. Toto je vedomé oddelenie verného OSM vstupu od neskoršej úpravy grafu.

## Overenie

- Nový import reálneho 4 km výrezu vrátil 5 801 globálnych cestných častí s verziou 3 a pôvodnými ID koncových uzlov. Pracovný výrez zobrazil 5 797 častí; štyri ďalšie nedávajú platnú časť vo výreze. Pri Pribinovej je 1,335 m spojka prítomná a jej grafové uzly sú zhodné s oboma susednými cestami.
- V izolovanom teste 0,8 m OSM spojka prežila import a vytvorila správne nadväzujúce uzly. Dve cesty s rovnakými súradnicami, ale odlišnými OSM ID uzlov, zostali oddelené.
- Na aktuálnom runtime `127.0.0.1:8766` sa uložený scenár `realna-d1-pozemna` načítal so 6 autami a 2 RSU. Žiadne heuristicky skryté úseky sa nehlásia; serverový `/api/simulator/editor/check` vrátil HTTP 200 a plán so 6 autami. Test použil oddelený headless Firefox; používateľská karta zostala otvorená a uložené dáta sa nemenili.
- Cielené Python testy importu, schémy a lokálneho PBF: 3/3 OK. Študijná kópia: `python3 scripts/refresh_study_code.py --check` PASS.

## Hranice

Vernosť OSM znamená vernosť dostupným údajom, nie záruku, že mapovanie zodpovedá aktuálnej premávke. V kontrolovanom zdrojovom výreze je 318 OSM relation obmedzení odbočenia, 97 značiek `lanes:forward` a 96 značiek `lanes:backward`. Tieto obmedzenia a asymetrické pruhy, ani podmienený prístup, sa zatiaľ nepremietajú do SUMO. Pri troch cestách tesne na okraji pracovného výrezu algoritmus orezania vyberie najdlhšiu vnútornú súvislú časť; 14 pôvodných bodov do 36 m od hranice sa preto v ich aktívnom tvare neobjaví. Na tieto hranice sa pri vyhodnotení trás musí prihliadať.

## Doplnenie: OSM pravidlá a úplnejšie orezanie (import revízie 9)

Toto doplnenie nahrádza vyššie uvedenú hranicu o asymetrických parametroch, zákazoch odbočenia a výbere jedinej časti cesty pri hranici. Staršie čísla revízie 3 zostávajú historickým dôkazom predchádzajúceho kroku.

- Import číta `maxspeed:forward/backward`, `lanes:forward/backward`, statický prístup podľa hierarchie `motorcar → motor_vehicle → vehicle → access`, implicitnú jednosmernosť diaľnice, `service`, `bridge`, `tunnel`, `layer` a relácie `type=restriction` cez OSM uzol. Pri `oneway=-1` otočí smer geometrie aj smerové tagy. Chýbajúce rýchlosti a pruhy sú výslovne označené ako triedny odhad a jeden pruh. Globálny aj lokálny graf nesú pôvod každého smerového údaja.
- Import rozdelí OSM way pri vstupe/výstupe z pracovného výrezu, takže pri opakovanom vstupe nezostane len najdlhšia súvislá časť. Cesty sa stále pripájajú iba podľa spoločných OSM uzlov; automatické heuristiky spájania a skrývania odpojených úsekov zostávajú vypnuté.
- Jednoduché `no_*` a `only_*` zákazy cez uzol sa prevedú na zakázané dvojice smerových hrán. Plánovač trás sleduje prichádzajúcu hranu, vrátane spojok od 0,5 m. Validator odmieta trasu cez zakázanú dvojicu. `make_inputs` zapisuje povolené prechody do `road.con.xml`; `netconvert --connection-files` ich uplatní. Tento súbor patrí aj do manifestu SUMO vstupov.
- Pri obnove starého scenára sa staré OSM úseky, ktorých ID sa zmenilo delením pri okraji, nahradia novými. Ak ich používa auto, trasa sa prepíše iba pri jednoznačnej náhrade so správnym koncovým bodom. Nejednoznačné a ručne spojené úseky sa zachovajú. Ručne nastavená rýchlosť a pruhy sa pri bezpečnej náhrade zachovajú.
- Posuvný prehľad **Cestné vstupy SUMO** je pri pracovnej mape. Ukazuje zdroj a revíziu, vylúčené ways, podmienené údaje, delenia na hranici, počet aplikovaných/neaplikovaných relácií a pre vybranú cestu ID hrán a uzlov, geometriu, smerové rýchlosti/pruhy aj pôvod hodnôt. Žlté položky sú výslovne neaplikované. Vrstva `bridge/tunnel/layer` pomáha interpretovať topológiu podľa OSM uzlov; neodovzdáva sa ako 3D výška SUMO.

### Dôkaz

- Pripnutý 4 km výrez: 5 812 globálnych OSM úsekov, 1 307 vylúčených ways pre statický prístup, 54 ways s podmienkou a 117 delení na hranici. Z importu prišlo 301 relácií odbočenia (285 cez uzol, 16 cez way). V pracovnej mape je pri uloženom `realna-d1-pozemna` 5 811 aktívnych úsekov, 302 zakázaných prechodov zo 254 aplikovaných relácií; 47 relácií je mimo aplikovateľného modelu alebo aktívneho grafu. Zachovalo sa 6 áut a 2 RSU.
- `tools/test_simulator_osm_rules.py` kontroluje smerové hodnoty, pôvod údajov, reláciu cez uzol a dve vnútorné časti jednej opakovane vstupujúcej cesty. `tools/test_simulator_osm_short_connector.py` kontroluje krátku Pribinovu spojku. Obe sady prešli.
- Oddelený headless Firefox načítal uložený scenár s importom revízie 9; `/api/simulator/editor/check` vrátil HTTP 200. Skutočný `netconvert` vytvoril 28 125 hrán a 36 704 prechodov, z ktorých **žiadny** nie je medzi 302 zakázanými dvojicami. SUMO úspešne načítalo sieť a trasy pri krátkom 1 s štarte. V obnovenom scenári zostali tri cesty s odlišným limitom podľa smeru a žiadna automatická hodnota sa nesprávne neoznačila za ručnú. Na vybranej obojsmernej ceste panel ukázal 40 km/h dopredu a 50 km/h dozadu, zhodne so smerovými OSM tagmi; posuvný zoznam mal vlastné rolovanie. Plánovač vytvoril aj novú náhodnú trojúsekovú trasu pri rešpektovaní zákazov; editorová kontrola zostala HTTP 200. Uložené vstupy ani historické výsledky sa nemenili.

### Zostávajúce hranice

- Prístupové hodnoty viazané na účel jazdy (napr. `destination` alebo `delivery`) sa zobrazujú ako neúplne uplatnené; statický filter vylučuje iba jednoznačne zakázané osobné autá.
- Časové tagy `*:conditional` sa uchovávajú a označujú v paneli, ale statická sieť SUMO ich teraz časovo nevyhodnocuje. OSM zákazy odbočenia cez celý `via` way sa bez rozšíreného stavového modelu neprevádzajú na obyčajné dvojice hrán. Panel ich počíta medzi neaplikované; žiadne tvrdenie o ich dodržaní v SUMO sa nerobí.
- OSM `bridge/tunnel/layer` sa používa na kontrolu významu uzlov, nie ako fyzická 3D geometria; križovanie rôznych OSM ways bez spoločného uzla zostáva nespojené. Presnosť OSM samotného a právnej aktuálnosti značiek nie je zaručená.
