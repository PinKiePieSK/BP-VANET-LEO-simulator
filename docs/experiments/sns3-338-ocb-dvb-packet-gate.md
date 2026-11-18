# Spoločný OCB → RSU → LAN → SNS-3 referenčný satelit → brána

**22. 10. 2026 · overený izolačný test.** Toto je prvý skutočný **jeden čas ns-3.38**, v ktorom pracuje pozemný `OcbWifiMac` aj satelitný PHY/MAC modulu SNS-3 3.38. Ide o funkčnú integračnú bránu, nie ešte o dopravný scenár, LEO konšteláciu alebo profil Starlink/Iridium/Globalstar. Predchádzajúce pokusy a záťaž VM sú v [denníku zostavy](sns3-338-ocb-compatibility-gate.md).

## Hypotéza a model

Hypotéza: v rovnakom ns-3 čase sa dá odoslať jeden skutočný OCB rámec z auta do RSU, doručiť jeho **identický 16 B skúšobný obsah** cez lokálnu IPv4/UDP LAN do uzla UT user a odtiaľ cez SNS-3 return link k uzlu GW user. Pri kontrole, ktorá zastaví iba `UT user`→satelitné odoslanie, musí pozemný OCB a LAN výsledok zostať identický a GW nesmie nič prijať.

`src/sns3-338-ocb-abi-smoke.cc` najprv vytvorí dva skutočné `OcbWifiMac` a `SatHelper::SIMPLE` v jednom procese. `src/sns3-338-ocb-dvb-packet-smoke.cc` potom vykoná skúšobný tok. Paketové bajty `4f434253415431000000000112345678` obsahujú `OCBSAT1`, identifikátor 1 a štyri rozpoznateľné dátové bajty. EtherType `0x88B5` je lokálny experimentálny L2 protokol; **nejde o CAM, GeoNetworking, BTP ani verejný ITS formát**. RSU tu iba prepošle rovnakých 16 B, zatiaľ čo skutočný aplikačný 96 B ICB1 vzniká z prijatého CAM v inom, zatiaľ P2P pilotovi. Rádiové uzly sú pevne 10 m od seba; 802.11p kanál má 10 MHz na kanáli 180, no tento smoke test nekalibruje útlm ani LOS/NLOS. LAN má 100 Mbit/s, nastavené oneskorenie 100 µs a PPP/IPv4/UDP. Náhodné semeno je 314159, beh 1.

