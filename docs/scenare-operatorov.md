# Plán troch porovnateľných topológií

> Historický návrh z 22. 10. 2026. Jeho budúci čas nie je aktuálnym stavom implementácie. P4/P5 neskôr overili oddelené servisné citlivostné obaly bez nezávislej operátorskej kalibrácie; presný rozsah a výsledky sú v [P4](experiments/p4-service-profiles-2026-10-26.md), [P5](experiments/p5-final-matrix-2026-10-26.md) a [rukopise](../thesis/rozpracovana-praca.md).

Stav 22. 10. 2026: cieľový návrh experimentov pre čo najvernejšie dosiahnuteľné podmienky, **nie implementované výsledky operátorov**. Spoločná referenčná simulácia SNS-3 používa DVB a dvojicu historických testovacích LEO satelitov. Každý operátorský profil bude mať konkrétnu službu a terminál, vlastnú verziovanú konfiguráciu, zdroje, kalibračné údaje a kontrolu dostupnosti údajov. Podrobnosti o cieľovej vernosti sú v [hlbkovej analýze](hlbkova-analyza-komunikacie.md).

## Rovnaký dopravný základ

Pre všetky tri profily sa uchová rovnaká **dopravná scéna, udalosť, geografická poloha, čas, cieľový príjemca, požadovaný deadline a meracie body**. Dopravné vstupy a relevantné náhodné podmienky sa párujú; interné procesy jednotlivých služieb nemusia používať totožný generátor náhody. Konkrétna dátová reprezentácia, protokol, veľkosť správ a frekvencia sa riadia skutočnou službou: 300 B UDP nemožno automaticky poslať cez každé satelitné IoT zariadenie. V2V/V2I bez satelitného segmentu je kontrolný variant. Pri satelitných trasách sa oddelene vykáže doručenie cez pozemný prístup, používateľský satelitný spoj, prípadnú ISL, feeder spoj a bránu. Širokopásmové IP služby sa budú skúšať aj pri zaťažení vyjadrenom ako podiel z dostupnej kapacity; správové služby pri ich natívnych limitoch a API. Pri neznámej kapacite alebo handoveri bude výsledkom interval citlivosti kalibrovaný podľa dostupných meraní.

## Konkrétne služby pre cieľové profily

