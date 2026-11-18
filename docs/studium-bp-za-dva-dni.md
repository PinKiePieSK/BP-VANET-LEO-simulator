# Bakalárska práca: VANET, cestné správy a satelit za dva dni

**Cieľ:** po dvoch dňoch vedieť vlastnými slovami vysvetliť, čo práca skúma, kadiaľ ide jedna správa, čo simulátor skutočne modeluje a čo z výsledkov možno vyvodiť. Plán ráta približne so 4 hodinami sústredenej práce denne. Ak máš menej času, prejdi najprv časti „Jedna veta“, „Cesta správy“, „CAM a DENM“, „Čo simulátor dokazuje“ a záverečné otázky.

**Na skutočné dvojdňové učenie použi [pracovný zošit s ôsmimi plnými blokmi](studium-bp-pracovny-zosit-2-dni.md).** Tento dokument je krátka orientácia, ktorú môžeš mať otvorenú vedľa zošita. [Podrobný sprievodca implementáciou](studium-bp-ako-funguje-simulator.md) a [katalóg vstupov editora](studium-bp-katalog-vstupov.md) sú referencie k cvičeniam.

## Jedna veta, ktorú si zapamätať

**BP skúma, ako sa lokálna komunikácia vozidiel (VANET) spojí so vzdialenou komunikáciou cez nízko letiaci satelit (LEO), a čo sa v navrhnutom simulovanom modeli stane s doručením a časom správy.** Satelit je časť navrhnutej trasy, nie náhrada za priame rádio medzi blízkymi autami. Toto zodpovedá [oficiálnemu zadaniu](zadanie-bp.md).

## Rozvrh plných blokov v pracovnom zošite

| Kedy | Čas | Téma so samostatným výkladom, kódom, úlohou a odpoveďou |
| --- | ---: | --- |
| Deň 1, blok 1 | 50 min | Jedna správa a všetky uzly na jej trase. |
| Deň 1, blok 2 | 55 min | Tri JSON súbory, platnosť vstupu a čas. |
| Deň 1, blok 3 | 55 min | Súradnice, cesty, SUMO a waypointy. |
| Deň 1, blok 4 | 55 min | CAM: naše rozhodnutie, Vanetza a pozemné rádio ns-3. |
| Deň 2, blok 5 | 60 min | DENM a preposlanie na skutočnej paketovej stope. |
| Deň 2, blok 6 | 55 min | Pozemný kanál, budovy a 3D LOS/NLOS. |
| Deň 2, blok 7 | 60 min | Satelitná dráha, terminálový filter, SNS-3 a hranice modelu. |
| Deň 2, blok 8 | 55 min | Kontrola výsledku a päťminútové vysvetlenie práce. |

Pauzu 5–10 minút si daj medzi blokmi. Čas v tabuľke zahŕňa čítanie, vlastnú úlohu aj kontrolu odpovede. Normy ETSI sú referencie; celé technické špecifikácie sa za dva dni učiť netreba.

## Cesta správy: hlavný príbeh

Predstav si auto, ktoré zistí nebezpečnú udalosť. V aktuálnej vetve projektu vznikne **DENM**, teda správa o udalosti. Blízke autá a cestná jednotka ju môžu počuť cez lokálne cestné rádio. Ak má informácia doraziť do vzdialenej oblasti, zdrojová RSU ju prenesie cez svoj satelitný terminál. Vzdialená RSU potom vytvorí a miestne rozšíri DENM s identitou vlastnej ITS stanice, pričom obsah udalosti a pôvodné `actionId` zostanú sledovateľné. Je to **experimentálny most v tomto projekte**, nie štandardizované satelitné rozhranie. Presný prípad je v [denníku CAM/DENM](experiments/u9-cam-denm-2026-11-02.md).

```text
auto A ── lokálne rádio ── auto B                 V2V
   │
   └──── lokálne rádio ── zdrojová RSU           V2I
                              │
                              LAN
                              │
                   satelitný terminál UT
                              │ user link
                         satelit LEO
                              │ feeder link; prípadne cez ISL a ďalší satelit
                         brána GW ── vzdialená RSU
                                           │ lokálne rádio
                                        ďalšie autá          I2V
```

