# ns-3.48: koncová IP proxy trasa so servisným obalom Certus 100

**Stav:** 22. 10. 2026 UTC. **Kód:** [`src/certus100-e2e.cc`](../../src/certus100-e2e.cc), [`tools/run_certus100_e2e.py`](../../tools/run_certus100_e2e.py). **Súvisiace rozhodnutie:** [operátorské služby](../decisions/operator-services.md). Tento samostatný míľnik spája aplikácie a ns-3 pakety od RSU cez LAN, UT proxy, abstraktný kapacitný úsek a server. Voliteľne používa vzorkovaný geometrický plán na **prípustnosť jediného úseku UT→satelit**. Nie je modelom rádiového protokolu ani prevádzkovej trasy Iridia.

## Účel a hypotéza

Prvá testovaná cesta je `RSU → LAN → UT/proxy → abstraktný Certus 100 IP serializer → server`. Server po prijatí odošle **diagnostické echo** tej istej aplikačnej správy opačným serializerom `server → UT → LAN → RSU`. Echo nie je Iridium acknowledgment, aplikačná služba ani namerané RTT. Cieľ je dokázať, že event ID a pôvodné aplikačné bajty prežijú proxy, každý paket má pozorovateľnú cestu po hopoch, a že preťaženie obmedzí serverové doručenie bez narušenia LAN.

