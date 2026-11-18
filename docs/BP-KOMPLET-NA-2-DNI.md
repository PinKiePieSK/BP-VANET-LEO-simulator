# BP: kompletný učebný materiál na dva dni

**Aktuálny projekt k 10. 11. 2026 · ns-3.38/SNS-3 3.38.** Toto je **jediný súbor na učenie**. Čítaj ho zhora nadol. Nemusíš otvárať editor, JSON, zdrojové súbory ani web. Názvy súborov slúžia na to, aby si po štúdiu vedel ukázať konkrétne miesto v kóde. Vysvetlenie vstupov, rozhodnutí, stôp aj hraníc modelu je priamo tu.

Neočakávam, že budeš vedieť čítať veľké C++ súbory. Stačí vedieť sledovať štyri otázky: **Čo je vstup? Aká podmienka sa testuje? Kto vykoná ďalší krok? Čím viem potvrdiť výsledok?**

## Najprv jedna mapa celého projektu

| Keď sa pýtaš… | Odpoveď | Aktuálny súbor |
| --- | --- | --- |
| Čo používateľ zadal a či je to platné? | Editor uloží `scenario`, `world`, `demand`; validátor zastaví nesúlad ešte pred simuláciou. | `viewer/simulator.js`, `tools/simulator_editor_api.py`, `tools/simulator_cli.py` |
| Kde vznikajú polohy áut? | `netconvert` zostaví cestnú sieť; SUMO vytvorí časové FCD polohy; náš export ich prevedie na 100 ms waypointy. | `tools/simulator_sumo.py`, `tools/simulator_mobility_export.py` |
| Kto vytvorí CAM a DENM? | Naša C++ aplikácia rozhodne o čase, obsahu a politike. Vanetza zakóduje správu a GeoNetworking/BTP. | `src/vanet-ground-network.cc`, `src/vanet-leo-network.cc` |
| Kto rozhodne, či rámec prejde rádiom? | ns-3 simuluje pozemný 802.11p MAC/PHY, útlm, kolízie a príjem. Naša geometria budov dodá LOS/NLOS. | `src/vanet-ground-network.cc`, `src/ground-building-condition.h` |
| Kto rozhodne o satelite? | Náš výber overí dráhu, eleváciu, terminál a modelové prekážky; SNS-3 potom vykoná generický DVB paketový prenos. | `tools/simulator_satellite_runner.py`, `src/satellite-link-condition.h`, `src/vanet-leo-network.cc` |
| Odkiaľ je výsledok `PASS`? | Verifier číta surové stopy a hashe vstupov. `PASS` potvrdzuje konkrétny kontrolný kontrakt, nie vernosť reálnej sieti operátora. | `tools/simulator_ground_verifier.py`, `tools/simulator_satellite_verifier.py`, `tools/simulator_message_verifier.py` |

**Dôležitý rozdiel:** „správa je v scenári“ → „aplikácia ju vytvorila“ → „rádio ju vyslalo“ → „prijímač ju dekódoval“ → „RSU ju vybrala na most“ → „brána ju prijala“ → „vzdialené auto ju prijalo“ sú odlišné udalosti. Pri každom tvrdení hľadaj príslušný riadok stopy. Pri CAM končí aktuálny tok po miestnom príjme; satelitný most používa DENM.

## Ako si rozdeliť dva dni

| Deň | Blok | Približne | Čítaj v tomto súbore | Po bloku vieš |
| --- | --- | ---: | --- | --- |
| 1 | 1 | 50 min | Časť I, kapitoly 1–3 | Nakresliť trasu auto–RSU–UT–SAT–GW–RSU–auto a pomenovať nástroje. |
| 1 | 2 | 60 min | Časť I, kapitoly 4–6 | Vysvetliť tok vstupov, súradnice a vznik CAM. |
| 1 | 3 | 60 min | Časť I, kapitoly 7–9 | Vysvetliť DENM, 3D budovy a satelitnú cestu. |
| 1 | 4 | 60 min | Časť I, kapitoly 10–13 | Spojiť stopu so skutočnou polohou auta a hodnotami CAM. |
| 1 | 5 | 60 min | Časť I, kapitoly 14–15 | Rozlíšiť obálky paketu, GN preposlanie, 3D LOS/NLOS a PHY príjem. |
| 2 | 6 | 70 min | Časť I, kapitoly 16–18; Časť II, kapitola 1 | Vysvetliť satelitné rozhodnutia, straty, CAM/DENM pravidlá a tri vstupy. |
| 2 | 7 | 70 min | Časť II, kapitoly 2–4 | Povedať význam údajov sveta, áut, ciest a mapy. |
| 2 | 8 | 75 min | Časť II, kapitoly 5–8 | Povedať význam rádiových, DENM a satelitných polí. |
| 2 | 9 | 75 min | Časti III a IV | Prečítať výrezy kódu a prejsť reálnu DENM stopu. |
| 2 | 10 | 50 min | Časť V | Vyriešiť otázky a nahlas vysvetliť model i jeho hranice. |

Časy zahŕňajú čítanie, vlastné poznámky a cvičenia. Odporúčaná prestávka je 5–10 minút. Ak máš menej času, najprv sa nauč **rozdiel medzi vytvorením správy, pokusom o vyslanie a jej skutočným modelovým príjmom**.

## Malý slovník kódu a jednotiek

`scenario['radio']['tx_power_dbm']` v Pythone znamená: zo scenára zober objekt `radio`, z neho číslo `tx_power_dbm`. `if` vykoná nasledujúce riadky len ak podmienka platí. `for` opakuje krok pre každý prvok. `raise ValueError` zastaví prípravu neplatného pokusu. V C++ `Station` predstavuje jednu ITS stanicu, `w` jeden časový waypoint, `Simulator::Schedule` naplánuje budúcu udalosť a `Send` odovzdá paket ďalšej vrstve. Ani `Schedule`, ani `Send` samy osebe nedokazujú príjem.

`s` = sekunda; `ms` = tisícina sekundy; `µs` = milióntina sekundy; `m/s` = metre za sekundu; `m/s²` = zrýchlenie; `dBm` = výkon vzhľadom na 1 mW; `dBi` = anténny zisk; `Hz` = frekvencia; `Mbit/s` = dátová rýchlosť. `5 000 000 µs = 5 s`. `10 m/s = 36 km/h`. Výkon `20 dBm = 100 mW`, čo ešte neurčuje komunikačný dosah.

# Časť I — súvislé vysvetlenie celého simulátora

## 1. Čo sa v práci skúma

**VANET** je sieť, v ktorej vozidlá komunikujú medzi sebou (**V2V**) a s cestnou infraštruktúrou (**V2I/I2V**). Lokálna správa sa prenáša cestným rádiom. **LEO** je nízka obežná dráha; satelitný úsek môže preniesť informáciu medzi vzdialenými oblasťami cez satelitné terminály pri cestných jednotkách **RSU**. Aktívny editor neumožňuje satelitný terminál v aute.

Model má dve hlavné vetvy:

```text
V2V: auto A -- CAM alebo DENM / GN-BTP / 802.11p OCB --> auto B

V2I: auto A -- tá istá lokálna rádiová vetva --> zdrojová RSU
                                                 |
                                                 | vlastná aplikačná politika
                                                 v
                                         LAN/IP/UDP -> UT -> LEO -> GW
                                                                   |
                                                                   v
                                                         vzdialený UT/RSU
                                                                   |
                                                 GN-BTP / OCB -> vzdialené autá
```

V aktuálnom režime sa **CAM vysiela iba lokálne ako jednoskokový broadcast**. Prijať ju môžu okolité vozidlá a RSU, ak to dovolí dosah, kanál a nastavenie uzla; príjem nie je zaručený každému susedovi. CAM sa nepreposiela ďalším GN skokom ani cez satelit. Cez satelitný most sa prenáša **prijatá DENM**, keď platí politika zdrojovej RSU a vznikne paketová cesta. Na vzdialenej RSU sa DENM znovu vydá do lokálnej oblasti. Historické režimy v tom istom C++ súbore vytvárali zo skutočne prijatej CAM vlastný report `ICB1` a odpoveď `GRA1/I2V1`; aktuálny runner zapína `--cam_denm_mode=1`.

## 2. Najskôr päť základov kódu

V tomto projekte `scenario`, `world` a `demand` sú **slovníky JSON**: názov poľa je kľúč, za ním je hodnota. Napríklad `scenario['seed']` znamená „zober hodnotu poľa `seed` zo scenára“. Pole `cars` je zoznam; `for car in cars` prejde autá po jednom. `if satellite_enabled:` vykoná nasledujúci blok len pri zapnutom satelitnom režime. `raise ValueError(...)` zastaví prípravu pre neplatný vstup.

V C++ je `Station` objekt jednej ITS stanice: drží jej rádio, polohu a stav prijatých správ. `device_->Send(...)` odovzdá bajty rádiovému zariadeniu ns-3. `SetReceiveCallback(...)` povie ns-3, ktorú našu funkciu zavolať pri prijatí. `Simulator::Schedule(...)` vloží budúcu udalosť do kalendára simulácie; `Simulator::Run()` udalosti vykonáva v časovom poradí. **Naplánovanie nie je doručenie.** Doručenie sa dá tvrdiť až po príjmovom callbacku a surovej stope.

Príklad z predletovej kontroly:

```python
if s['satellite_enabled']:
    need(duration >= 6, 'Satelitný beh potrebuje aspoň 6 s')
```

Číta sa: „Ak je satelit zapnutý, skontroluj minimálnu dĺžku; pri neúspechu beh ešte pred spustením odmietni.“ Tento riadok **nevysiela paket**.

## 3. Na čom sú založené nástroje a čo im pridáva náš kód

| Vrstva | Čo dodáva nástroj | Čo sme napísali my | Kde začať čítať |
| --- | --- | --- | --- |
| **SUMO** | Mikroskopickú premávku: každé auto má trasu, jazdí po sieti a reaguje na autá pred sebou, pruhy a križovatky v diskrétnych krokoch. | Editor ciest a áut, prevod JSON na SUMO XML, pravidlá platnosti trás, spustenie a kontrolu FCD. Explicitne nenastavujeme `carFollowModel`, takže platí predvolený model SUMO. | `simulator_sumo.py`, oficiálny opis SUMO, car following. |
| **Vanetza** | Implementáciu častí európskeho ITS zásobníka, najmä GeoNetworking, BTP a ASN.1 kódovanie/čítanie CAM a DENM. | Vyplnenie konkrétnych polí CAM/DENM, kedy správu vytvoriť, kam ju lokálne poslať, ktoré prijatie uznať, čo prepojiť so satelitom. | `Station` v integrovanom engine, Vanetza. |
| **ns-3.38** | Diskrétny kalendár sieťových udalostí, uzly a zariadenia, 802.11p OCB MAC/PHY, rádiový kanál, IP/UDP, LAN a stopy. | Prepojenie Vanetza s `NetDevice`, rozmiestnenie podľa SUMO, voľbu modelu kanála a parametrov, aplikačné callbacky a scenárové filtre. | `vanet-ground-network.cc`, `vanet-leo-network.cc`, ns-3, WAVE/OCB. |
| **SNS-3 3.38** | Satelitné uzly UT/SAT/GW, generický DVB user/feeder PHY/MAC, fronty, paketovú stopu a voliteľné modelové ISL. | Výber dráh a topológie, tvorbu vstupov pre SNS-3, výskumný filter user-link podmienok, nastavenie trás, politiky RSU a kontrolu surových paketov. | `simulator_satellite_runner.py`, `simulator_satellite_inputs.py`, SNS-3. |

SUMO **nesimuluje rádio**. Vanetza **neurčuje pohyb vozidiel**. ns-3/SNS-3 **nepozná význam „dopravná zápcha“**, kým ho nevytvorí naša aplikácia. Prehliadač **nie je fyzikálny simulátor**: kreslí vstup a prehráva overené stopy.

### Ako fungujú tieto nástroje zvnútra, bez predpokladu programovania

**SUMO** je mikroskopický dopravný simulátor: každé auto je samostatný objekt na cestnej sieti. Cestná sieť má uzly, orientované úseky, pruhy, rýchlostné limity a križovatky. Auto má vlastnú trasu a typ s parametrami ako maximálne zrýchlenie, brzdenie, minimálny odstup a faktor rýchlosti. Počas každého kroku 0,1 s SUMO aktualizuje polohu a rýchlosť podľa svojho dopravného modelu a okolitých vozidiel. Výstup FCD je časová séria; jeden riadok hovorí približne „auto `car0` je v tomto okamihu tu, ide takto rýchlo a týmto smerom“. V našom projekte sa pohyb **najprv vypočíta a uloží**, až potom sa z neho pripraví sieťový beh. Nejde o živé vzájomné riadenie SUMO a ns-3 cez TraCI počas každého paketu. SUMO teda nevie, či sa CAM stratila na rádiu; taká strata spätne neprepočíta jeho premávku.

**Vanetza** je knižnica implementujúca časti európskeho ITS protokolového zásobníka. Aplikácia jej dodá hodnoty CAM/DENM a požiadavku, ako ich na cestnej sieti šíriť. ASN.1 určuje štruktúru správy, UPER jej kompaktné binárne zakódovanie. BTP-B nesie port, aby príjemca vedel, či ide o CAM alebo DENM. GeoNetworking pridáva geografické smerovanie a pravidlá šírenia: lokálna CAM je jeden broadcastový skok, DENM môže byť adresovaná kruhovej oblasti a preposielaná podľa GN pravidiel. V našom C++ `router_.request(...)` znamená „požiadaj Vanetzu o odoslanie cez ITS zásobník“ a `router_.indicate(...)` znamená „odovzdaj prijatý GN rámec Vanetze na spracovanie“. Vanetza pritom sama nevypočíta pohyb vozidla ani rádiový útlm budovy; na tieto údaje používa naše prepojenie s pohybom a ns-3.

