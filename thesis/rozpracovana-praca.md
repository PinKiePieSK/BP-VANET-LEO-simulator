# VANET s integrovanou komunikáciou cez nízkoorbitálne satelitné siete

**Pracovný súvislý rukopis, 26. 10. 2026.** Cieľ a rozsah vychádzajú z [oficiálneho zadania](../docs/zadanie-bp.md). Priebežné experimentálne poznámky do fázy P5 sú bez zmeny zachované v [historickom rukopise](historia-pokusov-do-p5-20261026.md). Tento text oddeľuje výsledok reprodukovateľného **výskumného modelu** od výkonu komerčných služieb, ktorý zatiaľ nebol nezávisle validovaný.

## Abstrakt

Práca navrhuje a overuje spojenie lokálnej komunikácie vozidlo–vozidlo a vozidlo–infraštruktúra s diaľkovým prenosom krátkej informácie z cestnej jednotky RSU. Dopravný priebeh vzniká v SUMO; CAM je kódovaná cez Vanetza, prenášaná pomocou GeoNetworking/BTP po 802.11p OCB v ns-3.38 a prijatá RSU. RSU z prijatej CAM vytvorí samostatný 96 B report ICB1. Jeden referenčný model prenáša report cez SNS-3 3.38, dve LEO dráhy, generické DVB používateľské a feeder spojenie a modelovú medzisatelitnú hranu; spätný GRA1/I2V1 potvrdzuje identitu presného reportu. Tri ďalšie servisné obaly rešpektujú odlišné hranice Iridium Certus 100, Globalstar RM200M a Starlink Performance, avšak ich neznáme stratové a časové parametre sú citlivostné predpoklady. Konečná párovaná matica má šesť seedov, dva blízke UTC začiatky a štyri skupiny hustoty a lokálnej záťaže. Raw stopy, manifesty a nezávislé checkery dokazujú uskutočnenú paketovú cestu, účinok negatívnych vetiev a pôvod grafov. Výsledky potvrdzujú funkčnosť a reprodukovateľnosť modelu v skúmanom okne; bez porovnateľných meraní terminálov a služieb neodhadujú prevádzkovú dostupnosť ani poradie operátorov.

**Kľúčové slová:** VANET, ITS-G5, CAM, SUMO, ns-3, SNS-3, LEO, RSU, reprodukovateľný experiment.

## 1. Problém, cieľ a hranica tvrdenia

[V zadání](../docs/zadanie-bp.md) sa žiada analyzovať komunikáciu inteligentnej dopravy a LEO, navrhnúť integrovanú infraštruktúru, implementovať scenáre a vyhodnotiť experimenty. Lokálny prenos V2V/V2I a spojenie RSU so vzdialenou aplikáciou sú odlišné úlohy. V tejto práci je primárnou zostavou **pevná RSU so samostatným satelitným terminálom**. Priamy terminál v aute nie je skrytým predpokladom tejto zostavy. Samostatný referenčný experiment testuje prepnutie **jedného** UT medzi dvoma LEO objektmi, ale nie komerčný handover.

Výskumné otázky sú:

1. Dá sa konkrétna informácia odvodená z CAM dohľadať od vozidla cez lokálne rádio, RSU, satelitný model a vzdialenú aplikáciu, vrátane spätnej odpovede na presný report?
2. Ktoré kontrolované zásahy spôsobia stratu na lokálnom rádiu, LAN, používateľskom DVB, modelovej ISL, feeder spoji, fronte alebo aplikačnom deadline a zostane pritom lokálna V2V/V2I vetva aktívna?
3. Aký výsledok dá v tej istej aplikačnej úlohe hypotetická pozemná kontrola, generický DVB a tri **odlišné servisné obaly**, keď je každý profil označený podľa vlastnej vernosti a neznámych parametrov?
4. Čo možno overiť pri zmene jedného UT z SAT0 na SAT1 a čo sa z takého modelu **nedá** preniesť na operátorský handover?

