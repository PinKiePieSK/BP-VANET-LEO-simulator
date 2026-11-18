# Certus 100 IP servisný obal: skutočné ICB1 bajty a spätná aplikačná odpoveď

**Míľnik 22. 10. 2026 UTC.** Samostatná ns-3.38 sonda. Nadväzuje na [výber SkyLink 5100](../decisions/satellite-service-implementation.md), ale nie je spojená s OCB do jedného simulačného behu. Od predchádzajúcej [ns-3.48 Certus sondy](certus100-e2e.md) sa líši tým, že používa **šesť presných 96 B `ICB1` reportov vytvorených RSU z dekódovaných CAM** v [editable-v2 OCB pilote](editable-v2-ocb-geometry-e2e.md), nie syntetický 300 B obsah, a pracuje v pripnutej ns-3.38 zostave. Odpoveď `GRA1` je 46 B **naša aplikačná správa**, nie potvrdenie satelitnej siete.

## Hypotéza a scenár

Ak pevná RSU odovzdá niekoľko krátkych reportov IP terminálu s nominálnym Certus 100 uplinkovým stropom, potom sa všetky doručia v nezaťaženom **modeli**. Pri zámernej ponuke nad stropom a konečnom fronte musí simulátor zaznamenať konkrétne zahodené ID. Server odošle vlastnú potvrdenku späť cez oddelený nominálny downlinkový strop. Toto testuje kód obalu a bajtovú identitu; nepredpovedá výkon Iridium.

