# OCB/802.11p pilot v návrhovom editore

**22. 10. 2026 UTC; stav: overený izolovaný pozemný pilot.** Hypotéza: ten istý SUMO→Vanetza CAM/GN/BTP tok možno na historickom oficiálnom `OcbWifiMac` doručiť viacerým autám a RSU bez zmeny aplikačných bajtov; MAC hlavička sa musí od doterajšieho `AdhocWifiMac` líšiť wildcard BSSID. Kontrola bez kontaktu používa explicitný umelý 1 m `RangePropagationLossModel`. Nehodnotí skutočný geografický dosah.

## Reprodukcia a verzie

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
bash tools/setup_ns3_ocb38.sh
.venv/bin/python tools/run_editable_v2_ocb38_probe.py \
  data/inputs/editable-road-v2/packet-subset.json \
  --output results/editable_v2_ocb38_probe
.venv/bin/python tools/audit_its_g5_mac_gap.py
python3 tools/test_editable_v2_cam_radio.py
```

`setup_ns3_ocb38.sh` pripne oficiálny tag `ns-3.38` na commit `392e36833ce3c7e0ecde4188043f76345402d5a7`, použije jediný zaznamenaný [patch](../../patches/ns3.38-gcc13-cstdint.patch) pre GCC 13.3 (`<cstdint>` v hlavičke) a zostavuje najviac dve úlohy. Natívny `wave-simple-80211p` vypísal `Received one packet!`. Modul WAVE bol v [ns-3.39 odstránený](https://gitlab.com/nsnam/ns-3-dev/-/blob/ns-3.39/RELEASE_NOTES.md), preto je tento proces oddelený od pripnutého ns-3.48 a SNS-3. Ostatné verzie a vstupy sú uvedené v [rádiovom experimente v2](editable-v2-cam-radio.md) a v manifestoch výstupu; Vanetza je `v26.06`, SUMO je systémový pripnutý balík. Skript adaptuje pôvodný C++ zdroj do `build/editable-v2-cam-ocb38.cc`: `Wifi80211pHelper`, `NqosWaveMacHelper`, runtime kontrola typu `ns3::OcbWifiMac` a typy šírky/frekvencie podľa API ns-3.38. SHA-256 pôvodného aj odvodeného zdroja a binárky sú v `run-manifest.json`.

## Model a predpoklady

- Zdroj `car0` vyšle šesť CAM pri `t=20,0–22,5 s` po 0,5 s; `car1`, `car3` a `rsu0` sú príjemcovia. SUMO poskytuje FCD polohy/rýchlosti/smer; lokálna cesta má *syntetickú* WGS84 registráciu, nie geodeticky overenú polohu ulice.
- Vanetza serializuje 41 B CAM UPER podľa [ETSI TS 103 900 V2.3.1 Release 2](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf) a 85 B GeoNetworking SHB + BTP-B port 2001 + CAM. Polia polohy, rýchlosti a smeru pochádzajú zo SUMO FCD; identita stanice a ostatné chýbajúce veličiny sú zdokumentované predpoklady, nie merania reálneho vozidla. GN PositionFix má rovnaké FCD súradnice, rýchlosť a kurz; jeho 15-bitová rýchlosť sa pri prevode môže líšiť o 1 cm/s od CAM. ns-3.38 vysiela EtherType `0x8947` cez 802.11p, kanál 180/10 MHz/5,9 GHz, rýchlosť 6 Mbit/s, pevný výkon 20 dBm, 0 dB anténne zisky, 7 dB noise figure, Friis a konštantná rýchlosť šírenia. `NqosWaveMacHelper` nedokazuje priority EDCA; DCC a ETSI bezpečnostná vrstva nie sú zapnuté. [Dokumentácia ns-3 WAVE](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) odlišuje OCB MAC od ad hoc MAC; [ETSI EN 302 663](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf) určuje kontext ITS-G5 prístupovej vrstvy.
- Simulačné semeno je vo vstupnom JSON; `RngSeedManager::SetRun(1)`. PCAP je DLT_IEEE802_11. FCS štyri nuly sú zástupný zápis ns-3, nie vypočítané CRC. Časové polia raw trace sú v mikrosekundách; výpočty nižšie sú v milisekundách.

## Výsledok a dôkaz

Pozitívny beh: 6 TX, `car1=6`, `car3=6`, `rsu0=6` dekódovaných CAM (18/18 príjmov). Negatívna kontrola: 6 TX a `0/18` RX; každý prijímač má 24-bajtový prázdny PCAP header, čo checker správne považuje za nulový počet rámcov. V pozitívnom OCB behu je **24/24** zaznamenaných dátových rámcov s `Addr3/BSSID=ff:ff:ff:ff:ff:ff`, žiadny management rámec; runtime typ každého MAC je `ns3::OcbWifiMac`. V pripnutom ns-3.48 Adhoc porovnaní bolo 24 rámcov s BSSID `00:00:00:00:00:01`. Všetkých šesť identít CAM má rovnaký 41 B CAM a 85 B GN/BTP/CAM obsah v oboch profiloch. Pozorované oneskorenie od CAM vytvorenia po prijatie v tejto jednoduchej sieti je 0,266 ms na každý doručený príjem; rovnaké v oboch profiloch. Zhodné PDR/čas v tomto malom bezkolíznom pilote **nie sú** dôkazom ekvivalentného správania pri prevádzke.

Overovač číta FCD waypoint hash, raw trace, rozloženie GN/BTP/CAM, PCAP a každé dekódované `stationId`, čas a WGS84/speed/heading pole. K jednému ID priradí aj presný 121 B vyslaný 802.11 rámec z PCAP: 24 B MAC hlavička, 8 B LLC/SNAP, 85 B GN/BTP/CAM a 4 B nulový FCS placeholder. [`dissect_ocb_cam_frame.py`](../../tools/dissect_ocb_cam_frame.py) vytvorí 36 neprerušovaných polí s presnými offsetmi, od Frame Control až po FCS placeholder. Overí EtherType, BTP port, ITS PDU hlavičku aj GN timestamp, WGS84 polohu, rýchlosť a smer oproti CAM vstupu. Zvyšné CAM telo je jedno 33 B bitovo balené UPER pole; jeho sémantické polia sa zvlášť porovnávajú so spätným Vanetza dekódovaním, bez vymyslených bajtových hraníc. `run-manifest.json` nesie SHA-256 vstupu, zdrojov a verifikácie; `verification.json` nesie SHA-256 PCAP a trace. HTTP editor používa ten istý runner a vracia paketové udalosti len po kontrole hashov. Prehliadač `radio-packet.html?run=<id>` ukazuje klikateľný strom polí, zvýraznený hex rozsah, zrozumiteľné údaje vozidla a časy prijatia. Odkazy na pôvodné vysielacie a prijímacie PCAP umožňujú samostatnú kontrolu vo Wiresharku; server pre každý súbor kontroluje SHA-256 z verifikácie.

Prvý build starej verzie zlyhal na chýbajúcom `<cstdint>` pri GCC 13; vznikol zaznamenaný patch. Prvá kompilácia adaptéra zlyhala na C++20 a novom `MHz_u` API; izolovaný adaptér teraz používa C++17 a staré celočíselné API. Prvý checker predpokladal, že nulový RX nemá PCAP súbor; starý WAVE vytvára prázdny PCAP header, preto checker akceptuje iba chýbajúci alebo presne prázdny záznam. Neúspešné pokusy sa nepoužili ako výsledok.

## Hranice interpretácie a ďalší krok

OCB je otestované iba na **pozemnej** vetve a v oddelenom ns-3.38 procese. Súčasný integrovaný satelitný packet probe a SNS-3 používajú ns-3.48, preto nemožno z týchto dvoch samostatných behov počítať jednu E2E latenciu auto→RSU→satelit. Treba validovaný port OCB do spoločného event clocku alebo kontrolovaný synchronizačný adaptér. Pred porovnávaním scenárov treba doplniť QoS/EDCA, DCC, súbežné vysielanie, kolízie, obsadenie kanála, LOS/NLOS a kalibrované parametre; satelitný RF/operátorský servis potrebuje vlastnú validáciu. [Rozhodovací podklad](../decisions/its-g5-ocb-options.md) vymenúva akceptačné brány.