**ns-3** je diskrétny simulátor udalostí. Predstav si kalendár: v čase 5,000000 s sa má vytvoriť DENM, v 5,000260 s môže byť volaná funkcia príjmu RSU, neskôr sa môže vykonať odoslanie UT. Simulátor udržiava udalosti v časovom poradí. Uzly majú zariadenia (`NetDevice`), kanály, protokoly a aplikácie. Náš kód volá `Send`, ale potom model Wi-Fi MAC/PHY rieši prístup na médium, dĺžku rámca, možné súbežné vysielanie, útlm a prijatie. `Schedule` nie je meranie času na stene; jeden simulačný pokus môže v počítači trvať dlhšie alebo kratšie než zobrazených 60 s. Výsledný čas v stope je **simulačný čas**.

**SNS-3** je satelitné rozšírenie toho istého ns-3 behu. Pridáva terminál UT, družicu SAT, bránu GW, satelitné zariadenia, model user/feeder DVB PHY/MAC a vnútorné paketové stopy. Náš integrovaný scenár spája pozemný OCB úsek, modelovú LAN a SNS-3 v **jednom procese a na jedných simulačných hodinách**. To umožňuje porovnať čas `car0` vyslania a gateway príjmu bez lepenia logov z dvoch nezávislých časových osí. SNS-3 však týmto nedostáva skutočný proprietárny modem ani aktívny lúč operátora; používa nakonfigurovaný model.

## 4. Presný tok od editora po výsledok

1. **Editor** drží tri objekty: `scenario` (čo sa má skúmať), `world` (cesty, RSU, georeferencia, dopravné nastavenia) a `demand` (autá a trasy). Zobrazenie technických parametrov mení tie isté objekty cez `technical-parameters-bridge.js`. Tlačidlá, mapa a replay sú vo `viewer/simulator.js`.
2. **Kontrola pred behom** cez `simulator_cli.preflight` overí schému verzie 7, každé auto a RSU, jednotky, čas, technológie, rádiové voľby, DENM životný cyklus, prípadný orbitálny archív a politiku terminálov. Pozemný `world.network_execution='schema_only'` je označenie dopravného podkladu; skutočný sieťový beh spúšťa až `simulator_cli.run`.
3. **Uloženie** cez `simulator_editor_api.save` vytvorí `data/inputs/user/<id>/world.json`, `demand.json` a `config/scenarios/<id>.json`. Server používa lokálne HTTP endpointy `simulator_server.py`.
4. **SUMO príprava**: `simulator_sumo.make_inputs` vytvorí `road.nod.xml`, `road.edg.xml`, `vehicles.rou.xml` a RSU body. `netconvert` vyrobí dopravnú sieť `road.net.xml`; `sumo` po kroku 0,1 s vyrobí `fcd.xml` s polohou, rýchlosťou, smerom, zrýchlením a signálmi. Vozidlo, ktoré dôjde do cieľa pred koncom komunikačného okna, sa v tomto scenári zastaví a zostane prítomné, aby jeho rádio nezmizlo.
5. **Prevod polôh**: `simulator_mobility_export.prepare` zoberie FCD a vytvorí `waypoints.csv` každých 100 ms. Každý riadok nesie lokálne metre, WGS84, čas, rýchlosť, smer, zrýchlenie, rozmery auta a odvodené hodnoty pre CAM. Zatiaľ je to **vstup do sieťového behu**, nie vyslaná CAM.
6. **Sieť**: pozemný scenár spustí `simulator_ground_runner.py` a `vanet-ground-network.cc`. Satelitný scenár spustí `simulator_satellite_runner.py` a `vanet-leo-network.cc` v jednom procese ns-3/SNS-3. Všetky aktívne autá a terminály majú polohu už pri simulačnom `t=0`.
7. **Overenie**: `simulator_ground_verifier.py` alebo `simulator_message_verifier.py` kontrolujú bajty, čas, PCAP a pri satelite natívnu `PacketTrace.log`; výsledok sa uloží s manifestom hashov. `simulator_editor_api.replay` potom pripraví údaje pre prehliadač. Replay je čítanie uloženého behu, nie jeho pokračovanie.

Editorové tlačidlo „Spusti“ najprv uloží zmenený scenár, potom cez `simulator_server.py` spustí pracovníka `simulator_cli.py run`; výsledok je v `results/simulations/<run_id>/`. Výsledkový adresár sa nesmie prepísať. Náhľad konštelácie a glóbus ukazujú kandidátov; sieťový výsledok vzniká až v natívnom behu.

## 5. Súradnice, 3D priestor a význam „dostupnosti“

Editorová pracovná mapa má lokálne `x_m, y_m` v metroch: **+x východ, +y sever**. `georeference` hovorí, ktorému bodu lokálnej mapy (`anchor_x_m, anchor_y_m`) zodpovedá WGS84 zemepisná šírka, dĺžka a výška. Príklad: pri kotve `(2000, 2000)` je RSU `(2100, 2000)` zhruba 100 m východne od zvoleného WGS84 bodu. Presný prevod lokálny ENU → WGS84 robí `simulator_coordinates.py`; opačný prevod importovaných OSM ciest je v `simulator_osm_road_graph.py`. Obrazovka prevracia os Y iba kvôli kresleniu; uložená os Y stále smeruje na sever.

SUMO počíta pohyb v **lokálnej 2D cestnej sieti**. FCD `x/y` sú výsledné pozície auta v SUMO, nie nezmenené súradnice kliknutia v editore. Pri reálnej OSM mape `netconvert` upraví geometriu pruhov pri križovatkách; náš kód preto premieta kliknutú počiatočnú/cieľovú polohu na skutočný SUMO pruh. `simulator_mobility_export` počíta WGS84 pri **pevnom lokálnom ENU up=0**. To znamená, že CAM výška je odvodená z kotvy a tangenciálnej geometrie, **nie meraná nadmorská výška vozovky**. V novom audite parametrov sa pri CAM/DENM netvrdí neexistujúca presnosť GNSS; confidence je `unavailable`.

Satelitné dráhy pochádzajú z pripnutého **OMM/GP archívu**; `simulator_orbits.py` ich šíri pomocou SGP4 a transformuje TEME → zemský ITRS/ECEF v konkrétnom UTC čase. **Elevácia** je uhol družice nad miestnym horizontom pozorovateľa. **Maska** stanoví minimálnu eleváciu. Pre kandidáta sa používa maximum scenárovej masky a publikovaného rozsahu daného terminálového profilu. `simulator_time_visibility.py` počíta v čase kandidátov; `simulator_physical_coverage.py` odlišuje horizont, terminálovú obálku a neznámy aktívny lúč.

Rozlišuj päť tvrdení v tomto poradí: **(1) dráha je v archíve; (2) družica je nad horizontom; (3) vyhovuje maske a zornému poľu; (4) natívny model umožní prenos; (5) aplikácia skutočne prijme správu.** Krok 2 alebo 3 nikdy automaticky nedokazuje krok 5. Neoverený aktívny lúč, modem, reálna brána a prevádzka operátora bránia prekladu kroku 5 v modeli na komerčnú dostupnosť. Súčasný automatický výber pre natívny beh hľadá **jednu** družicu použiteľnú pre všetky aktívne RSU aj modelovú GW počas celého okna; explicitná viacdružicová topológia je samostatný režim.

## 6. Kto rozhoduje o vyslaní CAM

1. **SUMO** dá polohu, rýchlosť, smer, zrýchlenie a signály. `simulator_mobility_export.py` ich prevedie do škálovaných jednotiek ETSI (`latitude_e7`, `speed_cmps`, `heading_decideg`, atď.). Rozmery auta pochádzajú z `world.simulation.vehicle_model`.
2. **Náš C++ `Station::check`** sa plánuje pri každej 100 ms vzorke. Pozrie zmenu polohy (>4 m), rýchlosti (>0,5 m/s), smeru (>4°), čas od poslednej CAM a obsadenosť kanála CBR za poslednú sekundu. Pri zapnutom DCC nastaví scenárový minimálny interval 100/250/500 ms podľa prahov CBR. Ide o **výskumnú politiku**, nie potvrdenú úplnú ETSI DCC konformitu.
3. Ak politika dovolí odoslanie, **náš `make_cam`** vyplní ASN.1 polia, Vanetza ich zakóduje do UPER bajtov. **Vanetza router** pripraví BTP-B/GeoNetworking **single-hop broadcast** s portom CAM 2001. **Náš adaptér** odovzdá vzniknuté bajty `ns3::WifiNetDevice::Send`.
4. **ns-3** rozhoduje o prístupe k rádiovému médiu, trvaní PHY prenosu, kolíziách a príjme podľa zvoleného rádiového kanála. Pri príjme sa zavolá náš callback, ktorý odovzdá GN bajty Vanetze; tá vráti BTP payload a náš kód dekóduje/overí CAM. V aktuálnom režime tým spracovanie CAM končí: **nevytvára sa z nej satelitný paket ani vzdialené opakované vyslanie**.

Funkcie nadväzujú v poradí `simulator_mobility_export.prepare` → `Station::check` → `make_cam` → `Station::send_cam` → `Station::request` → `Station::indicate`. Ich podstatné rozhodnutia a úryvky sú vysvetlené v časti III. Pri každej sa pýtaj: **čo je vstup, čo je rozhodnutie, čo je výstup?**

## 7. Kto rozhoduje o DENM a jej preposlaní

V editore sa volí udalosť `source_id`, `at_s`, `sequence`, `operation`, `validity_s`, `radius_m`, `repetition_ms`. **Nejde o automatické rozpoznanie zápchy z dopravy SUMO.** V aktívnej vetve náš `make_denm` vytvorí modelovú udalosť `trafficCondition/trafficJam`, odvodí polohu z auta, nastaví `actionId`, časy, platnosť a pri `cancel` ukončenie. Vanetza DENM zakóduje. `Station::emit_denm` vytvorí GeoBroadcast do kruhu `radius_m`, BTP port 2002, maximálne 3 skoky; Vanetza rieši príslušnú GN logiku, ns-3 fyzický rádiový prenos. **Opakovanie** podľa `repetition_ms` plánuje náš kód pomocou `Simulator::Schedule`.

Prijímač DENM skontroluje identitu akcie, čas, platnosť a duplicitu. **Naša zdrojová RSU** odošle prijaté presné UPER bajty na LAN iba ak je vybraná ako `rsu_id`, má zapnutý `satellite_backhaul`, správa ešte nebola odoslaná a patrí k pôvodnej akcii. **Naše UT callbacky** po LAN príjme odošlú nové IP/UDP datagramy do SNS-3. **SNS-3** potom simuluje satelitný user/feeder prenos a prípadné ISL. **Naša gateway aplikácia** prijatý obsah pošle do vybranej vzdialenej RSU (`alert_target_rsu`). **Naša vzdialená RSU** upraví len `header.stationId`, ponechá pôvodné `actionId` a obsah udalosti, potom znovu vytvorí lokálny GN/BTP/OCB broadcast.

To je hlavné rozdelenie práce: **my určujeme význam udalosti, politiku mosta, príjemcu a regeneráciu; Vanetza rieši cestný protokolový zásobník; ns-3/SNS-3 vykonáva sieťový prenos podľa modelu.** Ak sa paket nedostane k RSU, náš most nemá čo odoslať.

## 8. Tienenie a rádio: čo je 2D, 3D a čo je odhad

**Pozemné V2V/V2I rádio.** ns-3 používa `OcbWifiMac` a 10 MHz 802.11p PHY. Scenár volí `friis` (voľný priestor) alebo `urban_los` (3GPP V2V urban útlm s vynúteným LOS). Pri vložených budovách sa účinne použije `urban_osm_building`: náš `OSMBuildingCondition` z polygónov a zvolenej výšky rozhodne, či **3D úsečka medzi anténami** pretína objem budovy; výsledok LOS/NLOS prevezme **ns-3 3GPP V2V propagation loss model**, ktorý počíta útlm a následný PHY príjem. Budovy teda neznamenajú priamo „paket zahodiť vždy“; menia stav kanála. Toto nie je difrakcia, odraz, presný materiál steny ani meraný mestský kanál.

Anténa auta je v modeli 1,5 m nad lokálnou rovinou. RSU používa `max(5 m, výška strechy + 2 m)`, ak je na pôdoryse budovy. Výšky OSM môžu byť priamo tagované, odvodené z počtu podlaží alebo lokálne odhadnuté; voľba `low/central/high` je **citlivostný scenár**, nie meranie. Ručne nakreslená budova má obdĺžnikový pôdorys a výšku zadanú používateľom.

**Satelitný user link.** Poloha družice a terminálu sú 3D; náš natívny filter `satellite-link-condition.h` počíta smer k družici, odklon od montáže, rýchlosť smerovania antény a zvyškový Doppler. Ak miestna budova pretína začiatok 3D lúča od RSU, alebo zlyhá limit montáže/Dopplera/smerovania, kanál odmietne user-link príjem. SNS-3 popritom používa vlastnú eleváciu, generický DVB PHY/MAC, fronty a modelový zisk. Pri Iridiu/Globalstare sa v natívnom filtri nevymýšľa úzky smerový limit montáže bez doloženej krivky; zadané hodnoty výkonu a zisku sú predpoklady modelu.

