# LEO kandidát 37741: viditeľnosť nestačila na paketový spoj

**Stav:** zámerne zachovaný neúspešný experiment, 22. 10. 2026. Cieľ bol overiť, či možno v tom istom ns-3.38/SNS-3 3.38 stacku, ktorý úspešne prenáša CAM→RSU→UT→referenčný GEO satelit→GW, použiť časovo aktuálnu LEO dráhu s terminálom pri `rsu0` a geograficky určeným bodom brány. Výsledok je **neprijatý paket**, nie meranie služby Globalstar alebo dôkaz jej nedostupnosti.

## Hypotéza, reálny význam a kontrast s kontrolou

Hypotéza: ak sa do SNS-3 vloží LEO GP objekt s oboma pozemnými koncami nad experimentálnou 10° maskou, malý UDP paket z UT prejde cez jeho DVB model do GW používateľa. V reálnom svete by to vyžadovalo viditeľnosť, kompatibilný terminál, obsluhujúci lúč, dostatočný SINR a riadiace/prístupové rámce. **Samotná elevácia nie je potvrdenie služby.** Kontrolou pre integračný stack je [úspešný statický GEO DVB beh so šiestimi CAM/ICB1](editable-v2-ocb-sns3-dvb-gate.md); tento LEO pokus mení aj orbitu, geografiu, beam a režim regenerácie, takže z rozdielu nemožno izolovať jeden fyzikálny faktor.

## Vstupy a algoritmus

