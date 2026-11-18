# U9: skúšobné predlohy, register RSU a glóbus (31. 10. 2026)

## Rozsah

Šesť nových predlôh v jednom editore: rovnaké tri komunikačné vetvy na ručne zostavenom koridore a na cestách Bratislavy. Každá predloha je editovateľná a používa ten istý U9 preflight, SUMO, ns-3.38/SNS-3 3.38 a read-only verifikátor ako používateľský scenár. Ide o skúšobné scény, nie o definitívne experimenty BP. Predlohy sú v `config/u9-demo-*.json`, ich cestná sieť a dopyt v `data/inputs/u9-demo/`.

| Predloha | Scéna | Výskumná otázka | Uzly |
| --- | --- | --- | --- |
| `u9-demo-blank-v2v` | 7 spojených úsekov s vedľajšou vetvou | dosah lokálnej CAM bez RSU | 5 áut, 0 RSU |
| `u9-demo-blank-rsu` | rovnaké trasy | prenos CAM cez tri rozmiestnené RSU | 5 áut, 3 RSU |
| `u9-demo-blank-satellite` | rovnaké trasy | spoločná pozemná a satelitná vetva, upozornenie druhej RSU a priame auto–satelit | 5 áut, 3 RSU, 4 aktívne Iridium NEXT |
| `u9-demo-real-v2v-bratislava` | OSM, 2 km výrez | V2V na reálnych geometriách ciest | 4 autá, 0 RSU |
| `u9-demo-real-rsu-bratislava` | rovnaký OSM výrez | pozemná vetva | 4 autá, 3 RSU |
| `u9-demo-real-satellite-bratislava` | rovnaký OSM výrez | spoločná vetva s upozornením, priamym terminálom a handoverom | 4 autá, 3 RSU, 4 aktívne Iridium NEXT |

Ručne navrhnuté RSU ležia na rôznych miestach koridoru; vzdialenosti dvojíc sú približne 575, 1086 a 1485 m. Bratislavské RSU sú tiež **modelové**, vzdialené 205, 321 a 492 m. Reálna je geometria ciest OSM, nie ich prevádzka ani poloha simulovaných zariadení. Zdroj OSM výrezu je uložený vo `map_objects.sources` s hashom `839e9307bc6e2544672deb04bf82a9e45a762d76de51260ef872befd32a503bb`; načítaných 2046 záznamov, do jazdného grafu vstúpilo 2040 úsekov. Dopyt a rýchlosti sú syntetické. Trafikant `car0` je zdroj sledovanej správy; v satelitných predlohách je cieľovou RSU `rsu1` a vybrané auto má vlastný priamy terminál.

## Overenie

Všetkých šesť predlôh prešlo schémou `u9_editable_scenario.validate`, `bp_u9.preflight`, generovaním SUMO siete a FCD a následným **natívnym U9 `run` + `verify`**. Každé z 5/4 áut bolo vložené bez teleportu. V 60 s SUMO jazdy každé auto prešlo aspoň dva úseky; v prázdnej scéne všetkých päť áut, v Bratislave všetky štyri autá. Tým je otestované aj odbočovanie po predpripravenej trase; úplné pravidlá cestnej premávky sa nemodelujú.

| Predloha | Natívny výsledok a vybraná surová kontrola |
| --- | --- |
| blank V2V | PASS; 29 CAM TX, 62 príjmov zo 116 ponúknutých párov, 0 teleportov |
| blank RSU | PASS; 29 CAM generovaných, 110 miestnych prijímacích párov, 29 vzdialene prijatých reportov a 29 návratov |
| blank satelit | PASS; upozornenie cez satelit na `rsu1` dostali `car3` a `car4`; 3/3 priame správy sa vrátili, 2 terminálové handovery potvrdené |
| real V2V | PASS; 21 CAM TX, 63 miestnych príjmov, 0 teleportov |
| real RSU | PASS; 21 CAM generovaných, 122 miestnych prijímacích párov, 21 vzdialene prijatých reportov a 21 návratov |
| real satelit | PASS; upozornenie cez satelit na `rsu1` dostali všetky 4 autá; 4/4 priame správy sa vrátili, 3 terminálové handovery potvrdené |

