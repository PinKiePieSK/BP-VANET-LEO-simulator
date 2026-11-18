# Výber satelitov, farby spojení a úplný replay — 1. 11. 2026

## Príčina hláseného nesúladu

Predchádzajúci uložený scenár `bratislava-4auta-3rsu-iridium-20261031-novy1` mal verejnú dĺžku **6 s** a `sample_count=60`. Jeho overený replay preto správne trval 6 s. V editore však zmena poľa dĺžky nenastavovala orbitálny výber ako zastaraný a spustenie nepreberalo neodovzdaný obsah poľa. Používateľ tak mohol vidieť 30 s v editore a následne spustiť starší scenár alebo starší výber satelitov. Oba body sú opravené: pred kontrolou, uložením a behom sa dĺžka výslovne potvrdí; zmena dĺžky zruší starý náhľad a prepočíta výber pre celý nový interval.

## Orbitálny výber

Starlink pri UTC `2026-10-22T12:45:00Z` a bratislavskom výreze: pre 6 s bolo stabilne viditeľných 410 satelitov a paketový podgraf mal ID `64434, 57226, 49144`; po zmene na 30 s bolo stabilne viditeľných 389 a podgraf sa zmenil na `64434, 63583, 55398`. Počas 30 s malo 373 kandidátov geometrickú cestu k bráne. Editor teraz priamo zobrazuje počet aj ID aktívnych paketových satelitov, počet stabilne viditeľných a veľkosť celej platnej konštelácie. Tri aktívne satelity sú uzly vybranej komunikačnej trasy; celý katalóg sa zobrazuje geometricky na glóbuse. Aktívne body majú výraznejší obrys. Zarovnali sme tiež referenčnú polohu miesta na záložnom glóbuse s pozíciou použitou pri výpočte viditeľnosti.

## Spojenia a replay

Paketové spojnice majú tmavý obrys nad cestami a farbu podľa smeru alebo vetvy: auto→auto modrá, auto→RSU zelená, RSU→auto ružová, RSU↔satelit oranžová, priame auto↔satelit purpurová, medzisatelitné spojenie fialová. Klikateľný filter zostal podľa skutočných identifikátorov koncových uzlov a typu prenosu. Farby sú vrstva zobrazenia, nemenia fyzikálny model.

Čas replay sa číta z overeného scenára a zobrazuje ako aktuálny/celkový čas. Natívny 10 s nábeh je mimo verejnej osi. Posledná poloha auta z kroku SUMO `29,9 s` sa pri konci `30,0 s` podrží; orbitálne vzorky obsahujú aj čas `30,0 s`. Posledný paket nemusí vzniknúť presne v poslednej sekunde.

## Dôkaz úplného behu

- UI: načítanie štyroch áut a troch RSU na 2 040 cestných úsekoch, zmena 6→30 s a automatický prepočet orbitálneho podgrafu; preflight 4 autá, 3 RSU, 3 satelity.
- Uložený scenár `qa-30s-starlink-20261101`: `world.simulation.duration_s=30`, `sample_count=300`, aktívne ID `64434, 63583, 55398`.
- Beh `20261101T100528Z32e8b570` v pracovnom runtime: manifest `status=PASS`; štyri autá prijali krížové upozornenie cez satelit na inú RSU, 110 zo 111 priamych správ dorazilo k bráne a 110 odpovedí sa vrátilo; tri potvrdené handovery terminálov.
- Replay API: 1 200 polôh áut od 0 do 29,9 s, 303 satelitných polôh od 0 do 30,0 s, 4 190 spojení do 29,918 s. UI pri konci osi zobrazilo `30.00 / 30.00 s`; v strede boli farebné spojenia viditeľné nad cestami.
- `test_u9_full_duration_clock`, `test_u9_replay_bounded`, `test_u9_active_server`: 7 testov PASS; syntaktická kontrola troch zmenených JS súborov PASS.

Poznámka: výsledok dokazuje funkčnosť vybraného scenára a zobrazenia, nie presné parametre komerčnej služby Starlink. Fyzikálny satelitný prenos zostáva generický model SNS-3 DVB; dostupnosť celej konštelácie je geometrická, nie masové instancovanie všetkých viditeľných uzlov.
