# Pracovný zošit: osem skutočných študijných blokov k BP

**Stav k 5. 11. 2026.** Tento zošit je pre človeka, ktorý už dlho nekódil. Jeden blok je **45–60 minút práce**: vysvetlenie, čítanie niekoľkých konkrétnych miest v kóde, vlastná úloha a kontrola odpovede. Nemusíš najprv čítať celé súbory. Pracuj vždy s aktívnym projektom ns-3.38/SNS-3 3.38 v tomto priečinku. [Katalóg všetkých vstupných polí](studium-bp-katalog-vstupov.md) používaj ako slovník, [podrobný sprievodca](studium-bp-ako-funguje-simulator.md) ako súvislý výklad.

Použijeme stále ten istý [uložený satelitný scenár](../config/scenarios/navrh-koridor-satelit.json), jeho [svet](../data/inputs/user/navrh-koridor-satelit/world.json) a [autá](../data/inputs/user/navrh-koridor-satelit/demand.json). Existuje aj [uložený beh](../results/simulations/scenar-navrh-koridor-satelit-20261103/run-manifest.json) s [paketovou stopou](../results/simulations/scenar-navrh-koridor-satelit-20261103/native/baseline/trace.csv). Sú to konkrétne vstupy a konkrétna modelová stopa, nie meranie reálnej siete.

## Ako čítať kód, keď si vyšiel z cviku

Každý riadok čítaj v poradí **vstup → podmienka → akcia → zaznamenaný výsledok**. Pri Pythone `s['radio']['tx_power_dbm']` znamená „v slovníku `s` otvor `radio` a v ňom `tx_power_dbm`“. Pri C++ `if (condition) { ... }` znamená „ak podmienka platí, vykonaj vnútro“. `Simulator::Schedule(...)` vloží akciu do budúceho času; **neznamená, že paket prišiel**. `Send(...)` je pokus odovzdať ho ďalšej vrstve; `ReceiveCallback` a `DENM_UPER_RX` sú dôkazy prijatia v modeli. Ak nerozumieš jednému typovému názvu, zatiaľ ho preskoč a sleduj hodnoty a rozhodnutia.

Rozvrh: **deň 1 bloky 1–4, deň 2 bloky 5–8**. Medzi blokmi si daj prestávku. Každá kontrola odpovede je hneď za úlohami, aby si sa nezasekol na syntaxi.

## Deň 1, blok 1 — kto je kto v jednej správe (50 min)

### Výklad: 15 min

VANET znamená, že vozidlá tvoria sieť s inými vozidlami alebo cestnou infraštruktúrou. **V2V** je auto → auto. **V2I** je auto → RSU. **I2V** je RSU → auto. Cestné rádio používa v projekte ITS-G5, konkrétne 802.11p v režime OCB. **RSU** je cestná stanica. **UT** je satelitný terminál pri RSU. Auto v aktívnom projekte satelitný terminál nemá.

