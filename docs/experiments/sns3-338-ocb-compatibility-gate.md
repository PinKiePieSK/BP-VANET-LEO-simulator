# Brána spoločného ns-3.38 WAVE OCB a SNS-3

**Dátum:** 22. 10. 2026. **Cieľ:** overiť, či už funkčný `OcbWifiMac` a satelitná knižnica SNS-3 možno použiť v **jednom procese a jednom čase ns-3.38**, bez zámienky DVB modelu za komerčnú službu. Tento dokument zachytáva aj nedokončené pokusy. Rozhodovacia logika je v [technickom audite](../decisions/satellite-stack-feasibility.md).

## Izolácia a zdroje

Zdroj je iba v `/tmp/ns3-sns3-338-feasibility`, bez zásahu do `vendor/ns-3.38-ocb-eval`, `vendor/ns-3.48` alebo používateľských dát. Pripnuté commity:

| Zložka | SHA |
| --- | --- |
| ns-3.38 | `392e36833ce3c7e0ecde4188043f76345402d5a7` |
| `contrib/satellite` tag 3.38 | `739a10dbe1db02fd2c4064501e4a48994e0b79f3` |
| `contrib/traffic` | `c68daaf18fadd3393bbb141fedf13fb94a99b6e2` |
| `contrib/magister-stats` | `c613ba7c8cbf284cf0aa24ca778974f711b56370` |
| `contrib/satellite/data` gitlink | `faf7d763438b43139af3d78ff30e4130b2692bd9` |

Východisko: čistá CMake konfigurácia zapla `wave;satellite`, ale pred týmto pokusom bolo dokončených len 47 z 914 kompilácií. Táto konfigurácia nebola runtime testom ani dôkazom vzájomnej kompatibility.

## Dátový gitlink a bezpečnostný limit

Prvý `git submodule update --init data` sťahoval **plnú históriu** do izolovaného checkoutu. Po približne 3,5 minútach mal pack v `.git/modules/data` **2 229 285 023 B** a čiastočný pracovný `ext-fadingtraces` **2 222 569 654 B**; oba spolu prekročili praktický 4 GiB strop pre tento krok na 8 GiB VM. Proces bol prerušený (`Ctrl-C`, exit 130), nie ponechaný bez limitu. Nedokončené `ext-fadingtraces` súbory vznikli týmto klonom, neboli používateľskými dátami. Po overení cesty a git tree sa odstránili z `/tmp` pracovného stromu.

Presný commit `faf7d...` už bol v stiahnutom packu, takže nebolo potrebné ďalšie sťahovanie. Použil sa `git sparse-checkout` s top-level súbormi a iba malými/potrebnými adresármi `antennapatterns`, `beamhopping`, `constellations`, `fadingtraces`, `linkresults`, `sgp4`, `sinrmeaserror`, `tle`, `utpositions`, potom `git checkout -f faf7d...` a `git sparse-checkout reapply`. Výsledný checkout bol **428 MiB**, objektový pack **2,1 GiB**; submodul hlásil presne očakávaný commit. Samotný `ext-fadingtraces` má v cieľovom git tree približne 3 250,7 MiB nekomprimovaných blobov a nepatrí do tohto malého testu. Plná história je už lokálne stiahnutá, preto sa shallow fetch dodatočne nepoužíval. Pri novej VM by sa mal skúsiť shallow/sparse fetch **pred** plným klonom.

## Cielená zostava a monitorovanie

Spustený cieľ:

```bash
cd /tmp/ns3-sns3-338-feasibility
./ns3 build sat-cbr-example -j 2
```

Prvý cielený pokus prešiel po **40/648** krokoch bez kompilátorovej chyby; súbežne však prebiehala ďalšia kompilácia v hlavnom projekte. `free -h` ukázalo swap **2,6/4,0 GiB** a `vmstat` krátkodobo približne **7 MB/s swap-out** pri 1 % idle CPU. Preto bol build prerušený `Ctrl-C` (exit 130). Log: `/tmp/ns3-sns3-338-target-build.log`, SHA-256 `acb6bf7b51ac301f1b043576dfa1b0ead67972280b7ded099f03f3c0636c8dc7`, 93 riadkov/8 852 B; záver obsahuje očakávaný `KeyboardInterrupt`, nie C++ chybu.