**Terén HGT a počasie.** Importovaný raster terénu, OSM budovy a štatistické vrstvy sa používajú v **oddelenej fyzikálnej analýze/náhľade**. Aktívny natívny paketový filter číta budovy pri RSU; **neprevádza celý HGT raster na 3D rádiový terén pre každý paket**. Tienenie lokálneho gateway okolia tiež nie je modelované, keďže modelová brána je mimo výrezu. Polia `weather` a `vegetation` sú spravidla `unknown`; voliteľný `link_budget` počíta citlivosť predpokladov pre audit, nie prevádzkovú dostupnosť operátora ani automatické rozhodnutie natívneho modemu.

## 9. Ako sa rozhoduje o satelitnej ceste

`simulator_satellite_runner._select_topology` načíta archivované objekty vybranej skupiny, propaguje ich na zvolený UTC čas a overí eleváciu pri každej aktívnej RSU aj pri modelovej bráne. Pri automatickom režime zvolí jednu družicu s najlepším minimálnym výhľadom, ktorá drží účinnú masku po celé okno; inak spustenie zlyhá. Pri explicitnom `catalog_ids` kontroluje vybrané družice, indexy `initial_serving_sat`, `feeder_sat`, `handover_target_sat` a spojitosť stromu `isls`. Globalstar s ISL odmieta. **Orbitálna geometria rozhoduje, čo smie byť kandidátom; skutočné prijatie paketu ešte podlieha natívnemu kanálu.**

`simulator_satellite_inputs.generate` vytvorí pre SNS-3 TLE rekonštrukciu, `isls.txt`, polohy UT/GW a diagnostickú anténnu mapu. C++ engine zapne SNS-3 konšteláciu, nastaví DVB parametre a vytvorí pre každú RSU vlastný UT a 100 Mb/s / 100 µs modelovú LAN. Aj pri vypnutom satelitnom režime konkrétnej RSU môže byť v natívnej topológii terminál fyzicky vytvorený; naša aplikačná politika mu zabráni odosielať. Toto je zdokumentovaná hranica implementácie.

Pri viacdružicovom explicitnom scenári SNS-3 vytvorí modelové ISL zariadenia. **Náš kód** kontroluje graf a nastavuje kapacity/fronty smerom k feeder družici, explicitnú návratovú trasu a vo výskumnom handoveri prenesie stav jedného UT do cieľového satelitu. Potvrdenie vyžaduje obojsmernú skúšobnú správu. To stále nie je dôkaz protokolu Starlink/Iridium/Globalstar.

## 10. Kde sledovať jeden konkrétny paket

Pri kontrole skutočného behu má zmysel poradie `inputs/scenario.json` → `inputs/world.json` → `ground/scenario/sumo/fcd.xml` alebo `native/baseline/sumo/fcd.xml` → `native/baseline/waypoints.csv` → paketové stopy. Pre učenie máš konkrétne hodnoty už v časti IV. Pri satelitnom CAM/DENM behu sú najdôležitejšie tieto typy súborov:

| Súbor | Čo presne hľadať |
| --- | --- |
| `native/baseline/denm-events.csv` | Kedy a z ktorého auta naša aplikácia naplánovala udalosť. |
| `native/baseline/trace.csv` | Bajty a čas v etapách `DENM_UPER_TX`, `RSU_DENM_LAN_TX`, `UT_DENM_SAT_TX`, `GATEWAY_DENM_RX`, `RSU_DENM_REGENERATED`, `DENM_UPER_RX`. Prázdny neskorší stupeň znamená, že sa tam správa nedostala. |
| `native/baseline/ocb-*.pcap` | Skutočné modelové cestné 802.11 rámce; pomáhajú odlíšiť aplikáciu od vyslania na vzduch. |
| `native/baseline/PacketTrace.log` a `satellite-ip-trace.csv` | Interná cesta SNS-3 a väzba IP/UDP datagramu na UID satelitného paketu. PacketTrace nie je záznam komerčných RF bajtov. |
| `native/baseline/satellite_rf.csv`, `phy_drop.csv`, `dcc_decisions.csv` | Prečo modelový user link alebo pozemné rádio prijali/odmietli prenos a prečo sa CAM vytvorila alebo preskočila. |
| `physical-timeline.json`, fyzikálny audit v UI | Časoví geometrickí kandidáti a hranice fyzikálnej interpretácie; nie dôkaz doručenia. |
| `run-manifest.json` | Ktoré vstupy, zdroje a výsledok boli pre tento beh hashovo pripnuté. |

Začni jedným `event_id` v `trace.csv`. Ak je `DENM_UPER_TX`, ale niet `RSU_DENM_LAN_TX`, problém je pred satelitným mostom (dosah, budova, oblasť, politika alebo príjmová logika). Ak je `UT_DENM_SAT_TX`, ale niet `GATEWAY_DENM_RX`, hľadaj `satellite_rf.csv`, `PacketTrace.log`, masku a routing. Ak vzdialená RSU prijala, ale autá nie, hľadaj jej lokálny GN/OCB úsek.

## 11. Jeden skutočný scenár: prečítaj hodnotu až po stopu

Ukážkový satelitný koridorový scenár je celý vysvetlený v časti IV. Má `source_id="car0"`, `rsu_id="rsu0"`, `alert_target_rsu="rsu1"`, `sample_count=600`, teda 60 sekúnd po 100 ms. Jediná udalosť sa má vytvoriť pri `at_s=5.0`, má `sequence=1`, `operation="new"`, `validity_s=45`, `radius_m=600`, `repetition_ms=0`. Posledné číslo znamená, že náš plánovač nezadá opakované vysielanie tejto udalosti. **600 m je cieľová oblasť GeoNetworking, nie zaručený fyzický dosah rádia.**

V tom istom scenári `radio.tx_power_dbm=20`, `radio.noise_figure_db=7`, `radio.mode="urban_los"`. Chýbajúce voliteľné `rate_mbps` a `channel_number` doplní `ground_config` na 6 Mbit/s a kanál 180, teda stred 5900 MHz. Oboje sa potom nastaví do pozemného ns-3 rádia; počet doručených rámcov z týchto čísel samotných nevypočítaš bez polôh, kanála a kolízií. `node_policy.cars.car0.ground="all"` dovolí príjem v RSU; obe RSU majú `satellite_backhaul=true`. `satellite.catalog_ids=[]` znamená automatický výber jednej vhodnej družice, nie nulový počet družíc.

Teraz sleduj riadok `denm_events[0]` v tomto poradí:

```text
scenario.json
  -> simulator_cli.preflight: platný čas, zdroj, policy, orbita
  -> simulator_sumo: SUMO pohyb car0
  -> simulator_mobility_export: waypoint car0 v čase udalosti
  -> make_denm / Station::emit_denm: UPER + GN/BTP
  -> ns-3 prijatie v rsu0
  -> RSU_DENM_LAN_TX -> UT_DENM_SAT_TX
  -> SNS-3 user/feeder/ISL podľa topológie
  -> GATEWAY_DENM_RX -> RSU_DENM_REGENERATED
  -> vzdialené ns-3 rádio -> DENM_UPER_RX v aute
```

Každá šípka má kontrolovateľný dôkaz v surovej stope a v súboroch opísaných v časti 10. Nie každá šípka musí v každom pokuse nastať. Presný výklad vstupných polí je v časti II.

## 12. Desať viet, ktoré máš vedieť vysvetliť bez kódu

1. SUMO vypočíta pohyb áut; sieť v ňom nebeží.
2. JSON editora sa najprv validuje a zmení na dopravný vstup a potom na časové polohy.
3. Naša aplikácia rozhoduje, kedy vznikne CAM/DENM a čo znamená udalosť.
4. Vanetza kóduje správu a vytvára cestný GN/BTP zásobník.
5. ns-3 WAVE simuluje lokálne 802.11p OCB rádio a jeho kanál.
6. RSU posiela na satelit iba obsah, ktorý prijala a ktorý povoľuje naša politika.
7. SNS-3 simuluje generickú DVB satelitnú paketovú cestu, nie modem operátora.
8. Orbitálny archív a elevácia určujú kandidáta, nie garantované doručenie.
9. Budovy menia modelovú pozemnú LOS/NLOS podmienku a user-link filter; raster terénu sa v natívnom pakete nepoužíva ako úplný 3D rádiový svet.
10. Výsledok tvrdí niečo o presne opísanom scenári a raw paketovej stope, nie o prevádzkovej kvalite komerčnej služby.

## 13. Jeden automobil od vstupu po CAM

Auto `car0` v `demand` nemá vopred pripravené CAM ani výsledné polohy. Má trasu `approach → middle → east`, `depart_s=0`, `depart_pos_m=100` na prvom úseku a `depart_speed_mps=10`. V manuálnej mape je 10 m/s **počiatočná** rýchlosť. Pri OSM mape má tá istá položka aj úlohu `vType.maxSpeed` a `departSpeed="max"`; SUMO prispôsobí skutočný odchod pruhu a okolitej premávke. Tieto dve vetvy preto nevysvetľuj rovnako.

```text
demand.vehicles[car0] + world.roads + world.simulation.vehicle_model
  → road.nod.xml, road.edg.xml, vehicles.rou.xml
  → netconvert: pruhy a križovatky v road.net.xml
  → SUMO: pohyb auta v krokoch po 0,1 s
  → fcd.xml: poloha, rýchlosť, smer, zrýchlenie a signály
  → simulator_mobility_export.prepare: waypoints.csv
  → C++ Station: poloha rádia a obsah prípadnej CAM
```

V skutočnom ukážkovom behu je v `waypoints.csv` pri `t=0` pre `car0` `x=600,00 m`, `y=1420,40 m`, `speed_cmps=1000`, `heading_decideg=900`. To znamená `10 m/s` a `90°`. Pri `t=5 s` je `x=652,94 m`, `y=1420,40 m`, `speed_cmps=1060`, teda `10,6 m/s`. To je **výsledok SUMO**, nie trvalý prepis `depart_speed_mps`. Zdrojová RSU stojí na `(850,1422)` m; v tomto okamihu je auto približne `sqrt((850−652,94)²+(1422−1420,40)²)=197,07 m` od nej v lokálnej rovine. Samotná vzdialenosť neurčuje, či RSU prijme rámec.

Waypoint pri 5 s má `latitude_e7=481523807`, čiže `48,1523807°`, a `longitude_e7=171030355`, čiže `17,1030355°`. Funkcia `enu_to_wgs84` prevádza lokálne metre cez kotvu sveta; nejde o meraný GPS záznam auta. `altitude_cm=2` po zaokrúhlení **nie je meraná nadmorská výška vozovky**. Prevod používa pevné lokálne `up=0`; malá nenulová elipsoidická hodnota môže vzniknúť geometriou tangenciálnej roviny. Výšku antény pre rádio určí osobitne `radio_height`: auto 1,5 m, RSU aspoň 5 m alebo 2 m nad zvolenou strechou. CAM výška a anténna výška v kanáli majú odlišný význam.

Z FCD vzniknú aj `speed_cmps` (cm/s), `heading_decideg` (desatiny stupňa), `acceleration_dmps2` (desatiny m/s²), `yaw_rate_cdegps` (stotiny stupňa/s), `vehicle_length_dm` a `vehicle_width_dm` (decimetre) a bitové svetlá. Pri yaw sa otočí znamienko, lebo SUMO a ETSI majú rozdielnu kladnú orientáciu. `generation_delta_ms` je časový kód CAM modulo 65536 ms; príprava kontroluje kolízie týchto identít v jednom behu. Neexistujúca neistota GNSS sa nemá vydávať za presnú polohu; confidence sa označí ako `unavailable`.

**V kóde sú tri oddelené kroky:** `simulator_mobility_export.prepare` vyrobí waypoint; `Station::update_position` nastaví `(x_m,y_m,radio_height)` v `ns3::MobilityModel` a aktualizuje Vanetza pozíciu; `Station::check` až následne rozhodne, či vznikne CAM. Preto 600 waypointov počas 60 s neznamená 600 vyslaných CAM.

## 14. Čo presne je paket na každom úseku

Slovo *paket* sa pri celej trase používa na viacero rôznych obálok. Pri ceste medzi autami alebo auto–RSU sa začína obsahom CAM/DENM: naša aplikácia vyplní hodnoty, Vanetza ich zakóduje ako ASN.1 UPER, pridá BTP-B a GeoNetworking. BTP port 2001 znamená CAM, port 2002 DENM. CAM má single-hop broadcast; DENM je GeoBroadcast do kruhu s limitom najviac troch GN skokov. Náš `Station::request` vezme GN bajty od Vanetze a zavolá `ns3::WifiNetDevice::Send`. Ns-3 vytvorí 802.11p OCB rámec, použije svoj MAC/PHY a kanál. Rádiový rámec nie je totožný s pôvodným UPER obsahom: má ďalšie hlavičky a môže sa pri príjme vôbec nedekódovať.

Keď RSU prijme DENM, aplikačný callback najprv overí čas, identitu akcie, platnosť a duplicitu. Až vyhovujúce **prijaté** UPER bajty vloží do nového IP/UDP datagramu pre LAN a satelitný úsek. SNS-3 prenáša tento datagram cez modelové UT/SAT/GW. Na konci gateway pošle obsah vybranej vzdialenej RSU, ktorá ho znovu miestne vydá cez Vanetza GN/BTP a druhé OCB rádio. Pôvodný Wi-Fi rámec auta teda neletí cez satelit ako jeden nezmenený rámec.

| Otázka | Odpoveď v aktívnom modeli |
| --- | --- |
| Kto vyberá, **kedy** vznikne CAM? | Náš `Station::check` podľa pohybu, intervalu a DCC. |
| Kto naplní modelový význam zápchy a životný cyklus DENM? | Naša aplikácia podľa `denm_events`; SUMO zápchu samo nedetekuje. |
| Kto realizuje miestny BTP/GN vrátane prípadného GN preposlania? | Vanetza; náš adaptér výsledné rámce odovzdáva ns-3. |
| Kto rozhoduje o lokálnom fyzickom príjme? | Ns-3 802.11p OCB PHY/MAC a zvolený model kanála. |
| Kto rozhoduje, či RSU pošle prijatú DENM do LAN? | Náš RSU aplikačný filter, nie automatické smerovanie SNS-3. |
| Kto realizuje modelový satelitný paketový prenos? | SNS-3, po výbere topológie a konfigurácii naším kódom. |
| Kto vyberie cieľovú RSU? | Naša gateway aplikácia podľa `alert_target_rsu` a politiky. |

