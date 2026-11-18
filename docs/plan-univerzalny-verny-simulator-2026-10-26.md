# Univerzálny a čo najvernejší simulátor BP — audit a pracovný plán

**Stav:** aktívny plán po dokončení pôvodných P0–P6; 26. 10. 2026. **Cieľ:** pripraviť simulátor ako výskumnú platformu, v ktorej sa nové scenáre skladajú z validovaných vstupov bez úprav zdrojového kódu. Konkrétne scenáre, rozsahy premenných a závery sa určia s vedúcim. Tento dokument nie je tvrdením, že vedúci schválil navrhovaný rozsah.

**Jediný runtime:** ns-3.38/SNS-3 3.38 v `vendor/ns-3.38-ocb-eval`. Pôvodné P0–P6 výsledky sú zmrazená východisková sada. Nová platforma má nové označenie schémy, nový výstupný menný priestor a nesmie ticho prepísať ich vstupy, raw stopy ani význam metrík.

## 1. Definícia cieľa a hranice univerzálnosti

„Univerzálny“ tu znamená **konfigurovateľný v explicitne podporovaných rodinách modelov**: miesto/UTC, cestná sieť a dopyt, počet a identita áut a RSU v deklarovanom rozsahu, merací interval, typ záťaže, rádio, satelitná topológia, prípustný terminálový profil, kontrolné vetvy, seed a metriky. Pre každý vstup musí byť vopred známe, či je vykonateľný, a neplatný vstup sa musí odmietnuť s konkrétnou príčinou. Neznamená to spustenie ľubovoľného deklarovaného flow z editora ani presnú repliku proprietárnej siete.

„Verný“ znamená, že každý parameter a jav má uvedený zdroj, rozsah platnosti a overenie. Používame štyri stupne tvrdenia: **(A) vykonaný a raw overený mechanizmus; (B) zhodný s publikovanou normou/produktovým limitom v presne uvedenom bode; (C) kalibrovaný a nezávisle validovaný pre konkrétnu zostavu; (D) výskumný predpoklad/citlivosť**. Úspešný checker posúva iba A; produktová špecifikácia sama o sebe neposúva model na C. Pri nedostupných interných údajoch zostane D s rozsahom citlivosti a označeným rozdielom od reálnej služby.

## 2. Hĺbkový audit súčasného stavu podľa skutočných zdrojov