SNS-3 používa zabudovaný **`SIMPLE`/Scenario72 referenčný DVB scenár** s jedným UT user a jedným GW user. Súbor `Scenario72GeoPos.txt` v pripnutých dátach nastavuje družicu na 0° šírky, 33° dĺžky a výšku **35 786 000 m**: je to statický **GEO** test, nie LEO ani dráha operátora. Externé auto/RSU lokálne súradnice nie sú geodeticky priviazané k UT; fyzikálnu vierohodnosť celého mesta preto z tohto behu vyvodiť nemožno. Satelitná časť používajúca user/feeder kanály, rámcovanie a plánovanie pochádza zo SNS-3, ale nebola kalibrovaná proti komerčnej službe. [Zdroj SNS-3 scenára](https://github.com/sns3/sns3-satellite/tree/3.38) a [dokumentácia ns-3 WAVE](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) opisujú rodinu modelov; rozhodujúce konkrétne parametre sú lokálne súbory pripnutého dátového commitu.

## Rozhrania, čas a surový dôkaz

| Hranica | Kladný beh | Záporný beh | Jednotka/dôkaz |
| --- | ---: | ---: | --- |
| auto odovzdá OCB rámec | 7 000 000 | 7 000 000 | µs, aplikačný log; PCAP TX 7 000 012 µs |
| RSU prijme presných 16 B | 7 000 128 | 7 000 128 | µs, callback a OCB PCAP RX |
| UT user prijme presných 16 B po LAN | 7 000 231 | 7 000 231 | µs, callback a PPP PCAP RX |
| SNS-3 UT sieťová/PHY TX | 7,00723 / 7,03255 | žiadny testovací paket | s, `PacketTrace`, ID 151 |
| SNS-3 satelit PHY RX/TX | 7,16639 / 7,16639 | žiadny testovací paket | s, `PacketTrace`, ID 151 |
| SNS-3 brána PHY/sieťový RX | 7,30202 / 7,30202 | žiadny testovací paket | s, `PacketTrace`, ID 151 |
| aplikácia GW user prijme presných 16 B | 7 309 015 | nič | µs, callback |

Čas auto TX→GW user RX bol **309 015 µs** v tomto predvolenom GEO modeli. Samotná aplikačná hranica UT user RX→GW user RX trvala **308 784 µs**. Je to jeden deterministický modelový paket bez opakovaní, takže z neho nevyvodzujeme PDR, jitter, dostupnosť ani latenciu LEO či operátora. `PacketTrace` eviduje modelové fázy pre ID 151, **neuchováva bajty PHY rámca**. Zhodu aplikačných bajtov kontroluje kód na RSU, UT a GW; PCAP dokazuje 54 B 802.11 dátový rámec a 46 B PPP/IPv4/UDP rámec vrátane platných IPv4/UDP checksumov. Koncové FCS v ns-3 PCAP sú nulový placeholder, nie vypočítaný rádiový CRC.

Surové [kladné a blokované logy, 4 PCAP na variant, `PacketTrace.log`, verifikácia a manifest](../../results/sns3_338_ocb_dvb_packet_gate/) sú uložené spolu. Checker vyžaduje rovnaký upstream čas a SHA-256 všetkých štyroch pozemných PCAP v oboch variantoch, jediné ID cez UT/SAT/GW v kladnom variante a nulový testovací return packet v zablokovanom variante. Úmyselná mutácia jedného bajtu OCB PCAP bola odmietnutá kódom 1. Celý beh cez nižšie uvedený runner bol opakovaný; SHA-256 oboch `PacketTrace.log` aj `run.log` zostali rovnaké.

## Reprodukcia a zlyhania

Použitý izolovaný checkout `/tmp/ns3-sns3-338-feasibility` má ns-3.38 `392e36833ce3c7e0ecde4188043f76345402d5a7`, `satellite` tag 3.38 `739a10dbe1db02fd2c4064501e4a48994e0b79f3`, `traffic` `c68daaf18fadd3393bbb141fedf13fb94a99b6e2`, `magister-stats` `c613ba7c8cbf284cf0aa24ca778974f711b56370` a `data` `faf7d763438b43139af3d78ff30e4130b2692bd9`. Konfigurácia `debug`, moduly `satellite;wave`, príklady zapnuté, testy vypnuté. Sparse dáta potrebujú aj `sims`, `interferencetraces`, `rxpowertraces` popri adresármi v [kompatibilitnom denníku](sns3-338-ocb-compatibility-gate.md). Pre aktuálny pripravený checkout spusti z koreňa projektu:

```bash
bash tools/run_sns3_338_ocb_dvb_packet_gate.sh \
  /tmp/ns3-sns3-338-feasibility /tmp/sns3-338-ocb-dvb-replay
```

Druhý argument musí byť nový alebo prázdny adresár. Runner overí všetkých päť commitov, prípadne aplikuje presne [jednoradový patch](../../patches/ns3-338-std-cstdint.patch), vloží dva zdrojové súbory do scratch, zostaví ich najviac jednou úlohou, spustí upstream CBR, ABI, kladný a blokovaný paketový variant, potom overí raw výsledky a uloží manifest. Samostatný opätovný audit už uložených dát:

```bash
python3 tools/check_sns3_338_ocb_dvb_packet_gate.py results/sns3_338_ocb_dvb_packet_gate
```

Prvý runtime pokus upstream `sat-cbr-example` zlyhal (`NS_FATAL`), lebo sparse dáta vynechali malý adresár `sims`; doplnenie z rovnakého pripnutého commitu prinieslo exit 0. Prvý build spoločného ABI cieľa zlyhal na `std::uint8_t` v upstream `sta-wifi-mac.h` pri GCC 13; súbor nepoužíval priamy `<cstdint>` include. Jednoradový patch je zhodný s tým, ktorý už mal funkčný izolovaný `vendor/ns-3.38-ocb-eval`, a opakovaná zostava aj ABI runtime potom prešli. Skoršie časovo obmedzené pokusy a swap/I/O merania sa zachovávajú v kompatibilitnom denníku; nejde o zamlčané neúspechy.

## Nasledujúca brána

Pre bakalársku hypotézu treba **nahradiť 16 B skúšobnú správu skutočným prijatým CAM → RSU vytvoreným 96 B ICB1** a použiť geograficky súhlasný LEO scenár s UT, satelitom a bránou na oboch koncoch nad zvolenou maskou. Potom oddelene validovať user/feeder rádiové podmienky, plánovanie, zaťaženie, handover, obsah na gateway a zápornú kontrolu. Ani táto budúca SNS-3 vetva by automaticky nebola Starlink, Iridium či Globalstar: proprietárny terminál, PHY/MAC a služba vyžadujú konkrétne verejné dáta alebo kalibráciu.