| Operátor a trieda | Kandidát | Skutočné obmedzenie pre spoločnú úlohu |
| --- | --- | --- |
| Starlink mobilný IP | [Performance terminál](https://starlink.com/public-files/specification_sheet_performance.pdf) s plánom povoľujúcim prevádzku za jazdy | IP report a dátový tok, ale iba pri povolenej oblasti použitia, správnej montáži a výhľade. [Podmienky používania za jazdy](https://starlink.com/sz/support/article/50e933eb-54f5-1a77-cc85-c6c8325564cf). |
| Iridium mobilný IP | [Certus 100](https://www.iridium.com/services/iridium-certus-100) | Výrobca uvádza maximálne 88 kb/s; ten istý bezpečnostný report možno poslať, vysokokapacitný tok nie je porovnateľný so Starlinkom. |
| Iridium správová služba | [Certus 9704/IMT](https://www.iridium.com/products/iridium-certus-9704-module) | Správy cez vlastné API do 100 kB, iná metrika a transport než IP Certus 100. |
| Globalstar dvojsmerné IoT | [RM200M](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet.pdf) | 9–144 B v smere zariadenie → sieť a 9–128 B opačne; spoločná udalosť potrebuje krátke kódovanie alebo explicitné segmentovanie. |
| Globalstar jednosmerné IoT | [STX3](https://www.globalstar.com/getmedia/2b486e44-178a-431c-af1d-23cc59ed6b83/stx3-sles-sheet.pdf) | Iba odoslanie, takže scenár s odpoveďou/RTT nie je pre tento terminál platný. |

Najprv sa vyberie **jedna spoločná krátka informácia**, ktorú vedia preniesť všetky zvolené profily, a meria sa jej včasné doručenie. Potom sa samostatne skúma natívne využitie každej služby. Terminál a služba sa do výsledku zapisujú spolu s názvom operátora.

| Profil | Reálna logika a modelovateľná topológia | Kontrola a hypotéza | Čo ešte treba pred výsledkami |
| --- | --- | --- | --- |
| [Starlink](https://starlink.com/technology) | Vozidlo/RSU potrebuje vhodný terminál. Používateľský spoj ide k LEO; pri dostupnej optickej ISL môže paket pokračovať k satelitu s bránou. Konkrétne pásma sa určia podľa zvoleného terminálu a generácie. | Rovnaká geometria s priamou bránou a s geometricky prípustnými ISL trasami rôznej dĺžky; hypotéza: mesh môže zvýšiť dostupnosť za cenu ďalších skokov. Pevne zadaný jeden ISL je len kontrolný test, nie model dynamického routovania. | Dátum a podskupina konštelácie, ephemeridy, terminál/anténa, použiteľné pásma konkrétnej generácie, link budget, servisné obmedzenia a neznámy MAC/scheduler. |
| [Iridium](https://www.iridium.com/network) | L-band používateľský terminál, LEO sieť s RF crosslinkmi a pozemnou bránou. Štyri susedné crosslinky na satelit sú hornou topologickou možnosťou, nie vždy použitou cestou každého paketu. | Variant bez/so smerovaním cez crosslinky; hypotéza: mesh môže zachovať doručenie, keď terminál a brána nie sú pod tým istým satelitom, no zvyšuje počet skokov. | Konkrétna služba a jej šírka pásma, aktuálne orbity, anténa vozidla, L-band link budget, routing/MAC a dátové limity zo zdrojov. |
| [Globalstar](https://www.globalstar.com/en-ap/about/who) | Používateľský terminál → LEO transparentný „bent-pipe“ → pozemná brána v dohľade. Operátorský profil nemá medzisatelitný mesh. | Brána dostupná/nedostupná pod tým istým satelitom; hypotéza: pri strate súbežnej viditeľnosti terminálu a brány satelitná trasa v tomto profile zanikne. | Pokrytie a lokality gateway v čase experimentu, frekvenčné priradenie konkretnej služby, terminál, anténa, link budget a MAC. |

Pre všetky profily treba osobitne rozlíšiť RSU terminál od palubného terminálu. Druhý je hypotetický scenár vozidla vybaveného satelitným zariadením; bez doloženého produktu alebo anténneho profilu sa nebude označovať za bežné sériové auto. Poloha auta ovplyvňuje 802.11p aj geodetickú polohu UT, no rôzne súradnicové systémy musia byť explicitne prepojené. TLE/ephemeridy sa musia archivovať s dátumom a kontrolným súčtom, lebo aktuálne orbitálne polohy nie sú trvalá konštanta.

## Podmienky prijatia operátorského profilu

1. Používateľský, feeder a prípadný medzisatelitný spoj majú dokumentovaný model šírenia, frekvenciu, výkon, anténu, zisk/straty, viditeľnosť, kapacitu, smerovanie a označenie pôvodu parametra. Rovnaký UTC začiatok a geodetické súradnice platia pre SUMO, terminály, satelity a brány.
2. Paketový trace preukáže konkrétnu cestu a obsah koncovej správy. Ak satelitný MAC/PHY nie je verejný, jeho správanie sa pomenuje ako náhradný alebo zjednodušený model.
3. Funkčný smoke test, kontrolný variant a zámerné zlyhania viditeľnosti, handoveru, brány a preťaženia prejdú automatickým overením. Každý beh uchová surové dáta aj konfiguráciu.
4. Parametre otvorených vrstiev prejdú fyzikálnou kontrolou; uzavreté vrstvy sa kalibrujú dostupnými meraniami a validujú na oddelených dátach. Bez takých dát sa uvedie interval neistoty.
5. Výsledok sa označí názvom operátora len v rozsahu zdrojovaných parametrov a presne určenej služby/terminálu. **100 % presnosť proprietárnej siete bez jej interných špecifikácií a kalibračných meraní nemožno verifikovať.**