Jedna DENM sa môže dostať dvoma spôsobmi: miestne od auta k ďalšiemu autu, alebo od auta k zdrojovej RSU, ďalej cez jej LAN a UT do modelového satelitu, brány a vzdialenej RSU, ktorá ju pošle ďalším autám. Vzdialený úsek používa IP/UDP ako obálku prenášaného obsahu. **CAM** je priebežný stav auta; **DENM** je správa o udalosti. Cieľom nie je predstaviť si, že pôvodný Wi-Fi rámec letí celou cestou nezmenený. Pri každom úseku vzniká rámec či paket vhodný pre danú sieť. [Celá cesta s obrázkom](studium-bp-ako-funguje-simulator.md#1-čo-sa-v-práci-skúma).

### Čítanie kódu: 15 min

V [scenári](../config/scenarios/navrh-koridor-satelit.json) nájdi `source_id`, `rsu_id`, `alert_target_rsu` a `node_policy.rsus`. Zatiaľ ignoruj ostatných približne sto riadkov. Tu je `car0` zdrojové auto, `rsu0` zdrojová RSU a `rsu1` cieľová RSU. Obe RSU majú `ground=true` aj `satellite_backhaul=true`. Kód [`unified_policy`](../tools/bp_u9.py) kontroluje, že politika patrí presne existujúcim autám a RSU. Kód [`preflight`](../tools/bp_u9.py) pri satelitnom behu vyžaduje zdrojové auto s `ground="all"` a obe aktívne RSU.

Všimni si rozdiel medzi **deklaráciou uzla** a **rozhodnutím poslať správu**. `node_policy` dovolí alebo zakáže cestu; samotná hodnota `true` paket nevytvorí. DENM vzniká až pri udalosti a musí byť skutočne prijatá RSU.

### Tvoja úloha: 15 min

Nakresli päť obdĺžnikov: `car0`, `rsu0`, `UT/SAT/GW`, `rsu1`, `car3`. Medzi nimi napíš presne: **ITS-G5**, **LAN/IP/UDP**, **SNS-3 DVB**, **LAN/IP/UDP**, **ITS-G5**. Potom nahlas povedz, ktorý úsek je V2I, ktorý I2V a kde sa objaví satelit.

### Kontrola: 5 min

`car0 → rsu0` je V2I po miestnom rádiu. `rsu1 → car3` je I2V po inom miestnom rádiu. Uprostred je modelový satelitný backhaul medzi RSU, nie priame satelitné rádio auta. Bez prijatia v `rsu0` sa most nemá čo pokúsiť preposlať.

## Deň 1, blok 2 — tri JSON súbory a jeden časový údaj (55 min)

### Výklad: 15 min

Editor ukladá tri odlišné veci. `world.json` je **miesto a dopravné prostredie**: plocha, cesty, RSU, georeferencia, model vozidla. `demand.json` je **konkrétny dopyt vozidiel**: autá, trasy a východiskové rýchlosti. `scenario.json` je **pokus**: zdroj a cieľ, rádio, satelit, sieťová politika, DENM udalosti. V aktuálnom behu zoznam áut z `demand.vehicles` prepíše `world.vehicles`. Názov `world.flows` môže zavádzať: `execution="not_implemented"` je záznam zámeru v editore, nie vykonaný tok paketov.

Kód ich najprv **validuje**. Validácia nie je simulácia. Ak `duration_s=60` a `sample_count=600`, počet vzoriek je `60×10`, lebo krok je 0,1 s. `utc_origin` je absolútny čas pre výpočet polohy satelitu; `at_s=5.0` je relatívny čas udalosti od začiatku behu. DENM teda vzniká na piatej sekunde simulácie. [`bp_u9.preflight`](../tools/bp_u9.py) kontroluje zhodu týchto hodnôt.

### Čítanie kódu: 20 min

V [`bp_u9.py`](../tools/bp_u9.py) nájdi `def preflight(s):`. `s` je scenárový slovník. Hľadaj riadok s `sample_count']==duration*10`; prečítaj ho ako „počet vzoriek sa musí rovnať trvaniu krát desať“. Potom nájdi `def runtime_inputs(s,out):`. Táto funkcia pripravuje kopiu vstupu pre SUMO a môže pridať krátky dobeh, aby v poslednom komunikačnom okamihu nezmizlo vozidlo. Nemýľ si **dĺžku dopravného behu** s **komunikačným oknom**.

V [dopyte](../data/inputs/user/navrh-koridor-satelit/demand.json) nájdi `car0.depart_s=0` a jeho trasu. `depart_speed_mps=10` je vstup v metroch za sekundu, približne 36 km/h. To **nie je tvrdenie**, že auto bude mať 10 m/s vo všetkých waypointoch; pohyb mení SUMO.

### Tvoja úloha: 15 min

Bez čítania odpovede vypíš šesť riadkov: `duration_s`, `sample_count`, `utc_origin`, `denm_events[0].at_s`, `car0.depart_s`, `car0.depart_speed_mps`. Ku každému napíš jednotku a povedz, či je v `world`, `demand`, alebo v scenári. Potom vysvetli rozdiel medzi `sample_count=600` a 600 odoslanými CAM.

### Kontrola: 5 min

Trvanie je 60 s vo `world`, počet vzoriek 600 v scenári. `utc_origin` je scenárový čas UTC, `at_s=5.0 s` je v scenárovom zozname DENM, `depart_s=0 s` a `depart_speed_mps=10 m/s` sú v `demand`. **600 vzoriek nie je 600 CAM**: C++ pri každom vzorkovom kroku ešte rozhoduje, či CAM vytvorí, a ns-3 následne rozhoduje o fyzickom doručení.

## Deň 1, blok 3 — od kliknutia v mape po polohu auta (55 min)

### Výklad: 20 min

Lokálny svet používa **x východ, y sever**, jednotku meter. `georeference` určuje, ktorému bodu lokálnej plochy zodpovedá zemepisná šírka/dĺžka/výška. Vo [svete scenára](../data/inputs/user/navrh-koridor-satelit/world.json) je kotva `(1000,1000)` pri `(48.1486°,17.1077°)`. Cestný uzol `n2=(900,1422)` je preto 100 m západne a 422 m severne od kotvy. Z toho ešte nepoznáš presný bod každého auta: auto jazdí po pruhu, ktorý vytvorí SUMO.

Naša funkcia [`make_inputs`](../tools/u9_editable_scenario.py) píše cesty a autá do SUMO XML. `netconvert` vytvorí pruhy a križovatky. SUMO krok po kroku vypočíta polohy, rýchlosti a ďalšie hodnoty každého auta a zapíše **FCD**. Funkcia [`u9_prepare_cam.prepare`](../tools/u9_prepare_cam.py) vytvorí z FCD časové **waypointy** pre ns-3. Obsahujú lokálne metre a odvodené WGS84. Pri OSM mape sa kliknutá pozícia premietne na skutočnú geometriu SUMO pruhu. Auto po príchode do cieľa zostane po zvyšok komunikačného okna zastavené, aby jeho rádio zostalo prítomné. [SUMO FCD dokumentácia](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html).

**Tretí rozmer:** SUMO jazdí na lokálnej 2D sieti. Prevod lokálnej polohy auta na WGS84 používa ENU s `up=0` voči kotve. CAM výška preto nie je presne zameraná výška vozovky. Natívne pozemné rádio má samostatný predpoklad výšky antény; ten nie je to isté ako hodnota WGS84 výšky v správe.

### Čítanie kódu: 15 min

V [`u9_editable_scenario.py`](../tools/u9_editable_scenario.py) vyhľadaj `def make_inputs` a slová `road.nod.xml`, `road.edg.xml`, `vehicles.rou.xml`. V [`u9_prepare_cam.py`](../tools/u9_prepare_cam.py) vyhľadaj `def prepare` a `fcd.xml`. Nemusíš rozumieť XML syntaxe: stačí vedieť, že prvá funkcia **dodáva SUMO vstup**, druhá **číta jeho výstup**. Ak niekto povie „SUMO určilo, či sa DENM doručila“, vieš odpovedať: SUMO dodalo pohyb, doručenie rieši sieťový beh.

### Tvoja úloha: 15 min

Na papier napíš cestu jedného údaja: `car0.depart_pos_m=100` → `vehicles.rou.xml` → `SUMO FCD` → `waypoints.csv` → pozícia `ns3::MobilityModel`. Pri každej šípke povedz, či sa len kopíruje hodnota alebo sa vypočítava nový stav. Ako by sa zmenila komunikácia, ak by SUMO priviedlo autá bližšie k RSU? Ktorý nástroj vyhodnotí rádio?

### Kontrola: 5 min

Vstupných 100 m je pozícia na **prvom úseku trasy**, nie zemepisná dĺžka. SUMO z XML vypočíta časový pohyb; `waypoints.csv` ho prevedie na sieťové polohy a údaje pre správy; ns-3 potom používa priebežné polohy v rádiovom modeli. Blízkosť môže zmeniť útlm, ale samotné doručenie určí ns-3 podľa kanála, MAC/PHY a rušenia.

## Deň 1, blok 4 — CAM: rozhodnutie aplikácie, protokol, rádio (55 min)

### Výklad: 20 min

CAM hovorí okoliu, kde je auto a ako sa pohybuje. Naša aplikácia pri každom 100 ms waypointu zavolá `Station::check`. Ten porovná polohu, rýchlosť a smer s poslednou **odoslanou** CAM. Pohybový spúšťač nastane pri zmene **väčšej než** 4 m, 0,5 m/s alebo 4°. Periodický spúšťač nastane po internom intervale. DCC používa obsadenosť kanála za poslednú sekundu a môže minimálny odstup CAM nastaviť na 100, 250 alebo 500 ms. Vzorka teda iba **ponúkne možnosť rozhodnúť**, či sa CAM vygeneruje.

Keď sa rozhodne odoslať, náš `make_cam` vyplní obsah; Vanetza ho zakóduje ako ETSI UPER, zabalí do BTP a GeoNetworking single-hop broadcastu na CAM porte 2001. Náš adaptér odovzdá bajty ns-3 Wi-Fi zariadeniu. ns-3 simuluje 802.11p OCB, model útlmu, MAC/PHY prístup a príjem. Prijímací callback zavolá Vanetzu a naša aplikácia dekóduje CAM. **Táto cesta neobsahuje satelit automaticky.** [C++ `Station::check`, `send_cam`, `request`, `indicate`](../src/u9-full-integration-per-rsu.cc).

### Čítanie kódu: 15 min

V C++ súbore vyhľadaj `void check(const Waypoint& w)`. Pozri sa iba na riadky s `dist`, `speed`, `heading`, `motion`, `elapsed_ok`, `periodic`, `trigger`, `send`. Čítaj ich ako rozhodovací strom. Potom nájdi `if (send) { send_cam(w); ... }`. Uvidíš presnú hranicu medzi **rozhodnutím našej aplikácie** a **odovzdaním Vanetze/ns-3**. Hľadaj tiež `log_bytes("CAM_UPER_TX"` v blízkosti `send_cam` a `DENM_UPER_RX` inde, aby si odlíšil vytvorenie bajtov od prijatia.

### Tvoja úloha: 15 min

Predstav si, že od poslednej CAM prešlo 100 ms a nový waypoint je vzdialený presne 4,0 m, rýchlosť sa zmenila o 0,4 m/s a smer o 3°. Predpokladaj, že periodický interval ešte neuplynul. Vytvorí sa CAM pre **pohybový** dôvod? Potom zmeň vzdialenosť na 4,1 m, pričom DCC vyžaduje minimálne 250 ms. Vytvorí sa v tomto kroku CAM? Rozlišuj podmienku pohybu a minimálny odstup.

### Kontrola: 5 min

Pri presne 4,0 m nie, pretože kód používa `>4.0`. Pri 4,1 m je `motion=true`, ale po 100 ms ešte nie je splnené `elapsed_ok` pre 250 ms. CAM sa v danom kroku neodošle. Ani keby sa odoslala, neznamená to, že ju iné auto prijme; to zistíš až zo stopy príjmu.

## Deň 2, blok 5 — DENM a presná hranica preposlania (60 min)

### Výklad: 20 min

V scenári je jedna explicitná udalosť: `car0`, čas `5.0 s`, sekvencia `1`, operácia `new`, platnosť `45 s`, geografický polomer `600 m`, opakovanie `0 ms`. Aplikácia **neodhalila zápchu zo SUMO**; udalosť je daná vstupom. Náš `make_denm` ju naplní ako modelovú `trafficCondition/trafficJam`, nastaví `actionId=(stationId,sequence)`, čas, pozíciu, platnosť a informáciu o ceste. Vanetza ju zakóduje; `Station::emit_denm` použije BTP port 2002 a GeoNetworking GeoBroadcast s najviac tromi skokmi. `radius_m=600` je **cieľová geografická oblasť GN**, nie zaručený dosah antény. [Tvorba a odoslanie DENM](../src/u9-full-integration-per-rsu.cc).

Príjemca môže byť auto alebo RSU. Naša zdrojová RSU mostuje iba **prijatú** správu, ak sedí vybrané `rsu_id`, politika backhaulu, identita pôvodnej akcie a ešte nebola odoslaná. Po LAN príjme UT vytvorí IP/UDP paket pre SNS-3. Na bráne naša aplikácia vyberie vzdialenú RSU; tá upraví vlastné `header.stationId`, zachová pôvodné `actionId` a vytvorí nové lokálne GN/BTP vysielanie. Mostenie je teda **aplikačné rozhodnutie nášho kódu**. Vanetza rieši cestný protokol, ns-3/SNS-3 paketové siete. Historické ICB1/GRA1 v tom istom C++ súbore nie sú aktívnou vetvou CAM/DENM.

### Čítanie skutočnej stopy: 20 min

Otvor [denm-events.csv](../results/simulations/scenar-navrh-koridor-satelit-20261103/native/baseline/denm-events.csv). Čas je v mikrosekundách: `5000000 µs = 5 s`. Potom otvor [trace.csv](../results/simulations/scenar-navrh-koridor-satelit-20261103/native/baseline/trace.csv) a hľadaj `event_id=d319516eb46351c4`. Tento konkrétny beh obsahuje napríklad `DENM_UPER_TX` pri `car0` v 5,000000 s, `RSU_DENM_LAN_TX` pri `rsu0` v 5,000260 s, `UT_DENM_SAT_TX` v 5,000367 s, `GATEWAY_DENM_RX` v 5,117122 s, `RSU_DENM_REGENERATED` pri `rsu1` v 5,135406 s a `DENM_UPER_RX` pri `car3` a `car4` v 5,135661 s. Časová medzera medzi prvým odoslaním a vzdialeným príjmom je približne **135,661 ms** v tomto modelovom behu. Nie je to predpoveď služby operátora.

### Tvoja úloha: 15 min

Na papier napíš význam každého zo šiestich názvov stôp. Čo by znamenalo, keby existoval `DENM_UPER_TX`, ale chýbal `RSU_DENM_LAN_TX`? Čo ak existuje `UT_DENM_SAT_TX`, ale chýba `GATEWAY_DENM_RX`? Koľko správ vzniklo podľa jedného `DENM_UPER_TX` a koľko príjmov podľa štyroch riadkov `DENM_UPER_RX`? Nepomiešaj **unikátnu udalosť** a **počet príjemcov**.

### Kontrola: 5 min

Bez `RSU_DENM_LAN_TX` hľadaj problém na pozemnej ceste alebo v pravidlách RSU. Bez `GATEWAY_DENM_RX` po `UT_DENM_SAT_TX` hľadaj satelitný kanál, topológiu, frontu a routing. V stope je jedna pôvodná DENM udalosť, ale viac príjmov tej istej udalosti rôznymi uzlami. Nie je správne povedať „štyri udalosti“.

## Deň 2, blok 6 — pozemný kanál a 3D tienenie (55 min)

### Výklad: 20 min

`radio.tx_power_dbm=20` znamená výkon vysielača v dBm; `radio.noise_figure_db=7` opisuje šum prijímača. Ak voliteľné polia chýbajú, doplní sa rýchlosť 6 Mbit/s a kanál 180, teda frekvencia `5000+5×180=5900 MHz`. Náš Python prenesie tieto hodnoty do C++ argumentov. **ns-3** simuluje fyzickú vrstvu a príjem. Z čísla výkonu samotného nevieš povedať dosah; chýba vzdialenosť, útlm, antény, rušenie a podmienky kanála. [Prenos parametrov](../tools/simulator_inputs.py), [natívny ns-3 kanál](../src/u9-full-integration-per-rsu.cc).

Pri `radio.mode="urban_los"` použije model mestského V2V útlmu s LOS. Ak je v `satellite.environment` budova, náš [`OSMBuildingCondition`](../src/u9-osm-ground-condition.h) zoberie jej 2D pôdorys a vybranú výšku a otestuje **3D priamku medzi anténami**. Auto má modelovú anténu 1,5 m, RSU aspoň 5 m alebo 2 m nad strechou. Výsledok LOS/NLOS odovzdá **ns-3 propagation loss modelu**. Prienik budovy preto automaticky neznamená „paket určite zahodiť“; mení rádiovú podmienku, z ktorej ns-3 vypočíta príjem. Nie sú modelované presné materiály steny, odrazy a difrakcia.

HGT raster terénu má inú úlohu: pomáha pri samostatnom fyzikálnom audite satelitného lúča. Aktívny pozemný paketový kanál nepoužíva celý raster ako detailný 3D mestský svet. Ručne zadaná budova a OSM výškový tag tiež nie sú meranie — pozri [výškové prípady](studium-bp-katalog-vstupov.md#satelliteenvironment-budovy-terén-a-odhad).

### Čítanie kódu: 15 min

V [`bp_u9.template`](../tools/bp_u9.py) nájdi prepnutie na `urban_osm_building`, keď existuje súbor budov. V [`u9_ground_obstructions.py`](../tools/u9_ground_obstructions.py) nájdi výber `height_case` a export zvoleného čísla. V C++ hľadaj `radio_height` a `urban_osm_building`. Nejde o čítanie celého kanálového modelu; cieľ je určiť **kde naša logika končí a kde začína ns-3**.

### Tvoja úloha: 15 min

Vysvetli, čo sa zmení pri dvoch pokusoch s tou istou trasou: (A) bez budovy, `urban_los`; (B) budova medzi autom a RSU, `height_case=high`. Čo urobí náš kód? Čo musí ešte urobiť ns-3? Prečo 300 m kruh okolo RSU v editore nie je výsledok tohto výpočtu?

### Kontrola: 5 min

Náš kód z geometrie a výšky rozhodne LOS/NLOS; ns-3 potom používa príslušný útlm a fyzický príjem. Kruh v UI je kreslená pomôcka, nemá dosah vypočítaný z 3GPP/802.11p nastavení. `height_case=high` je citlivostný scenár, nie istota o skutočnej výške budovy.

## Deň 2, blok 7 — satelit: dráha, brána, filter a paket (60 min)

### Výklad: 25 min

Satelitný scenár je založený na **pripnutom OMM/GP archíve** s kontrolným SHA-256. Náš kód používa SGP4 na polohu družice v konkrétnom UTC čase, transformuje súradnice do zemského rámca a spočíta **eleváciu** nad horizontom RSU a modelovej gateway. `mask_deg=0.5°` je jedna minimálna podmienka; účinné minimum je maximum masky a limitov profilu terminálu. Pri `catalog_ids=[]` sa hľadá jedna družica vhodná pre všetky aktívne RSU a GW počas okna. Ak sa nenájde, príprava behu zlyhá. Viditeľnosť je **predpodmienka**, nie doručenie. [Výber topológie](../tools/u9_native_editor.py), [orbitálny archív](../tools/u9_orbit_source.py).

Ďalšia vrstva je náš natívny **user-link filter**: zohľadní miestnu budovu pri RSU, montáž/zorné pole, rýchlosť smerovania a zvyškový Doppler. V ukážkovom `link_policy` je `compensation=0.98`; model predpokladá, že zostanú 2 % vypočítaného Dopplera. Pri hypotetickom Doppleri 30 000 Hz by zvyšok bol 600 Hz, čo je menej než zadaná tolerancia 20 000 Hz. To je iba **jedna** podmienka; nehovorí nič o stave celého modemu. Pri Iridiu/Globalstare kód smerové limity nastaví na všesmerové, pretože nemáme doloženú inštalovanú smerovú charakteristiku. Pri Starlinku sa používa verejné FOV a montážny predpoklad. [Filter](../src/u9-native-satellite-condition.h).

Potom SNS-3 simuluje generický DVB user/feeder paketový úsek, fronty a prípadné ISL. Náš kód vyberá topológiu, kapacity a IP trasu. `link_budget` je samostatný **audit predpokladov**, nie prikazovací vstup proprietárneho modemu. Operátorský aktívny lúč, skutočná GW a služobný scheduler sa tu neoverujú. [SNS-3](https://github.com/sns3/sns3-satellite), [hranica vernosti](decisions/stav-vernosti.md).

### Čítanie kódu: 15 min

V [`u9_native_editor._select_topology`](../tools/u9_native_editor.py) nájdi `floor = max(...)` a vetvu `declared = sat.get('catalog_ids') or []`. Prečítaj rozdiel medzi explicitnou družicou a automatikou. V [`u9_native_editor.run`](../tools/u9_native_editor.py) nájdi `satellite-terminal-config.csv` a jeho stĺpce. Všimni si, že `mask_deg` rozhoduje pri **výbere kandidáta**, kým Doppler a budova rozhodujú pri **natívnom user linku**. SNS-3 nakoniec simuluje svoj PHY/MAC.

### Tvoja úloha: 15 min

Usporiadaj tvrdenia od najslabšieho po najsilnejšie: „družica je v archíve“, „je nad maskou“, „user-link filter ju prijíma“, „SNS-3 paket prešiel do brány“, „vzdialené auto prijalo DENM“. Potom vysvetli, prečo ani posledné tvrdenie nie je meraním Starlinku/Iridia/Globalstaru.

### Kontrola: 5 min

Poradie je presne uvedené v zadaní úlohy. Posledný krok dokazuje **iba výsledok tohto modelu** s konkrétnymi vstupmi a generickým DVB; neobsahuje skutočné pridelenie lúča, komerčný modem a prevádzkové pravidlá operátora.

## Deň 2, blok 8 — výsledok, chyba a päťminútová obhajoba (55 min)

### Výklad: 15 min

Výsledok nesmieš čítať len ako `PASS`. [`bp_u9.verify`](../tools/bp_u9.py) a [`u9_check_cam_denm.py`](../tools/u9_check_cam_denm.py) porovnávajú vstupy, hash zdrojov, stopy bajtov, časy, PCAP a natívny `PacketTrace.log`. `PASS` hovorí, že beh spĺňa dané kontrolné podmienky. Nemusí znamenať, že každý paket dorazil každému príjemcovi. Pri otázke „koľko sa doručilo?“ vždy povedz **odkiaľ kam**, **koľko unikátnych správ**, **koľko oprávnených pokusov** a **aké okno**.

V ukážkovej stope `DENM_UPER_RX` obsahuje `rsu0`, `car1`, `car3`, `car4`: štyria príjemcovia jednej akcie. `car3` a `car4` prijali po regenerácii na vzdialenej RSU. Z jedného behu neodhadneš spoľahlivosť komerčnej satelitnej služby. [Manifest behu](../results/simulations/scenar-navrh-koridor-satelit-20261103/run-manifest.json) uvádza, ktoré zdroje a vstupy boli použité. Ak sa kód odvtedy zmenil, starý beh je **historický dôkaz**, nie automaticky nový výsledok.

### Praktická analýza: 20 min

Otvor `trace.csv` a vyhľadaj ID `d319516eb46351c4`. Pre toto ID čítaj `stage`, `node_id`, `time_us`, `bytes`, `raw_hex`. `stage` je etapa, `node_id` uzol, `time_us` simulačný čas v mikrosekundách, `bytes` počet bajtov a `raw_hex` ich doslovná hexadecimálna reprezentácia. Nemusíš dekódovať hex ručne; checker ho dekóduje a porovnáva. Zober časy `DENM_UPER_TX` a `DENM_UPER_RX` pri `car3`, vypočítaj rozdiel a vydeľ 1000, aby vznikli milisekundy.

Ak chceš iba šesť zaujímavých etáp bez dlhého súboru, spusti z koreňa projektu **čítací** príkaz:

```bash
python3 - <<'PY'
import csv
path = 'results/simulations/scenar-navrh-koridor-satelit-20261103/native/baseline/trace.csv'
wanted = {'DENM_UPER_TX', 'RSU_DENM_LAN_TX', 'UT_DENM_SAT_TX',
          'GATEWAY_DENM_RX', 'RSU_DENM_REGENERATED', 'DENM_UPER_RX'}
with open(path, newline='') as stream:
    for row in csv.DictReader(stream):
        if row['event_id'] == 'd319516eb46351c4' and row['stage'] in wanted:
            print(row['stage'], row['node_id'], row['time_us'])
PY
```

### Tvoja úloha: 15 min

Bez materiálu nahlas povedz päťminútové vysvetlenie: (1) čo je VANET a prečo RSU, (2) odkiaľ sa berie pohyb, (3) kto vytvorí CAM/DENM, (4) kto rieši cestné rádio a satelitné pakety, (5) čo znamená 3D tienenie, (6) čo presne dokazuje stopa a čo nie. Potom povedz jednu vetu o konkrétnom scenári: „Pri `at_s=5 s` auto `car0` ...“

### Kontrola: 5 min

Správna odpoveď má obsahovať: SUMO = pohyb; náš C++ = obsah a aplikačné rozhodnutia; Vanetza = ETSI ASN.1/GN/BTP; ns-3 = pozemný MAC/PHY a pakety; SNS-3 = generická satelitná paketová cesta; budovy = geometrická podmienka, ktorej účinok závisí od vetvy; stopa = modelový dôkaz konkrétneho behu. Pri `car3` je rozdiel `5 135 661 − 5 000 000 = 135 661 µs = 135,661 ms`.

## Ak po dvoch dňoch niečo zostane nejasné

Vráť sa len k miestu, ktoré zlyhalo. Pri súradniciach otvor blok 3 a [katalóg georeferencie](studium-bp-katalog-vstupov.md#2-worldjson-plocha-čas-a-súradnice). Pri otázke „kto rozhoduje?“ otvor bloky 4–7. Pri čísle v editore hľadaj názov poľa v [katalógu](studium-bp-katalog-vstupov.md) a potom v odkázanej funkcii. Pri podozrivom výsledku začni `inputs/scenario.json`, pokračuj `trace.csv`, až potom čítaj súhrn. Toto je pracovný postup, ktorý ti umožní vysvetliť vlastný projekt bez memorovania celého C++.