| Vrstva | Čo funguje | Presná diera, ktorá obmedzuje ďalšie scenáre | Najbližší overiteľný krok |
| --- | --- | --- | --- |
| Pôvod výsledku | P5 má raw OCB/LAN/ISL/PacketTrace, per-event ID, hashovaný manifest, negatívne a korupčné kontroly; P6 má čistú obnovu. | `tools/check_p5_native_matrix.py` porovnáva starý manifest s **aktuálnym** `src/p5-urban-matrix.cc`, runnerom a kontraktom. Bežná úprava jadra preto zneplatní kontrolu historického behu. Build aj `vendor/` sú mimo hlavného Gitu. | V0: nemenné vydanie zdrojov/checkerov pre P5/P6 a samostatná schéma nových behov; odskúšať obidve verzie po zmene. |
| Konfigurácia | P5 vie meniť seed, dve epochy a štyri skupiny v JSON; runner zachová párovanie. | `tools/prepare_editable_v2_cam.py` povoľuje len dve UTC epochy, krok 0,5 s a šesť CAM od 20 s. `tools/run_p5_native_matrix.py` povoľuje iba 22. 10. 2026 12:00–14:00 a pevné vetvy; `src/p5-urban-matrix.cc` vyžaduje `car0`/`rsu0`, 2 družice, konkrétny beam a šesť TX/RX. Jednoduchý JSON teda neznamená všeobecný E2E beh. | V1–V2: rozdeliť konfiguráciu, validátor, generátor vstupov, natívny model a experimentálny protokol; zrušiť nepotrebné fixture piny až po nových dôkazoch. |
| Doprava a čas | SUMO/OSM → FCD → ns-3 na spoločnej časovej osi; vozidlo sa naozaj pohybuje. | OSM je geometria ciest, nie meraná hustota alebo trasy. FCD sa odoberá po 0,5 s; SUMO nedostáva spätný účinok správy. Chýba parameterizované meracie okno a kontrola warm-up, teleportov a realizovanej ponuky pri každom novom behu. | V2/V5: nezávislý import dopytu, diagnostika SUMO a všeobecné časové vzorkovanie; TraCI/libsumo len pri výskumnej otázke o dopravnej spätnej väzbe. |
| CAM a lokálne rádio | Vanetza UPER CAM/GN/BTP sa prenáša cez ns-3 `OcbWifiMac`; PCAP dokazuje skutočný rámec. Existuje výber Friis/urban LOS/NLOS a PHY drop trace. | CAM vzniká zo šiestich pevných vzoriek; dynamika CAM/DCC nie je úplná ETSI zhoda. Mestský model má 20 dBm, 6 Mb/s, 7 dB NF, vypnuté shadowing a syntetickú budovu; nejde o kalibrovanú ulicu. Nie je potvrdené, že aplikácia 3GPP V2V útlmu na tento Wi-Fi PHY predikuje skutočnú PDR. | V5: riadený generátor CAM, meraný CBR/DCC, audit normy a samostatná terénna alebo publikovaná kalibrácia rádia. |
| RSU/aplikácia | ICB1 vzniká až po dekódovaní CAM; GRA1/I2V1 uzatvára identitu reportu a návrat. | Dnešný obsah, jedna zdrojová rola a príjemca sú súčasťou konkrétneho testu. Žiadna definovaná konfigurácia viacerých zdrojov/RSU, politiky duplicitných reportov či priestorového výberu príjemcu. | V2: explicitné aplikačné roly, formát, politiku RSU a menovatele; najprv zachovať kompatibilný ICB1 režim. |
| Orbity a výber trasy | Archivované OMM/GP, SGP4, UTC/WGS84, elevácia, 10° výskumná maska a ISL geometria. | P5 natívne vyberá dva pripnuté objekty 43253/43258, pevné proxy GW, umelo široký zisk 17 dBi a konkrétne beam 30/43. `tools/p5_service_geometry.py` používa najvyššiu geometrickú eleváciu a proxy mestá, nie aktívny lúč, bránu ani route. Generátor prevádza OMM na TLE a musí riešiť novšie 6-ciferné katalógové čísla. | V3: časovo platný orbitálny import, kandidáti a explicitná stavová cesta `geometry → beam → attach → route → packet`; TLE obmedzenia odmietnuť, nie potichu skresliť. |
| Satelitný prenos | SNS-3 vykonáva generický DVB user/feeder PHY/MAC; modelová ISL, per-hop kontroly a jeden-UT retune sú paketovo overené. | Pôvodný SNS-3 je DVB referenčný model; 17 dBi diagnostická mapa, 1 Gbit/s P2P ISL, proxy GW a syntetický retune nemodelujú Starlink/Iridium/Globalstar. P3 je jedno semeno/epocha. Fixné modelové predpoklady nemajú pri zmenenej geometrii zaručenú platnosť. | V3–V4: všeobecná, explicitne referenčná LEO topológia; anténa, link budget, fronty, scheduler a handover merané/parametrizované len v rozsahu zdrojov. |
| Operátorské profily | Iridium IP, Globalstar natívna MO/MT správa a Starlink IP majú oddelené servisné obaly a overené aplikačné bajty. | Sú prehrávané **po** RSU z identických ICB1, nie v jednom natívnom RF/MAC behu. `config/p4_service_profiles.json` má produktové maximá, ale aj hypotetické delay/loss/queue; `calibration` a `independent_validation` sú `null`. Proxy GW nie je overená anténa. | V6: profil viazaný na SKU/plán/miesto/čas a správnu architektúru; model servisnej hranice iba v rozsahu doložených údajov, inak interval/citlivosť. |
| Experimenty a UI | Párovaný runner, checker, grafy a editorový dopravný návrh existujú. | P5 kladná natívna cesta doručuje 100 % v testovanom krátkom okne; univerzálny editorový JSON má `schema_only`/`not_implemented`. Konfigurácia nových experimentov vyžaduje viacero špeciálnych runnerov. | V1/V7: jeden CLI vstupný kontrakt a výstupné API; editor napojiť iba na podporované režimy, bez predstierania vykonania ľubovoľného flow. |