Reálny význam: vozidlo pošle lokálny CAM, RSU ho dekóduje a vytvorí nový krátky UDP report, ktorý by vedel odoslať do Ethernet LAN terminálu SkyLink 5100. [NAL Technologies](https://naltec.com/products/skylink-5100/) uvádza Certus 100 **22 kbit/s UL / 88 kbit/s DL** ako produktové maximum. [User Guide v3.4](https://naltec.com/download/1044/skylink-5100/41483/skylink-user-guide-v3-4) dokumentuje `Satellite Only`, vypnutie Cellular, Ethernet a samostatné čítače. V sonde nemáme hardvér ani aktivovanú službu; IP servisný úsek je **nepriehľadná abstrakcia**.

## Moduly, vstupy a algoritmus

| Súčasť | Účel, vstup a výstup | Jednotky, predpoklady a obmedzenia |
| --- | --- | --- |
| [`v2-six-icb1-reports.csv`](../../data/fixtures/v2-six-icb1-reports.csv) | Šesť verifikovaných `RSU_REPORT_CREATED` riadkov pôvodného OCB trace: `event_id`, pôvodný čas a celý 96 B hex. | Čas v µs v pôvodnom ns-3 behu; nie UTC čas novej sondy. SHA-256 v každom `ICB1` pre 41 B CAM sa kontroluje pred odoslaním. SHA-256 fixture `656b3a4096997fbd8749d342edb141d942dd0f223f1d4139890d164213edcefc`. |
| [`certus100-ip-service-edge-38.h`](../../src/certus100-ip-service-edge-38.h) | Znovupoužiteľný `Certus100IpServiceEdge`: `Submit(report,event_id,ready)` a `Reply(response,event_id)`; dve UDP/IP smery, konfigurácia `uplinkBps`, `downlinkBps`, `queuePackets`, PCAP, trace/callbacky. | Produktové maximá 22 000/88 000 bit/s sú *horné medze vstupu* podľa [NAL](https://naltec.com/products/skylink-5100/) a [Iridium 9770](https://www.iridium.com/products/iridium-certus-9770/). Dva odlišné zariadenia seriálizujú smer samostatne. P2P/PPP je **syntetický nosič**, nie Iridium MAC alebo rádiový rámec. Front je `DropTail` na zariadení aj koreňový ns-3 queue disc, každý 4 pakety v tomto behu. Obsah frontu/rozvrhu je náš model, nie produktový parameter. |
| [`certus100-icb1-ip-envelope-38.cc`](../../src/certus100-icb1-ip-envelope-38.cc) | Testovací harness: RSU→terminál lokálna LAN proxy 100 Mbit/s, UDP report cez servisný obal na server; server overí každý ICB1 a vráti `GRA1` s ID a SHA-256 reportu; terminál ho prenesie k RSU. | Lokálna LAN je tiež ns-3 **P2P/PPP proxy**, nie skutočný Ethernet PHY/MAC. Dva miestne UDP proxy kroky predstavujú aplikačné odovzdanie, nie presnú implementáciu NAT/firewallu SkyLink. Nulové oneskorenie servisného kanála je zámerný syntetický vstup; nie odhad satelitnej latencie. |
| [`run_certus100_icb1_ip_envelope_38.py`](../../tools/run_certus100_icb1_ip_envelope_38.py) | Zostaví iba nový C++ harness, spustí pozitívny a záťažový variant, overí fixture, surový trace, štyri PCAP a manifest. | Jeden `g++` proces; neprerába spoločnú ns-3 build cache. Audit kontroluje PPP/IPv4/UDP dĺžku a checksum, celý ICB1/GRA1 obsah, event ID, konzerváciu TX/drop/RX a UL serializáciu. |

**Záťažový variant:** 60 paketov počas približne 1 s sa vytvorí zo šiestich pôvodných CAM obsahov; každá kópia dostane nové experimentálne `event_id` v `0xcb...` oblasti. Takéto ďalšie udalosti **nie sú skutočne prijaté CAM**. Len základný variant zachová všetkých šesť pôvodných 96 B reportov úplne bez zmeny. Spätný `GRA1` má 4 B magic, 1 B verziu, 8 B event ID, 32 B SHA-256 celého reportu a 1 B lokálny status. Žiadny protokol operátora sa tým nekóduje.

## Reprodukcia a surové výsledky

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_certus100_icb1_ip_envelope_38.py
```

Výstup: `results/certus100_icb1_ip_envelope_38/{baseline,overload}/trace.csv`, štyri surové PCAP na každý variant, `run.log`, `build.log`, `manifest.json`. Manifest pripína SHA-256 zdrojov, fixture, binárky, PCAP a trace aj presný kompilačný príkaz. `--ulBps` akceptuje iba `(0,22000]`, `--dlBps` iba `(0,88000]`; zámerné `--ulBps=30000` sa odmietlo pred behom.

| Variant | Ponúknuté reporty | Server overil | UL front zahodil | ACK na RSU | Interpretácia |
| --- | ---: | ---: | ---: | ---: | --- |
| Základ, 6 reportov po 0,5 s | 6 | 6 | 0 | 6 | Kontrola obsahu a oboch IP smerov v **nezaťaženom modeli**. |
| Syntetické opakovanie, 60 reportov za ~1 s | 60 | 30 | 30 | 30 | Kontrola limitu a konečného frontu; nie odhad PDR služby. |

Audit PCAP prešiel pre všetky zachytené datagramy: 126 B PPP/IPv4/UDP/ICB1 v UL a 76 B PPP/IPv4/UDP/GRA1 v DL, platné IP a UDP checksumy, identické aplikačné bajty na príslušných hraniciach. Každý výstupný report má práve jednu zo vzájomne vylučujúcich možností `SERVICE_UP_WIRE_TX` alebo `SERVICE_UP_QUEUE_DROP`; každému doručenému serverovému ID zodpovedá jedna potvrdenka na RSU. Záťažová stopa má 90 rámcov na každom LAN proxy PCAP a 60 rámcov na každom servisnom PCAP. **V žiadnom PCAP nie je Ethernet ani Iridium RF rámec**; DLT PPP je technické médium ns-3 proxy. Produktových 22/88 kbit/s tu tvorí iba hornú hranicu seriálizácie v oboch smeroch; nulový propagation delay znamená, že namerané časy skúmajú front a seriálizáciu modelu, **nie** RTT komerčnej služby.

Záznam neúspešných pokusov počas prípravy: (1) prvá kompilácia nemala lokálnu cestu k OpenSSL hlavičkám, doplnili sa už pripravené hlavičky bez systémovej inštalácie; (2) prvý beh neotvoril fixture pri absolútnej ceste v pracovnom adresári s medzerami, runner preto kopíruje pripnutý fixture ako relatívny vstup variantu; (3) 30 správ/s s predvoleným 4-paketovým frontom v krátkom okne ešte nespôsobilo drop, kontrola zaťaženia preto používa 60 správ/s. Neúspešné pokusy nefigurujú vo vyhodnotení. Žiadne operátorské meranie nebolo vykonané.

## Čo teraz stále chýba

Tento míľnik **nespája** OCB a Certus na jednom simulačnom clocku: presných šesť reportov prenáša ako pripnutý výstup predchádzajúceho overeného behu. Následná integrácia môže po prijatí CAM na RSU volať znovupoužiteľné `Submit(...)` v tom istom ns-3.38 behu. Musí dodať Iridium **user-leg geometrický kandidát** oddelene od servisného úspechu. Konkrétny beam, handover, crosslink, gateway, RF/MAC, komerčný delay/loss a podmienky spätnej IP cesty zostávajú nezistené podľa [parameter auditu](../decisions/satellite-service-implementation.md). Výsledný graf sa preto zatiaľ nesmie označiť za presnú latenciu ani dostupnosť Certus 100.