V ukážkovej stope `car1` po miestnom prijatí vytvorilo `GN_BTP_DENM_FORWARD_TX`: to je cestné GN preposlanie, nie nová dopravná udalosť ani satelitný backhaul. Na vzdialenej RSU ostáva pôvodný `actionId=(originatingStationId,sequenceNumber)`, aby sa dala sledovať pôvodná akcia; zmení sa `header.stationId`, pretože miestne vysiela iná ITS stanica. Rozlišuj teda **identitu udalosti**, **aktuálneho vysielača** a **identitu každého rámca**.

## 15. Pozemné rádio a 3D budova na jednoduchom príklade

Pozemný scenár vyberá `radio.mode=urban_los` alebo `friis`. `friis` je jednoduchší voľnopriestorový model útlmu. `urban_los` používa 3GPP V2V urban útlm s LOS podmienkou. Ak prostredie obsahuje budovy, runner účinne vyberie `urban_osm_building`, hoci pôvodné pole v JSON môže ostať `urban_los`. Python vtedy odovzdá C++ aj súbor pôdorysov a zvolených výšok. Auto má modelovú anténu 1,5 m, RSU aspoň 5 m alebo 2 m nad strechou. Náš `OSMBuildingCondition` skúma, či 3D úsečka medzi nimi pretína budovu vytvorenú vytiahnutím 2D pôdorysu do vybranej výšky.

Predstav si auto s anténou 1,5 m, RSU s anténou 5 m a budovu vysokú 12 m medzi nimi. Ak pri mieste budovy priamka leží pod strechou, test vráti NLOS. Pozemný model tým **neprikáže okamžité zahodenie každého paketu**: oznámi LOS/NLOS modelu útlmu v ns-3, ktorý ďalej vyhodnotí prijatý signál a PHY príjem. Ak budova stojí mimo pôdorysnej trasy priamky, výsledok môže byť LOS. Ak RSU stojí na pôdoryse budovy, výška strechy môže zvýšiť aj jej modelovú montážnu výšku.

`height_min_m`, `height_central_m`, `height_max_m` sú citlivostné hodnoty **tej istej neistej budovy**, nie tri skutočne odmerané budovy. OSM môže mať neoverený výškový tag, počet podlaží s predpokladom výšky na podlažie alebo iba interval neznámej výšky. `height_case=low/central/high` vyberie hodnotu pre beh; `interval` zachová neistotu v audite a pri natívnom exporte použije centrálny odhad alebo stred intervalu. Zmena `height_case` môže zmeniť LOS/NLOS aj výšku RSU; presný rozdiel v doručení však zistíš až z porovnateľných paketových behov.

V ukážke `radio.tx_power_dbm=20` znamená 100 mW, predvolený kanál 180 má stred `5000+5×180=5900 MHz`, šírka OCB kanála je 10 MHz a predvolená PHY rýchlosť 6 Mbit/s. `noise_figure_db=7` a anténne zisky (predvolene 0 dBi) vstupujú do rádia. **300 m kruh v editore je iba kresba**, nie pravidlo „197 m prijmi, 301 m zahoď“. Príjem závisí aj od útlmu, LOS/NLOS, šumu, rýchlosti PHY, prípadných kolízií a časovania. `shadowing` je dodatočná náhodná zložka podporovaného urban modelu; `friis` so zapnutým `shadowing` predletová kontrola odmietne. Model tu nemá kalibrované materiály stien, presné odrazy ani difrakciu.

Satelitná budova má **iný rozhodovací bod**. Náš natívny user-link filter od RSU vyšle 3D lúč v smere družice cez miestny výrez. Ak pretne budovu, môže user link odmietnuť priamo s dôvodom `building`. Tým sa nemodeluje okolie vzdialenej gateway. HGT terén slúži najmä na oddelený fyzikálny audit; aktívny pozemný packet engine ho nevyužíva ako detailný 3D svet pri každom V2V/V2I rámci. Počasie a vegetácia sú intervalové predpoklady auditu link budgetu, nie automatické príčiny zahodenia natívneho paketu.

## 16. Satelitná cesta po jednotlivých bránach rozhodovania

Vstup začína **pripnutým archívom dráh**. `orbit_snapshot.path` ukazuje na lokálny OMM/GP archív, `manifest_sha256` stráži jeho identitu a `utc_origin` určuje okamih výpočtu. `orbit_group` vyberá profil `iridium-NEXT`, `globalstar` alebo `starlink`. SGP4 z archívu vypočíta polohu družice, transformácia TEME → ITRS/ECEF ju dá do zemského rámca. Potom náš kód vypočíta smer a eleváciu pre každú aktívnu RSU a modelovú gateway. Účinná dolná hranica elevácie je maximum scenárovej `mask_deg`, minimálnej elevácie profilu a hranice odvádzanej zo zorného poľa terminálu. Preto `mask_deg=0,5°` **nemusí byť** konečný účinný limit, ak má profil prísnejšie obmedzenie.

V automatickom režime `catalog_ids=[]` sa hľadá **jedna** družica vhodná pre všetky aktívne RSU aj gateway počas celého okna. Kontrola vyhodnocuje celé okno po 0,5 s; ak sa taká nenájde, príprava behu zlyhá. Explicitný režim `catalog_ids=[...]` dovoľuje viacdružicovú topológiu: `initial_serving_sat` je prvá družica pri UT, `feeder_sat` pri bráne, `handover_target_sat` cieľ prepnutia a `isls` sú páry indexov ich modelových spojov. Kód overuje indexy, výhľad a spojitý strom. Globalstar s ISL odmieta. Viditeľná dráha teda znamená iba **kandidáta pre model**, nie pridelený servisný lúč operátora.

Po výbere SNS-3 vytvorí modelové SAT, UT a GW uzly, generický DVB user/feeder PHY/MAC, fronty a pri potrebe ISL zariadenia. Náš kód nastaví výkon UT, diagnostickú anténnu mapu, modelové ISL rýchlosti a fronty, lokálnu LAN a IP smerovanie. Na natívny **user channel** navyše pripája náš filter: skúma montáž/zorné pole, rýchlosť smerovania, zvyškový Doppler a miestnu budovu pri RSU. V `satellite_rf.csv` je preto `reason=accepted`, `building`, `mount_fov`, `doppler` alebo `pointing`. `accepted` znamená, že **náš filter neodmietol** tento pokus. Ešte musí uspieť SNS-3 PHY/MAC, fronty, smerovanie a prijatie gateway aplikáciou.

Výpočet Dopplera v natívnom filtri je `doppler_hz=−carrier_hz×radial_mps/c`; zvyšok po predpokladanej kompenzácii je `abs(doppler_hz)×(1−compensation)`. Pri `compensation=0,98` zostanú 2 %. V ukážkovej RF stope pri jednom **forward_user** rozhodnutí blízko 5 s bola nosná `1 683 750 000 Hz`, Doppler približne `−32 902 Hz`, zvyšok približne `658 Hz` a výsledok filtra `accepted`. Táto vzorka je downlink, preto jej `carrier_hz` nie je scenárových `link_policy.rf_hz=1 621 250 000 Hz` pre uplinkový predpoklad. Zvyšok 658 Hz je pod zadanou toleranciou 20 000 Hz, ale sám paket nedoručuje. Pri čítaní stopy vždy pozri `channel` (`forward_user` alebo `return_user`).

`satellite.link_budget` predstavuje **odlišný audit**. Z intervalov EIRP, prijímacieho G/T, požadovaného C/N0 a strát počíta interval predpokladanej rezervy. Keď predpoklady chýbajú, výsledok ostáva `unknown_missing_…`. Kladná modelová rezerva neprikáže SNS-3 doručiť paket a nepreukazuje aktívny modem, beam alebo komerčnú službu. Satelitné profily v tejto BP sú pomenované podľa zamýšľaných skupín dráh a verejných limitov; natívne satelitné rádio je **generický DVB model**, nie proprietárny protokol Starlinku, Iridia alebo Globalstaru.

## 17. Prvé miesto straty, oneskorenie a správny menovateľ

Rozlišuj **naplánované**, **vytvorené**, **ponúknuté vrstve**, **prijaté na uzle** a **prijaté cieľovou aplikáciou**. Naplánovaná DENM v `denm-events.csv` nie je rádio. `DENM_UPER_TX` je vytvorený zakódovaný obsah. `GN_BTP_DENM_TX` znamená odovzdanie cestnému zásobníku. `RSU_DENM_LAN_TX` znamená príjem zdrojovou RSU a jej rozhodnutie mostiť. `UT_DENM_SAT_TX` je pokus cez satelitný backend. `GATEWAY_DENM_RX` potvrdzuje príjem v modelovej bráne. `RSU_DENM_REGENERATED` je nové miestne vyslanie na vzdialenej RSU. Až `DENM_UPER_RX` na konkrétnom aute je dôkaz jeho aplikačného príjmu.

V ukážkovom behu idú hlavné časy takto: `car0 TX 5 000 000 µs` → `rsu0 LAN TX 5 000 258` → `UT SAT TX 5 000 365` → `GW RX 5 117 122` → `rsu1 regenerácia 5 135 406` → `car3 RX 5 135 655`. Rozdiely sú `0,258 ms`, `0,107 ms`, `116,757 ms`, `18,284 ms` a `0,249 ms`; spolu `135,655 ms`. Celé číslo **nie je oneskorenie jedinej satelitnej hrany**: zahŕňa pozemný, aplikačný a satelitný modelový úsek. Rovnako `UT_DENM_SAT_TX` ešte nie je dôkaz príjmu gateway; na ten potrebuješ `GATEWAY_DENM_RX` a súvisiacu internú SNS-3 stopu.

PDR potrebuje vždy presný **menovateľ a úsek**. Ak 10 unikátnych DENM bolo oprávnených na zdrojovú RSU a tá prijala 8, lokálna PDR je `8/10`. Ak zo 8 mostených dorazilo 6 do GW, PDR tohto úseku je `6/8`; celková auto→GW PDR je `6/10`. Pri GeoBroadcaste sa jedna akcia môže prijať na viacerých uzloch: štyri `DENM_UPER_RX` pri rovnakom `event_id` nie sú štyri nezávislé udalosti. Pri `repetition_ms>0` musíš povedať, či počítaš unikátne `actionId`, verzie `referenceTime`, fyzické rámce alebo príjemcov.

`PASS` od checkera znamená splnenie jeho konkrétnych časových a bajtových invariantov. Neznamená automaticky stopercentnú PDR, úplnú ETSI certifikáciu ani prevádzkovú dostupnosť. `trace.csv` spája etapy podľa `event_id`; PCAP ukazuje pozemné 802.11 rámce; `PacketTrace.log` internú SNS-3 cestu; `satellite_rf.csv` dôvod nášho user-link filtra. Manifest ukladá hash vstupov a kódu. Ak sa kód neskôr zmení, starý beh zostáva historickým dôkazom pôvodného stavu a nesmie sa bez overenia predstierať ako nový výsledok.

## 18. Dve malé stavové mašiny: CAM interval a životný cyklus DENM

Pri CAM sa ľahko pomýli **vzorka** s **pravidlom odoslania**. Každých 100 ms má aplikácia novú polohu, ale `Station::check` porovnáva nový waypoint s poslednou **odoslanou** CAM. `cbr(now)` počíta obsadenosť kanála v uplynulej sekunde. Konfigurácia má prahy `low_cbr=0,004` a `high_cbr=0,012`; podľa nich minimálny interval môže byť 100, 250 alebo 500 ms. Presne pri `0,004` už platí stredná vetva, presne pri `0,012` vysoká vetva, pretože C++ používa `>=`. Aj keď sa auto pohlo o 4,1 m, pri uplynutých 100 ms a požadovaných 250 ms sa nová CAM ešte neposiela. Naopak, ak interval uplynul a pohybová alebo periodická podmienka platí, `send_cam` sa zavolá; potom má výsledok ešte pred sebou Vanetzu a ns-3 rádio.

| Posledná CAM | Terajší krok | CBR → minimum | Pohyb > prah? | Rozhodnutie našej aplikácie |
| --- | --- | --- | --- | --- |
| Žiadna | Prvá vzorka | Ľubovoľné | Nehrá rolu | Prvú CAM vytvorí. |
| Pred 100 ms | Zmena 4,1 m | `0,010` → 250 ms | Áno | Teraz ju preskočí pre minimálny interval. |
| Pred 300 ms | Zmena presne 4,0 m; periodický čas ešte neuplynul | `0,010` → 250 ms | Nie (`>` je nepravda) | Teraz ju nevytvorí. |
| Pred 500 ms | Zmena 4,1 m | `0,013` → 500 ms | Áno | Môže ju vytvoriť; o príjme rozhodne rádio. |

DENM má stav určený dvojicou `(source_id,sequence)`, nie iba textom „zápcha“. Predstav si `car0`, `sequence=7`, `new at_s=5`, `validity_s=45`: prvá verzia platí najneskôr do pôvodného okna okolo 50 s. `update` pri `at_s=10` je povolený iba pre aktívnu akciu, s vyšším časom a pred koncom pôvodnej platnosti. `cancel` pri `at_s=12` ju ukončí; ďalší `update` tej istej dvojice už validátor odmietne. Druhý `new` tej istej dvojice v rámci scenára sa tiež odmietne, lebo identita už bola použitá. `repetition_ms=0` znamená bez plánovaných opakovaní; pri nenulovom platnom intervale náš kód plánuje opakované odoslanie do ďalšej verzie udalosti, konca platnosti alebo konca simulácie. Opakovanie existujúcej verzie nie je nový `actionId`.