Výsledky sú jedným deterministickým skúšobným behom každého profilu. Čísla nie sú odhadom spoľahlivosti v reálnej prevádzke ani štatistickým porovnaním technológií. Paketové okno je t = 10–12 s, pohyb trvá 60 s. Jeden dávkový pokus pri reálnej pozemnej vetve bol prerušený signálom pri práci so serverom; opakovanie z nového výstupného priečinka prešlo. Pôvodný neúplný priečinok zostal ako diagnostika. Plné výsledky a výstupy testov sú v `~/Desktop/BP-Simulator-Workspace/runtime/results/u9_runs/` a `~/Desktop/BP-Simulator-Workspace/preset-audit-20261031/`.
HTTP replay oboch satelitných predlôh sa otvoril ako overený beh: prázdny svet 160 polohových bodov a 420 udalostí, Bratislava 140 bodov a 361 udalostí. Detail konkrétneho paketu v bratislavskom behu vrátil 14 skutočných krokov od `CAM_UPER_TX`.

Prenosný `~/Desktop/BP-Simulator` a `BP-Simulator.zip` boli po zmene znovu zostavené. `unzip -tq` prešiel a `verify.py` potvrdil hash aj pin všetkých 11 556 súborov/odkazov; ZIP SHA-256 je `e4a3bdc76931299487d781578400d87a4d52a073f2570bafa9944ca619e4f42e`. Pôvodná verzia je zálohovaná v `~/Desktop/BP-Simulator-Workspace/backups/package-before-demo-20261031/`.

## Reálne evidované polohy RSU

