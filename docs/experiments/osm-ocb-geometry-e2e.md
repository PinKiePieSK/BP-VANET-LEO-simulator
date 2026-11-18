# Jedna časová os: OCB CAM → RSU report → geometricky riadený LEO proxy

**Stav:** izolovaný funkčný proof of concept, 22. 10. 2026. **Reprodukcia:**

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
bash tools/setup_ns3_ocb38.sh
bash tools/run_osm_ocb_geometry_e2e.sh
```

Runner vyžaduje pripnutý a zostavený ns-3.38 (`392e36833ce3c7e0ecde4188043f76345402d5a7`) s modulmi `wave`, `wifi`, `point-to-point`, `internet`, `mobility`, `propagation`, `network`, `core`, Vanetza v26.06 (`fb6c551030dcc12b924299bf401e35e5fe814713`), lokálne hlavičky OpenSSL a `.venv` s nástrojmi na prípravu archivovanej OSM trasy. `setup_ns3_ocb38.sh` odteraz zostaví aj P2P; pôvodný už pripravený WAVE strom sa doplnil príkazmi:

```bash
cd vendor/ns-3.38-ocb-eval
./ns3 configure --enable-modules=wave,applications,point-to-point
./ns3 build point-to-point -j1
```

**Hypotéza:** paket CAM skutočne prijatý RSU cez OCB možno v *tom istom ns-3 event clocku* transformovať na nový IP report a poslať cez explicitné uzly RSU, UT, LEO proxy, gateway proxy a server. Ak v rovnakom čase archívna geometria neumožní spojenie na oboch koncoch toho istého objektu nad experimentálnou 10° maskou, report sa vytvorí, ale na P2P cestu nevstúpi. Kontrolným variantom je synteticky záporná elevácia gateway.

## Vstup, algoritmus a jednotky

`tools/prepare_osm_ba_cam_waypoints.py` odvodí päť vzoriek `t=5…9 s` z archivovaného SUMO FCD nad cestou Bratislava OSM. Dopravný dopyt, časový počiatok `2026-10-22T12:45:00Z` a RSU stanovište sú experimentálne zadané. `tools/prepare_osm_ocb_geometry.py` z hashovo overeného archívneho CSV, jeho metadát a komprimovaného Globalstar OMM vytvorí **iba geometrický plán** `schedule.csv`; nečíta predpripravenú ICB1 správu. Každý riadok má UTC/`time_us`, katalógové ID `37741`, SHA-256 konkrétneho OMM záznamu, eleváciu UT a brány v stupňoch, vypočítané `round(slant_range_km / 299792.458 × 10^9)` ns a bit `enabled`. Polohou gateway je **centrum mesta Nemea**, nie overená anténa. Snímka OMM bola stiahnutá *po* simulovanom úseku, teda ide o retrospektívnu rekonštrukciu, nie o predpoveď dostupnú terminálu v čase scenára. Negatívny variant nastaví iba na účely kontroly eleváciu gateway na −1°; nepredstavuje skutočný stav.

`src/osm-ocb-geometry-e2e.cc` používa ns-3.38 `Wifi80211pHelper` a `QosWaveMacHelper`, kontroluje typ `OcbWifiMac` na aute aj RSU, 5900 MHz/10 MHz, OFDM 6 Mb/s, 20 dBm TX, 7 dB RX noise figure a Friis voľný priestor. Vanetza generuje Release 2 CAM UPER (41 B) z každého FCD riadku; BTP-B port 2001 a GN SHB vytvoria 85 B payload pre EtherType `0x8947`. RSU ho dekóduje cez Vanetza, porovná polohu/rýchlosť/heading s FCD a z **práve prijatých 41 B** zostaví nový 96 B `ICB1`: magic/verzia, ID udalosti, čas prijatia RSU v µs, dĺžka CAM, SHA-256 CAM a pôvodné bajty CAM. Nejde o tunelovanie pôvodného CAM ako UDP správy.

RSU potom pri tom istom evente vyhodnotí príslušný riadok geometrie. Ak je povolený, nastaví `Delay` kanála UT→LEO a LEO→gateway podľa `r/c` a pošle ICB1 cez štyri **idealizované 1 Gb/s ns-3 point-to-point** linky RSU→UT→LEO proxy→gateway proxy→server. Prvá a posledná linka majú nulovú modelovú propagáciu, všetky majú nenulový čas serializácie 126 B PPP/IPv4/UDP rámca. IP routing a UDP checksum bežia v ns-3. Pri blokovaní má `trace.csv` `RSU_REPORT_CREATED` a `GEOMETRY_BLOCK`, ale žiadny `RSU_REPORT_TX` ani P2P rámec. Geometria sa vyhodnotí raz pri prijatí CAM, nie počas letu paketu. Vzorky sú od seba 1 s, cesta trvá približne 18 ms.

## Merania, surové dáta a kontrola

`results/osm_ocb_geometry_e2e/{positive,blocked_gateway}/` obsahujú `schedule.csv`, `geometry-manifest.json`, stdout/stderr, raw `trace.csv`, dekódované CAM polia, RSS/noise trace a IEEE 802.11 PCAP TX/RX. Kladný PCAP má päť **123 B QoS OCB rámcov** s wildcard BSSID; posledné 4 B sú nulový placeholder FCS vytvorený ns-3, nie meraný CRC. Python checker `tools/check_osm_ocb_geometry_e2e.py` nezávisle preverí DLT105 a rámcové hlavičky, presných 85 B GN/BTP/CAM, GN long position vector (latitude/longitude s toleranciou 1 × 10⁻⁷°, rýchlosť do 1 cm/s a heading do 0,1°) proti FCD, CAM polia, čas a SHA-256 CAM v 96 B ICB1, všetky štyri dvojice PPP/IP/UDP TX/RX, IPv4/UDP checksum a čas `r/c + 126×8/1 Gbit/s` s toleranciou 2 µs z mikrosekundového záznamu. Výsledok a verzie/hashy zapíše do `verification.json`. Seed ns-3 je `314159`, run `1`.

| Variant | OCB CAM TX / dekódované na RSU | ICB1 vytvorené / poslané / prijaté serverom | RSU TX→server RX |
| --- | ---: | ---: | --- |
| Spoločná geometria nad 10° | **5 / 5** | **5 / 5 / 5** | 17 935, 17 963, 17 992, 18 020, 18 049 µs; priemer **17 991,8 µs** |
| Synteticky blokovaná gateway | **5 / 5** | **5 / 0 / 0** | Nedefinované |

Prvý pokus skompilovať zdroj proti ns-3.38 s `-std=c++20` zlyhal na staršej syntaxi šablónových konštruktorov v hlavičkách ns-3.38; runner používa `-std=c++17`. Prvý úplný runner po úspešnom vykonaní oboch variantov skončil iba preto, že ešte neexistoval nový kontrolný skript; po jeho doplnení kontrola prešla. Tieto neúspešné kroky nemenili vstupnú geometriu ani paketovú logiku.

## Presné hranice tvrdenia

Tento výsledok dokazuje **konkrétny spoločný ns-3.38 simulačný čas**, skutočnú implementovanú OCB MAC namiesto `AdhocWifiMac`, zachovanie/dekódovanie CAM a odvodeného reportu a paketový priechod explicitným LEO proxy uzlom pod geografickým gate. **Nedokazuje úplný ETSI ITS-G5 prístupový profil**: nebeží DCC spätná väzba, zabezpečenie/podpisy, kvalifikované priority CAM, kolízie viacerých vysielačov ani kalibrované mestské šírenie. Historický WAVE modul bol v [ns-3.39 odstránený pre údržbu a chyby](https://gitlab.com/nsnam/ns-3-dev/-/blob/ns-3.39/RELEASE_NOTES.md); jeho úspešný jednotkový beh nie je validácia rádia. [ETSI EN 302 663](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf) a [ETSI TS 102 687](https://www.etsi.org/deliver/etsi_ts/102600_102699/102687/01.02.01_60/ts_102687v010201p.pdf) sú ďalšie akceptačné referencie.

LEO uzol má identitu z archívneho OMM a dve z neho odvodené `r/c` linky, **nie orbitálnu mobilitu v ns-3**. Jeho IPv4 forwardovanie je umelá funkcia proxy pre pozorovanie paketových hopov; **nie je to tvrdenie, že družica Globalstar smeruje IPv4 na palube, ani natívny protokol terminálu**. P2P linky nemodelujú satelitný RF/PHY/MAC, beam, pridelenie služby, feeder stanicu, terminál Globalstar, handover, ISL ani operátorské opakovania. ns-3 P2P NetDevice má vlastný paketový front, ale tento experiment **nemá kalibrované servisné fronty operátora**. Rýchlosť 1 Gb/s je diagnostická voľba, **nie deklarovaná kapacita Globalstar**. Číselných približne 18 ms nie je odhad latencie operátora. Bez reálnej gateway/terminálu a kalibrácie nemožno výsledok vydávať za presnú dostupnosť alebo výkon Starlink/Iridium/Globalstar. Viewer/editor tento PoC zatiaľ nespúšťa; existuje ako presne ohraničený reprodukovateľný experiment.