Na príjme sa kontroluje `detectionTime`, `referenceTime`, platnosť, predchádzajúca verzia a duplicita. Tá istá verzia prijatá druhý raz môže byť `duplicate`; staršia po novšej `outdated`; zrušenie neznámej akcie `unknown_termination`; príchod po platnosti `expired`. Vzdialená RSU pritom zachová pôvodný `actionId`, aby sa celá cesta dala považovať za jednu udalosť. **GeoNetworking preposlanie, opakovanie aplikáciou a regenerácia na vzdialenej RSU sú tri rôzne mechanizmy**: môžu všetky vytvoriť ďalší rámec, ale nie každá vytvorí novú dopravnú akciu.


# Časť II — každé vstupné pole a jeho účinok

## 1. Tri súbory, ktoré editor uloží

`simulator_editor_api.save` zapisuje `world.json`, `demand.json` a scenár v `config/scenarios/`. `world` určuje mapu, dopravný model a RSU; `demand` určuje konkrétne autá; scenár určuje sieť, udalosti a satelit. Pred behom `simulator_cli.preflight` prepíše `world.vehicles` hodnotou `demand.vehicles`, takže pre konkrétny beh sú autá z **demand**. `world.flows` a `world.network_execution` sú deklaratívne údaje editora: `execution="not_implemented"` v nich nevytvára pakety. Tie vznikajú v aktívnom C++ engini podľa scenára.

Príklad čítania cesty v kóde: `scenario['radio']['tx_power_dbm']` = výkon pozemného vysielača; `world['rsus'][0]['x_m']` = lokálna súradnica prvej RSU. `[]` tu znamená „vyber položku“.

## 2. `world.json`: plocha, čas a súradnice

| Pole | Rozsah/jednotka a logický význam | Účinok a miesto v kóde |
| --- | --- | --- |
| `schema_version` | Presne `2`. | K; kontrola formátu v `validate`. |
| `extent_m` | Voliteľné `2000` alebo `4000` m; štandardná štvorcová plocha. | P; hranice lokálnych objektov a výrez mapy. |
| `width_m`, `height_m` | Voliteľná dvojica celých čísel `500…4000` m; oba naraz; nahrádza rozmery z `extent_m`. | P; hranice súradníc a výrez prostredia. |
| `map_source` | `manual` alebo `osm_live`; predvolené `manual`. | P; `osm_live` volí odlišné nastavenie vstupnej rýchlosti a mapovanie kliknutej polohy na SUMO pruh v `make_inputs` a `align_route_positions`. |
| `network_execution` | Presne `schema_only`. | K; starší world formát sám nemá sieťovú väzbu. Aktívny runner sieť spustí samostatne. |
| `simulation.duration_s` | World povoľuje `1…300` s, násobok kroku; aktuálny sieťový beh vyžaduje **celé `2…120` s**, pri satelite aspoň 6 s. | P; dĺžka dopravného a paketového okna. `simulator_cli.runtime_inputs` pridá `0,3 s` na SUMO dobeh. |
| `simulation.step_s` | World `0,1…1` s; aktuálny beh nastaví **0,1 s**. | P; SUMO FCD a rádiové waypointy každých 100 ms. |
| `simulation.seed` | World `0…2³¹−1`; aktuálny beh ho prepíše scenárovým `seed`. | P; deterministické dopravné generovanie. |
| `simulation.utc_origin` | ISO 8601 UTC; aktuálny beh prepíše scenárovým `utc_origin`. | P; absolútny čas pre orbitu a DENM. |
| `georeference.frame` | Presne `WGS84_ENU`. | P; lokálne **x na východ, y na sever**, metre. |
| `georeference.anchor_x_m`, `anchor_y_m` | Lokálny bod v rámci šírky/výšky mapy. | P; tento bod zodpovedá zadanému zemepisnému bodu. |
| `georeference.latitude_deg`, `longitude_deg`, `height_m` | Zemepisná šírka `−90…90°`, dĺžka `−180…180°`, výška `−500…9000 m`. | P; referencia ENU↔WGS84 v `simulator_coordinates.py`; polohy terminálov a CAM. Lokálne `up=0` pri prevode auta **nie je digitálny model výšky vozovky**. |

Príklad: kotva `(2000,2000)` na zemepisnom bode a auto `(2100,2000)` znamenajú približne 100 m na východ. Pri kreslení plátno prevracia y; JSON nie. FCD po spracovaní cez `netconvert` môže mať inú polohu než pôvodné kliknutie, hlavne v križovatke.

### Model jedného typu auta: `simulation.vehicle_model`

Celý objekt je voliteľný; ak chýba, `make_inputs` použije `accel=2`, `decel=4,5`, `sigma=0`, `length=5`, `width=1,8`, `minGap=2,5`, `speedFactor=1`, `manual_max_speed=40` v jednotkách nižšie. Ak objekt uvedieš, potrebuje **všetkých osem** kľúčov.

| Pole | Povolené | Ako sa použije |
| --- | --- | --- |
| `accel_mps2` | `0,1…10 m/s²` | P; SUMO `vType.accel`, schopnosť zrýchľovať. |
| `decel_mps2` | `0,1…15 m/s²` | P; SUMO `decel`, bežné spomalenie. |
| `sigma` | `0…1` | P; variabilita správania predvoleného SUMO car following modelu. |
| `length_m`, `width_m` | `1…20 m`, `0,5…3 m` | P; rozmery vozidla v SUMO; následne polia CAM. |
| `min_gap_m` | `0…10 m` | P; minimálny odstup v SUMO. |
| `speed_factor` | `0,1…2` | P; násobiteľ želanej rýchlosti v SUMO. |
| `manual_max_speed_mps` | `0,1…60 m/s` | P; maximálna rýchlosť spoločného `vType` len v `manual`; pri `osm_live` sa maxSpeed vytvorí osobitne z `depart_speed_mps` auta. |

Projekt explicitne neurčuje názov SUMO `carFollowModel`; platí model predvolený v použitej verzii SUMO. Vlastné sú hodnoty `vType` a generovanie XML, fyziku pohybu počíta SUMO. SUMO car following.

## 3. `world.roads`, `demand.vehicles` a `world.rsus`

| Pole | Jednotky a význam | Účinok |
| --- | --- | --- |
| `roads.nodes[]` | `2…30000` križovatkových/koncových uzlov. Každý má `id`, `x_m`, `y_m` v rámci plochy. | P; `make_inputs` píše `road.nod.xml`. |
| `roads.segments[]` | `1…30000` cestných úsekov; `id`, `from`, `to` sú ID uzlov. | P; orientovaný graf pre trasy. |
| `segments[].shape` | `2…30` bodov `[x_m,y_m]`, prvý/posledný sú príslušné uzly s toleranciou 0,01 m; každý diel aspoň 1 m, celok aspoň 2 m. | P; geometria SUMO hrany, potom jazdná poloha a rádio. |
| `segments[].speed_limit_mps` | `1…40 m/s`. | P; SUMO `edge.speed`; obmedzenie cestnej rýchlosti. |
| `segments[].lanes_each_direction` | Celé `1…3`. | P; počet pruhov **v každom povolenom smere**. |
| `segments[].oneway` | Voliteľné bool, predvolené `false`. | P; pri `true` nevznikne `reverse` SUMO hrana, trasa v protismere sa odmietne. |
| `segments[].osm_way_id`, `name`, `road_class` | Voliteľné OSM ID ako desiatkové číslice v texte, meno do 120 znakov, trieda do 40. | K/Z; pôvod a označenie cesty, samotný paketový engine z nich nerozhoduje. |
| `vehicles[]` | V aktuálnom behu `demand.vehicles`; aspoň **dve** autá. | P; každé sa stane SUMO autom a ITS rádiovým uzlom. |
| `vehicles[].id` | Jedinečné ID, aj vo výsledných stopách. | P/K; viaže waypointy a stanice. |
| `vehicles[].depart_s` | World `0…duration−step`; aktuálny beh vyžaduje **0 s**. | P; všetky rádiá sú pripravené na začiatku komunikačného okna. |
| `vehicles[].depart_speed_mps` | `0…40 m/s`. | P; v manuálnej mape počiatočná rýchlosť; pri `osm_live` `vType.maxSpeed` a `departSpeed="max"`, takže skutočnú vstupnú rýchlosť upraví SUMO podľa pruhu. |
| `vehicles[].route[]` | `1…200` nadväzujúcich krokov `{segment,direction}`; smer `forward/reverse`. | P; poradie SUMO hrán. Nepripojené úseky a jazda proti `oneway` sa odmietnu. |
| `vehicles[].depart_pos_m` | Voliteľná vzdialenosť od začiatku prvej hrany; predvolené 0; najviac dĺžka prvého úseku mínus 20 m. | P; kliknutá východisková poloha, pri OSM sa premietne na skutočný SUMO pruh. |
| `vehicles[].arrival_pos_m` | Voliteľná vzdialenosť na poslednej hrane; v rámci jej dĺžky. | P; koncová poloha. Po príchode sa auto do konca rádiového okna drží zastavené. |
| `vehicles[].technologies` | Neprázdny zoznam unikátnych hodnôt z `its_g5`, `cellular_v2x`, `ip_backhaul`, `satellite_terminal`; auto nesmie mať `satellite_terminal`, aktuálny beh vyžaduje `its_g5`. | K; deklarované schopnosti. Samotný záznam `cellular_v2x` **nespustí C-V2X**; aktuálna rádiová cesta je ITS-G5. Účinné zapnutie určuje `node_policy`. |
| `rsus[]` | `0…512` v aktívnom behu. | P; pevné cestné jednotky. Satelitný beh potrebuje aspoň jednu s backhaulom. |
| `rsus[].id`, `x_m`, `y_m` | Jedinečné ID; lokálne metre v rámci mapy. | P; poloha pozemného rádia a prípadného satelitného UT. |
| `rsus[].technologies` | Rovnaký deklaratívny zoznam; aktuálny beh vyžaduje `its_g5`. | K; `satellite_terminal` tu ešte samo osebe nezapína prevádzku, rozhoduje `node_policy.rsus[id].satellite_backhaul`. |

`netconvert` zostrojí sieť; `sumo` vypíše FCD. `simulator_mobility_export.py` z FCD pripraví per auto čas, lokálne `x/y`, WGS84 `lat/lon`, rýchlosť, smer, zrýchlenie, yaw, svetlá a rozmery. Tieto údaje **sa menia v čase podľa SUMO**, nie podľa stálej hodnoty `depart_speed_mps`. Význam FCD podľa SUMO.

### `demand.json`

| Pole | Význam |
| --- | --- |
| `schema_version` | Presne `1` (K). |
| `kind` | `synthetic_trips` alebo `measured_trips` (K). Merané trasy vyžadujú odkaz na zdroj; editorom vygenerované trasy sú syntetické. |
| `provenance` | Neprázdny text; pri `measured_trips` sa musí začínať `https://` (K). |
| `vehicles` | Tie isté polia áut z tabuľky vyššie; **tento zoznam vstupuje do aktuálneho behu** (P). |

### `world.flows[]`: opis zámeru, nie vykonávané smerovanie

World vyžaduje `1…100` záznamov. Každý obsahuje `id`, `source`, `target` (ID uzla alebo `broadcast`), `technology`, `message_type` (`CAM`, `DENM`, `IP_REPORT`, `CUSTOM`) a `execution="not_implemented"`. Validátor kontroluje existenciu uzlov a deklarovanú technológiu; pre CAM/DENM povoľuje iba pozemné V2X technológie. **Žiadna z týchto hodnôt sama neurčuje adresáta satelitného mosta ani nevysiela správu.** Aktívne správanie tvorí `scenario.denm_events`, `source_id`, `rsu_id`, `alert_target_rsu`, `node_policy` a C++ aplikácia. `validate`, `vanet-leo-network.cc`.

## 4. Globálna OSM vrstva `world.map_objects` a UI

`map_objects` je voliteľný objekt verzie `1`, ktorý udržiava editovateľné **pôvodné WGS84** body pri `osm_live`. Cestný `roads[]` má `id`, `coordinates` ako 2…30 dvojíc **`[longitude,latitude]`**, `speed_limit_mps`, `lanes_each_direction` a voliteľné `oneway`, `osm_way_id`, `name`, `road_class`. Auto `cars[]` má `id`, `longitude_deg`, `latitude_deg`, `road_id`, `depart_s`, `depart_speed_mps`, `direction`, `technologies`, `ground_mode`, `source`; môže mať `route[]` a `arrival_pos_m`. RSU `rsus[]` má `id`, zemepisnú dĺžku/šírku, `technologies`, booleany `ground`, `satellite_backhaul`, `primary`, `alert_target`. `sources[]` nesie pôvod OSM výrezu: `bbox`, `retrieved_at`, `sha256`, `provider`, `tiles`, `ways`, `roads`, voliteľný `dataset_sha256`. Tieto objekty sa pri ukladaní kontrolujú a premietajú do lokálneho grafu.

Toto je **zdroj editovania a pôvodu**. Skutočný SUMO a ns-3 beh používa projekciu do `world.roads`, `demand.vehicles`, `world.rsus` a účinnú `node_policy`. Pri rozpore treba sledovať uložené súbory v `results/simulations/<run_id>/inputs/`, nie iba ikonu na mape.