Verejný [US DOT GIS register V2X RSU, vrstva september 2025](https://geo.dot.gov/server/rest/services/hosted/V2X_Deployment_Map_ULS_RSUs___Licenses___Updated_Basemap_Sept_2025_WFL1/FeatureServer/0) poskytuje bodové GeoJSON cez ArcGIS REST. Backend požaduje ohraničený 2 km WGS84 výrez, transformuje ho do lokálnej ENU mapy, kontroluje hranice, deduplikuje rovnaké súradnice a odpoveď drží v malej cache. Vo vrstve **Evidované RSU · USA** sa značky kreslia fialovo v glóbuse aj pracovnom výreze; dajú sa vypnúť. Referenčné body sa nepridávajú automaticky do rádiovej simulácie. Pri New Yorku (40.7415°, −73.94°, stred výrezu 1000 × 1000 m) API vrátilo 18 unikátnych bodov; pri posunutom výreze 40.742001° s pôvodnou kotvou sa v UI zobrazilo 25 značiek. Pri Bratislave 0. Test výrezu, deduplikácie, neplatného vstupu, neúplnej odpovede a vypnutia/zapnutia vrstvy prešiel.

Register označuje vrstvu ako „Active“, no tento experiment neoveruje aktuálnu prevádzku, presnosť jednotlivých záznamov, čas platnosti ani konkrétnu rádiovú technológiu. V Európe existujú napríklad [nemecké údaje o RSU v okolí Stuttgartu](https://www.govdata.de/suche/daten/roadside-units-r-its-s-und-c-its-services), ich otvorený súradnicový export však pri tomto teste nebol priamo dostupný cez stabilné API. Preto je voliteľná referenčná vrstva teraz len pre USA a bratislavské RSU sú hypotetické.

## Satelity na reálnej mape

Orbitálny náhľad vracia ECEF súradnice každého satelitu nad miestom a panel oblohy kreslí azimut/výšku pre viditeľné body; aktívny paketový podgraf je zvýraznený zlatou farbou. Satelity sa na glóbuse zobrazujú ako **subsatellitné body** v natívnej GeoJSON vrstve MapLibre. Pri cestnom zoome nad 12 sa tieto značky skryjú, pohľad na oblohu zostáva. Značky sú **geometria**, nie dôkaz spojenia ani zobrazenie fyzickej výšky satelitu nad povrchom.

Kontrola výberu konštelácií pre Bratislavu, požiadavka 4 aktívnych: Iridium NEXT 79 platných / 4 nad miestom / 4 aktívne; Globalstar 30 / 2 / 2; Starlink 10 627 / 412 stabilne nad miestom počas okna / 4 aktívne. Starlink má v čase náhľadu t = 10 s 416 bodov nad maskou; 473 objektov so šesťmiestnym katalógovým ID nie je pripojiteľných do paketového enginu. UI bolo vizuálne overené pre Iridium aj Starlink v reálnom režime.
Samostatne prešiel aj 60 s pohybový náhľad: Iridium 79 a Starlink 10 627 objektov, po 13 časových snímok; prvý objekt sa medzi začiatkom a koncom premiestnil o približne 446,5 km a 442,9 km.

### Oprava zobrazenia po spätnej väzbe

Prvé vizuálne overenie prehliadlo dva prechodové defekty. Samostatný canvas s ručnou projekciou bodov sa pri otáčaní a zoome vedel rozísť s mapou. Zároveň sa po asynchrónnom načítaní orbitálneho náhľadu niekedy neaktualizoval mapový zdroj, takže počítadlo ukazovalo objekty, ale glóbus nie. Canvas bol odstránený; všetky značky teraz vykresľuje rovnaký MapLibre renderer ako povrch. Aktualizácia zdroja sleduje identitu načítaného náhľadu aj pohybových dát. Pre svetlú reálnu mapu sú body kontrastne tmavé, pre tmavý prázdny svet svetlé.

V prehliadači bolo po oprave overené: Iridium NEXT 79 bodov, Globalstar 30 bodov a Starlink 10 627 bodov; reálny i prázdny režim, posun glóbusu, návrat na celú Zem, cestný zoom, vypnutie/zapnutie vrstvy a 60 s orbitálny náhľad Starlinku. Pri t = 10 s zobrazil Starlink 416 geometricky viditeľných bodov. Kontrolná snímka je v `~/Desktop/BP-Simulator-Workspace/globe-fix-20261031/starlink-real-after.png`. Zmena sa týkala iba prehliadača; predchádzajúcich šesť natívnych paketových behov sa neprepočítavalo.

Tri následné snímky od používateľa ukázali ďalšie vizuálne prekrývanie: kruhový **pohľad na oblohu** bol absolútne umiestnený nad glóbusom a v užšom paneli vyzeral ako druhá, odsunutá konštelácia. Tento graf je teraz samostatne **pod glóbusom**, jasne označený ako pohľad z RSU. Všeobecné CSS pravidlo pre všetky `canvas` sa zúžilo iba na záložný glóbus a ten je pri MapLibre režime vypnutý cez `display:none`. Tlačidlo „Celá Zem“ používa mierku 0,45 zodpovedajúcu stálemu pomeru strán panelu, takže planéta sa zmestí do pracovnej plochy. HTML načítava verziované CSS a mapový modul (`orbit6`), aby nové otvorenie stránky získalo aktuálne súbory. V čistej karte sa **pred** stlačením náhľadu zobrazilo Iridium 79/4 aj Starlink 10 627/416, pri posune zostali body na tej istej Zemi a panel oblohy nič neprekrýval. Konečná snímka: `~/Desktop/BP-Simulator-Workspace/globe-fix-20261031/starlink-before-preview-orbit6.png`. Už otvorená karta so starým JavaScriptom stále vyžaduje obnovenie stránky; zmena súboru na disku jej bežiaci kód nevymení.

## Hranice

Testy potvrdzujú funkčnosť týchto konkrétnych scenárov, nie všetkých kombinácií parametrov, ľubovoľnej hustoty mapy či kvalitu operátorskej siete. Satelitná RF/MAC vrstva je generický SNS-3 DVB model; konštelačné polohy sú archivovaný orbitálny vstup a brána, anténa, Doppler/steering a aplikácia sú výskumné modely. OSM geometria nie je meraný dopravný tok ani automaticky merané tienenie budov. Pred porovnávaním technológií ako výsledku BP treba s vedúcim zvoliť scenáre, metriky, nezávislé epochy/seedy a citlivostné rozsahy.