Po skončení súbežnej kompilácie bol swap-out v dvoch následných sekundách **0**, dostupná RAM približne **4,3 GiB**. Cieľ sa obnovil s `-j 1`, pričom Ninja znovu použil 40 hotových objektov a ukázal **608** zvyšných krokov. Log pokračovania: `/tmp/ns3-sns3-338-target-build-resume.log`. Build sa musí zastaviť pri trvalom zhoršení swap-out; žiadne zvýšenie paralelizmu sa neplánuje.

Obnovený beh bol na pokyn koordinácie zastavený **22. 10. 2026 o 17:06:48 UTC**, po dokončení **100/608** zvyšných krokov; celkom teda tento test dokončil najviac 140 z pôvodne chýbajúcich objektov. Monitorovanie VM počas behu zachytilo približne **7,5 MB/s swap-in** a **20 % iowait**; pokračovať v ďalších stovkách C++ kompilácií by pri aktuálnej spoločnej záťaži nebolo primerané. `Ctrl-C` skončil kódom **130**. Log obnovenia má 129 riadkov/13 225 B, SHA-256 `641d564e4e3be1df27d5ab0454eb5b340562a56ecd32885c71c1fb608e40c2d2`. Posledný hotový objekt bol `satellite-output-fstream-wrapper.cc.o`; záver je `KeyboardInterrupt`, nie kompilátorová chyba. Po zastavení neostal proces Ninja ani kompilátor z tohto checkoutu. Stav je možné obnoviť neskôr v pokojnom okne VM tým istým `./ns3 build sat-cbr-example -j 1`; hotové objekty zostali v izolovanom `/tmp` checkoute, pokiaľ ho systém nezmaže.

**Dodatočný krátky pokus o 17:17–17:20 UTC:** po skončení ostatných C++ kompilácií mala VM približne 4,3 GiB dostupnej RAM a pokojné `vmstat` bez swap-out a iowait. Izolovaná zostava sa obnovila pri 508 zostávajúcich krokoch: prvých šesť prešlo s `-j 1`, potom ďalších **46/502** s `-j 2`. Počas sledovaných sekúnd nebol swap-out; kompilácia však stále vyžadovala ešte približne **456** krokov. Bola zastavená `Ctrl-C` (exit 130), aby sa nenechal dlhý build bez priebežnej kontroly pri práci v editore. Nebola hlásená C++ chyba, no cieľový binár stále **neexistuje**. Spolu bolo v tomto checkoute dokončených približne 152 z 608 krokov, ktoré zostávali po prvom cielenom pokuse. Po zastavení neostal proces kompilátora. Presný príkaz na neskoršie pokračovanie v pokojnom okne VM je `cd /tmp/ns3-sns3-338-feasibility && ./ns3 build sat-cbr-example -j 1`; zvýšenie na `-j 2` pripadá do úvahy len pri súčasnom monitorovaní `vmstat` a bez iných C++ zostáv.

**Časovo ohraničený pokus o 17:34–17:37 UTC:** pri približne 3,7 GiB dostupnej RAM a 0 swap-out sa v tom istom izolovanom checkoute spustilo `timeout 180s nice -n 10 ionice -c2 -n7 ./ns3 build sat-cbr-example -j 1`. Celé tri minúty kompiloval jediný veľký súbor `contrib/satellite/stats/satellite-stats-helper-container.cc` pri jednom aktívnom `cc1plus` (približne 830 MiB RSS), bez dokončeného ďalšieho kroku Ninja. Na konci bola dostupná RAM približne 2,6 GiB a krátko sa objavil swap-in približne 272 KiB/s; swap-out zostal 0. Časový limit ukončil proces kódom **124** a Ninja oznámil prerušenie. Toto nie je dôkaz C++ chyby, ale potvrdzuje, že aj jednovláknové dokončenie celého historického stromu bude pri súčasnej VM zdĺhavé. Binár `sat-cbr-example` stále nevznikol. Pri ďalšej práci má prednosť merateľný cieľový integračný test alebo ľahšia zostava pred opakovaním neobmedzeného plného buildu.