Ovládacie prvky `spawn_count` a `traffic_trip_percent` v `technical-parameters-bridge.js` menia **budúce generovanie áut/trás**; už vytvorenému behu nič spätne nepridajú. Priblíženie, zvolená vrstva, glóbus a kruh okolo RSU sú vizualizácia. Napríklad kruh 300 m v `viewer/simulator.js` **nie je dosah odvodený z rádiového modelu**.

## 5. `scenario.json`: voľba behu, pozemné rádio a politika

Scenár má **presne** horné kľúče v tabuľke; ďalšie nie sú povolené. Verzia je `7`. Úplný `preflight`.

| Pole | Povolené/význam | Účinok |
| --- | --- | --- |
| `schema_version` | `7`. | K; správna aktívna schéma. |
| `scenario_id` | Malé písmeno na začiatku, potom malé písmená/číslice/pomlčky, 3…48 znakov. | K; identita behu. |
| `world_template`, `demand` | Projektové cesty **pod `data/inputs/`**, bez `..`. | P; načítanie konkrétneho sveta a vozidiel cez `simulator_inputs.project_input`. |
| `source_id` | ID existujúceho auta s aktívnym pozemným rádiom. | P; primárna stanica a predvolený zdroj DENM. |
| `rsu_id` | ID zdrojovej RSU; `""` iba ak RSU nie sú. | P; jednotka, z ktorej môže začať most. |
| `alert_target_rsu` | Text; pri satelitnom cieli iná aktívna RSU. | P; vzdialená RSU pre opätovné miestne vyslanie DENM. |
| `seed`, `ns3_run` | Každé celé `1…2³¹−1`. | P; deterministické zdroje náhodnosti SUMO/ns-3; číslo behu umožní opakovanie. |
| `utc_origin` | Presne `YYYY-MM-DDTHH:MM:SSZ`. | P; absolútny čas orbitalnej geometrie a časových polí správ. |
| `sample_count` | `20…1200`, presne `duration_s × 10`. | P; počet 100 ms vzoriek. |
| `mode`, `time_policy` | Presne `unified`, `ready_at_t0_full_duration`. | K/P; aktuálna vetva a spoločné časové okno; autá majú `depart_s=0`. |
| `satellite_enabled` | Bool, presne zodpovedá tomu, či niektorá RSU má `satellite_backhaul=true`. | P; volí pozemný alebo integrovaný ns-3/SNS-3 beh. |
| `radio`, `link_policy`, `satellite`, `node_policy`, `denm_events` | Vnorené objekty nižšie. | P/K podľa konkrétneho poľa. |

### `radio`

| Pole | Jednotky, rozsah | Kto a ako ho používa |
| --- | --- | --- |
| `mode` | `friis` alebo `urban_los`. | P; `simulator_inputs.ground_config` vyberie model útlmu ns-3. Ak existujú budovy, `simulator_cli.template` účinne prepne na `urban_osm_building`. |
| `tx_power_dbm` | `0…33 dBm`. | P; výkon ITS-G5 vysielača v ns-3. |
| `noise_figure_db` | `0…20 dB`. | P; šum prijímača v ns-3. |
| `rate_mbps` | Voliteľné `3/6/12/24 Mbit/s`, predvolené 6. | P; modulácia/dátová rýchlosť 10 MHz 802.11p PHY. |
| `channel_number` | Voliteľné `172,174,…,184`, predvolené 180. | P; stredová frekvencia `5000+5×channel_number` MHz a kanál. |
| `tx_gain_dbi`, `rx_gain_dbi` | Voliteľné `−20…20 dBi`, predvolené 0. | P; anténne zisky pri pozemnom linku. |
| `shadowing` | Voliteľné bool, predvolené `false`; s `friis` musí byť `false`. | P; dodatočná náhodná zložka podporovaného urban modelu. Samotná voľba nie je 3D stavba. |

Účinná cesta je `radio` → `ground_config` → `simulator_ground_runner.py` alebo `simulator_satellite_runner.py` → C++ `WifiPhy`/propagation model. **Naša aplikácia volí parametre a model; ns-3 rieši MAC/PHY prenos a pravdepodobnosť príjmu.**

### `node_policy`

| Pole | Význam v aktívnom engini |
| --- | --- |
| `cars[id].ground="all"` | Auto komunikuje s autami aj RSU cez ITS-G5. Povinné pre zdroj satelitnej DENM. |
| `cars[id].ground="cars"` | Povolená komunikácia s autami; RSU aplikačne ignoruje príjem z tohto auta. Fyzické zariadenie môže byť vytvorené. |
| `cars[id].ground="off"` | Auto sa aplikačne nevysiela ako aktívna stanica; nesmie byť zdrojom DENM. |
| `rsus[id].ground` | Bool, povolenie miestnej ITS-G5 činnosti RSU. |
| `rsus[id].satellite_backhaul` | Bool, vyžaduje `ground=true`; povoľuje aplikačný satelitný most danej RSU. V natívnom modeli môže topológia vytvoriť UT/LAN aj pre neaktívnu RSU; filter zabraňuje aplikácii použiť ho. |

Objekt musí mať **presne** mapy `cars` a `rsus`, po jednom zázname pre každé ID. `unified_policy`, filtre v C++.

### `denm_events[]`

Najviac 64 udalostí. Každá má **presne** šesť povinných polí a voliteľné `source_id`. Validácia životného cyklu, tvorba správy.

| Pole | Jednotky/význam | Skutočné rozhodnutie |
| --- | --- | --- |
| `source_id` | Voliteľné ID auta; inak scenárové `source_id`. | P; ktorá stanica vytvorí DENM. |
| `at_s` | Reálne číslo `0 ≤ t < duration_s`. | P; kedy aplikácia vyvolá `new/update/cancel`, nie výsledok detekcie zo SUMO. |
| `sequence` | Celé `0…65535`. | P; s ID zdroja identifikuje akciu `actionId`. |
| `operation` | `new`, `update`, `cancel`. | P; `new` vytvorí akciu, `update` mení ešte platnú, `cancel` ju ukončí. Poradie a platnosť kontroluje preflight. |
| `validity_s` | Celé `1…86400 s`. | P; ako dlho je správa platná, používa sa pri tvorbe a príjme. |
| `radius_m` | Celé `1…1780 m`. | P; polomer kruhu GeoBroadcast vo Vanetze. **Nie** maximálny dosah vysielača; fyzický príjem počíta ns-3. |
| `repetition_ms` | `0` alebo celé `100…60000 ms`. | P; náš C++ rozvrh opakovaní; `0` znamená bez opakovania. |

Náš kód používa modelový typ udalosti `trafficCondition/trafficJam`, pozíciu auta a plánovaný čas. Vanetza ju UPER zakóduje, vloží do BTP portu 2002 a GeoNetworking GBC s najviac 3 skokmi; ns-3 pošle skutočné rádiové rámce. Prijímacia RSU mostuje iba vyhovujúcu prijatú správu podľa `node_policy`, deduplikácie a cieľa. ETSI DENM.

## 6. Satelitné polia a čo znamená „dostupné“

Pri `satellite_enabled=true` je povinný objekt `satellite` s `orbit_group`, `orbit_snapshot`, `dynamic_physical=true`, `gateway` a `mask_deg`. Povolené sú iba nižšie uvedené ďalšie polia.

| Pole | Jednotky/význam | Účinok |
| --- | --- | --- |
| `orbit_group` | `iridium-NEXT`, `globalstar`, `starlink`. | P/K; profil frekvencií, elevácie, antény a prípustnej topológie. |
| `orbit_snapshot.path`, `manifest_sha256` | Cesta `data/orbits/<archív>` a 64 hex znakov SHA-256 manifestu. | P/K; pripnuté OMM dráhy pre konkrétny UTC čas; hash bráni tichej výmene vstupu. `validate_pin`. |
| `dynamic_physical` | Presne `true`. | K/P; podmienka natívneho integrovaného behu. |
| `gateway` | `[latitude_deg,longitude_deg,height_m]`; šírka `−90…90°`, dĺžka `−180…180°`; editor pri výške povoľuje `−500…9000 m`. | P; **modelová** brána pre feeder link a SNS-3, nie dôkaz umiestnenia operátorskej GW. |
| `mask_deg` | `0 ≤ uhol < 90°`. | P; minimálna elevácia; účinné minimum je maximum masky a profilu služby/antény. |
| `catalog_ids` | Voliteľný zoznam NORAD ID. Prázdny zoznam znamená automatický výber **jednej** družice pre aktívne RSU a GW počas celého okna. | P; explicitný viacdružicový výber musí prejsť geometriou a topológiou. |
| `isls` | Dvojice indexov do `catalog_ids`; pre Globalstar ISL nepovolené. | P; hrany modelovej medzisatelitnej siete SNS-3. |
| `initial_serving_sat`, `handover_target_sat`, `feeder_sat` | Indexy družíc v explicitnom `catalog_ids`. | P; počiatočné pripojenie UT, cieľ handoveru a družica pri feeder/GW. |
| `beam_gain_dbi` | Diagnostický/modelový zisk anténnej predlohy. Editor povoľuje `−10…60 dBi`, ale `simulator_satellite_inputs.generate` odmietne hodnotu **nad 50 dBi**. | P; vstup do SNS-3 predlohy, **nie** overený aktívny operátorský lúč. Rozsah 50…60 v UI je aktuálny nesúlad, beh s ním nevznikne. |
| `ut_power_dbw` | Výkon UT `−50…20 dBW`. | P; parameter natívneho satelitného vysielača. |
| `forward_isl_bps`, `reverse_isl_bps` | Celé `100…10¹⁰ bit/s`. | P; rýchlosti modelového ISL, ak sa používa. |
| `forward_queue_packets`, `reverse_queue_packets` | Celé `1…10000` paketov. | P; veľkosť modelových ISL front. |
| `antenna_model` | Ak je uvedený, presne `public-v1`. | K/P; profil verejných terminálových obálok. |
| `terminal_mounts` | Mapa aktívnych RSU → `{tilt_deg,azimuth_deg,frame}`. | P; iba pre Starlink a `antenna_model=public-v1`; `tilt 0…180°`, `azimuth 0…<360°`; pre RSU `frame="north"`. Chýbajúci záznam znamená predvolenú montáž nahor. `validate_mounts`. |
| `environment`, `link_budget` | Objekty rozpísané nižšie. | P/K; budovy majú účinok na natívny user link a pozemný LOS; terén a štatistické útlmy sú najmä fyzikálny audit. |

Pri explicitnom `catalog_ids` hodnoty topológie kontrolujú `_select_topology` a `simulator_satellite_inputs.generate`. Pri automatike sa najskôr hľadá vhodná jedna družica. Prázdny kandidátsky zoznam, nedostatočná geometria alebo nevyhovujúca konfigurácia vedú k odmietnutiu prípravy; nejde o „nulové pakety“ skrytého behu.

### `link_policy`: presne šesť kľúčov

| Pole | Rozsah a význam v natívnom filtri |
| --- | --- |
| `rf_hz` | `1×10⁹…5×10¹⁰ Hz`; frekvencia pre výpočet Dopplera. |
| `compensation` | `0…1`; podiel kompenzovaného Dopplera; zvyšok `abs(doppler)×(1−compensation)`. |
| `doppler_tolerance_hz` | `0…1×10⁷ Hz`; ak zvyšok prevýši toleranciu, user link je odmietnutý. |
| `zenith_cone_deg` | `0…90°`; montážny smerový limit. |
| `steering_rate_deg_s` | `0…360°/s`; limit rýchlosti smerovania. |
| `beam_half_angle_deg` | `0…90°`; polovičný uhol lúča. |

`simulator_satellite_runner.py` zapíše tieto čísla do natívneho CSV, ktoré číta `satellite-link-condition.h`. Pri **Iridiu/Globalstare** natívny kód smerové limity nastaví na všesmerové hodnoty `180/360/180°`, keďže pre daný terminál nie je doložená inštalovaná smerová krivka. Frekvencia a Doppler sa stále uplatňujú. Pri Starlinku sa uplatní verejné FOV a montážny predpoklad. Tento filter môže user link odmietnuť; ak ho prijme, o ďalšom PHY/MAC osude rozhoduje SNS-3.

### `satellite.environment`: budovy, terén a odhad

Objekt verzie `1` má `georeference` presne rovnakú ako `world`, `extent_m` alebo dvojicu `width_m,height_m`, `buildings`, `terrain`, `height_case`, `uncertain_route_policy`, `statistical_layers`, `sources`. Kontrola je v `validate_environment`. Rozmery sa musia rovnať svetu.

| Pole | Význam a účinok |
| --- | --- |
| `buildings[]` | Najviac 50 000 budov. Každá potrebuje `polygon_xy_m` (3…150 lokálnych bodov), `height_min_m`, `height_max_m` (`0…500 m`) a text `height_source`. Záznamy môžu mať `id`, `height_central_m`, `height_reference`, `building_class`. OSM `height` je neoverený tag; `building:levels` sa mení pomocou predpokladu 2,5…4 m na podlažie; neznáma výška tvorí interval, nie presný bod. |
| `height_case` | `interval`, `low`, `central`, `high`. Natívny export pre `low/high` vyberie minimum/maximum; pre `central/interval` centrálny odhad, prípadne stred intervalu, ak chýba. Pre voľby `low/central/high` validátor vyžaduje `height_central_m` každej budovy. Samostatný audit pri `interval` zachová neistotu. `simulator_ground_obstructions.py`. |
| `terrain.origin_xy_m`, `step_m`, `width`, `height`, `elevation_m` | Mriežka HGT: začiatok `[-120,-120]`, krok 30 m, rozmery z výrezu, výšky `−500…9000 m`. **Používa ju samostatný fyzikálny náhľad/audit lúča**, nie plný výškový model pre každý pozemný paket v ns-3. |
| `uncertain_route_policy` | Presne `optimistic_with_uncertainty_flag`; neistota sa nesmie predstierať ako potvrdené doručenie. |
| `statistical_layers.weather`, `.vegetation` | Každá vrstva má `recommendation`, `status`, `assumed_loss_db_interval` alebo `null`; pri číselnom intervale `0…100 dB` a stav `scenario_assumption_not_ITU_prediction`. Ide o výslovný odhad pre fyzikálny link budget, **nie natívny paketový filter dažďa/vegetácie**. |
| `sources.osm`, `.terrain` | Pôvod podkladov pre audit a opakovateľnosť. |