**Dôležité:** diagram je koncepčný. Konkrétny beh môže použiť jednu družicu alebo explicitnú viacdružicovú topológiu. V najnovšom automatickom výbere model hľadá jednu družicu viditeľnú všetkým aktívnym RSU a modelovej bráne počas celého okna; ak sa nenájde, beh odmietne. Brána a satelitné rádio nie sú overenou trasou komerčného operátora. Pozri [audit parametrov](experiments/audit-parametrov-2026-11-04.md).

### Kto s kým komunikuje

| Skratka | Jednoduchý význam | Typická cesta v práci |
| --- | --- | --- |
| **V2V** | Vozidlo → vozidlo | Priamo lokálnym rádiom; satelit netreba. |
| **V2I** | Vozidlo → infraštruktúra | Auto → RSU lokálnym rádiom. |
| **I2V** | Infraštruktúra → vozidlo | RSU → auto lokálnym rádiom. |
| **V2N** | Vozidlo → vzdialená sieť/služba | Všeobecný pojem; v tejto architektúre môže ísť cez RSU a jej backhaul. |
| **RSU backhaul** | Spojenie RSU so vzdialenou sieťou | RSU → LAN → UT → satelit → GW → vzdialená aplikácia alebo RSU. |

RSU je cestná jednotka pri komunikácii s autami. **UT** je samostatný satelitný terminál. Auto vybavené len cestným rádiom sa samo so satelitom nespojí.

## CAM a DENM: dve správy, ktoré treba poznať

| | CAM | DENM |
| --- | --- | --- |
| Otázka, na ktorú odpovedá | „Kde som a ako sa pohybujem?“ | „Čo sa stalo, kde a ako dlho to platí?“ |
| Spúšťač | Priebežné oznamovanie vlastného stavu, s pravidlami generovania. | Zistená alebo explicitne modelovaná udalosť. |
| Príklad | Poloha, rýchlosť, smer vozidla. | Prekážka, nebezpečie či iná cestná udalosť. |
| V projekte | Skutočne kódovaná ETSI Release 2 správa cez Vanetza a lokálny GN/BTP/OCB. | Skutočne kódovaná správa s modelovou udalosťou, `actionId`, platnosťou a životným cyklom `new → update → cancel`. |

CAM sa v bežnom lokálnom profile vysiela jedným skokom a prijatá CAM sa automaticky neposiela ďalej. DENM môže byť geograficky adresovaná a opakovaná či aktualizovaná podľa udalosti. Presné pravidlá uvádzajú [ETSI CAM TS 103 900 V2.3.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf) a [ETSI DENM TS 103 831 V2.3.1](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.03.01_60/ts_103831v020301p.pdf).

**Pozor na názvy:** v staršom rukopise nájdeš `ICB1`, `GRA1` a `I2V1`. Sú to experimentálne formáty historických scenárov. Aktuálna vetva `APPLICATION_MODE=CAM_DENM` používa CAM a DENM; IPv4/UDP na satelitnom úseku je transportná obálka, nie tretia dopravná správa. [Aktuálny denník](experiments/u9-cam-denm-2026-11-02.md) je pre učenie tejto vetvy presnejší než [starší súvislý rukopis](../thesis/rozpracovana-praca.md).

### Vrstvy bez zbytočného memorovania

```text
Obsah:         CAM alebo DENM                    ČO sa hovorí
Prenos lokálne: BTP + GeoNetworking             KOMU a v akej oblasti
Prístup:       ITS-G5 / IEEE 802.11p OCB         AKO sa to vyšle vzduchom pri ceste
Most RSU:      aplikácia RSU + IP/UDP             AKO sa obsah prenesie vzdialene
Satelit:       UT + user link + SAT + feeder/GW   CEZ KTORÉ uzly ide vzdialená cesta
```

