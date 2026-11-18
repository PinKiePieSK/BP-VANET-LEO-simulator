# U9: cestné objekty, nový výrez a spoločný komunikačný beh — 31. 10. 2026

## Aktuálne správanie

Reálna mapa načíta cestný graf z OpenStreetMap API pre celý pracovný výrez 2 × 2 km. Každý prijatý jazdný úsek je samostatný objekt s ID, geometriou, OSM way ID, dostupným názvom, triedou, smerovosťou a rýchlosťou. Všetky aktívne úseky sa zvýraznia tyrkysovo na lokálnej mape aj glóbuse. Kliknutie nástrojom **Vybrať** zobrazí parametre úseku; vybraný úsek sa zvýrazní zlatou farbou. Výber na glóbuse používa vzdialenosť od premietnutej geometrie v obrazovke, aby úzky vykreslený úsek nespustil omylom voľbu nového miesta.

Nové kliknutie na miesto v reálnej mape — aj na rovnaké miesto — založí nový rozpracovaný výrez. Odstráni jeho autá, RSU, trasy a predošlý cestný graf a načíta cesty nového výrezu. Uložené scenáre na disku tým nie sú prepísané; dajú sa znovu načítať. Prázdny kreslený režim je samostatný.

## Kontroly ciest a editora

V Bratislave pri 48,1486° N, 17,1077° E importer prijal 2 046 kandidátnych jazdných segmentov z 1 512 rôznych OSM way. Z nich 2 040 malo materiálnu geometriu po orezaní na 2 × 2 km a všetkých 2 040 bolo v aktívnom grafe, v lokálnom SVG prekrytí a vo výbere objektov. Zvyšných šesť nemalo materiálny úsek vo výreze. Pri druhom výreze pri 48,16° N, 17,1077° E bolo 1 310 kandidátov a 1 306 aktívnych úsekov. Zmena miesta v živom editore vynulovala autá i RSU; návrat na pôvodnú kotvu znova načítal 2 040 ciest a ponechal nulu objektov. Skúška výberu úseku na lokálnej mape ukázala OSM way 1103019200; samostatná skúška na glóbuse vybrala Hodžovo námestie, OSM way 96721878, triedu `secondary`, dĺžku 36 m a jednosmernosť bez zmeny miesta.

Nezávislý audit presného projektovania a orezávania prešiel nad uloženým vstupom; jeho skript je na ploche v `BP-Simulator-Workspace/road-object-audit-20261031/audit_projection.cjs`. Pomenovaných je 1 357 z 2 040 aktívnych segmentov, 1 000 je jednosmerných. Zastúpené sú triedy `residential`, `service`, `secondary`, `tertiary`, `primary`, `unclassified`, `living_street` a spojky. Uložený `world.json` prešiel schémovou validáciou. Zamerané Python testy: 11/11 PASS. Syntax kontrola upravených JavaScript a Python súborov: PASS.

## Paketová skúška po overení grafu

Na bratislavskom výreze bol cez editor uložený scenár `bratislava-4auta-3rsu-iridium-20261031`: štyri autá na trasách, tri RSU a štyri aktívne satelity Iridium NEXT z archívu (80 záznamov, 79 platných pre epochu, štyri nad maskou miesta). Preflight PASS. Úplný beh `combined_advanced` má ID `20261031T092453Z262c6213`; overovač `bp_u9.py verify` aj `run-manifest.json` uvádzajú **PASS**. SUMO vložilo 4/4 áut, každé malo 600 FCD vzoriek v 60 s, bez kolízie, teleportu alebo varovania. Simulácia vytvorila 21 RSU reportov, 16 prijala brána a upozornenie cez satelit a cieľovú `rsu1` prijali všetky štyri autá. Priama auto–satelitná vetva mala štyri odoslané CAM a štyri odpovede. Potvrdené boli tri handovery terminálov: dve RSU a jedno priame auto. Prehrávač zobrazuje postupné paketové udalosti a obsah.

Vstupy, surový beh a snímky sú mimo čistého prenosného balíka v `/home/samuel-petrik/Desktop/BP-Simulator-Workspace/road-object-audit-20261031/`. Živý scenár je tiež v `Desktop/BP-Simulator-Workspace/runtime/config/u9-scenarios/` a dá sa načítať vo webovom editore.

## Rozsah tvrdenia

„Všetky cesty“ tu znamená všetky jazdné OSM úseky prijaté importérom v definovanom výreze, ktoré spĺňajú jeho filtre prístupu a majú po orezaní materiálnu geometriu. Online OSM sa môže zmeniť a jeho dáta nie sú zárukou úplnosti alebo aktuálnosti skutočnej siete. Zjednodušený graf nepreberá všetky obmedzenia odbočenia, semafory ani reálnu intenzitu dopravy. Budovy sú v U9 len vizuálne. Výber Iridium satelitov je geometrický; paketový satelitný model je experimentálny generický DVB a nepreukazuje dostupnosť skutočnej operátorskej služby.

## Obnova po limite OSM API — 1. 11. 2026

Pri opakovanom importovaní väčšieho výrezu OSM editačné API vrátilo HTTP 509 s časom ďalšieho pokusu. Doterajší import zahodil aj úspešne stiahnuté čiastkové dlaždice a editor zobrazil konečnú chybu. Import teraz ukladá každú overenú XML dlaždicu do externého `BP-Simulator-Workspace/cache/osm` s SHA-256, dátumom získania a presným bbox. Opakovaná požiadavka používa cache bez siete; čas `retrieved_at` v zdroji scenára ostáva dátumom pôvodného stiahnutia, nie opätovného použitia. Server vracia pri limite HTTP 429 a `retry_after_s`; editor opakuje požiadavku najviac šesťkrát podľa času určeného serverom. Pri zmene miesta alebo mapového režimu sa čakajúci pokus zruší.

Kontroly: dva unit testy cache a cooldown PASS; živý 500 × 500 m bratislavský import a jeho opakovanie dali 185 jazdných úsekov a identický pôvodný timestamp, s prostredím 588 budov a 625 vzoriek terénu. Lokálny HTTP server vrátil z cache 200 s rovnakými počtami; simulovaný limit vrátil 429 s `retry_after_s=30`. Pokus o 4 km výrez stále narazil na externý 509, ale tri úspešné veľké dlaždice zostali v cache na ďalší pokus. Úplné načítanie 4 km pri trvajúcom limite preto nie je týmto testom potvrdené; jeho dostupnosť závisí od OSM servera. Izolovaná testovacia karta s nasimulovaným HTTP 429 navyše zobrazila „Pokus 1/6; cesty automaticky načítam znova za 30 s“ bez konečnej chyby. Zdroj, runtime, prenosný priečinok a ZIP sú synchronizované; manifest 11 456 položiek, ZIP a SHA-256 kontrola prešli.