- Orbitálny záznam: archivovaná GP/OMM JSON snímka skupiny `globalstar` získaná 22. 10. 2026 z cache CelesTrak, katalogové číslo **37741**, názov `GLOBALSTAR M091`, epocha elementov **2026-10-21T06:54:00.067392Z**. Hash zdrojového archívu a manifestu je vo výstupnom `run-manifest.json`. Katalógový názov **nepreukazuje**, že objekt v danom okamihu poskytuje službu alebo že model má Globalstar PHY/MAC. [CelesTrak opisuje OMM a obmedzenie 5-miestneho TLE](https://celestrak.org/NORAD/documentation/gp-data-formats.php); práve tento objekt má 5-miestne ID a preto sa dal konvertovať do TLE formátu požadovaného SNS-3 3.38.
- `sgp4` 2.27 vytvorí zo zdrojového OMM `Satrec` (WGS72) a exportuje TLE. Po spätnom načítaní TLE je rozdiel propagovanej polohy pri čase paketu **0,313 m**; oba vstupy sú preto pre túto jednu epóchu prakticky rovnaké. Na konverziu TEME→ITRS a nezávislé elevácie sa použil Astropy 7.1.1 s lokálnym EOP súborom; jeho SHA-256 a verzia `astropy_iers_data` sú v manifeste. `UT=(48.1480603°N,17.1035340°E,0 m)` sa zhoduje s `rsu0` v uložených waypointoch; `GW=(37.8167°N,22.6667°E,0 m)` je **Nemea city proxy**, nie overená gateway anténa operátora.
- SNS-3 má jeden pohyblivý LEO objekt, jedno UT, jeden GW, žiadne ISL, sieťovú regeneráciu, referenčný DVB-S2/RCS2 stack a testovací `SatAntennaGain72BeamsShifted` beam pattern. Družica sa aktualizuje po 10 ms. Štart je 2026-10-22 12:45:20 UTC, UDP payload má 16 B a odosiela sa v čase simulácie 1 s. Seed `314159`, run `1`; beh končí po 4 s. Zdroj má presné vstupy/výstupy/jednotky v `src/sns3-338-leo-candidate-probe.cc` a spúšťač v `tools/run_sns3_338_leo_candidate_37741_probe.py`.
- Pri UTC **2026-10-22T12:45:21Z** má podľa nezávislého SGP4/Astropy UT eleváciu **20,345°** a proxy GW **21,305°**. To sú geometrické uhlové polohy, nie pokrytie beamom ani rezervy link budgetu.

## Pozorovanie a interpretácia

Program korektne vytvoril LEO topológiu a odoslal 16 B UDP v t=1 000 000 µs. `PacketTrace.log` pri ID **9** ukazuje `UT ND SND` a `UT LLC ENQ` o t≈1,009 s. Neobsahuje `UT PHY SND` pre tento paket ani jeho prijatie v GW. V tom istom **štvorsekundovom** behu sa v `UT PHY FWD` zahodilo **35** modelových dopredných rámcov, vrátane opakovaných riadiacich rámcov. `stat-per-ut-fwd-user-link-sinr-scatter-1.txt` uvádza pri t≈1,019 s **−0,129901 dB**. Následné cielené stopy identifikovali rozhodnutie error modelu pri všetkých 35 dropoch; výsledky a ich hranice sú nižšie. −0,13 dB samo o sebe nie je univerzálny servisný prah.

## Cielené rozlíšenie PHY zlyhania

Nová hypotéza: ak pôvodnú paketovú cestu blokuje referenčný SNS-3 *block error* model (`EM_AVI`), postupné vypnutie chýb najprv iba na doprednom prijímači UT a potom aj na návratovom prijímači GW bude posúvať **ten istý paket ID 9** po vrstvách. Všetky tri varianty ponechávajú ten istý GP objekt, čas, pozemné body, beam pattern, dátový obsah, seed a sieťovú topológiu. Zásah do error modelu je výhradne **diagnostický kontrafaktuál**; varianty s `EM_NONE` nevypovedajú o kvalite skutočného rádiového spoja ani o parametri operátora.

| Variant | FWD UT | RTN GW | Pozorovaná paketová cesta ID 9 |
|---|---|---|---|
| Pôvodný | `EM_AVI` | `EM_AVI` | UT ND/LLC, bez UT PHY; 35 UT FWD PHY dropov |
| Dopredné chyby vypnuté | `EM_NONE` | `EM_AVI` | UT PHY → SAT PHY/ND → SAT návratový PHY; **GW PHY drop** |
| Obe chyby vypnuté | `EM_NONE` | `EM_NONE` | UT PHY → SAT PHY/ND → GW PHY/ND → **GW aplikácia**, presných 16 B |

`SatPhyRxCarrier::CheckAgainstLinkResultsErrorModelAvi` v pripnutom zdroji SNS-3 volá pre dopredné rámce `SatLinkResultsFwd::GetBler(modcod, frameType, Es/N0)` a pri náhodnej hodnote menšej ako BLER nastaví `phyError`. Zdrojová premenná sa volá `ber`, ale volaná funkcia vracia **BLER**, preto v práci používame presný názov. Pri pôvodnom behu stopy `NS_LOG` uvádzajú pre všetkých **35** zahodených FWD rámcov `BLER=1`, `error=1`; pri t≈1,019 s `Es/N0=−0,129901 dB`. Pri variante iba s vypnutým FWD error modelom sa paket prvýkrát odoslal z UT na PHY a dorazil na družicu. Štyri zachytené návratové rozhodnutia v GW mali `BLER=1`, `error=1`; prvé dve majú `C/SINR≈−4,18 dB` v `NS_LOG` (log vypisuje aj odvodené `Eb/N0`). Paket ID 9 sa zahodil na GW PHY. V treťom variante sa identický aplikačný obsah prijal v t=**1 119 741 µs**, teda **119 741 µs** po odoslaní z UT user. Toto číslo je čas **diagnostického bezchybového modelu**, nie meranie LEO služby ani vhodný údaj do porovnania operátorov.

Výsledok izoluje *miesto rozhodnutia o chybe* na oboch smeroch. **Neurčuje**, či je fyzikálnym dôvodom nízky zisk umelého 72-beam vzoru pri LEO, terminálové parametre, zvolený MODCOD, prenosový výkon, šírka pásma alebo ich kombinácia. Tiež nepotvrdzuje priradenie skutočného beamu/pozemskej brány. Žiadne nastavenie `EM_NONE` sa preto nesmie použiť ako predvolená konfigurácia experimentov bakalárky.

### Audit referenčnej anténnej mapy

Ďalšia otázka bola, či použitá anténna mapa zodpovedá LEO geometrii. V pripnutom SNS-3 dátovom súbore `SatAntennaGain72BeamsShifted/GeoPos.in` je **kotva mapy** `45° N, 33° E, 35 786 000 m`; zemepisná šírka kotvy **nie je fyzikálnou polohou geostacionárnej družice**. [Dokumentácia SNS-3](https://www.sns3.org/doc/satellite-design.html) opisuje základný viac-lúčový referenčný systém na geostacionárnej dráhe približne v tejto výške. Skutočný SGP4 objekt sondy mal v čase paketu výšku **1 406 917,195 m**. V pripnutom zdroji `SatAntennaGainPattern::GetSatelliteOffset` sa mape k aktuálnej polohe družice pripočíta iba rozdiel **zemepisnej šírky a dĺžky**; `GetAntennaGain_lin` následne interpoluje rovnakú zemepisnú mriežku. V tejto funkcii sa pôdorys lúča podľa rozdielnej výšky GEO/LEO ani podľa uhlovej vzdialenosti od boresightu nepreškáluje.

Sonda preto v čase t=1 s priamo cez `GetAntennaGain_lin` odčítala modelový zisk použitého lúča 30: **7,5442 dB pri UT** a **8,8191 dB pri proxy GW**; zisk lúča 43 pri proxy GW bol **4,6537 dB**. Ide o *hodnoty tejto nevhodnej referenčnej mapy*, nie o zisky antén Globalstar. V dátovom súbore lúča 30 je maximum **51,4453 dB**, takže hodnota na UT je o približne **43,90 dB** nižšia než vrchol tej istej mapy. SNS-3 kanál pritom počíta free-space loss zo skutočných polôh vysielača a prijímača, ale násobí ho týmto ziskom z posunutej GEO mapy. Výsledná kombinácia nie je validovaný LEO beam/link budget. Nízky mapový zisk je konkrétny kandidát vysvetlenia malého SINR; tento audit **neizoluje** jeho podiel oproti ostatným PHY nastaveniam.

`verification.json` teraz obsahuje menovitú polohu mapy, skutočnú výšku družice a tri zisky; `run-manifest.json` má SHA-256 `GeoPos.in` a oboch použitých beam súborov. Runner odmietne chýbajúce, nejednoznačné či nefinite hodnoty a nesúlad s pripnutou referenčnou konfiguráciou. Zvyšný `PacketTrace.log` má **rovnaký SHA-256** `817d4779…` ako pri predchádzajúcej izolácii PHY; meranie zisku nemení trasu paketu. Audit zakazuje vyvodiť výsledok pre operátora alebo „opraviť“ nízky zisk ľubovoľným zvýšením výkonu. Ďalší rádiový profil musí mať geometriu lúča viazanú na smer zo satelitu k pozemnému bodu, explicitné parametre antény a citlivosť na neistotu týchto parametrov.

### Technická špecifikácia sondy a návod

`src/sns3-338-leo-candidate-probe.cc` vytvorí jednu SGP4 družicu, jedno UT pri súradniciach RSU, jednu **mestskú proxy** GW, používateľské uzly a ns-3 UDP socket. Aplikačný payload je 16 B `LEOGEO1` + pevné bajty; prijímacia funkcia kontroluje dĺžku a bajtovú zhodu. V čase paketu sonda číta výšku družice v metroch a modelové zisky lúčov 30/43 v dB; tieto diagnostické čísla nemenia rádiový výpočet. `--output` je existujúci prázdny adresár na raw stopy. Voliteľné `--disableFwdErrors=1` nastaví iba `ns3::SatUtHelper::FwdLinkErrorModel=EM_NONE`; `--disableRtnErrors=1` iba `ns3::SatGwHelper::RtnLinkErrorModel=EM_NONE`. Obe voľby sa nastavia **po** konštruktore `SimulationHelper`, ktorý inak načíta predvolené `EM_AVI`, a **pred** vytvorením scenára. Exit `0` znamená jeden bajtovo správny príjem, exit `1` bez príjmu alebo pri nezhode. `PacketTrace.log` sleduje interné paketové ID a vrstvy, nie všetky bajty satelitných PHY rámcov; UDP payload je kontrolovaný na konci, no sondou nemožno odvodzovať presný obsah operátorských protokolov.

`tools/run_sns3_338_leo_candidate_37741_probe.py` overí pripnuté Git commity a hash archívneho OMM, vypočíta nezávislú eleváciu a OMM→TLE rozdiel, vytvorí štyri textové vstupy scenára, skompiluje C++ sondu a spustí tri varianty. Kontroluje konkrétne hrany ID 9, zhodu počtu FWD error rozhodnutí s UT PHY dropmi, návratové rozhodnutia v GW, presný aplikačný payload a audit anténnej mapy. Ukladá manifest SHA-256, `verification.json`, textové vstupy, PacketTrace a SINR/RX-power pre všetky tri varianty do `results/sns3_338_leo_candidate_37741_phy_isolation/`. Kompilácia a každý beh používajú deterministický seed `314159`, run `1`; topológia a model sú viazané na pripnuté ns-3.38/SNS-3 3.38 commity. `NS_LOG` sa v prvých dvoch behoch zapína len na `SatPhyRxCarrier=level_info`.

Prvý pokus so štartom o 20 s skôr a aplikáciou v t=20 s tiež nedoručil paket. Následný kratší pokus presunul UTC začiatok priamo na 12:45:20 a nechal paket v t=1 s; jeho raw výsledok je uložený. Pôvodný krátky pokus bez `SetUserCountPerUt(1)` skončil skorým tvrdením SNS-3 `User count per UT not set`; po doplnení povinného parametra vznikla topológia a odhalil sa skutočný linkový neúspech. Záverečný spúšťač preto očakáva, že skúšobný program skončí kódom `1` a vytvorí `verification.json` so stavom `EXPECTED_LINK_FAILURE`; spúšťač sám skončí úspešne len vtedy, keď nezávisle potvrdí presne tento pozorovaný výsledok.

## Reprodukcia a uložené dáta

```bash
.venv/bin/python tools/run_sns3_338_leo_candidate_37741_probe.py \
  /tmp/ns3-sns3-338-feasibility /tmp/novy-leo-kandidat-37741
```

Runner kontroluje pripnuté commity ns-3/SNS-3, hashe archívneho GP súboru, vytvorí štyri scenárové vstupy bez prepisu odlišných dát, zostaví cielenú sondu a overí pôvodnú neúspešnú cestu aj dva diagnostické kontrafaktuály. Nové kompletné výstupy sú v `results/sns3_338_leo_candidate_37741_phy_isolation/`; pôvodný samostatný neúspešný beh zostáva v `results/sns3_338_leo_candidate_37741_failure/`. Na základnú konfiguráciu sa neaplikuje náhradné doručenie, umelá kapacita ani „opravený“ beam bez dôkazu.

**Ďalšia technická brána:** určiť fyzikálne a protokolovo zdôvodnený LEO terminal/beam/gateway profil a dosiahnuť opakovateľné UT↔GW doručenie so zapnutým `EM_AVI` pri oboch geodeticky platných koncoch. Až potom preniesť šesť CAM/ICB1 z funkčného GEO integračného behu na LEO a merať porovnateľné rozdelenia.