## Kritériá výsledku

- **Zostaviteľnosť:** úspešný `sat-cbr-example`, potom cielený LEO DVB príklad z toho istého stromu a jednoduchý binárny súbor, ktorý skutočne vytvorí `OcbWifiMac` aj `SatHelper` (iba súčasná existencia knižníc nestačí).
- **Runtime a geografia:** LEO test musí mať UT/SAT/GW PHY udalosti a kladné elevácie oboch pozemných úsekov pri zvolenom pakete. Doručenie pri neplatnej geometrii sa nesmie interpretovať ako fyzikálny výsledok.
- **Architektúra:** `standard/DVB` znamená referenčný DVB-S2/RCS2 profil, nie Starlink, Iridium alebo Globalstar. ISL či sieťová regenerácia sú len vlastnosti daného testovacieho scenára.
- **Obsah:** pri následnom integrovanom teste musí 96 B report vzniknúť zo skutočne prijatého CAM a bajtovo sa zhodovať na RSU/UT/GW aplikačnej hranici. SNS-3 PHY trace bez takej kontroly sám nedokazuje obsah správy.

**Vtedajší stav po časovom limite o 17:37 UTC:** zostava ešte nebola hotová; toto bol stav pri poslednom vyššie uvedenom pokuse, nie konečný výsledok dňa.

## Dokončenie v pokojnom okne VM

Neskorší `timeout 600s nice -n 10 ionice -c2 -n7 ./ns3 build sat-cbr-example -j1` po približne 5,5 minútach dokončil problematický `satellite-stats-helper-container.cc`. Časový limit 10 minút potom skončil kódom 124 pri **182/456** zostávajúcich krokoch, bez C++ chyby. Obnovenie s `-j2` pri meranej dostupnej RAM približne 2,9–3,0 GiB a bez swap-out dokončilo posledných **274/274** krokov, vrátane linkovania `libns3.38-satellite-debug.so` a `sat-cbr-example`. Žiadna systémová konfigurácia VM sa nezmenila. Referenčný `sat-cbr-example --scenario=simple --packetSize=96 --interval=1s` pri prvom spustení zlyhal na neprítomnom `data/sims` v sparse checkoute. `sims` obsahoval len 70 B `readme.txt`; spolu s malými `interferencetraces` a `rxpowertraces` sa doplnil z **rovnakého pripnutého dátového commitu**. Opakovaný beh skončil kódom 0 a zaznamenal 96 B aplikačný príjem pri 8,31302 s po odoslaní pri 8 s.

Spoločný scratch cieľ OCB + SNS-3 si vyžiadal ešte WAVE/Wi-Fi objekty. Prvý build zlyhal v upstream `sta-wifi-mac.h`: používal `std::uint8_t` bez priameho `<cstdint>` pri GCC 13. Ten istý jednoradový include už mal overený `vendor/ns-3.38-ocb-eval`; bol prenesený iba do izolovaného checkoutu a uložený ako [presný patch](../../patches/ns3-338-std-cstdint.patch). Zostava potom prešla. Runtime `ocb-sns3-abi-smoke` v jednom procese vytvoril dva `OcbWifiMac` a `SatHelper::SIMPLE` s jedným GW user (exit 0). Následný [skutočný paketový integračný test](sns3-338-ocb-dvb-packet-gate.md) doručil 16 B skúšobný obsah po trase OCB→RSU→LAN→SNS-3 UT/SAT/GW; kontrolný variant zablokoval iba UT→satelit a ponechal upstream PCAP bajtovo identické. Checker prešiel, úmyselnú PCAP mutáciu odmietol a úplný runner dal pri opakovaní rovnaké hashe trace.

**Aktuálny stav:** zostaviteľnosť a runtime kompatibilita OCB + SNS-3 **v jednom ns-3.38 čase sú overené pre zabudovaný GEO/DVB `SIMPLE` scenár**. Geograficky platný LEO experiment s prijatým CAM, RSU vytvoreným ICB1 a súčasnou UT/GW eleváciou ešte **nie je hotový**. Výsledok sa nesmie priraďovať komerčným konšteláciám ani zamieňať so zatiaľ geometricky riadenou P2P vetvou editora.
