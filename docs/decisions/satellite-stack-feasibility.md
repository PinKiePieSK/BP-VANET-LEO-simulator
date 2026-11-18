# Spoločný OCB a satelitný PHY/MAC: technická brána

**Audit a aktualizácia 22. 10. 2026.** Brána spoločného behu **ns-3.38 + SNS-3 tag 3.38** už prešla pre zabudovaný **GEO/DVB `SIMPLE` scenár**: dva `OcbWifiMac` aj `SatHelper` vznikli v jednom procese a skúšobný paket prešiel OCB→RSU→LAN→UT→satelit→GW. [Raw dôkaz, kontrolný variant a opakovanie](../experiments/sns3-338-ocb-dvb-packet-gate.md). Nasledujúca tabuľka zachytáva **stav pri pôvodnom audite pred dokončením zostavy**; aktualizovaný záver je na konci. Editorový OCB→RSU→P2P beh ostáva osobitným experimentom. SNS-3 DVB PHY/MAC nemožno označiť za skutočný Starlink, Iridium Certus ani Globalstar RM200M.

## Overený stav a hranica dôkazu

| Vetva | Lokálna evidencia | Čo z nej vyplýva |
| --- | --- | --- |
| `vendor/ns-3.38-ocb-eval` (`392e36833ce3c7e0ecde4188043f76345402d5a7`) | `src/wave/model/ocb-wifi-mac.h`, `helper/wifi-80211p-helper.h`, `helper/wave-mac-helper.h`; [OCB pilot](../experiments/editable-v2-ocb38-pilot.md) a [spoločný P2P pilot](../experiments/editable-v2-ocb-geometry-e2e.md) prešli s reálnymi 802.11 PCAPmi. | Pozemný `OcbWifiMac` je vykonaný. Satelitný úsek tohto behu je idealizovaný P2P proxy. |
| `vendor/ns-3.48` (`d2add90b452d600cfb4859baed8e9ea633519447`) + `contrib/satellite` (`2c0c6d4d7fd1628eda1b923a7e135749513769fa`) | `sat-cbr-example` aj historický LEO `sat-constellation-example` sú lokálne zostavené/spustené. `src/vanet-sns3.cc` používa `SimulationHelper::CreateSatScenario`, `SatTopology` UT/GW user uzly, `SatHelper::GetUserAddress` a skutočný satelitný packet trace. | Existuje jeden ns-3 clock s autami, RSU a SNS-3 user/feeder PHY. Pozemná vetva má `AdhocWifiMac`, nie OCB. Geografický audit navyše našiel neplatný feeder horizont v pôvodnom doručenom behu; [integračný denník](../experiments/sns3-integracia.md) ho oprávnene nepovažuje za fyzikálne platnú trasu. |
| `/tmp/ns3-sns3-338-feasibility` | ns-3.38 `392e368...`, SNS-3 `739a10dbe1db02fd2c4064501e4a48994e0b79f3`, `traffic` `c68daaf...`, `stats` `c613ba7...`; čistá konfigurácia povolila `wave;satellite`. Zostava bola zastavená po 47/914 krokoch; satelitná knižnica ani príklad nie sú hotové. Dátový gitlink SNS-3 `faf7d763438b43139af3d78ff30e4130b2692bd9` nie je inicializovaný. README satelitného tagu stále hovorí o ns-3.37, hoci tag sa volá 3.38. | Konfigurácia **nedokazuje ABI ani runtime kompatibilitu**. Nedá sa tvrdiť, že spoločný OCB + SNS-3 beh už existuje. |