Budova v pozemnej vetve: náš `OSMBuildingCondition` zisťuje prienik 3D úsečky medzi vozidlovými/RSU anténami s pôdorysom vytiahnutým do vybranej výšky. Oznámi LOS/NLOS **ns-3 3GPP V2V modelu útlmu**; ten s 802.11p PHY určí výsledok príjmu. Budova v satelitnej vetve: náš `NativeSatelliteCondition` môže priamo odmietnuť miestny **user link** podľa prieniku 3D lúča, Dopplera a montáže. Miestne budovy nepredstavujú model vzdialeného feeder linku.

### `satellite.link_budget`: len audit predpokladov

Voliteľné vetvy `user_uplink`, `user_downlink`, `feeder_uplink`, `feeder_downlink`. Každá môže mať intervaly `eirp_dbw_interval`, `rx_gt_db_per_k_interval`, `required_cn0_dbhz_interval`, `other_loss_db_interval`; voliteľne `pointing_loss_db_at_70deg_interval`, `environment_loss_db_interval`. Feeder navyše potrebuje explicitné `frequency_hz` v `10⁸…10¹¹ Hz`; user frekvencia je z profilu. Interval je dvojica `[minimum,maximum]`, ostatné straty `0…100 dB`. Ak niečo potrebné chýba, výsledok auditu zostane `unknown_missing_…`. Ak predpoklady stačia, `simulator_link_budget.py` spočíta FSPL, interval C/N0 a rezervy. **Tieto odhadové intervaly samy nenastavujú satelitný modem ani neprikazujú SNS-3 doručiť paket.**

## 7. Hodnoty, ktoré editor v aktuálnej vetve neponúka ako voľbu

| Hodnota | Kde vzniká a čo znamená |
| --- | --- |
| **100 ms** | `simulator_cli.py` vynúti krok 0,1 s a `sample_count=duration×10`; z tohto rytmu vznikajú waypointy a kontroly CAM. |
| **CAM BTP 2001, DENM BTP 2002; DENM max. 3 GN skoky** | Nastavenie nášho C++ odosielania; Vanetza realizuje príslušný cestný zásobník. |
| **CAM pohyb >4 m / >0,5 m/s / >4°** | Podmienky nášho `Station::check`; `>` znamená, že rovná hodnota ešte pohybový spúšťač nevyvolá. `Station::check`. |
| **DCC prahy CBR 0,004 a 0,012; minimá 100/250/500 ms** | Scenárová výskumná politika z `ground-radio-reference.json` používaná v C++ pri `dcc=1`. |
| **10 MHz OCB** | Pevná šírka 802.11p kanála. Výber `channel_number` a `rate_mbps` zostáva editovateľný. `vanet-leo-network.cc`. |
| **Auto 1,5 m; RSU `max(5 m, strecha+2 m)`** | Model výšky pozemných antén v C++ `radio_height`. Nie je to presná montáž skutočného zariadenia. |
| **RSU↔UT LAN 100 Mbit/s, 100 µs** | Modelový lokálny IP úsek v integrovanom C++ engini. |
| **Pozemný aplikačný front 512 paketov a obsluha 1 µs** | Argumenty v `simulator_satellite_runner.py`; ide o front pred satelitnou trasou, odlišný od editovateľného **ISL** frontu. |

## 8. Päť otázok pri ľubovoľnom výsledku

1. **Aký je uložený vstup?** V bežiacom projekte je rozhodujúci obsah `results/simulations/<run_id>/inputs/scenario.json`, `world.json`, `demand.json`, nie iba zobrazený kruh alebo formulár. Konkrétny výťah je v časti IV.
2. **Bol vstup len deklarácia?** `flows`, technologický štítok alebo `map_objects` ešte nie je paket. Hľadaj prevod do SUMO XML, `ground.json`, natívneho CSV alebo C++ argumentu.
3. **Kto rozhodoval?** Pozícia = SUMO; tvorba CAM/DENM a most = náš C++; GN/BTP/ASN.1 = Vanetza; 802.11p MAC/PHY = ns-3; satelitný DVB paketový prenos = SNS-3; výber orbitálnej geometrie a user-link filter = náš kód.
4. **Čo je tvrdenie o dostupnosti?** OMM existencia, geometrická viditeľnosť, zorné pole, prijatie filtrom, prijatie na PHY a aplikačné prijatie sú rôzne dôkazy. Nevyvodzuj komerčnú službu z posledného modelového kroku.
5. **Kde sú bajty?** Pri pozemnom behu čítaj `simulator_ground_verifier.py`; pri satelitnom `simulator_message_verifier.py` a natívny `PacketTrace.log`. `PASS` znamená, že konkrétny beh spĺňa definované kontroly, nie automaticky že každá naplánovaná DENM prišla každému autu.


# Časť III — päť kúskov skutočného kódu, ktoré stačí pochopiť

Táto časť ukazuje **skrátené výrezy** aktívneho kódu. Vynechané riadky sú vysvetlené slovne; jednotlivé bloky nie sú samostatné skompilovateľné programy. Čísla riadkov sa po ďalšej zmene projektu môžu posunúť.

## 1. Validácia pred simuláciou

```python
# tools/simulator_cli.py — preflight, skrátené na časové rozhodnutia
world['vehicles'] = demand['vehicles']
world['simulation'].update(seed=s['seed'], utc_origin=s['utc_origin'], step_s=.1)
validate_world(world)
duration = world['simulation']['duration_s']
need(type(duration) is int and 2 <= duration <= 120
     and s['sample_count'] == duration * 10,
     'Pohyb a komunikácia musia trvať rovnako, 2–120 s')
need(all(vehicle['depart_s'] == 0 for vehicle in demand['vehicles']),
     'Všetky autá musia byť pripravené v čase 0 s')
```

**Čítaj po riadkoch:** Autá z `demand` sa stanú aktuálnymi autami `world`. Scenárový seed a UTC čas sa prenesú do sveta, krok sa nastaví na 0,1 s. Potom sa kontroluje platnosť sveta a rovnosť `sample_count = duration×10`. Pre 60 s je to 600 vzoriek, nie 600 CAM. Každé auto musí odísť v čase nula, aby rádio existovalo od začiatku komunikačného okna. Tento kód ešte **nevytvoril žiadny paket**.

## 2. CAM: rozhodnutie našej aplikácie

```cpp
// src/vanet-leo-network.cc — Station::check, podstatné riadky
const double load = cbr(now);
const int minimum = dcc_enabled ?
    (load >= dcc_high_cbr ? dcc_high_ms :
     (load >= dcc_low_cbr ? dcc_mid_ms : 100)) : 100;
const auto elapsed = last_ ? now - last_->time_us : 1000000LL;
const auto dist = last_ ? std::hypot(w.x_m-last_->x_m, w.y_m-last_->y_m) : 0.0;
const auto speed = last_ ? std::abs(w.speed_cmps-last_->speed_cmps)/100.0 : 0.0;
const auto angle = last_ ? std::abs(w.heading_decideg-last_->heading_decideg)/10.0 : 0.0;
const auto heading = std::min(angle, 360.0-angle);
const bool motion = last_ && (dist>4.0 || speed>0.5 || heading>4.0);
const bool elapsed_ok = elapsed >= minimum*1000LL;
const bool periodic = elapsed >= tgen_ms_*1000LL;
const int trigger = !last_ ? 0 :
    (elapsed_ok && motion ? 1 : (elapsed_ok && periodic ? 2 : -1));
if (trigger >= 0) send_cam(w);
```

`cbr(now)` je obsadenosť kanála v predchádzajúcom okne. `minimum` je minimálny odstup daný našou DCC politikou. `dist`, `speed`, `heading` sú **zmeny voči poslednej odoslanej CAM**, nie absolútne súradnice/rýchlosť. Podmienka používa striktne `>`: presne 4,0 m nespúšťa pohybovú CAM. Aj keď je `motion=true`, musí uplynúť `minimum`. Až `send_cam(w)` začne tvorbu CAM. Naša aplikácia rozhodla **kedy**; Vanetza a ns-3 rozhodujú o ďalších krokoch zásobníka a rádia.

## 3. DENM: čo tvoríme a čo odovzdáme Vanetze

```cpp
// src/vanet-leo-network.cc — skrátené z make_denm a emit_denm
management.actionId.originatingStationId = w.station_id;
management.actionId.sequenceNumber = event.sequence;
management.validityDuration = v::asn1::allocate<Vanetza_ITS2_DeltaTimeSecond_t>();
*management.validityDuration = event.validity_s;
// situation.eventType = trafficCondition / trafficJam

btp.destination_port = v::btp::ports::DENM;
v::geonet::GbcDataRequest request(mib_, v::aid::DEN);
request.upper_protocol = v::geonet::UpperProtocol::BTP_B;
request.max_hop_limit = 3;
v::geonet::Circle circle;
circle.r = double(radius_m) * v::units::si::meters;
request.destination.shape = circle;
auto confirm = router_.request(request, std::move(packet));
```

Naša aplikácia určí **obsah**, identitu udalosti, platnosť, čas a oblasť. `radius_m=600` vytvorí cieľový kruh GeoBroadcast; **nie je to fyzikálny dosah antény**. `max_hop_limit=3` povoľuje najviac tri GN skoky. Volanie `router_.request` odovzdá požiadavku Vanetze. Tá realizuje cestný GN/BTP zásobník. Náš adaptér jeho rámce odovzdá ns-3 OCB zariadeniu, ktoré simuluje prenos.

## 4. Most cez RSU: ktorý prijatý paket poslať ďalej

```cpp
// src/vanet-leo-network.cc — výber z Station::indicate
const auto prior = denm_seen_.find(action);
const std::string rejection = now > detected + validity * 1000 ? "expired" :
    (m.termination && prior == denm_seen_.end() ? "unknown_termination" :
     (prior != denm_seen_.end() && reference <= prior->second ?
       (reference == prior->second ? "duplicate" : "outdated") : ""));
if (!rejection.empty()) return;
denm_seen_[action] = reference;
log_bytes("DENM_UPER_RX", id_, id, raw);
if (track_.front().kind == "rsu" && id_ == rsu_id &&
    m.actionId.originatingStationId == denm->header.stationId &&
    !satellite_off_rsus.count(id_) && denm_sat_sent[id_].insert(id).second) {
    auto socket = denm_rsu_uplink_sockets.at(id_);
    socket->SendTo(n::Create<n::Packet>(raw.data(), raw.size()), 0,
        n::InetSocketAddress(ut_lan_addresses.at(id_), denm_uplink_port));
    log_bytes("RSU_DENM_LAN_TX", id_, id, raw);
}
```

Najprv sa odmietne expirovaná, neznáma zrušená, duplicitná alebo zastaraná verzia. `DENM_UPER_RX` hovorí, že naša aplikácia prijala a rozpoznala DENM. Do LAN sa dostane len pri zdrojovej RSU, so správnou identitou akcie, zapnutým backhaulom a bez druhého odoslania toho istého `id`. Toto je vlastné **aplikačné filtrovanie**, nie automatické smerovanie SNS-3. V UT callbacku potom naša aplikácia posiela IP/UDP do satelitnej cesty; SNS-3 simuluje jej paketový priechod. Gateway po skutočnom príjme vyberá cieľovú RSU; tá vydáva nový miestny GN/BTP rámec.

## 5. Dva odlišné významy budovy a satelitného filtra

```cpp
// src/ground-building-condition.h — pozemná podmienka
condition->SetLosCondition(Blocked(a->GetPosition(), b->GetPosition())
    ? ns3::ChannelCondition::LosConditionValue::NLOS
    : ns3::ChannelCondition::LosConditionValue::LOS);

// src/satellite-link-condition.h — výrez user-link filtra
const double off_axis = angle(p.normal, direction);
const double doppler = -carrier_hz * radial / 299792458.0;
const double residual = std::abs(doppler) * (1-p.compensation);
```

Na zemi náš geometrický test oznámi **LOS/NLOS** modelu útlmu v ns-3; budova sama v tomto kroku ešte nezahodí každý paket. Pri satelitnom **user linku** náš natívny filter testuje budovu pri RSU, zorné pole/montáž, smerovanie a reziduálny Doppler. Ak podmienka zlyhá, user link môže odmietnuť; pri prijatí podmienky ešte SNS-3 simuluje vlastný PHY/MAC. To sú dve odlišné rozhodovacie miesta. HGT terén a odhad počasia/vegetácie sú najmä oddelená fyzikálna analýza, nie detailná natívna prekážka každého paketu.

# Časť IV — jedna úplná ukážka vstupu a skutočnej stopy

Toto je **výťah z reálneho uloženého scenára** `navrh-koridor-satelit`. Je zostavený z polí, ktoré rozhodujú v nasledujúcom príklade; ostatné polia a presné rozsahy sú už v časti II.

