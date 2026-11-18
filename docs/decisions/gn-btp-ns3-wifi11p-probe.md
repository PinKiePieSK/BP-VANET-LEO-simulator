# Vanetza GN/BTP/CAM cez ns-3.48 802.11p rádio: izolačná skúška

Stav: **prešiel pozitívny 10 m a negatívny 100 km beh**. Táto skúška nadväzuje na [CSMA adaptér](gn-btp-ns3-probe.md); používa skutočný ns-3 `WifiNetDevice`, `AdhocWifiMac`, 802.11p PHY a bezdrôtový kanál. Nedokazuje úplnú zhodu s ITS-G5 ani OCB.

## Účel, hypotéza a príkaz

Hypotéza: pri dobrom rádiovom signále sa presný 41-bajtový CAM UPER fixture prenesie cez Vanetza BTP-B/GeoNetworking, LLC/SNAP s EtherType `0x8947`, model 802.11p PHY/MAC a na druhom uzle sa dekóduje ako CAM `stationId=1001`. Pri zámerne veľmi veľkom odstupe sa rámec nebude dekódovať. Východisko tvorí [rozhodnutie o ITS stacku](its-stack.md); táto sonda má jeden paket a slúži ako integračná a fyzikálna kontrola.

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
tools/run_vanetza_ns3_wifi11p_probe.sh
```

Skript znovu zostaví pripnutú Vanetza `v26.06` (`fb6c551030dcc12b924299bf401e35e5fe814713`) s najviac dvoma úlohami a linkuje miestny ns-3 **3.48**. OpenSSL vývojové hlavičky sa rozbalia len v ignorovanom `build/`, ako opisuje [predchádzajúca sonda](gn-btp-ns3-probe.md). Systémové balíky sa nemenia. Zdroj sondy: [`tools/vanetza_ns3_wifi11p_probe.cpp`](../../tools/vanetza_ns3_wifi11p_probe.cpp); PCAP verifier: [`tools/check_vanetza_ns3_wifi11p_pcap.py`](../../tools/check_vanetza_ns3_wifi11p_pcap.py). Skript odstráni a znova vytvorí len svoje štyri možné `build/vanetza_wifi11p_*.pcap` záznamy. Proces končí nenulovým kódom pri neúspechu ktorejkoľvek skúšky.

## Implementovaná cesta a parametre

`Vanetza Release 2 CAM UPER (41 B) → BTP-B port 2001 (4 B) → GN SHB (40 B v tomto behu) → ns-3 WifiNetDevice::Send (85 B, EtherType 0x8947) → LLC/SNAP → 802.11 data frame → YansWifiPhy/YansWifiChannel → LLC/SNAP 0x8947 → Vanetza GN/BTP router → CAM UPER dekóder`. Nevyužíva IPv4 ani UDP. `WifiNetDevice::DoSend` v miestnom ns-3 pridáva `LlcSnapHeader` s požadovaným EtherType. Prijímač porovná port, typ BTP-B, validitu CAM a `stationId`. Odosielanie a časovače Vanetza sú v jednom diskrétnom čase ns-3.

| Parameter | Nastavenie a význam |
|---|---|
| Dva uzly | Statické polohy `(0,0,0)` a `(10,0,0)` m alebo `(100000,0,0)` m v ns-3; 1 broadcast CAM v čase 100 ms; stop 1 s. |
| Reprodukovateľnosť | `RngSeedManager::SetSeed(314159)`, run `1`; pevná CAM binárna vzorka. |
| PHY/MAC | `WIFI_STANDARD_80211p`, `AdhocWifiMac`, `YansWifiPhy`, 10 MHz kanál 180, stred **5900 MHz**, fixný `OfdmRate6MbpsBW10MHz` aj pre broadcast. 6 Mbit/s a 10 MHz sú v [ETSI EN 302 663 V1.3.1, čl. 4.2](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf); kanál 180 / 5900 MHz zodpovedá G5-CCH v [ETSI EN 302 663 V1.2.1, tabuľka 2](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.02.01_60/en_302663v010201p.pdf). |
| Link budget | TX 20 dBm, TX/RX zisk 0 dB, receiver noise figure 7 dB. **20 dBm je zvolený testovací predpoklad**, nie kalibrácia konkrétneho vozidlového rádia. |
| Šírenie a chyby | `FriisPropagationLossModel` na 5,90 GHz, `ConstantSpeedPropagationDelayModel`, predvolený ns-3 `TableBasedErrorRateModel`; bez tienenia, odrazov, fadingu a interferencie. Pozri [ns-3 Wi-Fi dokumentáciu](https://www.nsnam.org/docs/models/html/wifi-user.html) a [ns-3 model šírenia](https://www.nsnam.org/docs/models/html/propagation.html). |
| GN poloha | Východisko `48.1486° N, 17.1077° E`; zemepisná dĺžka prijímača je **lineárny približný prepočet** z ns-3 metrov cez `111195·cos(latitude)` m/°. Pri 100 km nejde o geodeticky presnú WGS84 vzdialenosť. Negatívny test závisí od presnej euklidovskej vzdialenosti v ns-3, nie od tohto približného GN údaja. |

## Výsledok a nezávislé kontroly

```text
GN_L2_TX_BYTES=85 TX_TIME_US=100000
CAM_RX_STATION=1001 RX_TIME_US=100266
RADIO_11P_DISTANCE_M=10.00 PHY_OK=1 L2_RX=1 CAM_RX=1
PHY_RX_SIGNAL_DBM=-47.86 PHY_RX_NOISE_DBM=-96.98 PHY_RX_SNR_DB=49.11
FRIIS_EXPECTED_RSS_DBM=-47.86 RSS_DELTA_DB=0.00
GN_BTP_CAM_OVER_NS3_WIFI11P=pass DELAY_US=266
GN_L2_TX_BYTES=85 TX_TIME_US=100000
RADIO_11P_DISTANCE_M=100000.00 PHY_OK=0 L2_RX=0 CAM_RX=0
GN_BTP_CAM_OVER_NS3_WIFI11P_DISTANT_LOSS=pass
WIFI11P_PCAP_LLC_GN_BTP_CAM=pass FRAME_BYTES=121 GN_BTP_CAM_BYTES=85 CAM_BYTES=41
```

`MonitorSnifferRx` na prijímači dal modelovaný signál −47,86 dBm a šum −96,98 dBm; rozdiel 49,11 dB je SNR. Nezávislý výpočet Friis pre 10 m, 5,90 GHz, 20 dBm a nulové zisky dáva asi **−47,86 dBm**. Sonda porovnáva výpočet s trace s toleranciou 0,2 dB. V 100 km kontrolnom variante je očakávaná voľnopriestorová úroveň asi −127,86 dBm, no PHY trace úspešného prijatia tam nevznikol; nekonštruujeme z toho nameranú hodnotu RSS. Týchto 1/1 a 0/1 rámcov nie je štatistický odhad PDR alebo dosahu.

Surové 802.11 PCAP sú v `build/vanetza_wifi11p_10m-{0,1}-0.pcap` a `build/vanetza_wifi11p_100km-0-0.pcap`. Python verifier nezávisle číta DLT 105, 802.11 data/broadcast hlavičku, LLC/SNAP `aa aa 03 00 00 00 89 47`, presne 85 B GN+BTP+CAM, BTP port `07 d1 00 00` a presných 41 B CAM. Porovnáva celý zachytený vyslaný a prijatý 121 B rámec; pri 100 km nevznikol prijímací PCAP. `tcpdump -nn -e -r build/vanetza_wifi11p_10m-1-0.pcap -xx` tiež ukazuje EtherType GeoNet `0x8947`, ale jeho následný automatický rozbor GN/BTP nemusí sedieť s profilom Vanetza; skutočné dekódovanie GN/BTP/CAM overuje príjem cez Vanetza a bajtová kontrola v skripte.

## Zaznamenaný neúspešný pokus a hranica vierohodnosti

Prvý pokus o Radiotap PCAP (`DLT_IEEE802_11_RADIO`) v ns-3.48 na 10 MHz pri vysielaní skončil na `NS_ASSERT primaryChannelWidth <= GetTotalWidth()` v `WifiPhyOperatingChannel::GetPrimaryChannelIndex`. `WifiPhyHelper::PcapSniffTxEvent` totiž volá `GetPrimary20Index()` aj pre 10 MHz kanál. Namiesto zmeny modelu rádia sa použil surový `DLT_IEEE802_11` PCAP; finálny beh aj nezávislý parser prešli. Vývojový záznam je v `build/vanetza_ns3_wifi11p_probe.log` len z posledného behu; pôvodná asercia je overená zdrojom ns-3.48 `src/wifi/helper/wifi-helper.cc` a `src/wifi/model/wifi-phy-operating-channel.cc`.

`AdhocWifiMac` sa podľa [oficiálnej staršej dokumentácie ns-3 WAVE](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) správa **podobne** ako `OcbWifiMac`, ale nie je identický: OCB pridával osobitné spracovanie BSSID, rámcov a parametrov EDCA. [ETSI EN 302 663 V1.3.1, čl. 4.3](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf) vyžaduje `dot11OCBActivated` a DCC pravidlá; tieto sonda neimplementuje. Miestne ns-3.48 nemá `src/wave`/`OcbWifiMac`. Sonda má statické uzly, jeden bezkolízny LOS paket, vypnutú GN bezpečnosť/beaconing a pevný CAM fixture bez generovania z mobility; nemožno z nej vyvodzovať interoperabilitu reálneho ITS-G5 rádia, správanie v NLOS, dosah v teréne, kapacitu alebo end-to-end spoľahlivosť. Ďalšia brána je OCB alebo validovaná Artery/INET prístupová vrstva, CAM/DENM z pohybu a oddelená rádiová kalibrácia/validácia.