Upstream [SNS-3 README](https://github.com/sns3/sns3-satellite) uvádza zhodné tagy všetkých troch príspevkových modulov, dátový submodul a referenčné príklady; aktuálne vydanie 3.48 je deklarované pre ns-3.48. [ns-3 WAVE dokumentácia](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) opisuje `Wifi80211pHelper`, `QosWaveMacHelper` a `OcbWifiMac`. Lokálne zdrojové stromy, nie samotný názov `WIFI_STANDARD_80211p`, rozhodujú o tom, ktorý MAC sa vykoná.

### Krátka reprodukcia SNS-3 3.48 počas auditu

Už zostavený `sat-constellation-example` sme spustili na dodanom dvojdružicovom LEO scenári s 96 B CBR správou a jednosekundovým intervalom. Prvý pokus skončil `NS_ASSERT` ešte pred simuláciou, pretože `--OutputPath` vyžaduje existujúci adresár. Po `mkdir -p` skončil druhý pokus kódom **0**:

```bash
cd 'vendor/ns-3.48'
mkdir -p /tmp/sns3-348-stack-audit
./ns3 run 'sat-constellation-example --scenarioFolder=constellation-leo-2-satellites --packetSize=96 --interval=1s --OutputPath=/tmp/sns3-348-stack-audit'
```

`PacketTrace.log` má 25 908 riadkov vrátane hlavičky a SHA-256 `d611969be30a46b409938da4855982d2e015bbf53de05010d32ebaef16164e52`. Napočítané `RCV ... PHY`: SAT/FWD 755, SAT/RTN 425, UT/FWD 1 581, GW/RTN 415; globálne aplikačné throughput skaláre sú 14,8913 kb/s FWD a 23,2213 kb/s RTN. Toto je **funkčný lokálny smoke test SNS-3**, nie validácia pokrytia, handoveru ani operátora. Súbor `standard/standard.txt` tohto scenára obsahuje `DVB`; dráhy sú historické testovacie TLE, nie aktuálne Starlink/Iridium/Globalstar.

## Konkrétne rozhranie pre integráciu

1. Štyri pozemné uzly z FCD sa vytvoria rovnako ako v `src/editable-v2-ocb-geometry-e2e.cc`: `Wifi80211pHelper` + `QosWaveMacHelper` + `OcbWifiMac`. Na RSU sa kontroluje **dekódovaný CAM z prijatých bajtov**, nie plánovaný odosielací fixture. `ICB1` 96 B vznikne až z tohto príjmu.
2. `SimulationHelper::LoadScenario` a `CreateSatScenario` vytvoria UT, GW, orbiter a pripojených používateľov. `Singleton<SatTopology>::Get()->GetUtUserNodes()` a `GetGwUserNodes()` sú aplikačné okraje; `SatHelper::GetUserAddress(gwUser)` je cieľ pre UDP. P2P môže reprezentovať iba explicitnú lokálnu RSU→UT LAN. Medzi UT a GW sa nesmie ponechať paralelná P2P skratka.
3. Satelitná vetva musí zaznamenať identitu a bajty aplikačného reportu pri RSU, UT user a GW user, plus SNS-3 `PacketTraceEnabled` udalosti na UT PHY, orbiteri a GW PHY. `SatUtPhy`, `SatOrbiterUserPhy`, `SatOrbiterFeederPhy` a `SatGwPhy` sú modelové vrstvy; SNS-3 [dokumentuje](https://www.sns3.org/doc/satellite-design.html) aj satelitné štatistiky MAC/PHY a linkové chyby. Interný packet UID sám nestačí na dôkaz obsahu po enkapsulácii; kontrola musí párovať event ID, payload a časy.
4. Pre prvý fyzikálne prijateľný test sa zvolí **jediný viditeľný UT–orbiter–GW priechod** s explicitnou WGS84 polohou UT a skutočnou polohou testovacej GW z dátového scenára. V každom TX/RX čase sa samostatne skontroluje elevácia na oboch koncoch. Nemea city proxy a archivovaný objekt Globalstar 37741 sa nesmú predstierať ako anténa ani ako satelitný DVB scenár. ISL a handover patria až do samostatných následných kontrol.

Toto rozhranie nevytvára terminál konkrétneho operátora. SNS-3 `SatConf` nastavuje napríklad šírku a frekvenciu forward/return user/feeder kanálov, `SatHelper::PacketTraceEnabled` aktivuje sledovanie a `SatTrafficHelper` ponúka UDP záťaž. Číselné frekvencie, šírky, zisk antény, chybové krivky, logon a plánovanie však zostanú **vlastnosťami zvoleného referenčného scenára**. Súbor scenára a jeho dátový commit musia byť súčasťou manifestu. Sieťová regenerácia/IPv4 v orbiteri je voľba SNS-3 referencie, nie dôkaz o architektúre Globalstar; pri transparentnej vetve sa musí nastaviť zodpovedajúci režim.

## Presný ďalší experiment a rozhodovacie kritériá

### Prečo teraz nevytvárať skratku cez iný build

Čítací audit lokálneho `contrib/satellite/CMakeLists.txt` pre tag 3.38 našiel jeden veľký `build_lib(satellite)` so 236 prekladovými jednotkami vrátane 35 v adresári `stats`, bez voľby vypnúť iba satelitné štatistiky. `SimulationHelper` priamo používa `SatStatsHelperContainer`; jeho vynechanie by bolo vlastnou zmenou upstream modulu, nie prepínačom zostavenia. Súčasná konfigurácia už vypína testy a zužuje príklady; `sat-cbr-example` je cielený build, ale sám **nelinkuje `wave`**. Po jeho prípadnom úspechu musí nasledovať osobitný malý scratch cieľ, ktorý v jednom binári vytvorí `OcbWifiMac` aj `SatHelper`, a až potom plný paketový test.

Zmena debug profilu na `-g0 -O0` by znížila ladené symboly, no preložila by doterajšie objekty nanovo; release `-O3` môže zvýšiť pamäťový nárok optimalizátora a tiež mení profil. Recyklácia hotových knižníc z `vendor/ns-3.38-ocb-eval` nie je čistá CMake skratka: v tomto vendor strome chýbajú viaceré knižnice satelitnej konfigurácie a zmiešanie dvoch kópií jadra by mohlo vytvoriť duplicitný stav `TypeId`/singletonov. Prenesenie historického OCB do hotového ns-3.48 SNS-3 takisto nie je iba zmena názvu API: v ns-3.48 už nie je virtuálne `WifiMac::Enqueue(...)` v podobe, ktorú `OcbWifiMac` 3.38 prepisuje, ani jeho `ConfigureStandard`/`WaveFrameExchangeManager`. Tieto dôvody vychádzajú z porovnania lokálnych CMake súborov a hlavičiek; žiadna alternatíva zatiaľ neprešla zostavením. Najmenej rizikové pokračovanie je ponechať izolované hotové objekty 3.38, dokončiť ich iba pri skutočne pokojnej VM a overiť scratch binár aj geografiu. Dovtedy ns-3.38 OCB a ns-3.48 SNS-3 DVB zostávajú oddelené referencie.

V izolovanom checkoute bol inicializovaný **iba pripnutý** dátový gitlink cez sparse checkout a začala cielená zostava najmenšieho satelitného príkladu. Pri pokračovaní použiť najviac jednu úlohu:

```bash
cd /tmp/ns3-sns3-338-feasibility
git -C contrib/satellite/data rev-parse HEAD   # očakávané faf7d763438b43139af3d78ff30e4130b2692bd9
./ns3 build sat-cbr-example -j 1
./ns3 run sat-cbr-example
```

Táto zostava bola **prerušená** pri 100/608 zostávajúcich krokoch po nameranom swap-in a diskovom čakaní; ďalší pokojný pokus dokončil približne 52 objektov bez swap-out, ale ponechal približne 456 krokov. Následný jednovláknový 180 s pokus nedokončil ani jeden veľký `satellite-stats-helper-container.cc` objekt (približne 830 MiB RSS), hoci neskončil kompilátorovou chybou. `sat-cbr-example` ešte neexistuje. Úplný priebeh a dôvody zastavenia sú v [denníku kompatibilitnej brány](../experiments/sns3-338-ocb-compatibility-gate.md). 3.38 spoločná vetva zostáva nepreverená a editor sa na ňu nepresúva. Ak sa zostava alebo upstream príklad nepodarí reprodukovať bez ad hoc patchov, vetvu označiť za nepoužiteľnú. Pri úspechu nasleduje jediný malý scratch scenár s jedným OCB CAM→RSU a jedným 96 B reportom cez skutočnú SNS-3 UT→satelit→GW cestu. Kladná kontrola musí mať rovnaký `ICB1` payload v RSU/UT/GW, skutočné UT/SAT/GW PHY udalosti a kladnú eleváciu oboch RF úsekov v čase paketu. Záporná kontrola musí blokovať iba satelitné doručenie pri zachovanom OCB prijatí. Uložiť presné commity, scenár, seed, raw trace, PCAP, časy a zlyhania. Až tento výsledok by oprávňoval zmeniť označenie z „P2P proxy“ na „SNS-3 referenčný satelitný PHY/MAC“.

**Alternatíva po neúspechu brány:** ponechať overené OCB 3.38 a SNS-3 3.48 ako **dve odlišné referencie**, alebo samostatne portovať/testovať OCB na 3.48. Nemožno zmiešať výsledky ich časov do jedného end-to-end merania. Žiadna z týchto možností bez meraní a verejných rozhraní terminálu neoprávňuje tvrdiť presné PHY/MAC komerčného Starlinku, Iridia či Globalstaru.

## Aktualizované rozhodnutie po runtime teste

Vyššie uvedená alternatíva bola plánom **pred** dokončením brány. `sat-cbr-example`, spoločný ABI test a pozitívny aj blokovaný OCB→RSU→LAN→SNS-3 UT/SAT/GW paketový test teraz prešli v ns-3.38. Doplnil sa iba chýbajúci priamy `<cstdint>` include v izolovanom historickom strome; [patch](../../patches/ns3-338-std-cstdint.patch) a [reprodukčný runner](../../tools/run_sns3_338_ocb_dvb_packet_gate.sh) ho zaznamenávajú. Surový PacketTrace pri skúšobnom pakete ID 151 ukazuje UT PHY TX, satelit PHY RX/TX a GW PHY RX aj sieťový RX. Aplikačné bajty sa kontrolujú na RSU, UT a GW, OCB a LAN PCAP sú v kontrolnom bloku identické. [Úplný experiment](../experiments/sns3-338-ocb-dvb-packet-gate.md).

**Rozhodnutie pre ďalší vývoj:** ns-3.38 + SNS-3 3.38 je použiteľný spoločný technický základ pre **generický referenčný DVB satelitný úsek**. Aktuálny `SIMPLE` test je statický GEO model s experimentálnym 16 B payloadom a pevnými rádiovými uzlami; nie je to výsledok bakalárskej LEO hypotézy. Ďalej preniesť z editovateľného SUMO/Vanetza pilota **skutočne dekódovaný CAM** a z neho RSU vytvorený 96 B ICB1 do tejto satelitnej vetvy, zvoliť zosúladený LEO scenár a nezávisle skontrolovať UT i GW eleváciu, typ linku, payload a zápornú kontrolu. Až po tejto integrácii možno merať spoločné end-to-end oneskorenie a porovnávať scenáre. Označenie Starlink/Iridium/Globalstar vyžaduje osobitný terminálový a servisný model, ktorý tento test neobsahuje.