```json
{
  "scenario_id": "navrh-koridor-satelit",
  "source_id": "car0",
  "rsu_id": "rsu0",
  "alert_target_rsu": "rsu1",
  "sample_count": 600,
  "utc_origin": "2026-10-22T12:45:10Z",
  "radio": {"mode": "urban_los", "tx_power_dbm": 20,
            "noise_figure_db": 7},
  "node_policy": {
    "cars": {"car0": {"ground": "all"}},
    "rsus": {"rsu0": {"ground": true, "satellite_backhaul": true},
             "rsu1": {"ground": true, "satellite_backhaul": true}}
  },
  "denm_events": [{"source_id": "car0", "at_s": 5.0,
                   "sequence": 1, "operation": "new", "validity_s": 45,
                   "radius_m": 600, "repetition_ms": 0}],
  "satellite": {"orbit_group": "iridium-NEXT", "catalog_ids": [],
                "mask_deg": 0.5,
                "gateway": [48.1489, 17.104, 0.0]},
  "link_policy": {"rf_hz": 1621250000.0, "compensation": 0.98,
                  "doppler_tolerance_hz": 20000.0,
                  "zenith_cone_deg": 90.0,
                  "steering_rate_deg_s": 90.0,
                  "beam_half_angle_deg": 90.0}
}
```

**Pozor:** výťah nie je kompletný spustiteľný scenár; preto sa neuč syntax kopírovaním. Plný formát a všetky polia sú v časti II. Ukážkové auto `car0` má `depart_s=0`, `depart_speed_mps=10 m/s`, `depart_pos_m=100 m` na prvom úseku trasy. Lokálna kotva sveta je `(1000,1000)` m pri `(48.1486°,17.1077°)`. `sample_count=600` pri kroku 0,1 s znamená 60 s. Rádio má voliteľné predvolené `rate_mbps=6` a `channel_number=180`, teda 5900 MHz. `catalog_ids=[]` znamená **automatický výber jednej vhodnej družice**, nie nulový počet družíc.

Nasledujúce riadky sú z **jedného uloženého natívneho modelového behu**. Všetky majú rovnaké `event_id=d319516eb46351c4`. Čas je v mikrosekundách od začiatku simulácie:

| Etapa `stage` | Uzol | `time_us` | Čo to dokazuje |
| --- | --- | ---: | --- |
| `DENM_UPER_TX` | `car0` | 5 000 000 | Aplikácia vytvorila zakódované bajty DENM. |
| `RSU_DENM_LAN_TX` | `rsu0` | 5 000 258 | RSU ju prijala a odovzdala do lokálnej LAN pre UT. |
| `UT_DENM_SAT_TX` | `rsu0` | 5 000 365 | UT sa pokúsil poslať IP/UDP cez satelitný backend. |
| `GATEWAY_DENM_RX` | pôvod `rsu0` | 5 117 122 | Modelová gateway prijala obsah. |
| `RSU_DENM_REGENERATED` | `rsu1` | 5 135 406 | Vzdialená RSU vytvorila nový miestny DENM prenos. |
| `DENM_UPER_RX` | `car3` | 5 135 655 | Vzdialené auto prijalo a dekódovalo DENM. |
| `DENM_UPER_RX` | `car4` | 5 135 656 | Druhé vzdialené auto prijalo tú istú akciu. |

Ďalšie dva `DENM_UPER_RX` pri `rsu0` a `car1` znamenajú miestne príjmy **tej istej** udalosti. Zároveň sú v stope GN preposielania: to neznamená nové udalosti, ale ďalšie GN rámce v geografickej distribúcii. Od prvého odoslania do príjmu `car3` prešlo `5 135 655 − 5 000 000 = 135 655 µs = 135,655 ms` **v tomto modeli**. Čas z jedného behu nie je prevádzková latencia komerčnej služby.

Ak by chýbal `RSU_DENM_LAN_TX`, hľadáš pozemné rádio, polohu, budovu, GN oblasť alebo RSU aplikačnú politiku. Ak existuje `UT_DENM_SAT_TX`, ale chýba `GATEWAY_DENM_RX`, hľadáš user/feeder link, topológiu, frontu a routing. Ak existuje regenerácia na `rsu1`, ale nie príjem auta, hľadáš jej miestne rádio. **Stopu čítaj vždy zľava doprava podľa etáp, nie iba podľa `PASS`.**

# Časť V — cvičenia s odpoveďami

Skús najskôr odpovedať bez čítania riadku „Odpoveď“. Nemusíš nič spúšťať ani hľadať mimo tohto dokumentu.

## Deň 1: osem otázok

1. Ktorý nástroj vypočíta pohyb auta? **Odpoveď:** SUMO. Naša aplikácia pripraví sieť/trasy; SUMO vráti časové polohy FCD. Ns-3 ich prevezme do sieťového behu.
2. Aký je rozdiel medzi `world`, `demand` a `scenario`? **Odpoveď:** Mapa/dopravné nastavenia; konkrétne autá/trasy; sieťový pokus, rádio, satelit a udalosti.
3. Ak je kotva `(1000,1000)` a bod `(900,1422)`, kde leží? **Odpoveď:** 100 m západne a 422 m severne od kotvy v lokálnej rovine.
4. Znamená `sample_count=600` 600 CAM? **Odpoveď:** Nie. Je to 600 časových vzoriek počas 60 s. Aplikácia pri každej kontroluje, či CAM vytvorí.
5. Po 100 ms sa auto posunulo presne o 4,0 m, rýchlosť/smer sa zmenili menej. Vznikne pohybová CAM? **Odpoveď:** Nie, kód testuje `dist>4.0`.
6. Po 100 ms sa posunulo o 4,1 m, ale DCC minimálny odstup je 250 ms. Vznikne hneď CAM? **Odpoveď:** Nie, `motion=true`, ale `elapsed_ok=false`.
7. Čo znamená `radius_m=600` pri DENM? **Odpoveď:** Kruhovú cieľovú oblasť GeoNetworking, nie 600 m garantovaného rádiového dosahu.
8. Rozhoduje `world.flows[].execution="not_implemented"` o skutočnom prenose? **Odpoveď:** Nie. Aktívne pakety vznikajú podľa scenárových udalostí, politík a C++ aplikácie.

## Deň 2: desať otázok

1. Kto rozhoduje, či auto vytvorí CAM? **Odpoveď:** Naša C++ aplikácia podľa pohybu, intervalu a DCC. Vanetza rieši cestný zásobník, ns-3 prenos.
2. Kto rozhoduje o mostení DENM cez satelit? **Odpoveď:** Naša aplikácia v prijímacej RSU a UT/GW callbackoch. SNS-3 prenáša pakety po modelovej satelitnej ceste.
3. Čo znamená `satellite_enabled=true`? **Odpoveď:** Integrovaný beh sa môže spustiť, ak sú platné aktívne RSU a satelitné vstupy. Samo o sebe to ešte nedokazuje doručenie.
4. Čo robí 3D budova pri pozemnom rádiu? **Odpoveď:** Náš geometrický test dá LOS/NLOS ns-3 modelu; ns-3 potom počíta útlm a výsledok PHY.
5. Čo robí budova pri satelitnom user linku? **Odpoveď:** Náš natívny filter môže priamo odmietnuť miestny user link podľa prieniku lúča; SNS-3 má ďalšie vlastné podmienky.
6. Je HGT terén použitý ako úplný 3D rádiový svet každého pozemného paketu? **Odpoveď:** Nie, je súčasťou samostatnej fyzikálnej analýzy/náhľadu.
7. Ak je hypotetický Doppler 30 000 Hz a `compensation=0.98`, koľko zostane? **Odpoveď:** `30 000×(1−0,98)=600 Hz`. To je len jedna podmienka user linku.
8. Je družica nad maskou = doručená DENM? **Odpoveď:** Nie. Ešte treba natívny filter, SNS-3 PHY/MAC, routing, gateway a miestny príjem.
9. Čo znamenajú štyri `DENM_UPER_RX` pri jednom `event_id`? **Odpoveď:** Viac príjemcov jednej akcie, nie štyri vytvorené dopravné udalosti.
10. Čo dokazuje 135,655 ms v ukážke? **Odpoveď:** Čas medzi uvedenými etapami v jednom konkrétnom modelovom behu. Nedokazuje latenciu operátora.

## Praktické úlohy: najprv sa rozhodni, až potom čítaj riešenia

1. Scenár trvá 60 s, ale niekto nastaví `sample_count=500`. Dôjde k nesprávnej PDR, alebo k odmietnutiu vstupu pred behom?
2. Pozemný kanál sa zmení z 180 na 172. Aká je nová stredová frekvencia? Vieš bez simulácie povedať, že počet prijatých CAM stúpne?
3. `car0` má v satelitnom scenári `node_policy.cars.car0.ground="cars"`. Prejde predletovou kontrolou ako zdroj DENM pre RSU?
4. Zdrojové auto má waypoint v čase 5 s, ale v stope niet `DENM_UPER_TX`. Na ktorej vrstve hľadáš chybu ako prvej?
5. `DENM_UPER_TX` existuje, `RSU_DENM_LAN_TX` nie. Môžeš povedať „satelit zahodil paket“?
6. `UT_DENM_SAT_TX` a `GATEWAY_DENM_RX` existujú, ale vzdialené auto nemá `DENM_UPER_RX`. Ktoré etapy chceš skontrolovať medzi nimi?
7. Pri budove zvolíš `height_case=high` a geometria prejde do NLOS. Znamená to na pozemnej vetve povinnú stratu každého rámca? Je odpoveď rovnaká pre natívny satelitný user-link filter?
8. Družica je nad `mask_deg`, RF filter píše `accepted`, ale `GATEWAY_DENM_RX` chýba. Ktoré tvrdenia vieš povedať a ktoré ešte nevieš?
9. V jednej stope sú štyri `DENM_UPER_RX` s rovnakým `event_id`. Ak je cieľom PDR unikátnych udalostí do gateway, je správny čitateľ 4?
10. Ukážková cesta má 135,655 ms; z toho `UT_DENM_SAT_TX → GATEWAY_DENM_RX` trvá 116,757 ms. Koľko ms zostáva na ostatné úseky? Znamená 116,757 ms čas jednej RF hrany?

### Riešenia praktických úloh

1. Odmietnutie: `sample_count` musí byť `duration×10`, teda 600. PDR neexistuje, lebo validný beh nevznikol.
2. `5000+5×172=5860 MHz`. O počte príjmov z tejto zmeny samotnej nič isté nevyvodíš; zmení sa rádiová konfigurácia a treba nový porovnateľný beh.
3. Nie. Satelitná DENM vyžaduje, aby jej zdrojové auto malo `ground="all"`, čiže komunikovalo aj s RSU.
4. Začni `denm_events`, časom, zdrojovým ID a plánovaním aplikácie. Waypoint existuje, ale ešte nedokazuje vytvorenie DENM. Nezačínaj SNS-3.
5. Nie. Najskôr rieš miestnu cestu auto→RSU a jej aplikačný filter: GN oblasť, rádio, budovu, duplikát či politiku. Satelitný most nebol ponúknutý.
6. `GATEWAY_DENM_SAT_TX`, `UT_DENM_SAT_RX`, `UT_DENM_LAN_TX`, `RSU_DENM_LAN_RX`, `RSU_DENM_REGENERATED`, miestne GN/OCB a napokon príjem auta. Prvá chýbajúca etapa určí okruh problému.
7. Na zemi nie: NLOS je vstup do ns-3 modelu útlmu a PHY rozhodnutia. Pri satelitnom user linku môže náš filter pri prieniku lúča s budovou priamo vrátiť odmietnutie `building`; stále ide o model miestneho výrezu.
8. Vieš povedať, že geometrická a vybraná lokálna filter podmienka prešli. Bez príjmu gateway nevieš tvrdiť end-to-end doručenie; skontroluj SNS-3 PacketTrace, fronty, user/feeder cestu a routing.
9. Nie. Štyri riadky môžu byť štyria príjemcovia jednej udalosti. Pre PDR unikátnych akcií do GW potrebuješ počet unikátnych oprávnených odoslaných `actionId` a počet z nich prijatých v GW.
10. `135,655−116,757=18,898 ms`. Úsek UT→GW obsahuje modelový satelitný paketový priechod a prípadné ďalšie spracovanie; automaticky ho neoznačuj za čas jednej RF hrany.

## Päťminútová odpoveď na obhajobe

„V práci modelujeme spojenie lokálnej VANET a vzdialeného backhaulu cez LEO. Editor definuje cesty, autá, RSU, rádio, satelitné predpoklady a udalosti. SUMO vypočíta pohyb; náš kód ho prevedie na waypointy. Naša aplikácia vytvára CAM alebo DENM a rozhoduje o preposlaní prijatej DENM cez RSU. Vanetza realizuje ITS správy, BTP a GeoNetworking; ns-3 simuluje miestne 802.11p rádio; SNS-3 generický satelitný paketový úsek. Naša geometria a filtre testujú orbitálnu viditeľnosť, budovy a terminálové obmedzenia. Výsledok kontrolujeme na raw paketových stopách. Z týchto modelových behov netvrdíme prevádzkovú dostupnosť konkrétneho operátora.“

## Voliteľné zdroje až po dočítaní

Ak si neskôr budeš chcieť overiť konkrétny riadok, aktívne časti sú `tools/simulator_cli.py`, `tools/simulator_sumo.py`, `tools/simulator_mobility_export.py`, `tools/simulator_satellite_runner.py`, `src/vanet-leo-network.cc`, `src/ground-building-condition.h` a `src/satellite-link-condition.h`. Uložený ukážkový beh je `results/simulations/readable-corridor-final-20261110`. Pre teóriu sú oficiálne zdroje [ns-3](https://www.nsnam.org/about/what-is-ns-3/), [SUMO](https://sumo.dlr.de/docs/SUMO_at_a_Glance.html), [Vanetza](https://github.com/riebl/vanetza) a [SNS-3](https://github.com/sns3/sns3-satellite). **Na učenie z tohto súboru ich otvárať nemusíš.**