### Dôležitý záver auditu

Terajší systém je silný **dôkaz existencie vybranej paketovej cesty**. Slabina nie je v absencii ďalšej ikonky alebo pomenovania operátora, ale v previazaní výskumného enginu s pevnou fixture a v nedostatku externej kalibrácie. Univerzalizácia nesmie odstrániť súčasné raw kontrolné body ani zmeniť staré výsledky na falošne „zlyhané“ iba preto, že sa posunul zdrojový kód.

## 3. Zdroje reality a pravidlo ich použitia

Overené verejné východiská k 26. 10. 2026 (zdroje sa pri implementácii pripnú dátumom, verziou, archivovanou kópiou/hashom a rozsahom platnosti):

| Oblasť | Primárny zdroj | Čo z neho možno oprávnene vziať | Čo z neho nemožno vyvodiť |
| --- | --- | --- | --- |
| CAM/DCC | [ETSI EN 302 637-2 V1.4.1](https://www.etsi.org/deliver/etsi_EN/302600_302699/30263702/01.04.01_30/en_30263702v010401v.pdf), [ETSI TS 102 687 V1.2.1](https://www.etsi.org/deliver/etsi_ts/102600_102699/102687/01.02.01_60/ts_102687v010201p.pdf) | Schéma a pravidlá CAM generovania, architektúra DCC a CBR vstup. | Zhoda bez testu časovania, stavov a interoperabilného kódovania. |
| Doprava a rádio | [SUMO TraCI](https://sumo.dlr.de/docs/TraCI/), [SUMO Calibrator](https://sumo.dlr.de/docs/Simulation/Calibrator.html), [ns-3 propagácia](https://www.nsnam.org/docs/models/html/propagation.html) | Reprodukovateľný dopravný vstup/spätná väzba a zdokumentovaný V2V urban model. | Meraný bratislavský dopyt alebo fyzická validácia nášho 802.11p kanála. |
| SNS-3 | [oficiálna dokumentácia modelu](https://www.sns3.org/doc/satellite-design.html) a pripnutý lokálny zdroj | DVB-RCS2/S2 referenčný PHY/MAC, scheduler, sloty, fronty a konfiguráciu dostupnú v presnej verzii. | Proprietárny PHY/MAC a vnútorné routovanie troch operátorov. |
| Orbity | [CelesTrak GP/OMM formáty](https://celestrak.org/NORAD/documentation/gp-data-formats.php), [historické dáta](https://celestrak.org/norad/archives/request.php?FORMAT=json) | Časovo identifikované orbitálne prvky a geometrické kandidáty. Aktuálna dokumentácia upozorňuje, že TLE nezachytí objekty so 6-ciferným katalógovým číslom. | Aktívne priradenie terminálu, beam, prevádzkovú bránu, aktuálnu kapacitu alebo služobnú dostupnosť. |
| Iridium | [Certus 9770](https://www.iridium.com/products/iridium-certus-9770/), [architektúra siete](https://www.iridium.com/network) | Produktové maximá a deklarovaný typ služby/terminálu; presnú konfiguráciu verzovať. | Distribúciu delay, straty, frontu či handoveru konkrétneho zákazníka. |
| Globalstar | [RM200M datasheet](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet1.pdf), [technológia bent-pipe](https://www.globalstar.com/en-us/about/our-technology) | MO/MT veľkosti a architektúru terminál–družica–gateway bez modelovej ISL. | Potvrdenie, že proxy mesto je skutočná dostupná gateway alebo že geometria znamená doručenie. |
| Starlink | [Performance špecifikácia](https://www.starlink.com/public-files/specification_sheet_performance.pdf), [technológia](https://starlink.com/technology) | Parametre konkrétneho hardvéru, existenciu optickej mesh architektúry a jej deklarované maximum. | Aktívnu ISL trasu, plánovač, presnú dostupnosť alebo rozdelenie oneskorenia v Bratislave. |

Existujúca [analýza externých meraní](decisions/empiricka-kalibracia-konkretnych-sluzieb.md) správne oddeľuje Starlink Gen 2 gateway RTT a Iridium agregáty od modelu našej RSU→aplikácia trasy. Nový register parametrov musí pri každej položke niesť: `name`, jednotku, hodnotu/interval alebo distribúciu, zdroj a dátum, terminál a plán, geografiu a čas, modelový hop, stav A–D, miesto použitia v kóde, neistotu, kalibračnú a nezávislú validačnú množinu. Chýbajúca kalibrácia zostáva explicitné `null`, nikdy sa nenahrádza marketingovým maximom.

**Rešeršný podklad k V4–V7 (26. 10. 2026):** [register reálnych parametrov, rozhodnutí, citlivostných odhadov a požiadaviek na meranie](decisions/resers-realne-parametre-a-medzery-2026-10-26.md). Tento podklad dopĺňa zdroje a implementačné brány; fázu V4 sám osebe neuzatvára a nepreklasifikuje existujúce `scenario/sensitivity` profily na validované.

## 4. Pevné poradie práce a prijímacie brány

### V0 — Zmraziť východiskový dôkaz a zmapovať závislosti

**Stav: HOTOVO 26. 10. 2026.** [Dôkaz V0](experiments/v0-history-freeze-2026-10-26.md) obsahuje zdrojový balík, mapu celého reťazca a pevných parametrov, 15/15 historických kontrol a mutačnú skúšku aktuálny checker FAIL / zmrazený checker PASS. Nasleduje V1.

**Prečo prvé:** bez verziovaného stavu zdroja nevieme po refaktoringu nezávisle overiť P5/P6. **Rozsah:** vytvoriť nemenný snapshot zdrojov, patchov, configov, checkerov, závislostí a hashov; oddeliť „historický checker“ od nového vývoja. Spísať presnú mapu `config → runner → generátor → C++ → raw trace → checker → graf`; zaznamenať pevné hodnoty a ich pôvod. Neprepisovať výsledky.

**Brána V0:** staré P5/P6 sa dajú overiť pripnutým historickým nástrojom aj po zmene aktuálneho kódu; nová verzia má vlastné schémy/ID a starý manifest sa nikdy nevydáva za jej výstup. Východiskový preflight a čistá obnova sú zachované ako referencia.

### V1 — Jeden verzovaný scenárový kontrakt a preflight

**Stav: HOTOVO 26. 10. 2026.** [Kontrakt](decisions/scenario-v3-contract.md) a [dôkaz V1](experiments/v1-scenario-contract-2026-10-26.md) pokrývajú štyri odlišné pripnuté konfigurácie, desať cielených negatívnych/pozitívnych testov, štyri prepočítané manifesty a jednoznačný stav `preflight_only_no_packets`. Samotný natívny runner, viac flow/uzlov/RSU a spojitá dostupnosť patria do V2/V3. Nasleduje V2.

**Rozsah:** jeden deklaratívny vstup pre `world` (OSM/SUMO, WGS84), `clock` (UTC, warm-up, okno, krok), `agents` (vozidlá, RSU, terminály), `applications` (CAM/ICB1/GRA1), `ground_radio`, `satellite_reference` alebo `service_profile`, `experiment` (seed, opakovania, vetvy, metriky) a `provenance`. Každý parameter má jednotku, rozsah a explicitný default iba tam, kde je bezpečný. Samostatný preflight má overiť fyzikálne/geometrické a modelové predpoklady pred drahým buildom/behmi. Exportovaný editorový v2 JSON sa môže previesť len cez kontrolovaný adaptér, nie premenovať na vykonaný scenár.

**Brána V1:** jeden príkaz validuje scenár a vypíše presný plán vykonania aj neprípustné položky; tri minimálne odlišné platné konfigurácie a sada chybných vstupov majú deterministický výsledok. Každý spustený výsledok obsahuje normalizovanú konfiguráciu a hash všetkých vstupov.

### V2 — Odviazať natívny VANET/RSU engine od šesťsprávovej fixture

**Stav: HOTOVO 26. 10. 2026.** [Kontrakt vykonateľnej podmnožiny](decisions/scenario-v3-native-v2.md) a [raw dôkaz V2](experiments/v2-native-scenario-2026-10-26.md) pokrývajú 13 natívnych vetiev v štyroch konfiguráciách, tri odlišné počty správ/identity/uzly/UTC, dvojité opakovanie a profil Friis. Nový šesťsprávový prípad je s P5 zhodný v 258 raw riadkoch a 18 PCAP súboroch; tri sémantické mutácie zlyhali. Operátorské profily a všeobecné pripojenie ešte nie sú podporované. Nasleduje V3.

**Rozsah:** premenný počet a časy CAM, zdrojové a cieľové ID, počet účastníkov v deklarovanom rozsahu, poloha/počet RSU a politika prijatia/odoslania. ICB1 v kompatibilnom režime ostáva presne definovaný; iné typy správ iba s vlastným explicitným formátom a checkerom. Odstrániť asercie `6`, `car0`, `rsu0`, `20–22,5 s` z univerzálneho enginu a ponechať ich len v starej fixture. Pridať štruktúrované `offered/created/queued/sent/dropped/received` udalosti. Zjednotiť výstupné cesty vrátane ciest s medzerami.

**Brána V2:** najmenej tri skutočné end-to-end behy s rozdielnym počtom správ, ID, autami/RSU a časom; PCAP/ICB1/GRA1 checkery sledujú presné bajty a menovatele. Starý šesťsprávový prípad je funkčne zhodný v novej verzii a starý originál ostáva nezmenený.

### V3 — Časovo všeobecná LEO topológia, viditeľnosť a pripojenie

**Stav: HOTOVO 26. 10. 2026 v explicitnej natívnej referenčnej podmnožine.**
[Kontrakt V3](decisions/v3-leo-topology-contract.md) a
[geometrický/paketový dôkaz](experiments/v3-leo-topology-2026-10-26.md)
obsahujú osem preflightov a 21 vetiev v troch natívnych zostavách.
Geometria, beam, attach, route a doručenie sú oddelené udalosti; šesťciferné
TLE, nepodporované podmienky a reálne operátorské tvrdenia zostávajú
explicitne mimo podpory. Nasleduje V4.

**Rozsah:** načítať časovo zodpovedajúce OMM/GP; validovať vek prvkov, EOP, rozsah času, katalógové čísla, WGS84, masku a priame/ISL spojenia. Kandidátna geometria, zvolený beam, stav UT attach, dostupná GW/ISL route a doručenie aplikácie musia byť päť **odlišných** udalostí. Nahradiť fixnú dvojicu/beam/proxy predpokladov parametrizovaným referenčným výberom a vysvetliteľným `no_candidate/no_beam/no_attach/no_route/phy_drop` výstupom. Ak SNS-3 nevie vierohodne zostaviť určitý prípad, preflight ho označí `unsupported`; neprevedie ho na falošný outage operátora. Handover jedného UT preniesť do všeobecnej konfigurácie so zachovaním MAC/IP a sondu v oboch smeroch.

**Brána V3:** niekoľko geograficky a časovo odlišných intervalov s úspešnou i neúspešnou kvalifikáciou; nezávislá geometrická kontrola, skutočné paketové trasy, no-ISL/no-beam/no-route/rollback kontroly. OMM→TLE konverzia je výslovne obmedzená alebo nahradená podporovaným vstupom pre 6-ciferné objekty.

### V4 — Vernosť generickej satelitnej referencie

**Stav: HOTOVO 26. 10. 2026 v explicitnej generickej DVB referenčnej podmnožine.**
[Kontrakt parametrov](decisions/v4-generic-dvb-contract.md) a
[natívny raw dôkaz](experiments/v4-generic-dvb-2026-10-26.md) obsahujú
päť párovaných behov, skutočné CAM odvodené ICB1 v ISL fronte, meraný Rx
výkon, `distance/c + serializácia`, tri sémantické/provenienčné mutácie a
read-only V3 regresiu. Fyzikálne a frontové mechanizmy sú A; použitie na
konkrétnu operátorskú sieť ostáva D. Nasleduje V5.

**Rozsah:** zdokumentovať a sprístupniť skutočné SNS-3 parametre: anténnu mapu, výkon, šum, frekvencie, link budget, MODCOD, scheduler, fronty, retransmisie, user/feeder záťaž a ISL kapacitu/latenciu. Namiesto automatického 17 dBi a 1 Gbit/s určiť buď zdrojované referenčné nastavenie, alebo explicitný citlivostný interval. Záťaž frontov generovať **skutočnými aplikačnými paketmi** s identitou; oddeliť control-plane a data-plane oneskorenie. Nesľubovať, že DVB je RF model konkrétneho operátora.

**Brána V4:** zmena jedného fyzikálneho parametra má vysvetliteľný účinok na raw PHY/queue trace a koncovú metriku; jednotkové/link-budget kontroly a nezávislé analytické limity (`distance/c`, serializácia, kapacita) súhlasia. Časť bez verejného alebo kalibračného podkladu ostáva D.

### V5 — Doprava, ITS-G5 a mestské rádio

**Stav: HOTOVO 26. 10. 2026 v explicitnej pozemnej výskumnej podmnožine.**
[Vykonateľný kontrakt a audit ETSI hraníc](decisions/v5-ground-fidelity-contract.md) a
[deväť natívnych raw vetiev s tromi sémantickými mutáciami](experiments/v5-ground-2026-10-26.md)
uzatvárajú oddelenie mapy/dopytu, 100 ms FCD, realizovanú hustotu a teleporty,
pohybovo spúšťané Vanetza CAM, lokálne meraný CBR/DCC výskumný regulátor,
OCB PCAP, LOS/NLOS, syntetickú budovu, shadowing a synchronizované rádiové
prekrývanie. Úplná ETSI DCC zhoda, skutočný dopravný dopyt, budovy a terénna
kalibrácia rádia neboli preukázané; sú výslovne D/mimo tvrdenia. Nasleduje V6.

**Rozsah:** oddeliť mapu od dopravného dopytu; umožniť import meraných tokov alebo otvorene označený syntetický dopyt. Overiť realizovanú hustotu, rýchlosti, teleportačné udalosti a RSU/prekážky. Implementovať pravidlá generovania CAM z pohybu s dostatočným časovým rozlíšením a DCC zo skutočne meranej kanálovej záťaže, ak bude tvrdená ETSI zhoda. Nastaviť rádio podľa doloženého zariadenia/scenára; obrys budov/LOS/NLOS a shadowing validovať oddelene. TraCI spätnú väzbu pridať iba pri otázke o dopravnom účinku.

**Brána V5:** konformitný audit CAM/DCC proti zvolenej verzii ETSI; dopravný vstup a rádio majú vlastné kalibračné/validačné dôkazy alebo štítok D. Viacero dopravných intenzít vyvolá interpretovateľné CBR, kolízie, dropy a lokálnu PDR; rozlíši sa vplyv mobility, hustoty a rádia.

### V6 — Tri odlišné servisné architektúry bez falošnej presnosti

**Rozsah:** Starlink IP, Iridium Certus 100 IP a Globalstar RM200M MO/MT nesmú zdieľať nesprávnu topológiu alebo veľkosť správy. Profil je viazaný na SKU, generáciu, anténu, plán, mobilitu, geografiu a dátum. Geometria sa môže zmeniť na servisný gate iba pri doloženom pravidle pripojenia; inak je len kandidát. V samostatnom adaptéri modelovať skutočne známe limity, queue/retry a pravdepodobnostné alebo intervalové neznáme. Spoločné aplikačné ID a vstupy umožnia párované vyhodnotenie, no výsledok musí prezradiť, či vznikol natívnym SNS-3 alebo servisným replayom.

**Brána V6:** tri profily majú správne odlišnú topológiu a payload, validátor odmietne nereálny typ prenosu, manifest priraďuje každý parameter k zdroju/statusu A–D. Bez nezávislej validačnej množiny žiadny výstup nenaznačí reálne poradie PDR, latencie alebo dostupnosti.

### V7 — Meranie, kalibrácia, neistota a API výsledku

**Rozsah:** jeden per-event formát s časmi a dôvodom straty na každej vrstve; denominator a deadline sú vopred vo vstupe. Oddeliť správnosť implementácie (raw checker), zhodu s normou/modelom, kalibráciu a nezávislú validáciu. Kde máme porovnateľné merania, rozdeliť ich podľa behu/dňa/miesta na kalibračnú a validačnú sadu, porovnávať rovnaké koncové body a zverejniť chybu modelu. Kde chýbajú, robiť citlivosť a interval identifikovateľnosti. Štatistickú jednotku určiť pred behom; nové UTC epochy musia byť skutočne vzdialené v čase, nie 92 s. Rozhodnutie o p95/p99 má vychádzať z počtu nezávislých pozorovaní a výpadkov.

**Brána V7:** každý graf sa dá spätne dohľadať k raw paketu a konfigurácii; negatívne/korupčné kontroly odmietnu falošný úspech. Výstup má pri každom čísle `model_only`, `sensitivity` alebo `externally_validated` s rozsahom platnosti. Údaje bez porovnateľnej validácie sa neprezentujú ako prevádzkové odhady.

### V8 — Použiteľnosť a odovzdanie univerzálnej platformy

**Rozsah:** jeden CLI postup `validate → run → verify → analyze`, katalogizované vzorové konfigurácie a pri každej limity. Editor je voliteľný klient toho istého validátora; zobrazí vykonateľnosť pred štartom a nespustiteľné flows ponechá ako návrh. Vydanie musí obsahovať zdroje, piny, patche, potrebné dátové balíky/licencie, checker a malý offline smoke test; veľké raw výsledky môžu byť osobitný hashovaný archív. Otestovať rozbalenie/kontrolu z presného odovzdávacieho artefaktu, nielen z aktuálneho pracovného priečinka.

**Brána V8:** iný človek vie na podporovanom Ubuntu podľa jedného návodu zmeniť aspoň tri nezávislé parametre, spustiť nový kompatibilný scenár a vysvetliť úspech/zlyhanie z raw stopy. Všetky výstupy pravdivo uvádzajú vernostný stupeň a pôvod parametrov.

## 5. Závislosti, rozhodnutia s vedúcim a pravidlá postupu

`V0 → V1 → V2 → V3 → V4`; V5 môže po V2 bežať nezávisle od V3/V4; V6 potrebuje V1/V3 a evidenciu zdrojov; V7 sa buduje priebežne, finálna brána nasleduje po zvolených modeloch; V8 uzatvára vybraný rozsah. **Každý bod dokončiť celý vrátane nového raw dôkazu, checkera, negatívnej kontroly a aktualizácie dokumentácie pred ďalším bodom.** Ak konkrétny model nemožno vierohodne vytvoriť z dostupných údajov, zapísať presnú hranicu, citlivostný náhradný model a rozhodnutie, čo nebude predmetom tvrdenia; neblokovať ostatné vrstvy.

Po konzultácii s vedúcim vybrať: (1) primárnu dopravnú informáciu a deadline; (2) minimálnu rodinu scenárov, počet uzlov/RSU a meracie okno; (3) či sa hodnotí len VANET s referenčným LEO, alebo aj podmienené služby konkrétnych terminálov; (4) aké merania a zariadenia sú skutočne dostupné. Tieto rozhodnutia určia, ktoré voliteľné moduly sa rozšíria, **nie** to, či základný engine musí pravdivo prijímať konfiguráciu a produkovať auditovateľný výsledok.

### Najbližší vykonávací celok

V0–V8 sú uzavreté v uvedených a explicitne obmedzených rozsahoch. [V7 výsledkový kontrakt](decisions/v7-result-and-measurement-contract.md) a [966 raw naviazaných per-event záznamov](experiments/v7-result-api-2026-10-26.md) oddelili modelovú neistotu od nedostupnej operátorskej kalibrácie/validácie. [V8 jednotný CLI, preflight editora a offline vydanie](experiments/v8-release-2026-10-26.md) prešli novým štvorsprávovým behom s tromi zmenenými parametrami, surovým checkerom a zápornými kontrolami. V5 je oddelená pozemná referenčná vrstva; jej dynamické CAM/rádio ešte nebolo paketovo vložené do satelitnej aplikácie. V4 zostáva generická DVB referencia. Ďalšie scenáre a rozsah BP sa vyberú s vedúcim; prípadná kalibrácia konkrétneho terminálu, cesty alebo lokálneho rádia vyžaduje porovnateľné externé merania.
