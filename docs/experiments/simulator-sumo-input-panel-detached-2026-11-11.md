# Cestné vstupy SUMO a krátke odpojené cesty — 11. 11. 2026

## Rozsah zmeny

Na požiadavku používateľa panel pri pracovnej mape zobrazuje iba hodnoty, ktoré vytvárajú cestné vstupy SUMO. Súhrn uvádza počet uzlov `road.nod.xml`, smerových hrán `road.edg.xml` a explicitných spojení `road.con.xml`. Po výbere cesty ukazuje ID a súradnice uzlov, ID oboch smerových hrán, ich smer, počet pruhov, limit v m/s aj km/h, presné body tvaru a prípadné explicitné výjazdy. Odstránené sú informácie o zdroji OSM, verzii importu, spôsobe orezania, značkách vrstvy/prístupu a pôvode rýchlosti či pruhov. Staršie editovacie ovládanie cesty zostáva dostupné pod týmto prehľadom.

Časové značky `*:conditional` sa už z nového importu neukladajú do cestných záznamov ani do súhrnu zdroja. Podmienené relácie odbočenia sa neimportujú. Pri načítaní staršieho scenára sa tieto polia vyčistia z pracovných a globálnych cestných údajov. Validator ich ešte prijíma v starších uložených súboroch kvôli spätnej kompatibilite; do SUMO ich nevysiela.

V režime reálnej mapy sa opäť odstránia krátke izolované komponenty cestného grafu s celkovou dĺžkou pod 100 m. Najväčší komponent, komponent s trasou auta alebo ručným spojením a samostatné komponenty aspoň 100 m zostanú. Filter nemení súradnice uzlov, nespája medzery a neodstraňuje krátke, ale pripojené spojky či mini výbežky. Úseky skryté z pracovného grafu sa nedostanú ani do vstupu SUMO.

## Overenie

- Uložený scenár `realna-d1-pozemna`: pred filtrom 5 811 aktívnych úsekov, po filtri 5 722; zachovaných 6 áut a 2 RSU. Zostalo 13 komponentov a **žiadny nechránený odpojený komponent kratší než 100 m**.
- Panel v oddelenom headless Firefoxe obsahoval iba cestné XML údaje. Pri vybranej ceste zobrazil limity 11,111 m/s (40 km/h) a 13,889 m/s (50 km/h) pre opačné smery, jeden pruh v každom smere a súradnice bodov v poradí zodpovedajúcom obom hranám. Zoznam má vlastný posuvník.
- Editorový `/api/simulator/editor/check` vrátil HTTP 200. `netconvert` vytvoril 27 750 hrán a 36 302 spojení; zo 302 zakázaných prechodov sa v sieti nevyskytol ani jeden. Krátky 1 s štart SUMO s trasami áut prešiel. Existujúce uložené scenáre a historické výsledky neboli prepísané.

## Prenos do verzie spúšťanej ikonou — 13. 11. 2026

Kontrola odhalila, že pracovný runtime a balík na ploche ešte obsahovali staršie súbory z 10. 11.; zdrojové filtrovanie z tejto fázy sa preto v ikone neuplatňovalo. Jedenásť novších súborov rozhrania a spracovania ciest sa zosúladilo medzi zdrojovým projektom, pracovným runtime a prenosným balíkom. Aktualizoval sa manifest, identita pracovného balíka a ZIP. Bežiaci server teraz vydáva nový `earth-map.js`; Python modul importu, načítaný už spusteným procesom, sa plne obnoví po ďalšom spustení ikony.

Izolovaná skúška filtra potvrdila vyradenie 30 m odpojeného úseku a jeho uzlov, pričom 120 m samostatný úsek, pripojené cesty a 20 m úsek použitý autom ostali. Tri cielené Python testy OSM importu prešli. Pracovné zdroje sa bajtovo zhodujú s projektom; ZIP prešiel kontrolou štruktúry a manifest balíka overil 10 231 súborov a odkazov. Nový úplný beh SUMO/ns-3 v tomto prenose nevznikol; pôvodná integrácia filtra je overená vyššie.
