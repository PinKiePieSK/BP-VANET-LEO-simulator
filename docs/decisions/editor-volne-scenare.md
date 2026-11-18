# Voľne skladateľné scenáre: rozsah a brány overenia

**Stav 22. 10. 2026:** návrh kontraktu a prvý implementačný míľnik. Používateľský editor má umožniť zostaviť cestnú sieť a vybavenie uzlov nezávisle od pevného dvojvozidlového referenčného príkladu. Uložený návrh ešte nie je výsledok paketovej simulácie.

## Zámer používateľa

1. Kresliť viac úsekov, križovatky a oba smery jazdy. Každý jazdný smer má vlastnú hranu a pripojenie ku križovatkám; nie je to len obrázok jednej čiary.
2. Vytvoriť viac vozidiel, určiť ich štart, trasu, smer, počiatočnú rýchlosť a čas odchodu. Opakovateľnosť vyžaduje explicitné ID a seed, nie náhodný vizuálny počet ikon.
3. Rozmiestniť viac RSU a priradiť im technológie a funkciu, napríklad lokálnu ITS komunikáciu, IP bránu a pevný satelitný terminál. RSU sama o sebe nie je satelitný modem.
4. Každému autu povoliť iba rozhrania, ktoré podľa scenára fyzicky má. Priamy satelitný prenos vyžaduje osobitný terminál, anténu a kompatibilnú službu; obyčajné 802.11p rádio túto vetvu nevytvorí.
5. Zvoliť ciele správ a cestu doručenia (V2V, V2I/I2V, RSU–UT–vzdialená aplikácia, prípadne vozidlový UT). Povolenie rozhrania iba umožňuje pokus o spojenie; nedokazuje dostupnosť, rádiový kontakt ani doručenie.

## Rozhranie návrhu a simulačnej pravdy

Editor ukladá verzovaný JSON. Validátor kontroluje referenčnú integritu uzlov a hrán, súradnice v metroch, možné trasy, jedinečné ID a názvy technológií. Dopravný generátor vytvára SUMO sieť a trasy; prvá brána vyžaduje rozumný priebeh bez neplánovaných teleportov. Paketová brána potom pre každý zvolený tok musí ukázať skutočný vysielač, prijímač, protokol, obsah správy, čas a dôvod úspechu alebo zlyhania. Prehrávač číta iba tieto uložené výsledky a odlišuje dopravné dáta, odvodenú geometriu a raw pakety.

Referenčný `tools/scenario_run.py` dnes prijíma iba jednu dvojsmernú polyčiaru, jednu RSU a presne dve autá. Jeho SNS-3 stopa pochádza z historického satelitného scenára, ktorý [kontrola času a polohy](osm-sns3-reference-gate.md) zamietla pre spoločný OSM experiment. Tento beh ostáva regresnou skúškou implementácie, nie implicitným simulátorom ľubovoľného nového návrhu.

## Poradie rozšírenia

| Brána | Merateľný výsledok | Stav |
| --- | --- | --- |
| A. Editor a dopravná sieť | Export/import JSON, dvojsmerné hrany, križovatka, aspoň tri autá a dve RSU; `netconvert` a SUMO spracujú rovnaký vstup | rozpracované |
| B. Lokálna paketová sieť | Ľubovoľný počet vybavených áut a RSU v rovnakej SUMO mobilite; každá odoslaná CAM má identitu, raw bajty, oprávnených príjemcov a PCAP | plán |
| C. Výber technológie | Model vytvára len nakonfigurované rozhrania a odmieta nepodporovanú kombináciu; párovaná kontrola mení jediný parameter | plán |
| D. Satelitná vetva | Rovnaký čas a geografia, konkrétny UT/služba, samostatné user/feeder/gateway/ISL kroky podľa zvoleného profilu, validácia na externých dátach | plán |
| E. Porovnanie | Rovnaká dopravná situácia a aplikačná informácia, viac seedov/epoch/záťaží, intervaly neistoty a obmedzenia každého profilu | plán |

Základné kritérium: vizuálna možnosť „vybrať Starlink/Iridium/Globalstar“ sa nesmie prezentovať ako zmena paketového modelu, kým kroky C–D neprejdú. Pri proprietárnych protokoloch nebudeme tvrdiť bitovo presný operátorský RF rámec bez dostupnej špecifikácie alebo merania. Vernosť je po vrstvách rozpracovaná v [hĺbkovej analýze](../hlbkova-analyza-komunikacie.md) a aktuálny dôkaz v [stave vernosti](stav-vernosti.md).
