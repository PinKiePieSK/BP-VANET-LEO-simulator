# Uzavretie cestných vstupov simulátora — 11. 11. 2026

## Stav cestnej časti

Hlavný panel pri označenej ceste alebo kreslení ukazuje uzly, smerové hrany, presnú rýchlosť v m/s odovzdávanú do `road.edg.xml`, počet pruhov, body tvaru a explicitné spojenia `road.con.xml`. Prepočet na km/h je označený ako približný. Technická stránka už nezobrazuje ani neupravuje neúčinné spoločné pole ako skutočný smerový vstup: pre každú existujúcu hranu ukazuje a umožňuje upraviť jej limit a pruhy, pri jednosmerke iba jeden smer. Staré scenáre bez smerových polí používajú spoločné polia ako záložné hodnoty. Zmena smerového parametra v technickej stránke sa zapíše do živého editora a označí scenár za zmenený.

Technická stránka pre porovnanie uvádza počet vstupných smerových hrán, jednosmerných úsekov, maximum pruhov v jednom smere a rozsah smerových limitov odovzdaných do `road.edg.xml`. Ukazuje počet aj zoznam pravidiel zakázaných odbočení, z ktorých exporter zostaví povolené spojenia. Trieda cesty je zreteľne označená ako vstup generátora áut, OSM way ako identifikátor zdroja; ani jedno sa nezapisuje do hrany SUMO. Pevné vypnutie normalizácie súradníc v `netconvert` je uvedené na technickej stránke. Výsledná podoba križovatiek a efektívne hodnoty siete sú výstup `road.net.xml`; verzie nástrojov a príkazy sú v manifeste overeného behu.

Pri opätovnom importe OSM zostávajú ručne nastavené rýchlosti aj pruhy zachované samostatne podľa smeru. Generátor áut pri vážení cesty berie aktuálne smerové pruhy: pri obojsmernej ceste ich priemer, pri jednosmerke povolený smer. Pri symetrických cestách ostáva pôvodná váha.

## Overenie

- V samostatnom headless Firefoxe technická stránka živého scenára zobrazila `13.89` a `9.123456` m/s a 4/2 pruhy pre oba smery jednej cesty. Pri jednosmernej ceste s 5 pruhmi zobrazila len jeden limit a jeden počet pruhov; súhrn ukázal maximum 5.
- Úprava opačného limitu na `11.234567` m/s a počtu pruhov vpred na 6 sa preniesla do editora bez zmeny opačných pruhov. Hlavný panel ukázal presnú hodnotu a `road.edg.xml` obsahoval `road0_forward` so 6 pruhmi a limitom `13.89`, `road0_reverse` s 1 pruhom a limitom `11.234567`.
- Na uloženom OSM scenári `realna-d1-pozemna` sa po vynútenom opätovnom importe zachoval ručný limit `12.345678` m/s vpred a pôvodný limit `8.33` m/s späť; zachovaná bola aj globálna kópia a pôvod `manual`. Uložený scenár ani historické výsledky sa nemenili.
- Úprava predného limitu z technickej stránky v tomto OSM scenári prešla cez globálnu kópiu a `/api/simulator/editor/check` vrátil HTTP 200 pre 6 áut a 2 RSU.
- Pri otvorení Technických parametrov počas načítania OSM sa stránka po dokončení importu obnovila bez zásahu používateľa: editor aj technická stránka ukázali 5 722 ciest a 302 zakázaných smerových odbočení.
- `netconvert` na skúšobnej 6/1-pruhovej ceste zachoval šesť a jeden pruh. Vstup `road.edg.xml` mal rýchlosť opačnej hrany `11.234567` m/s, ale výsledný `road.net.xml` ju v overenej inštalácii zapísal ako `11.23` m/s. Preto UI výslovne rozlišuje presný vstupný XML limit od výslednej siete SUMO; na porovnávanie vykonaných scenárov treba kontrolovať aj `road.net.xml`.
- Študijná kópia bola obnovená a kontrola `scripts/refresh_study_code.py --check` prešla.

Rozsah ďalšej práce: typ auta, jeho trasa, odchod, seed a časový krok sú dopravné vstupy SUMO, ktoré sa prejdú v nasledujúcej časti o autách. Tento záznam neoznačuje výslednú sieť vytvorenú `netconvert` za používateľom poslaný vstup.