Kontrolný variant má 5 správ/s, teda `5 × 300 B × 8 = 12 kbit/s` aplikačného zaťaženia. Negatívny variant má 30 správ/s, teda 72 kbit/s. [Modul Iridium Certus 9770](https://www.iridium.com/products/iridium-certus-9770) uvádza najviac **22 kbit/s od terminálu a 88 kbit/s k terminálu**; [SkyLink 5100](https://ifp.iridium.com/products/nal-research-skylink-5100-satellite-terminal/) používa tento modul a [Certus 100](https://www.iridium.com/services/iridium-certus-100) je IP služba. Sú to produktové maximá, nie garantované rýchlosti alebo RF bitové rýchlosti. Predpoklad: pri nastavenom fronte a 500 ms *experimentálnom* deadline kontrola prejde, preťaženie spôsobí stratu alebo zmeškanie deadline.

## Algoritmus a skutočný obsah paketu

- RSU vytvorí **syntetický** incident `incident=road-obstacle`, stanicu `12001`, pevné polia `lat_e7=481486000`, `lon_e7=171077000`, `event`, `seq`. Telo je text doplnený nulovými bajtmi do 272 B. Neprišlo z prijatej CAM ani DENM; preto ho práca nesmie označiť za ETSI správu alebo údaje z reálneho vozidla.
- Pred telo sa vloží 28 B **in-band** `ReportHeader` v sieťovom poradí: `seq:u32`, `event_id:u64`, `source_hash_fnv64:u64`, `created_sim_time_ns:u64`. `event_id = 0xC100000000000000 + seq`. FNV-1a 64 sa počíta nad **272 B telom** vrátane doplnenia. Je to kontrolný hash, **nie kryptografická integrita ani podpis**. Aplikačný report má presne 300 B. UDP/IPv4/P2P PPP rámec meraný v trace má 330 B (`300+8+20+2`), pri použitých nastaveniach bez IP options/fragmentácie.
- RSU a UT používajú UDP sockety. UT prijatý report skopíruje do **nového UDP/IP datagramu**; server verifikuje in-band ID a FNV hash skutočného tela. Serverové diagnostické echo a UT návratová proxy vytvárajú ďalšie nové UDP/IP datagramy. Aplikačných 300 B zostáva bitovo rovnakých, okrem samostatnej skúšky úmyselného poškodenia.
- ns-3 `TraceTag` nesie `seq/event_id/hash` pre `p2p_tx`, `p2p_rx` a queue-disc drop. **Tag je len metadátum simulátora a nie je na rádiovom/PPP drôte.** Runner kontroluje zhodu tagu s 28 B in-band hlavičkou na aplikácii. `payloads.csv` obsahuje celý **aplikačný paket v hex** na `RSU_TX`, `UT_RX`, `UT_TX`, `SERVER_RX`; runner porovnáva každý bajt a znovu počíta hash. IP/UDP hlavičky a checksum sa v tomto artefakte neexportujú ako PCAP; ich celková dĺžka sa pozoruje v P2P trace.
- `LAN_UP`/`LAN_DOWN` sú P2P linky 1 Gbit/s s 0 ms propagáciou ako testovací predpoklad. `SERVICE_UP` je P2P serializer 22 kbit/s a `SERVICE_DOWN` iný P2P serializer 88 kbit/s. **Dva smerové serializéry nie sú Iridium full-duplex RF kanál.** Každý má 4-paketový queue-disc a 4-paketovú frontu zariadenia; to sú skúšobné hodnoty. Pri zostavenej experimentálnej konfigurácii sa 300 B aplikácie serializuje so spomenutým PPP/IP/UDP overheadom, takže 22/88 kbit/s na P2P je konzervatívny obal vzhľadom na publikované *IP* maximá.
- `deadline=500 ms` je testovacia požiadavka aplikácie, nie norma pre túto správu, reklamované RTT ani limit Iridia. `app_server_expired` je prijatie po deadline, nie fyzická strata. Propagačné, orbitálne, beam, handover, ISL, feeder, gateway a core oneskorenie tu nie sú implementované; nastavené `Delay=0 ms` sa nesmie interpretovať ako ich nulová fyzická hodnota.

### Pozorované hop-y

CSV `event,hop,seq,event_id,body_hash_fnv64,time_s,bytes,detail` rozlišuje: `app_rsu_tx` → `LAN_UP p2p_tx/rx` → `app_ut_rx` → `app_ut_proxy_tx` → `SERVICE_UP p2p_tx/rx` alebo `queue_disc_drop` → `app_server_on_time/expired`. Diagnostický návrat: `app_server_echo_tx` → `SERVICE_DOWN p2p_tx/rx` → `app_ut_down_rx` → `app_ut_return_tx` → `LAN_DOWN p2p_tx/rx` → `app_rsu_echo_rx`. Pri každom hop-e sa eviduje rovnaké `event_id` a hash pôvodného tela; zhodu dát potvrdzuje hex export. Názov `p2p_tx` výslovne znamená ns-3 bodový link, nie satelitné PHY.

## Reprodukcia, zdroje a vstupy

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 tools/run_certus100_e2e.py
```

Runner kompiluje samostatným `g++ -std=c++20 -O1` proti **už zostaveným knižniciam ns-3.48** vo `vendor/ns-3.48/build/`; nevyvoláva paralelný build. Kontroluje `VERSION=3.48`, zaznamená Git commit ns-3, SHA-256 kódu, produktové odkazy a konfiguráciu do `results/certus100_e2e/manifest.json`. `results/` sa necommituje. Základnými vstupmi sú `pps`, 10 s generovania, 300 B report, 4-paketové fronty, 500 ms deadline. Každý beh má surový event CSV a `*-payloads.csv` s hex bajtmi. Bez voľby `--geometrySchedule` je geografia v reportovom texte pevná a syntetická; geometrické behy pripájajú **iba** časový plán vybraného objektu z archivovanej 2026 OMM snímky.

| Beh | RSU TX / LAN doručené / UT proxy | SERVICE_UP TX / drop | Server včas / neskoro | Echo doručené RSU | Interpretácia |
| --- | ---: | ---: | ---: | ---: | --- |
| `under` 5/s | 50 / 50 / 50 | 50 / 0 | 50 / 0 | 50 | Koncová paketová integrácia prešla; celé reporty a ID sa zhodujú. |
| `over` 30/s | 300 / 300 / 300 | 92 / 208 | 5 / 87 | 92 | **Negatívny kapacitný test prešiel:** lokálna LAN zostala funkčná; preťaženie bolo v abstraktnom servisnom fronte. |
| `integrity_reject` 5/s, zmena bajtu `seq=7` v UT | 50 / 50 / 50 | 50 / 0 | 49 včas / 1 hash reject | 49 | Server odmietol report s pozmeneným aplikačným telom; ostatné bajty a ID prešli. |

Skript vyžaduje rovnosť množín sekvenčných ID na jednotlivých hopoch, rozklad `300 = 92 TX + 208 drop` pri preťažení, úplnú 300 B zhodu na všetkých nezmenených aplikačných hopoch, 330 B rámec v zvolených P2P trace a jedinú jednobajtovú odchýlku v úmyselnej negatívnej skúške. Znovu nezávisle počíta FNV-1a 64 z hex exportu. Pri preťažení netvrdí, že príčina každého oneskorenia je známa z RF; iba ns-3 queue-disc poskytol pozorovaný drop.

**Neúspešné vývojové behy:** prvý pokus použiť `-std=c++17` skončil pri kompilácii, pretože ns-3.48 vyžaduje C++20. Pri prvom callbacku `UtReceive` bolo poradie viazaných argumentov nekompatibilné s ns-3 callback API; opravené. Tieto pokusy negenerovali použiteľné experimentálne výsledky a nie sú zahrnuté v tabuľke.

## Voliteľný geometrický gate: presné pravidlo a skúšky hranice

Vstup je [`iridium-43253-bratislava-20261022.ns3-schedule.csv`](../../data/derived/orbit-geometry/iridium-43253-bratislava-20261022.ns3-schedule.csv) s [metadátami](../../data/derived/orbit-geometry/iridium-43253-bratislava-20261022.ns3-schedule.metadata.json). Simulačný čas `t=0` zodpovedá **2026-10-22 12:45:00 UTC**. Dvanásť intervalov `[start_offset_s,end_offset_s)` má krok 30 s. Podľa konzervatívneho pravidla dvoch koncových vzoriek je `[0,150)` povolené a `[150,360)` blokované; mimo exportovaného okna je stav tiež blokovaný. Pri intervale s neistým prechodom cez prah sa nevymýšľa presný čas crossing-u.

Pri voliteľnom `--geometrySchedule=geometry-schedule.csv` C++ načíta a skontroluje schému, spojitosť intervalov, kladný delay v povolených intervaloch a konzistenciu zdrojových identifikátorov v riadkoch. **C++ sám nevypočítava SHA-256 súboru.** Reprodukčný Python runner pred spustením overí SHA-256 CSV proti metadátam, súlad s hashom pôvodnej geometrickej CSV a metadát, odkazované hashe OMM/EOP a hash generátora; potom skopíruje presné bajty plánu do `results/certus100_e2e/geometry-schedule.csv` a uloží jeho hash do manifestu. Pôvodne vypočítaná geometria a plný pôvod snímky sú v [orbital geometry gate](orbit-geometry-gate.md). Toto overenie dokazuje pôvod *súboru*, nie funkčnosť operátora.

Pri `UtReceive` sa **pred vložením paketu do servisnej fronty** kontroluje stav intervalu v čase prijatia reportu na UT. Neoprávnený paket dostane `geometric_tx_block` so `seq`, ID a hashom. Povolený paket môže stále čakať vo fronte alebo byť na linke pri neskoršom vypnutí. Preto je na prijímacom P2P zariadení samostatný ns-3 `RateErrorModel` s `ErrorRate=0` pri povolenom a `ErrorRate=1` pri blokovanom intervale; jeho **`PhyRxDrop`** sa zapisuje ako `geometric_rx_drop`. Ide o deterministické testovacie hradlo na abstraktnom serializeri, **nie model rádiovej BER ani skutočného výpadku Iridia**. Linkový `Delay` sa v povolenom intervale nastaví na archivovaný `one_way_vacuum_delay_ns = max(r_i/c,r_i+1/c)`, konzervatívny čas **jediného úseku UT→satelit vo vákuu**. Neobsahuje ďalší satelitný hop, feeder, gateway, IP core, fronty mimo testovacieho serializeru ani celé RTT. Pri odoslaní si in-flight paket nesie delay platný pri začiatku jeho P2P prenosu; prijímacie hradlo sa vyhodnotí v čase jeho skutočného prijatia. Pri geometrii sa diagnostické echo vypne, pretože návratová geometria a cesta nie sú modelované.

Runner samostatne spúšťa tri hraničné prípady s jedným reportom (`--pps=1 --durationS=1`) a kontroluje presné `seq`, hash, celý 300 B paket, čas aj dôvod výsledku:

| Prípad (`--sourceStartS`) | Pozorovaný výsledok | Požadovaná interpretácia |
| --- | --- | --- |
| `geometry_before` (149,0 s) | Server dostal 1/1 o `149.127748195 s`; P2P čas od TX po RX = 120 ms serializácia + **7,745555 ms** archivovaný jeden r/c úsek. | Len syntetická služba s geometricky prípustným jedným legom. |
| `geometry_after` (150,0 s) | `geometric_tx_block` 1/1 v UT o `150.000002640 s`; žiadny `SERVICE_UP p2p_tx`, žiadny server RX. | Polootvorený interval od 150 s je blokovaný ešte pred frontou. |
| `geometry_inflight` (149,95 s) | `SERVICE_UP p2p_tx` o `149.950002640 s`; `geometric_rx_drop` z ns-3 `PhyRxDrop` o `150.077748195 s`; **žiadny** `p2p_rx` ani server RX. | Paket začatý pred hranicou sa nesmie falošne doručiť po vypnutí. |

Surové záznamy sú `results/certus100_e2e/geometry_*.csv`, aplikačné bajty v príslušných `geometry_*-payloads.csv`. Paket vložený do frontu pred koncom okna sa môže v tomto abstraktnom modeli ešte serializovať aj po konci okna a bude zahodený na príjme; príčina sa vykazuje ako geometrický gate, nie ako neznámy RF drop. Ide o **vzorkovanú geometriu jedného katalogizovaného satelitu**. Neznamená to aktuálnu prevádzkovú príslušnosť tohto objektu, pridelený beam, terminálový attach, gateway, RF link budget, pokrytie ani dostupnosť služby.

## Obmedzenia a ďalší krok

Nie je tu prijatá skutočná CAM/DENM; text incidentu je iba syntetický testovací vstup. Žiadne výsledné oneskorenie, PDR či echo časovanie sa nesmie uviesť ako zmerané alebo predikované správanie Certus 100. Po pripojení reálne dekódovanej lokálnej správy treba preniesť jej bajty alebo jednoznačný odvodený report a uchovať mapovanie `ETSI message/actionId ↔ event_id ↔ IP report`. Po geometrickom gate nasleduje validácia mobility UT, skutočne dostupných ISL/gateway a RF/servisná kalibrácia na merania rovnakej služby a terminálu.
