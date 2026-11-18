# Audit paketových bajtov referenčného pilotu

**Dátum:** 22. 10. 2026. **Stav:** experimentálny paketový audit súčasného dvojdružicového referenčného scenára SNS-3. Tento krok plní iba časť brány 0 v [hĺbkovej analýze](../hlbkova-analyza-komunikacie.md): zisťuje, ktoré bajty a hlavičky sú naozaj zachytené na pozemných rozhraniach. Nie je to ešte ETSI ITS-G5 ani operátorský paket.

## Hypotéza, kontrola a hranica pozorovania

Hypotéza: každý zachytený aplikačný UDP datagram pilotu má platné kontrolné súčty IPv4 a UDP a jeho obsah sa bajt po bajte zhoduje s obsahom v aplikačnom zázname pre rovnaký tok a poradové číslo. Kontrolou je opätovné dekódovanie surových PCAP súborov nezávislým nástrojom a zámerne poškodený záznam, ktorý audit musí odmietnuť. Ide o kontrolu konzistencie implementovaného **diagnostického IP/UDP pilotu**, nie o tvrdenie, že bežná ETSI CAM používa UDP. Pri ETSI ITS-G5 CAM je cieľovou cestou štandardné ASN.1 kódovanie → BTP → GeoNetworking → 802.11 OCB; pilot používa `AdhocWifiMac` a aplikačné proxy v RSU.

Vstupy auditu: `run/payloads.csv` a všetky `run/*.pcap` z jedného behu. ns-3 vytvára PCAP s linktype 105 pre 802.11 a linktype 9 pre bodovú PPP linku. Surový PCAP uchová presné zachytené bajty. Dekodér číta riadiace pole a LLC/SNAP pri dátových 802.11 rámcoch, PPP protokol, IPv4 hlavičku a UDP segment. Validuje dĺžky, IPv4 header checksum, UDP checksum s pseudohlavičkou a porovnáva aplikačný obsah s `payloads.csv`. ARP, Wi-Fi riadiace rámce a iné porty sa započítajú, no neprehlasujú sa za experimentálne UDP správy. Ak objaví fragmentovaný IPv4 datagram, skončí chybou, pretože tento nástroj nezostavuje fragmenty. Nezachytené pakety neinterpretuje ako rádiovú stratu.

Výstupy: `run/pcap-packets.csv` obsahuje čas v sekundách, identifikáciu zachyteného rámca, MAC adresy dostupné v 802.11, IPv4 adresy, TTL, identifikátor IP, porty, dĺžky v bajtoch, stav kontrolných súčtov, SHA-256 a **úplný hex aplikačného obsahu**. `run/pcap-audit.json` uvádza počty rámcov, stav, SHA-256 a veľkosť každého PCAP. Prehrávač zobrazuje k vybranej správe tieto hlavičky z PCAP spolu s aplikačným hexom. PPP nemá v tomto zázname ethernetové MAC adresy; bodová linka `PointToPointHelper` nie je Ethernet PHY/MAC.

Súbory bodovej linky si z historických behov ponechávajú názov `packet-ethernet-*`, ale ich PCAP `linktype=9` znamená PPP. V kóde sa preto táto linka volá `lanLink` a udalosť po RSU proxy `p2p_tx`; staršie behy majú ešte názov udalosti `ethernet_tx`. O vrstvách rozhoduje typ zariadenia a zachytená hlavička, nie názov súboru alebo starý popis udalosti.

Prechod názvu vyvolal jeden neúspešný vývojový beh `20261022T143000Zp2p`: zostavenie, simulácia a audit zachytených paketov prešli, ale kontrola cesty stále očakávala staré `ethernet_tx` a beh sa správne ukončil s `failed.txt`. Kontrolný skript teraz očakáva `p2p_tx`; neúspešný beh zostáva zachovaný ako diagnostika a nie je započítaný do výsledkov.

Čistý beh s opravenou kontrolou `20261022T144000Zp2pfix` skončil `COMPLETE` a nezmenených zostalo všetkých 21 odtlačkov vstupov. Zachytil opäť 817 rámcov (648 zachytení experimentálnych UDP datagramov), výsledky aplikácií boli 50/50 V2V, 8/25 V2I a 8/25 cez referenčný satelitný segment. Geometrická kontrola schválila všetkých osem doručených satelitných trás. Rovnaké počty ako pred premenovaním ukazujú, že sa menil názov a dokumentácia modelu LAN, nie úspešnosť tejto konkrétnej simulácie.

