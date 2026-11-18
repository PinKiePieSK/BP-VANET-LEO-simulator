# Jednotný CAM → RSU → servisný IP backhaul → server: integračný fixture

Stav: **prešli tri nezávislé behy**. Tento míľnik spája lokálny CAM/GeoNetworking/BTP/802.11p paket s novým IP reportom z RSU, LAN, UT proxy a obmedzeným servisným uplinkom v **jednom ns-3.48 diskrétnom čase**. Je to overiteľná paketová integrácia, nie validovaný model kompletného ITS-G5 ani rádiového rozhrania Iridium.

## Hypotéza a význam scenára

Predstavovaný prípad: vozidlo odošle kooperatívnu polohovú správu CAM, RSU ju prijme a ako telemetriu postúpi cez terminál na vzdialený server. Hypotéza H1: pri 10 m LOS server dostane report obsahujúci **skutočne prijatých 41 B CAM** a jeho SHA-256; jeho ID, čas a bajty ostanú zachované cez oba IP úseky. Kontrola H0: pri zámerne extrémnych 100 km sa rámec vôbec nedekóduje, takže RSU report nevytvorí. Test integrity: po platnom prijatí v UT zmeníme jeden bajt CAM v reportovej aplikácii; server report odmietne aj napriek korektne vytvorenému novému UDP/IP paketu. Nie je to bezpečnostný útok ani odhad reálneho dosahu.

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
tools/run_integrated_cam_backhaul.sh
```

Skript overí pripnutú Vanetza `v26.06`, commit `fb6c551030dcc12b924299bf401e35e5fe814713`, zostaví cieľové knižnice s **najviac jednou** paralelnou úlohou a linkuje miestny ns-3 **3.48**, commit `d2add90b452d600cfb4859baed8e9ea633519447`. Vývojové OpenSSL hlavičky načíta len z lokálne rozbaleného presného balíka v ignorovanom `build/`; nevyžaduje sudo. Zdroj [`src/integrated-cam-backhaul.cc`](../../src/integrated-cam-backhaul.cc), reprodukčný skript [`tools/run_integrated_cam_backhaul.sh`](../../tools/run_integrated_cam_backhaul.sh) a nezávislý bajtový overovač [`tools/check_integrated_cam_backhaul.py`](../../tools/check_integrated_cam_backhaul.py) majú SHA-256 odtlačky v `results/integrated_cam_backhaul/manifest.json` spolu s verziami a parametrami. Každý beh je samostatný proces so semenom `314159`, run `1`.

## Algoritmus, formát a hranica paketov

1. **Auto:** pevný ETSI Release 2 CAM UPER fixture 41 B (`stationId=1001`) sa vloží do BTP-B na porte `2001` (4 B), Vanetza GN Single Hop Broadcast (40 B pri tomto behu) a odošle cez ns-3 `WifiNetDevice::Send` s EtherType `0x8947`. Nejde cez IPv4/UDP. Wi-Fi zariadenie pridá LLC/SNAP a 802.11 rámec. Úplný GN/BTP/CAM payload má 85 B; PCAP 802.11 rámec má 121 B v tomto ns-3 modeli. ASN.1, GN aj BTP dekóduje **Vanetza na RSU**, nie testovací proxy.
2. **RSU:** až po platnom BTP porte, CAM ASN.1 a `stationId` vytiahne **bajty prijatej** `Session..Application` časti Vanetza `UpPacket`. Pri `CohesivePacket` zostávajú tieto bajty po BTP parsovaní v Session, preto samostatná Application časť môže mať 0 B. RSU vytvorí nový 96 B binárny report a UDP datagram do UT cez 1 Gbit/s P2P LAN.
3. **UT:** prijme a validuje pôvodný report, potom ako **aplikačný proxy** vytvorí nový UDP/IP datagram s identickým 96 B payloadom smerom na server. V negatívnom teste zmení posledný bajt payloadu až po prijatí platného LAN reportu. P2P servisný úsek je nastavený na **22 000 bit/s** a nulové modelové šírenie.
4. **Server:** kontroluje magic/verziu, ID, čas, dĺžku, SHA-256 nad vloženými 41 B CAM, ASN.1 dekódovanie, `stationId=1001` a pri tomto izolovanom fixture aj presnú zhodu s pôvodným CAM testovacím vzorom. Tým sa overuje väzba bajtov v tomto experimente. SHA-256 **nie je podpis ani autentifikácia RSU**; pri reálnom nasadení by samotný hash nebránil falšovaniu celého reportu.

Report sa serializuje v sieťovom poradí bajtov:

| Offset | Dĺžka | Pole | Jednotka/zdroj |
|---:|---:|---|---|
| 0 | 4 B | ASCII `ICB1` | Verzia lokálneho výskumného reportu, nie štandard ETSI/Iridium. |
| 4 | 1 B | verzia `1` | Bez jednotky. |
| 5 | 8 B | event ID `ca000000000003e9` | Jedna fixture udalosť odvodená od `stationId=1001`; nová identita vzniká v RSU. |
| 13 | 8 B | čas prijatia CAM v RSU | µs od začiatku behu; v pozitívnom behu `100266`. |
| 21 | 2 B | dĺžka CAM `41` | Bajty. |
| 23 | 32 B | SHA-256 prijatého CAM | `9663a77649030ab76dfc515791ee4f15bf1bbe3f4b8d0592956b38a09470d22e`. |
| 55 | 41 B | pôvodný CAM UPER | Presne bajty prijaté a dekódované na RSU. |

Celý CAM fixture má hex `0202000003e93039005a4af9b60eaf87f100c80c80003a981e00384fc2b77e02c08a8333ffe1fffa00`. V CSV majú prvé CAM/radio záznamy event ID `0`, keďže RSU ešte report nevyrobila; od `RSU_REPORT_TX` sa prenáša uvedené ID. CSV `raw_hex` obsahuje presné aplikované bajty na každom bode. P2P `PhyTxBegin`/`PhyRxEnd` uchovávajú celý 126 B **PPP + IPv4 + UDP + report** rámec; overovač parsuje vrstvy podľa hlavičiek, kontroluje dĺžky, IPv4 aj UDP checksum a porovnáva celý 96 B UDP payload. Vyhľadanie magic v C++ P2P logu slúži iba na diagnostické označenie ID; **overenie payloadu** robí parser v Pythone a sockety v UT/serveri.

## Parametre a ich pôvod

| Parameter | Nastavenie a interpretácia |
|---|---|
| Lokálne rádio | Dva statické uzly 10 m alebo 100 km, `WIFI_STANDARD_80211p`, `AdhocWifiMac`, YansWifiPhy, kanál 180 / 5900 MHz / 10 MHz, fixne 6 Mbit/s, TX 20 dBm, nulové zisky, noise figure 7 dB, Friis LOS, predvolený `TableBasedErrorRateModel`, bez interferencie. [ETSI EN 302 663 V1.3.1](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf) uvádza 10 MHz/6 Mbit/s; 20 dBm je **testovací predpoklad**, nie kalibrovaný vozidlový terminál. Výber kanála a meranie RSS opisuje [predchádzajúca Wi-Fi sonda](gn-btp-ns3-wifi11p-probe.md). |
| LAN RSU–UT | P2P model 1 Gbit/s, 0 ms propagation; zvolený izolujúci predpoklad. |
| Servis UT–server | P2P model 22 kbit/s uplink, 0 ms propagation. Limit 22 kbit/s je verejne uvedené **maximum pre konkrétny modul [Iridium Certus 9770](https://www.iridium.com/products/iridium-certus-9770/)**, nie nameraný garantovaný bit rate každej služby/konštelácie. Segment je abstraktná kapacitná obálka: nemá satelit, service link RF, handover, gateway, frontu operátora ani orbitálny čas šírenia. |
| Čas a mobilita | Jeden diskrétny čas ns-3, CAM o `t=100000 µs`, stop 2 s; `SimulatorRuntime` má fixný ITS epoch `2026-10-22 12:00:00 UTC`. **SUMO ani orbitálna geometria nie sú napojené.** Georeferencovaný pilot začína o 12:45 UTC, teda tento fixture nie je synchronizovaný s jeho scenárom. GN zemepisný bod RSU pri 100 km sa odhaduje lineárne; presná rádiová vzdialenosť je euklidovská hodnota v ns-3. |

## Výsledky a artefakty

```text
CASE=positive WIFI_DISTANCE_M=10.00 PHY_OK=1 CAM_RX=1 RSU_REPORTS=1 UT_RX=1 SERVER_ACCEPT=1 SERVER_REJECT=0 SERVICE_RATE_BPS=22000
CASE=no_radio WIFI_DISTANCE_M=100000.00 PHY_OK=0 CAM_RX=0 RSU_REPORTS=0 UT_RX=0 SERVER_ACCEPT=0 SERVER_REJECT=0 SERVICE_RATE_BPS=22000
CASE=tamper WIFI_DISTANCE_M=10.00 PHY_OK=1 CAM_RX=1 RSU_REPORTS=1 UT_RX=1 SERVER_ACCEPT=0 SERVER_REJECT=1 SERVICE_RATE_BPS=22000
POSITIVE {"cam_rsu": 1, "pass": true, "radio_tx": 1, "server_accept": 1}
NO_RADIO {"cam_rsu": 0, "pass": true, "radio_tx": 1, "server_accept": 0}
TAMPER {"cam_rsu": 1, "pass": true, "radio_tx": 1, "server_reject": 1}
```

V pozitívnom behu bol CAM vytvorený o `100000 µs`, dekódovaný RSU o `100266 µs`, na UT doručený o `100267 µs` a na server o `146085 µs`. Modelové celkové oneskorenie je **46,085 ms**; servisný 126 B PPP rámec s rýchlosťou 22 kbit/s tvorí približne **45,818 ms**. Tieto časy nemožno interpretovať ako reálne satelitné oneskorenie, pretože servisný link má 0 ms propagation a neobsahuje geometriu ani operátorské postupy. Príjem 1/1 nedokazuje PDR ani kapacitu. PHY pri 10 m uviedlo RSS `−47,86 dBm`, šum `−96,98 dBm`, čo je zhodné s kontrolou Friis v kóde v tolerancii 0,2 dB.

Surové `positive.csv`, `no_radio.csv`, `tamper.csv`, `verification.json`, `manifest.json` a 802.11 PCAP sú v `results/integrated_cam_backhaul/`. Overovač kontroluje v PCAP skutočný 802.11 data broadcast, LLC/SNAP `0x8947`, 85 B GN/BTP/CAM, BTP port `2001` a presných 41 B CAM. V `no_radio` existuje len vysielací PCAP; prijímací PCAP nevznikol. Táto negatívna skúška overuje príčinnú väzbu rádio→RSU report; `tamper` overuje kontrolu zmeny obsahu pri serveri. Neúspešný integračný pokus s extrakciou iba `OsiLayer::Application` dal na RSU 0 B napriek platnému CAM; oprava extrahuje `Session..Application` podľa hranice `CohesivePacket` a je zahrnutá v kóde.

## Čo tento výsledok ešte netvrdí

`AdhocWifiMac` je podľa [oficiálnej dokumentácie ns-3 WAVE](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) podobný staršiemu `OcbWifiMac`, nie identický. Miestne ns-3.48 neobsahuje `src/wave`, takže chýba validované `dot11OCBActivated`, plné EDCA/DCC a bezpečnostný profil ITS-G5. Auto a RSU sú statické; CAM je pevný fixture, nie správa generovaná z SUMO ani hazardná DENM. Servis je **22 kbit/s IP kapacitný segment**, nie Iridium satelit/RF, pozemná brána, medzisatelitné spojenie či reálna latencia. V tomto behu neexistuje identita konkrétneho terminálu, geometrická viditeľnosť, beam alebo queue operátora. Ďalší krok je pripojiť pohyb a geometriu k spoločnému času, samostatne validovať rádio/OCB a nahradiť 0 ms servisnú propagáciu zdokumentovanou, meraniami obmedzenou službou.
