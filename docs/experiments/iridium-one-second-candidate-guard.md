# Jednosekundový Iridium kandidátsky plán a konzistencia paketovej cesty

**22. 10. 2026 UTC.** Cieľom bolo odstrániť zbytočne široký 30 s blok v predchádzajúcej [kandidátskej geometrii](iridium-candidate-switch-gate.md) a súčasne zabrániť tomu, aby abstraktný IP proxy prijal paket vyslaný pod ID jedného kandidáta až po prepnutí na iné ID. Výsledok je **geometrická a kauzálna kontrola**, nie model handoveru ani dostupnosti Iridium Certus 100.

## Hypotéza, vstupy a predpoklady

Pri rovnakom 360 s okne UTC, pevnej RSU a hashovaných orbitálnych vstupoch by 1 s vzorkovanie malo lokalizovať zmenu najvyššieho geometrického kandidáta užšie než predchádzajúci 30 s plán. Kontrolou je predošlý plán, ktorý blokoval `[90,120)` s. Pravidlo výberu najvyššej elevácie **nie je známy algoritmus Iridia**. [Iridium opisuje LEO a L-band používateľský spoj](https://www.iridium.com/network), ale identitu práve obsluhujúcej družice, lúč, attach ani gateway z verejného GP katalógu nezískame. [CelesTrak opisuje GP/OMM ako elementy pre SGP4](https://celestrak.org/NORAD/documentation/gp-data-formats.php), nie ako servisnú telemetriu.

Vstupom je archív `data/orbits/20261022T124815Z-retlector/iridium-NEXT.json.gz`, pôvodný 30 s výpočet `data/derived/multi-constellation/bratislava-20261022T124500Z.csv`, jeho metadáta, pripnutá EOP tabuľka, pevný bod **48,1486° N, 17,1077° E, 0 m** a okno **22. 10. 2026 12:45:00–12:51:00 UTC**. Archív obsahoval 80 katalogizovaných objektov; vekovým pravidlom do 48 h do konca okna prešlo 79. Experimentálna maska je **10°**, nie publikovaný prah terminálu. Snímka bola získaná po začiatku modelovaného okna, preto ide o retrospektívnu rekonštrukciu.

## Algoritmus a výstupy

[`refine_iridium_candidate_schedule.py`](../../tools/refine_iridium_candidate_schedule.py) najprv overí SHA-256 pôvodného CSV, manifestu, komprimovaných aj dekomprimovaných OMM, jednotlivých záznamov a lokálnej EOP tabuľky. Každú sekundu propaguje prijaté OMM cez SGP4/WGS72, transformuje TEME→ITRS pomocou Astropy/EOP a počíta topocentrickú WGS84 eleváciu, azimut a šikmú vzdialenosť. Zo sledovaných objektov nad 10° vyberá maximálnu **nezaokrúhlenú** eleváciu; pri zhode rozhoduje menšie číselné katalógové ID. Každá tridsiata sekundová vzorka sa doslova porovná s pôvodným 30 s výpočtom.

Výstupy sú 361 riadkov [sekundových vzoriek](../../data/derived/multi-constellation/iridium-candidate-1s-bratislava-20261022.ns3-schedule.samples.csv), 360 polootvorených intervalov [paketového plánu](../../data/derived/multi-constellation/iridium-candidate-1s-bratislava-20261022.ns3-schedule.csv) a [metadáta pôvodu](../../data/derived/multi-constellation/iridium-candidate-1s-bratislava-20261022.ns3-schedule.metadata.json). Plán povoľuje `[t,t+1)` iba pri rovnakom ID nad maskou na oboch koncových vzorkách. Pri povolení zadá abstraktnému kanálu maximum z dvoch `r/c` časov UT→objekt, zaokrúhlené nahor na ns. **Nevypočítava skutočný okamih prekročenia ani súvislú viditeľnosť vnútri 1 s.** Feeder, ISL, gateway, atmosféra, RF, plánovanie a terminálová registrácia nie sú jeho súčasťou.

V [`certus100-e2e.cc`](../../src/certus100-e2e.cc) je pri kandidátskom pláne identita vybraného objektu uložená k `seq` pri UT odoslaní. Po IP prijatí na serverovom proxy sa znovu pozrie aktívne ID. Ak sa líši, vznikne `geometric_candidate_mismatch_drop` s oboma ID a aplikácia paket **neakceptuje**. Interný `p2p_rx` môže byť zaznamenaný, pretože ide o diagnostický abstraktný serializer; udalosť mismatch je kontrola modelovej cesty na serverovej hranici, **nie skutočný satelitný PHY drop**. Vypnutý interval na príjme používa existujúci `geometric_rx_drop`. Report ostáva 300 B syntetický IP obsah; služobná kapacita 22 kbit/s je iba produktové maximum v modeli, nie garantovaný goodput.

## Výsledok a cielené testy

Najvyšší geometrický kandidát bol v t=113 s **43253**, v t=114 s **43258**. Počet kandidátov nad 10° bol na oboch koncoch **2**. Plán blokuje len `[113,114)` s; predchádzajúce pravidlo blokovalo `[90,120)` s. Toto **nie sú merané dĺžky servisného výpadku**. Skyfield nezávisle prepočítal topocentrické uhly a vzdialenosti pri t=112–115 s zo zhodných OMM/SGP4; rozdiely Astropy mali najviac približne **0,000043°** a **0,0027 km**. Spoločné SGP4 jadro znamená kontrolu transformácie, nie nezávislé overenie reálnej polohy.

| Štart syntetického reportu | Pozorovanie v abstraktnom ns-3 proxy |
| ---: | --- |
| 90,5 s | 1/1 prijatý, ID 43253; pôvodný hrubý plán by interval blokoval. |
| 112,5 s | 1/1 prijatý, ID 43253. |
| 112,95 s | 0/1; vyslaný pod 43253 a zahodený na modelovom príjme v blokovanom intervale. |
| 113,5 s | 0/1; blokovaný pred servisnou frontou. |
| 114,0 s | 1/1 prijatý, ID 43258. |

Zaťažená kontrola poslala **30** syntetických reportov v jednej sekunde od t=112 s s modelovým frontom do 40 paketov. Osem bolo prijatých na serveri, **8** spadlo na modelovom príjme počas blokovaného intervalu a **14** dorazilo na abstraktný serverový socket až pod novým ID 43258, kde ich nová kontrola odmietla. Všetkých 30 zostalo zachovaných v účtovnej rovnici `8 + 8 + 14 = 30`; žiadny mismatch sa nevykázal ako úspešné doručenie. Tento experiment preveruje kauzalitu proxy a frontu, nie nominálnu prevádzku Iridia pri 30 reportoch/s.

[`check_iridium_candidate_1s.py`](../../tools/check_iridium_candidate_1s.py) opätovne vytvorí súbory bajtovo, kontroluje hashovaný pôvod, štyri Skyfield vzorky, päť jednotlivých paketových prípadov a frontový beh. Nezávisle číta celé 300 B aplikačné bajty, ID, FNV-1a hash tela, po etapách kontroluje identitu a účtuje všetky koncové dôvody. Poškodenie vstupného CSV sa zamietne ešte pred tvorbou plánu. Zmenený C++ zdroj prešiel všetkými **šiestimi pôvodnými Certus proxy regresnými prípadmi** aj existujúcim 30 s kandidátskym checkerom. Pri prvom diagnostickom zápise mismatch sa našla čiarka, ktorá vytvárala nadbytočný CSV stĺpec; detail bol opravený a checker teraz odmieta nadbytočné polia. Pri prvom prieskumnom parsovaní OMM bolo tiež potrebné výslovne označiť epochu bez offsetu ako UTC; finálny generátor používa pripnutý UTC parser.

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/refine_iridium_candidate_schedule.py
.venv/bin/python tools/check_iridium_candidate_1s.py
.venv/bin/python tools/check_iridium_candidate_schedule.py
```

Surové CSV a manifest paketových behov vznikajú v ignorovanom `results/iridium_candidate_1s/`. Reprodukčný checker znova kompiluje `src/certus100-e2e.cc` a spustí základných šesť prípadov. Plán má SHA-256 `885d9be5740dae603d3acdcd45c1a0e05c7e30373a193834a42ca38bf04c6381`; vzorky `d572ea6ce0737df08177898a35d9731c03804f417cf737b12925709828250505`.

## Čo zostáva pred operátorským tvrdením

Jednosekundový grid ešte neurčuje sub-sekundový prechod, reálny výber družice, čas attachu, beam, terminálovú anténu, skutočný RF/MAC ani trasu cez crosslink a gateway. Paketový prenos prebehol na **ns-3 P2P proxy**, nie cez družicový uzol SNS-3. Výsledok znižuje jednu známu modelovú chybu a umožňuje korektnejšie citlivostné pokusy s frontami. Nasledujúca technická brána je výber a odovzdanie v spoločnom OCB/CAM→RSU→LEO PHY scenári s potvrdeným satelitným RX/TX a pri skutočne zdokumentovanom terminálovom/feeder profile; bez toho nesmie byť graf označený ako Iridium handover.