BTP je ľahký transportný protokol cestnej vetvy, GeoNetworking používa geografické adresovanie. Bežná lokálna CAM cez GN/BTP **nie je UDP paket**. IP/UDP sa v tejto práci používa pri satelitnom moste. [ETSI BTP a GeoNetworking](https://www.etsi.org/deliver/etsi_en/302600_302699/3026360501/01.02.01_60/en_3026360501v010201p.pdf), [Vanetza](https://github.com/riebl/vanetza).

**Skúška porozumenia:** Keď RSU dostane CAM a vytvorí nový vzdialený report, znamená to, že pôvodný rádiový rámec auta preletel satelitom? Nie. RSU vytvorila nový obsah/paket podľa prijatej správy. Pri aktuálnom DENM moste sa prenášajú kódované bajty DENM v IP/UDP obálke a vzdialená RSU správu znovu miestne distribuuje.

## Satelitná časť jednoduchými slovami

**LEO** znamená nízku obežnú dráhu. Družice sa vzhľadom na pozemného používateľa pohybujú, preto sa mení ich viditeľnosť, vzdialenosť, elevácia a potenciálne pripojenie. Samotná viditeľnosť na oblohe ešte nedokazuje, že terminál je pripojený, má aktívny lúč alebo doručí paket.

**User link** je rádiový úsek medzi UT a družicou. **Feeder link** je úsek medzi družicou a pozemnou bránou GW. **ISL** je spoj medzi dvoma družicami, ktorý existuje len v topológii, kde ho model alebo služba naozaj má. **Handover** je zmena obsluhujúcej družice či lúča; projekt má osobitné výskumné skúšky prepnutia jedného terminálu, ale to nie je dôkaz správania konkrétneho operátora. [SNS-3](https://github.com/sns3/sns3-satellite) poskytuje satelitné modely a príklady pre ns-3.

Názvy **Starlink, Iridium a Globalstar** v scenároch hovoria o rozdielnych zamýšľaných službách a vstupoch. Aktívne satelitné rádio je generický model **DVB v SNS-3 3.38** s diagnostickým anténnym ziskom, modelovou bránou a ďalšími explicitnými predpokladmi. Simulované doručenie preto nie je meraním dostupnosti, latencie ani spoľahlivosti týchto komerčných služieb. [Aktuálna hranica vernosti](decisions/stav-vernosti.md), [audit 4. 11. 2026](experiments/audit-parametrov-2026-11-04.md).

## Prečo sú v práci štyri nástroje

| Nástroj | Úloha v jednej vete |
| --- | --- |
| [SUMO](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html) | Vypočíta pohyb áut; jeho FCD výstup nesie čas, polohu a rýchlosť. |
| [Vanetza](https://github.com/riebl/vanetza) | Pomáha vytvárať a spracovať európske ITS správy a cestný protokolový zásobník. |
| [ns-3](https://www.nsnam.org/about/what-is-ns-3/) | Simuluje sieťové udalosti, uzly, rádiový prenos a pakety v čase. |
| [SNS-3](https://github.com/sns3/sns3-satellite) | Rozširuje ns-3 o satelitné uzly a model ich komunikácie. |

Aktívny projekt používa **ns-3.38/SNS-3 3.38** v `vendor/ns-3.38-ocb-eval`; staré zmienky o ns-3.48 sú história migrácie. [Záznam obnovy](experiments/obnova-native-2026-10-25.md).

## Čo simulátor dokazuje a čo ešte nie

**Dokazuje v konkrétnych kontrolovaných behoch:** že vzniknú kódované CAM/DENM, lokálne sa odošlú a prijmú, že paketová cesta môže prejsť z RSU cez modelový satelitný úsek k bráne a vzdialenej RSU, a že vybrané blokácie spôsobia očakávanú stratu. Kontrola sleduje bajty, časy a stopy; samotné slovo `PASS` bez počtov doručenia nestačí. Príklady sú v [denníku CAM/DENM](experiments/u9-cam-denm-2026-11-02.md).

**Nedokazuje:** skutočný výkon Starlinku, Iridia či Globalstaru; aktívne lúče a brány operátora; proprietárny modem alebo jeho plánovač; reálnu mieru nehôd; úplnú zhodu celej implementácie s ETSI vrátane bezpečnostného podpisu. [Audit parametrov](experiments/audit-parametrov-2026-11-04.md) vysvetľuje, ktoré fyzikálne hodnoty sú vstupné predpoklady.

Veta vhodná na obhajobu: **„Overujeme uskutočniteľnosť a správanie presne opísaného simulačného modelu; na predikciu konkrétnej služby by bolo treba nezávislé merania terminálu, lúčov a celej trasy.“**

## Ako čítať výsledok

- **Doručenie / PDR:** počet úspešne prijatých *unikátnych* správ delený počtom oprávnených odoslaných správ. Vždy povedz, na ktorom úseku a podľa akého menovateľa.
- **Oneskorenie:** čas prijatia mínus čas vytvorenia či odoslania, presne podľa zvolenej metriky. Stratená správa nemá oneskorenie nula; do štatistiky oneskorenia doručených sa nezaráta.
- **Jitter:** premenlivosť oneskorenia; z niekoľkých paketov sa nedá spoľahlivo odhadnúť chvost rozdelenia.
- **Dostupnosť:** podiel času, keď definovaná služba funguje. Krátke okno s viditeľným satelitom nie je meranie celodennej dostupnosti.
- **Záporná kontrola:** cielene vypnutá linka, zakrytý výhľad alebo malá geografická oblasť. Ak vzdialený príjem zmizne a lokálna vetva zostane, model rozlišuje oba úseky.

**Mini príklad:** Auto pošle 10 správ. RSU prijme 8; brána prijme 6 z tých 8. Lokálny pomer je 8/10 = 80 %. Pomer RSU→brána je 6/8 = 75 %. Celkový pomer auto→brána je 6/10 = 60 %. Tieto tri percentá odpovedajú na tri rôzne otázky.

## Dvanásť otázok na koniec druhého dňa

Najprv odpovedz bez pozerania, ideálne nahlas. Ak nevieš, vráť sa len k príslušnej časti.

1. Čo je VANET a prečo je témou tejto BP?
2. Aký je rozdiel medzi V2V a V2I?
3. Čo robí RSU a čo robí UT?
4. Ktorá správa opisuje priebežný stav auta a ktorá udalosť?
5. Ide bežná lokálna CAM automaticky cez internet alebo satelit?
6. Čo znamenajú BTP, GeoNetworking a OCB v ceste správy?
7. Prečo viditeľný LEO satelit ešte neznamená doručenie?
8. Čo je user link, feeder link, GW a ISL?
9. Načo slúžia SUMO, Vanetza, ns-3 a SNS-3?
10. Čo znamená 6/6 prijatých správ v jednom modeli a čo to neznamená?
11. Ako vypočítaš doručenie, ak RSU prijme 8 z 10 a brána 6 z 8?
12. Aká je najdôležitejšia hranica tvrdení o Starlinku, Iridiu a Globalstare?

### Krátke odpovede

1. Sieť komunikujúcich vozidiel; BP skúma jej spojenie so vzdialenou trasou cez LEO. 2. Auto↔auto oproti auto↔cestná infraštruktúra. 3. RSU komunikuje s cestou; UT je satelitný terminál. 4. CAM; DENM. 5. Nie, lokálne sa šíri cez cestný profil. 6. Ľahký transport; geografické adresovanie; režim cestného Wi-Fi rádia. 7. Chýbať môže aktívny lúč, pripojenie, RF kvalita či vzdialená cesta. 8. UT–SAT; SAT–GW; brána; SAT–SAT. 9. Pohyb; ITS správy; sieťový simulátor; satelitné rozšírenie. 10. Úspech šiestich konkrétnych pokusov v danom scenári, nie prevádzková spoľahlivosť. 11. 80 % lokálne, 75 % RSU→brána, 60 % celkovo. 12. Generický model a scenárové predpoklady sa nesmú vydávať za meranie operátora.

## Čítanie, keď zostane čas

1. [Oficiálne zadanie](zadanie-bp.md): prvý odsek a zoznam požiadaviek.
2. [Aktuálny experiment CAM/DENM](experiments/u9-cam-denm-2026-11-02.md): úvod, normatívna hranica a otvorené obmedzenia.
3. [Audit parametrov](experiments/audit-parametrov-2026-11-04.md): tabuľka opráv a zostávajúce hranice.
4. [ETSI CAM](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf) a [ETSI DENM](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.03.01_60/ts_103831v020301p.pdf): úvod a základná funkcia; celé technické špecifikácie sa za dva dni učiť netreba.