Práca neposudzuje zníženie nehôd, plynulosť alebo rozhodovanie vodiča. Simulácia nemá spätnú väzbu z prijatej správy do SUMO cez TraCI. Deadline 60 s je vopred zvolený výskumný prah pre vzdialený dopravný stav, nie bezpečnostná lehota DENM ani záruka služby. C-V2X/PC5, plná ETSI CAM/DCC konformita a aktívne komerčné RF/MAC protokoly sú mimo vykonaného modelu. [Metrický kontrakt](../docs/experiments/p0-experiment-contract-2026-10-25.md) tieto hranice zafixoval pred finálnou kampaňou.

## 2. Návrh infraštruktúry a nástroje

```text
primárne auto ── CAM / GN-BTP / 802.11p OCB ── ostatné autá
        │
        └── CAM ── RSU ── nový ICB1 ── LAN ── terminál UT
                                               │
                   generický DVB: UT → SAT0 → modelová ISL → SAT1 → proxy GW → aplikácia
                   servisné obaly: UT → geometrický kandidát → model služby → aplikácia
                                               │
        auto ← I2V1 / OCB ← RSU ← GRA1 / návratová cesta
```

SUMO vytvára FCD pohyb. Lokálna sieť používa ns-3.38 `OcbWifiMac`, 10 MHz kanál a kontrolovaný mestský citlivostný rádiový model; Vanetza vytvára skutočne kódované UPER CAM a GN/BTP obsah. RSU vytvorí ICB1 **až po dekódovaní prijatej CAM**. ICB1 obsahuje `event_id`, čas prijatia, pôvodných 41 B CAM a ich SHA-256; satelitná vetva neposiela pôvodný OCB rámec. Vzdialená aplikácia prijme iba report so zhodným obsahom a ID. GRA1 nesie ID a hash celého ICB1, lokálny I2V1 doručí odpoveď autu. Bajtovú a časovú cestu v oboch smeroch dokladá [P1 raw experiment](../docs/experiments/p1-two-leo-roundtrip-2026-10-25.md).

SNS-3 3.38 je zvolený ako **referenčný generický DVB-S2/RCS2 paketový model**. Použitá 17 dBi konštantná diagnostická anténa, 1 Gbit/s bodová ISL a proxy GW sú experimentálne vstupy; nemodelujú anténu, optický spoj ani bránu konkrétneho operátora. Výber SNS-3 spomedzi kandidátov odporučených vedúcim dokumentuje [analýza modelov](../docs/vyber-satelitneho-modelu.md). Jediný aktívny checkout je `vendor/ns-3.38-ocb-eval`; zdrojové piny a patche kontroluje [migračný preflight](../scripts/check_migration.py).

Geometria má spoločný čas UTC a polohu WGS84. Archivované GP/OMM vstupy prechádzajú vekovým filtrom, SGP4 propagáciou a transformáciou TEME→ITRS; pri každom RSU reporte sa skúša experimentálna 10° elevácia. [CelesTrak GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php) poskytuje orbitálne prvky, **nie** aktívne priradenie lúča alebo služby. OMM snímka bola získaná po simulovanom deji, takže výpočet je retrospektívny. Na Globalstar sa vyžaduje tá istá družica pri UT a hypotetickej mestskej proxy Nemea; na priamu Starlink kontrolu tá istá družica pri UT a hypotetickej proxy Viedeň. Iridium používa iba UT geometrického kandidáta, lebo aktívna mesh/GW trasa nie je známa. Výpočtový a zdrojový postup je v [P4](../docs/experiments/p4-service-profiles-2026-10-26.md) a [P5](../docs/experiments/p5-final-matrix-2026-10-26.md).

## 3. Päť profilov a vernosť modelu

Všetky profily riešia **rovnakú aplikačnú informáciu**, ale ich transport a význam parametrov sa nesmú zamieňať.

