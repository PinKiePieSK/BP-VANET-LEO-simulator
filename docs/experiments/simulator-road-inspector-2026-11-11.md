# Panel cesty a spoločné uzly — 11. 11. 2026

## Rozsah

V `viewer/simulator.js` pribudol pre vybranú cestu zoznam všetkých bodov v lokálnych metroch. Konce majú skutočné ID grafových uzlov, medzibody majú index v `shape`. Pri úprave konca sa najprv skontrolujú kandidátne tvary všetkých ciest naviazaných na uzol a potom sa naraz zmení uzol aj ich koncové body. Kontrola odmieta susedné body bližšie ako 1 m, skrátenie cesty za nástup alebo cieľ auta a súradnice mimo pracovnej plochy. Po zmene sa SVG vrstva prekreslí podľa verzie cestného grafu.

Panel má voľbu obojsmernej a jednosmernej prevádzky v smere od začiatku ku koncu, samostatný výber klasifikácie ručnej cesty, jeden číselný výber limitu a pôvodnú voľbu pruhov v každom smere. Jednosmernosť sa neuloží, ak existujúca trasa auta na úseku obsahuje opačný smer. Zobrazené `roadX_forward` a prípadné `roadX_reverse` sú odvodené ID hrán SUMO. Nová ručná cesta má predvolenú triedu `urban`; výber triedy nemení limit a výber limitu nemení triedu. `road_class` zostáva metadátum pre generovanie náhodnej dopravy. Body OSM cesty sú len na čítanie, lebo ich lokálna geometria sa pri obnovení výrezu znovu premieta z globálnych súradníc.

## Overenie

- Firefox 159 headless načítal aktuálny `simulator.js`; syntaktická kontrola cez `new Function` prešla.
- V prehliadači prešlo 9 cielených kontrol: posun spoločného uzla zmenil oba úseky; medzibod iba vlastný úsek; neplatná geometria a poloha auta zostali odmietnuté; zobrazili sa všetky body, celý rozsah výberu limitu a odvodené SUMO ID; opačná trasa auta blokovala jednosmernosť a po odstránení trasy sa jednosmernosť správne uložila.
- Pri behu servera cez projektovú `.venv` sa v skutočnom editore vytvorili dve ručné cesty. Editor ich spojil cez rovnaké ID uzla; zmena súradnice v paneli premiestnila uzol aj obe geometrie. SVG vrstva obsahovala nové súradnice oboch ciest (`300,3870` pri lokálnom Y = 130 m vo svete vysokom 4000 m). Táto kontrola neukladala scenár ani nespúšťala simuláciu.
- Používateľský Firefox bol spustený na `127.0.0.1:8766` z pracovného runtime `~/Documents/BP-Simulator-Pracovny-parove-20261103/runtime`, ktorý mal ešte staré súbory. Rovnaká oprava panela sa preniesla do jeho `viewer/` bez prepísania U9 špecifických funkcií v JavaScripte. Živý server následne vrátil aktualizované HTML, JS a CSS. V oddelenej headless karte tohto servera prešla integrovaná kontrola dvoch ciest, spoločného ID uzla, panela, zmeny súradnice aj okamžitého prekreslenia SVG. Server ani používateľská karta sa pri tejto kontrole nereštartovali.
- Po upresnení používateľa bola klasifikácia ručnej cesty vrátená ako samostatný výber bez väzby na rýchlostný limit. V samostatnej headless karte živého runtime prešli kontroly: nová cesta má triedu `urban`; zmena triedy na `motorway` nemení rýchlosť; nastavenie 30 km/h zachová `motorway`; ďalšia zmena triedy na `living_street` zachová 30 km/h. Panel ukazuje vysvetlenie odlišných účinkov oboch volieb.
- Vizuálna kontrola panelu v headless Firefox potvrdila dvojicu vstupov X/Y a vnorený posuvník pri viacerých bodoch. Použitý bol vložený testovací svet; screenshot nie je dôkazom behu simulácie.
- `python3 scripts/refresh_study_code.py --check` po obnove študijných kópií: PASS, 64 aktívnych súborov.

Táto úprava nemení schému vstupu do SUMO ani paketové správanie. V `tools/simulator_sumo.py` sa do `road.nod.xml` zapisuje ID/X/Y každého grafového uzla a do `road.edg.xml` ID, koncové uzly, tvar, počet pruhov a rýchlosť každej povolenej smerovej hrany. OSM názov, way ID a `road_class` sa ako atribúty SUMO hrany nezapisujú.