`GlobalValue::Bind("ChecksumEnabled", BooleanValue(true))` v `src/vanet-sns3.cc` zapína skutočný výpočet IP/UDP kontrolných súčtov. Predtým ich ns-3 v PCAP zámerne nechával vypnuté kvôli rýchlosti simulácie. Starý geograficky úspešný beh `20261022T133000Zgeo4` audítor správne odmietol: prvý zachytený datagram má chýbajúci UDP/IP checksum. Staré výsledky sa neprepisujú. [Dokumentácia ns-3 k prepínaču](https://www.nsnam.org/docs/models/html/fd-net-device.html) a miestny zdroj `vendor/ns-3.48/src/network/model/node.cc` vysvetľujú globálny prepínač.

## Čo audit nezachytáva

802.11 PCAP neobsahuje rádiové meranie SNR, skutočný FCS ani celý OFDM priebeh. Záznam bodovej linky je PPP. Vnútorné DVB-S2/RCS2 symboly, FEC bloky, satelitné rámce a nepublikované rámce Starlinku/Iridia/Globalstaru nie sú týmto PCAP auditom pozorované; satelitný úsek má samostatný `PacketTrace.log` a hop trace s UID a odtlačkom. Rovnosť odtlačku nie je automaticky rovnosť každého bajtu interného PHY rámca. Reálne servisné obmedzenia, link budget a identita aktívnych satelitov zostávajú ďalšie brány.

## Reprodukcia a výsledok

Úplný beh vytvorí vlastný adresár a uloží aj príkaz, hash zdrojov a surové súbory. V prvom diagnostickom behu `20261022T133500Zc0decafe` prešiel ns-3, paketový audit, geografický audit aj tvorba prehrávania, ale konečná kontrola zdrojových hashov ho **správne označila za neúspešný**, keďže sa počas neho opravilo dekódovanie krátkeho 802.11 ACK rámca. Jeho výsledky nie sú vyhodnotením scenára. Čisté opakovanie s nezmenenými vstupmi `20261022T140000Zcafefeed` skončilo `COMPLETE`; 21 vstupných hashov sa na konci zhodovalo.

Úspešný beh zaznamenal **817 rámcov** v piatich PCAP súboroch, z toho 160 riadiacich 802.11 ACK rámcov a 9 ARP rámcov. Audítor dekódoval **648 zachytení experimentálnych UDP datagramov** (viaceré zachytenia toho istého paketu na rôznych rozhraniach), u všetkých prešli IPv4/UDP kontrolné súčty a celé aplikačné bajty zodpovedali `payloads.csv`. Obsahujú 50 rôznych poradových čísel V2V, 25 V2I a 25 vzdialeného toku; tieto počty **neznamenajú doručenie koncovej aplikácii**. Koncové počty boli 50/50 V2V, 8/25 V2I a 8/25 cez satelitný úsek. Pri ôsmich doručených satelitných správach prešla aj nezávislá horizontová kontrola. `tcpdump` pri vzorke UDP uviedol `[udp sum ok]` a nezobrazil chybný IP checksum. Prehrávač zobrazil ku konkrétnej správe 300 B aplikačný hex a zachytenia na 802.11 aj PPP rozhraniach.

Negatívna skúška skopírovala surové záznamy do dočasného adresára, zmenila jeden bajt prvého V2V payloadu v kopírovanom PCAP a nechala pôvodný aplikačný register. `tools/pcap_audit.py` odmietol vstup: `PCAP payload disagrees with application bytes ... ('v2v', 0)`. Originálny beh a jeho PCAP sa nemenili. Starší `20261022T133000Zgeo4` sa nedá cez nový audit označiť za úspešný, pretože jeho kontrolné súčty neboli vytvorené. Tieto dve odmietnutia tvoria potrebný záporný dôkaz k pozitívnemu behu.

Rovnaký vstup pod novým identifikátorom (bez prepisu úspešného behu):

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
mkdir -p results/visual_runs/20261022T140000Zcafefee2
cp results/visual_runs/20261022T140000Zcafefeed/scenario.json \
   results/visual_runs/20261022T140000Zcafefee2/scenario.json
python3 tools/scenario_run.py 20261022T140000Zcafefee2
```

Po úspešnom behu možno audit samostatne zopakovať:

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 tools/pcap_audit.py results/visual_runs/20261022T140000Zcafefeed
tcpdump -nn -vv -r results/visual_runs/20261022T140000Zcafefeed/run/packet-wifi-16-0.pcap
```

Výsledok tohto experimentu je technická integrácia a dôkaz o **zachytených** bajtoch; hypotézy o pokrytí alebo výkonnosti komerčnej siete z neho nevyplývajú.