| Profil | Implementované v tomto projekte | Vstupný zdroj a obmedzenie |
| --- | --- | --- |
| Pozemná WAN referencia | Hypotetický IP/UDP obal, 10 Mbit/s a 10 ms na smer. | Kontrola s rovnakým ICB1; nejde o zmeraný internet. |
| SNS-3 DVB referencia | Natívny paket UT→SAT0→modelová ISL→SAT1→GW a návrat; S0 blokácia UT, S2 bez ISL. | Výskumná anténa, modelová ISL a proxy GW, nie operátorské RF. |
| Iridium SkyLink 5100 / Certus 9770 / Certus 100 IP | Samostatné IP UL/DL fronty a časovanie, publikované maximá 22 kbit/s UL a 88 kbit/s DL, vzorkovaný UT geometrický kandidát. | [Iridium 9770](https://www.iridium.com/products/iridium-certus-9770) uvádza **maximá**, nie garantovaný goodput. Delay, straty, mesh/GW a attach sú citlivostné predpoklady. |
| Globalstar RM200M | Natívna MO 96 B ICB1 a MT 46 B GRA1 bez transparentného IP socketu a bez ISL; spoločný UT/GW geometrický kandidát. | [Oficiálny list RM200M](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet1.pdf) uvádza MO 9–144 B, MT 9–128 B. Proxy Nemea nie je overená anténa; retry/latencia sú scenár. |
| Starlink Performance Gen3 / Local Priority 50GB | IP/UDP servisný obal a priama dvojkoncová kandidátna geometria pri pevnej RSU. | [Performance kit](https://starlink.com/public-files/specification_sheet_performance.pdf) uvádza 140° FoV. Aktívny lúč, gateway, optická trasa, scheduler, plán a strata nie sú merané. |

Použité základné a nízke/vysoké citlivostné hodnoty sú úplne uvedené v [zdrojovanom registri P4](../config/p4_service_profiles.json); stav každého údaja a chýbajúce merania v [evidenčnom registri P0](../config/bp_service_evidence_v1.json). Hodnoty 150–750 ms Iridium, 0,5–5 s Globalstar a 15–100 ms Starlink na smer, ako aj stratové pravdepodobnosti, sú **zvolené hranice scenára**, nie empirické rozdelenia služieb. Cudzia mobilná Starlink RTT stopa s iným terminálom a koncovými bodmi sa používa iba ako externý kontext, nikdy ako kalibrácia tejto matice. Žiadny profil nemá porovnateľnú nezávislú raw validáciu; formálny P0 kontrakt preto blokuje tvrdenie `operator_prediction`.

## 4. Metodika a meranie

### 4.1 Jednotka, identita a denominator

Primárna populácia je počet **unikátnych** ICB1, ktoré RSU vytvorila z dekódovaných CAM. Vzdialený úspech vyžaduje rovnaké `event_id` a presný obsah reportu vo vzdialenej aplikácii do 60 s od `RSU_REPORT_CREATED`. Neúspech je správa bez takého prijatia, vrátane neskorého aplikačného prijatia. Delay sa počíta **iba z úspešných** ako `REMOTE_APP_RX − RSU_REPORT_CREATED`; chýbajúci paket nemá delay 0. GRA1 v RSU a I2V1 v aute sú osobitné návratové metriky. Lokálny menovateľ tvorí každý ponúknutý pár `(primárny CAM, oprávnený príjemca)`, nie počet satelitných vyslaní. Interné `PacketTrace` opakovania nie sú nové aplikačné správy. Metodiku pripína [P0 kontrakt](../config/bp_experiment_contract_v1.json).

Odlišujeme: (a) geometrického kandidáta, (b) pripojenie/attach terminálu a (c) aplikačné doručenie. Ak model nemá callback pripojenia alebo dôvod dropu, uvádzame `not_observed` či `unknown`, nie odhad. IP/UDP checksumy, celé OCB a LAN PCAP, `PacketTrace`, surový ICB1/GRA1/I2V1 obsah a časové poradie čítajú checkery nezávisle od počítadla runnera. Hash v manifeste sám nestačí: korupčné skúšky menili obsah **aj zodpovedajúci manifestový hash** a sémantické checkery ich odmietli.

### 4.2 Postup P0–P4

P0 zmrazil význam informácie, deadline, denominator a zdrojový register. P1 overil jednu úplnú obojsmernú cestu šiestich reportov; záporné `blocked` a `no_isl` mali 0/6 vzdialených doručení a `no_return_route` 6/6 dopredu, 0/6 návratov. P2 spojil OSM cestu Bratislavy, syntetickú riedku/hustú dopravu, mestské rádiové citlivosti a kontrolované straty na LAN, DVB user/feeder, modelovej ISL fronte a 60 s deadline. V P2 základ 6/6 kontrastuje napríklad s frontovým zásahom 5/6 a neskorým aplikačným prijatím 5/6 **včas**; celý modelový P2 pilot má 8/8 úspešných kontrolných variantov. Výsledky neznamenajú kalibrovanú bratislavskú prevádzku ani plnú ETSI CAM/DCC zhodu. [Mestský P2](../docs/experiments/p2-urban-osm-paired-2026-10-25.md), [hopové straty](../docs/experiments/p2-controlled-hop-loss-2026-10-25.md), [dokončenie P2](../docs/experiments/p2-completion-2026-10-26.md).

P3 doplnil jediné rádio/UT s tou istou MAC/IP pred SAT0→SAT1 preladením. Potvrdenie vyžaduje obojsmernú sondu cez nový SAT1 user a modelovú ISL. Kladný experiment má dve správy pred, dve počas `pending` zahodené a dve po potvrdení cez SAT1; štyri záporné/kontrolné varianty prešli. Žiadosť→retune 300 ms je syntetický parameter. Jedna epocha a jeden seed neoprávňujú distribúciu handover latency ani operátorský záver. [Kontrakt a raw P3](../docs/experiments/p3-single-ut-handover-2026-10-26.md).

P4 oddelene overil IP fronty Iridium, natívne veľkostné obmedzenia a spoločnú dvojkoncovú geometriu Globalstaru a priamu kandidátnu geometriu Starlinku. Všetkých 13 servisných prípadov malo pozitívne, blokované a citlivostné kontroly nad rovnakými šiestimi ICB1. Servisná vrstva sa prehráva **až po natívnom prijatí RSU**, preto jej výsledok nepredstiera proprietárny satelitný PHY/MAC. [Raw a parametre P4](../docs/experiments/p4-service-profiles-2026-10-26.md).

### 4.3 Preregistrovaná konečná matica P5

Najprv prebehol krátky pilot variability s dvoma seedmi a dvoma UTC počiatkami. Vysokostratový Iridium variant kolísal medzi 4/6 a 6/6 na párovanú jednotku; vopred napísané pravidlo preto zvolilo **šesť nových seedov** 314171–314176. [Zmrazený protokol](../config/p5_final_matrix.json) vznikol pred finálnym behom. Ku každému seedu patria dva overené UTC počiatky 22. 10. 2026 12:45:00 a 12:46:32, iba 92 s od seba. Dvanásť párovaných jednotiek sa kríži so štyrmi skupinami riedka/hustá doprava × nízka/vysoká **lokálna CAM záťaž**. Každá skupina má tri natívne vetvy: S0 blokované satelitné odoslanie, S1 generický DVB s modelovou ISL a S2 bez ISL. Z rovnakého S0 RSU výstupu sa následne prehráva pozemná kontrola a 3 × 4 servisné varianty (základ, blokácia, nízka/vysoká citlivosť). S0, S1 a S2 majú identické ponúknuté zdrojové CAM; neskoršia spätná odpoveď S1 môže kauzálne zmeniť čas ďalšieho OCB príjmu o jednotky mikrosekúnd. Servisné obaly majú medzi sebou presne rovnaké ICB1 bajty/časy. [Diagnostika párovania](../docs/experiments/p5-final-matrix-2026-10-26.md).

Pre každú skupinu sa vypočíta podiel doručených z 72 vytvorených reportov. 95 % interval je percentilový bootstrap s 10 000 opakovaniami po **šiestich seed klastroch**; dve epochy a párované varianty daného seedu zostávajú spolu. CSV uvádza aj minimum/maximum cez 12 jednotiek. Tento interval opisuje variabilitu **nastaveného modelu pri šiestich seedoch**, nie neistotu skutočnej služby. Z jednotlivého šesťsprávového behu sa nevypočítava p99. Kód grafov, výsledky a limit metódy sú v [P5 denníku](../docs/experiments/p5-final-matrix-2026-10-26.md).

## 5. Výsledky

### 5.1 Referenčná paketová cesta a lokálne správy

V 144 natívnych behoch vzniklo 864 riadkov primárnych udalostí. V každej zo štyroch skupín a každej vetvy vytvorila RSU 72/72 ICB1. S1 doručila **72/72** reportov do GW a **72/72** odpovedí do auta; S0 a S2 **0/72** do GW. Lokálne páry primárny CAM–auto zostali v každej vetve **216/216** pri riedkej a **504/504** pri hustej doprave. Takýto úplný úspech pre všetky testované lokálne skupiny znamená, že zvolená záťaž v tomto modeli nevytvorila lokálnu stratu; **nie** že sa preukázala kapacitná rezerva alebo mestská spoľahlivosť. S1 priemerné RSU→GW oneskorenie v riedkej/nízkej skupine bolo 122,2 ms. Ostatné skupiny, po jednotkách aj bootstrap intervaly sú v [natívnom grafe](../results/p5_analysis_final_20261026/p5_native_reference.png) a `summary.csv`/`local.csv`.

### 5.2 Servisná citlivosť

Servisný checker overil 12 jednotiek × 4 skupiny × 13 variantov × 6 správ, teda **3 744** per-event riadkov. Geometrický kandidát nad skúšobnou 10° maskou existoval pri všetkých 288/288 reportoch každého profilu **v tomto krátkom okne**; nejde o priebežnú dostupnosť ani aktívny beam. Hypotetická pozemná kontrola a základné varianty každého obalu dali v každej skupine 72/72 včasných doručení; blokované varianty 0/72. Rozdiely vysokého citlivostného variantu sú:

| Skupina | Iridium vysoký zásah | Globalstar vysoký zásah | Starlink vysoký zásah |
| --- | ---: | ---: | ---: |
| Riedka, nízka záťaž | 64/72; CI 0,819–0,944 | 72/72; CI 1–1 | 66/72; CI 0,875–0,958 |
| Riedka, vysoká záťaž | 65/72; CI 0,847–0,958 | 72/72; CI 1–1 | 58/72; CI 0,736–0,861 |
| Hustá, nízka záťaž | 63/72; CI 0,847–0,903 | 72/72; CI 1–1 | 65/72; CI 0,847–0,972 |
| Hustá, vysoká záťaž | 67/72; CI 0,847–0,986 | 72/72; CI 1–1 | 65/72; CI 0,833–0,972 |

*CI je 95 % bootstrap nakonfigurovaného modelu, nie interval komerčnej PDR.* Podiel Globalstaru pri vysokom zásahu zostal 1, no jeho predpokladaná servisná latencia sa v riedkej/nízkej skupine zmenila zo základných 1 017,1 ms na 5 433,8 ms. V tej istej skupine má hypotetická pozemná kontrola 10,1 ms, základ Iridium 301,1 ms a Starlink 33,3 ms. Tieto absolútne čísla pochádzajú z **rôzne zvolených časových obalov**, preto sa nesmú vyhlásiť za poradie skutočných operátorov. [Servisný graf](../results/p5_analysis_final_20261026/p5_service_sensitivity.png), [úplná tabuľka](../results/p5_analysis_final_20261026/summary.csv), [P5 audit](../docs/experiments/p5-final-matrix-2026-10-26.md).

## 6. Diskusia, validita a ďalšia práca

**Vnútorná validita.** Runnery odmietajú prepísať predchádzajúci výsledok. Manifest pinuje kód, protokol, vstupné FCD/waypointy, orbitálne záznamy a raw stopy. Nezávislé checkery čítajú celé ICB1/GRA1/I2V1 bajty, IP/UDP kontrolné súčty, PCAP, SNS-3 `PacketTrace` a časové poradie. Blokované, bez-ISL a bez-návratové varianty bránia úspechu cez neplánovanú trasu. Tri P5 korupčné skúšky po obnovení manifestového hasha odmietli zmenený natívny report, vzdialený servisný report i graf. Analytický checker oba PNG/PDF grafy znovu vytvoril bajtovo zhodne. [Reprodukčný postup](../docs/reprodukcia.md) vedie od grafu ku konkrétnemu raw reportu.

**Externá validita.** OSM poskytuje cestnú geometriu, ale doprava, polohy RSU a lokálne rádiové podmienky sú výskumné vstupy bez terénnej kalibrácie. SUMO je jednosmerný zdroj pohybu; spätné dopravné účinky sa nehodnotia. Vzorkovanie CAM po 500 ms a externý `T_GenCam_Dcc` nie sú úplná ETSI implementácia; budúce tvrdenie o norme vyžaduje kontrolu najmenej po 100 ms, stavový DCC a konformitný audit podľa [P2 denníka](../docs/experiments/p2-completion-2026-10-26.md). Diagnostická anténa, generický DVB a modelová ISL nie sú fyzikou Starlinku/Iridia/Globalstaru. Orbitálny archív bol získaný retrospektívne a dve finálne epochy pokrývajú iba 92 s rozdiel, nie denný alebo sezónny prechod. Proxy Nemea/Viedeň nie sú overené prevádzkové antény. Chýbajú aktívny beam, attach, scheduler, route, servisná záťaž, skutočné gateway a matching raw terminálové merania. Profilové straty a delay preto tvoria **citlivosť predpokladov**. Bez ich nezávislej kalibrácie/validácie nie je obhájiteľné poradie operátorov, PDR, p99 ani prevádzková dostupnosť.

K ďalšiemu vedeckému rozšíreniu patria porovnateľné raw merania konkrétnej zostavy a plánu na rovnakom mieste/čase, oddelená kalibračná a validačná sada, viac UTC epoch mimo úzkeho okna, kalibrovaný rádiový/dopravný vstup, reálny gateway/beam podklad a spätná väzba aplikácie do dopravy. Tieto body sú **otvorené obmedzenia**, nie implicitné súčasti hotového modelu.

## 7. Reprodukovateľnosť a záver

Celý priečinok projektu vrátane ignorovaných `vendor/`, `build/`, `data/`, `results/`, `archive/` je prenosová jednotka. [Aktuálna reprodukcia](../docs/reprodukcia.md) uvádza obnovu, preflight, finálne checkery a nový beh P5 na jedinom ns-3.38/SNS-3 3.38 runtime. [P6 odovzdanie](../docs/experiments/p6-handoff-2026-10-26.md) dokladá čistú obnovu v oddelenej kópii, nový obojsmerný P1 a krátky P5 smoke experiment a 15/15 finálnych kontrol nad dočasnými kópiami zachovaných výsledkov. [Pracovný plán](../docs/pracovny-plan-simulatora.md) uchováva poradie P0–P6 a výsledok každej brány. Čitateľ môže overiť jeden graf cez analytický manifest a service-metrics až k presnému ICB1 v natívnom raw trace a zodpovedajúcemu CAM v OCB PCAP.

Práca teda ukazuje, že **konkrétnu krátku cestnú informáciu možno v zvolenom referenčnom modeli preniesť a auditovať** cez lokálnu sieť, RSU a satelitný paketový segment s obojsmernou odpoveďou; kontrolované výpadky menia vzdialený výsledok bez skrytého vypnutia lokálneho toku. Oddelené servisné obaly ukazujú, na ktoré neznáme hodnoty sú výsledky citlivé. Z publikovaných produktových hraníc a orbitálnej geometrie samotných nemožno určiť skutočný výkon troch komerčných služieb. Toto rozlíšenie je hlavným metodickým výsledkom a hranicou návrhového záveru.

## Použité podklady a dôkazy

- [Oficiálne zadanie BP](../docs/zadanie-bp.md), [kontrakt P0](../config/bp_experiment_contract_v1.json), [register zdrojov](../config/bp_service_evidence_v1.json) a [P0 audit](../docs/experiments/p0-experiment-contract-2026-10-25.md).
- [P1 obojsmerná cesta](../docs/experiments/p1-two-leo-roundtrip-2026-10-25.md); [P2 mestský pilot](../docs/experiments/p2-urban-osm-paired-2026-10-25.md), [hopové straty](../docs/experiments/p2-controlled-hop-loss-2026-10-25.md), [P2 dokončenie](../docs/experiments/p2-completion-2026-10-26.md); [P3 jeden UT](../docs/experiments/p3-single-ut-handover-2026-10-26.md); [P4 služby](../docs/experiments/p4-service-profiles-2026-10-26.md); [P5 matica](../docs/experiments/p5-final-matrix-2026-10-26.md).
- [Iridium Certus 9770](https://www.iridium.com/products/iridium-certus-9770), [Globalstar RM200M produktový list](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet1.pdf), [Starlink Performance kit](https://starlink.com/public-files/specification_sheet_performance.pdf), [CelesTrak GP/OMM formát](https://celestrak.org/NORAD/documentation/gp-data-formats.php). Produktové stránky sú dynamické; kontrola ich hraníc a rozsahu použitia je v registri a P4 denníku.
