# Rozdelenie vstupov auta podľa simulátora — 13. 11. 2026

Pri vybranom aute má objektový panel dve karty. **Vstupy SUMO** ukazujú ID vozidla a typu, rýchlosť, počiatočnú a prípadnú cieľovú polohu, smer a celú usporiadanú trasu. Zobrazené sú pevné pravidlá odchodu, pruhu a vstupnej rýchlosti, ktoré sa líšia medzi ručnou a OSM mapou. Nižšie je spoločný `vType` model všetkých áut: zrýchlenie, brzdenie, sigma, rozmery, odstup, faktor rýchlosti a pri ručnej mape maximálna rýchlosť typu. Karta ukazuje časový krok, začiatok, seed, koniec behu a požadovaný FCD výstup. Seed a koniec behu sú spoločné aj s ďalšími časťami scenára.

**Ostatné vstupy** obsahujú referenčné auto CAM, deklarované technológie, individuálnu politiku pozemného rádia a DENM. Tieto hodnoty sa nezapisujú do `vehicles.rou.xml`. Úpravy spoločného pozemného rádia ostávajú v Technických parametroch; táto karta zoskupuje vstupy konkrétneho auta.

Ručne zadaná trasa používa ID smerových hrán, napríklad `road0_forward`. Pred zmenou stavu editor preverí existenciu hrán, jednosmerky, napojenie uzlov, zakázané OSM odbočenia, dĺžku trasy a polohy odchodu/príchodu. Kliknutie na cieľ na mape a generovanie trasy ostávajú dostupné. Počiatočná a cieľová poloha sú lokálne metre; exportér ich po `netconvert` premieta na výslednú sieť. Dosiahnutá jazda, vnútorné pruhy, zápchy ani presná efektívna rýchlosť nie sú vstupné hodnoty editora.

Odchod každého auta zostáva **0 s** a krok SUMO **0,1 s**, pretože aktívny natívny beh vyžaduje spoločný štart s komunikáciou; editor ich ukazuje ako pevné, nie ako falošne editovateľné. Pri reálnej mape sa do SUMO zapisuje individuálny `maxSpeed`, `departSpeed="max"` a `departLane="best"`; pri ručnej mape spoločný typ `passenger` s nastaviteľným `maxSpeed` a číselný `departSpeed` každého auta. Počet áut, ich umiestnenie a trasa zostávajú vstupmi scenára, nie meranou premávkou.

## Overenie

- V samostatnom headless Firefoxe boli pri vybranom aute viditeľné dve neprekrývajúce sa karty. Cestný SUMO panel sa pri výbere auta skryl, aj keď zostal aktívny nástroj kreslenia ciest.
- Zmena rýchlosti na 54 km/h zapísala 15 m/s; zrýchlenie na 3,2 m/s², seed na 12345, trvanie na 4 s a ručne zadaná dvojúseková trasa sa objavili v stave editora. Druhá karta obsahovala iba komunikačné nastavenia auta.
- `simulator_sumo.validate` prijal vzniknutý svet. `make_inputs` zapísal pri ručnej mape `route_car0` s `road0_forward road1_forward`, `departSpeed="15"`, `departPos="20"` a spoločný `vType` s `accel="3.2"`. Pri reálnej mape ten istý vstup vytvoril individuálny `passenger_car0`, `maxSpeed="15"`, `departSpeed="max"`, `departLane="best"`.
- Skutočný `netconvert` a SUMO vložili obe skúšobné autá, FCD obsahovalo `car0` aj `car1`; manifest mal seed 12345 a trvanie 4 s. Skúška nepreukazuje realizmus vodičského modelu ani presnosť OSM topológie.

Zmenené aktívne súbory prešli syntaktickou kontrolou JavaScriptu a študijná kópia 64 súborov prešla obsahovou kontrolou. Zdroj, pracovný runtime, bežiaci server, prenosný balík a ZIP vracajú rovnaké bajty štyroch zmenených súborov. Manifest balíka overil 10 231 súborov a odkazov; ZIP nemá poškodený záznam. Test aktívneho servera prešiel.
