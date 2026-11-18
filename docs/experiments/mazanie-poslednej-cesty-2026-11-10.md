# Mazanie poslednej cesty v editore — 10. 11. 2026

Používateľ chcel odstrániť aj jedinú cestu z návrhu. `viewer/simulator.js` predtým blokoval zmazanie pri `roads.segments.length <= 1`. Zároveň blokoval odstránenie auta pri dvoch alebo menej vozidlách, takže poslednú cestu s autami nebolo možné uvoľniť.

Editor teraz dovoľuje zmazať aj posledné auto a poslednú cestu. Pri zmazaní zdrojového auta sa vyprázdni alebo priradí `source_id` a zdroj vo `world.flows`; súvisiace DENM udalosti a politika auta sa odstránia. Cesta používaná trasou auta sa stále nesmie zmazať, kým sa auto nepresmeruje alebo neodstráni. Po zmazaní cesty sa odstránia len tie cestné uzly, ktoré už nepoužíva žiadny úsek. Prázdny návrh je stav editora; preflight pred skutočným behom naďalej vyžaduje platné autá a cestu.

V lokálnom editore bola vytvorená jediná ručná cesta, vybraná v zozname a zmazaná; zoznam potom ukázal `Cesty (0)`. V druhom pokuse mala jediná cesta jedno auto: kliknutie **Odstrániť** na ceste správne oznámilo závislú trasu, odstránenie posledného auta zmenilo zoznam na `Autá (0)` a následné odstránenie cesty na `Cesty (0)`. V zdrojovom projekte prešlo 38 testov a `refresh_study_code.py --check` pre 64 súborov.

Prenosný balík a ZIP prešli `verify.py` pre 10 231 položiek, `unzip -tq` a opätovným rozbalením a verifikáciou. Aktuálny pracovný adresár má tie isté dva zmenené súbory editora a preflight cez `run.sh` prešiel. V stále otvorenom staršom okne sa zmenil len `viewer/simulator.js` a jeho verzia odkazu v HTML; server na porte 8766 ich poskytuje s HTTP 200. Ostatné scenáre a výsledky zostali zachované.
