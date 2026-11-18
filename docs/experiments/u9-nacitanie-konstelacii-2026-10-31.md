# U9 — načítanie satelitov na glóbuse, 31. 10. 2026

## Príčina a oprava

Po prepnutí technického profilu z pozemného na satelitný sa orbitálny katalóg automaticky nevyžiadal. Pri novom prázdnom návrhu sa načítal až po inom úkone, typicky po prehrávaní. Mapový modul navyše pri každom bežnom prekreslení znovu skladal a prepočítaval všetky body konštelácie a kruhový náhľad oblohy. Pri Starlinku ide o viac než 10-tisíc bodov.

`viewer/u9-simulator.js` teraz automaticky vyžiada orbitálny náhľad po prepnutí na satelitný profil a po vložení prvej RSU. Zobrazuje stav načítavania a chybu aj priamo pri glóbuse; bez RSU vysvetlí potrebný krok. `viewer/u9-earth-map.js` prepočítava a posiela GeoJSON do MapLibre len pri zmene konštelácie, času, vrstvy alebo aktívneho podgrafu. Zmena mierky iba aktualizuje text mierky.

Pri zmene predlohy, výrezu alebo miesta sa zruší predošlý stav načítavania. Záložný canvas používa rovnakú hlášku ako MapLibre počas prepnutia štýlu.

## Meranie a prijímacia kontrola

Priame volanie lokálneho orbitálneho backendu na tomto stroji: Iridium NEXT 79 polôh za 0,107 s; Globalstar 30 polôh za 0,066 s; Starlink 10 627 polôh za 1,506 s, odpoveď približne 0,633 MiB. Samostatný 60 s pohybový náhľad Starlinku vytvoril 13 snímok za 1,67 s a približne 3,99 MiB JSON. Tieto časy zahŕňajú serverový výpočet, nie výkres GPU.

V čistej karte prehliadača sa predloha Iridium zobrazila bez prehrávania. Po výbere Starlinku sa okamžite ukázalo „Načítavam konšteláciu…“ a následne 10 627 satelitov, z toho 416 geometricky nad maskou pri danom mieste. Globalstar ukázal 30 objektov, z toho 2 nad maskou. Starlink prešiel v prázdnom aj reálnom mapovom režime a obrazovo bolo potvrdené, že body ležia na glóbuse. Prepnutie pozemnej predlohy na satelitný profil samo vyvolalo načítanie 79 objektov Iridium. Nový prázdny návrh upozornil na chýbajúcu RSU a po jej vložení automaticky načítal konšteláciu. Vypnutie a zapnutie satelitnej vrstvy Starlinku nezmenilo počet objektov. JavaScript troch upravených súborov prešiel syntaktickou kontrolou Node.js. Prenosný balík prešiel kontrolou 11 556 súborov a odkazov, ZIP prešiel testom `unzip -tq` a SHA-256 kontrolou.

Záverečný test po nasadení: počas načítavania Starlinku bol otvorený nový prázdny návrh; glóbus korektne prešiel na „Pridaj RSU“ a nezostal v starom stave. Náhľad zobrazuje archivované orbitálne dáta a geometrickú viditeľnosť. Aktívny generický DVB podgraf ostáva oddelený; body celej konštelácie nie sú tvrdením o reálnom pripojení k službe operátora. Pri veľmi slabom grafickom procesore môže prvý výkres 10 627 bodov stále trvať dlhšie než backendový výpočet.

## Doplnenie po hlásení o nekonečnom koliesku

V používateľskej otvorenej karte bol profil V2V bez RSU. V tomto profile bol výber konštelácie deaktivovaný a CSS dával každému deaktivovanému tlačidlu kurzor `wait`, takže vyzeralo ako stále načítavanie. Orbitálny náhľad bol navyše predtým zviazaný so satelitným komunikačným profilom. Zmenené: výber konštelácie a prehranie jej geometrie funguje aj pri V2V/pozemnom profile a bez RSU. Výber aktívneho paketového podgrafu zostáva dostupný iba v satelitnom profile s RSU. Základná orientačná výšková maska pre samotný glóbus bez satelitného profilu je 10°. Kurzory zakázaných tlačidiel už nevyzerajú ako prebiehajúce načítanie.

Asynchrónne odpovede pohybového náhľadu sa viažu na konkrétny výber; stará odpoveď po rýchlom prepnutí neprepíše novú konšteláciu. Lokálny test bez RSU načítal Iridium 79, Globalstar 30 a Starlink 10 627 satelitov. Rýchly sled Starlink→Globalstar skončil na Globalstare 30; náhľad pohybu vo V2V sa spustil a zastavil. Samostatná skúška satelitnej predlohy ďalej vybrala 4 aktívne objekty z Iridia a po prepnutí zobrazila 10 627 objektov Starlinku s 4 aktívnymi v generickom DVB podgrafe. Test prešiel na oddelenom porte 8766 aj po nasadení na pôvodnej adrese 8765. Testovací server 8766 bol ukončený; produkčný server 8765 ostal zapnutý.

## Oprava inicializácie po prepnutí mapy — 1. 11. 2026

Nový prázdny alebo reálny návrh a prepnutie medzi mapovými režimami mazali orbitálny náhľad. Nasledujúce načítanie bolo podmienené neexistenciou `scenario.satellite`, hoci tento objekt existuje aj v prázdnom návrhu; satelity sa preto zobrazili až po ručnom prepnutí konštelácie. Cestný import navyše volal `markDirty`, ktorý znova mazal už načítaný pohyb.

Editor teraz po oboch typoch prepnutia spustí náhľad celej konštelácie alebo výpočet viditeľnosti, ak už má terminály. Bežná úprava mapy zachová geometrický orbitálny náhľad a zastaví len prehrávanie; pri zmene orbitálnych vstupov sa náhľad stále zruší. Pri obnove rozpracovaného mapového režimu sa obnoví aj výber jeho konštelácie. Úvodné načítanie má poistku aj pre prípad, že sa scenár pripraví pred registráciou glóbusu.

Izolovaná karta na bežiacom lokálnom serveri `:8766` ukázala bez ručného prepnutia 80 satelitov Iridium pri štarte a po novej reálnej mape. Globalstar zobrazil 33 satelitov aj po novej prázdnej mape; Starlink 11 140 aj po novej reálnej mape. Prepnutie medzi zachovanými prázdnym a reálnym návrhom s odlišnými konšteláciami obnovilo správny výber a 80, respektíve 33 objektov. Údaje pochádzajú z aktuálneho pripnutého archívu, preto sa líšia od historických počtov vyššie. Test kontroloval prvky a ich počet v mapovom GeoJSON, nie doručovanie paketov. Zdroj, bežiaci runtime, prenosný priečinok a ZIP obsahujú rovnaké tri zmenené súbory; manifest 11 456 položiek, `unzip -tqq` a SHA-256 kontrola prešli.
