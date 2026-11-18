# Editovateľný v2 scenár: jeden OCB a geometrický paketový beh

**Stav 22. 10. 2026:** reprodukovateľný obmedzený proof of concept, kladný a zámerne blokovaný kontrolný beh. Jediný čas udalostí je ns-3.38; pohyb štyroch rádiových uzlov vzniká z FCD SUMO. Objekt Globalstar a Nemea slúžia ako **archívny geometrický plán** pre bránu a jednosmerné šírenie po dvoch abstraktných P2P hopoch. Tento experiment **nemodeluje Globalstar rádio, terminál, riadenie siete ani prevádzkovú službu**.

## Hypotéza a vzťah ku skutočnému svetu

Hypotéza v hraniciach implementácie: Ak je `car0` v dosahu `car1`, `car3` a `rsu0`, všetci traja cez 802.11p OCB prijmú tie isté CAM. RSU potom z prijatého CAM vytvorí ICB1 report. Keď geometrický plán povoľuje RSU aj gateway proxy, report dorazí na server cez IPv4/UDP P2P. Zámerne blokovaná gateway **nesmie zmeniť pozemné CAM prijatie**, ale musí zabrániť odoslaniu všetkých reportov.

Reálny význam skúmaného variantu je hlásenie z cestnej infraštruktúry do vzdialeného servera pri chýbajúcom vhodnom pozemnom backhaule. `rsu0` v editovateľnom scenári má `its_g5` a `ip_backhaul`, **nemá deklarovaný satelitný terminál**. V tomto experimente preto ide o hypoteticky doplnený UT. Spoločná viditeľnosť jedného objektu ID 37741 voči WGS84 polohe RSU a centru Nemea je iba kandidátska geometria; anténa Nemea, jej aktuálny stav a skutočný operátorský výber nie sú známe. Zdroj a výpočet sú popísané v [geometrickom pláne](editable-v2-globalstar-geometry-schedule.md). Globalstar verejne opisuje transparentný priechod cez vhodnú pozemnú bránu; náš **LEO uzol je umelý IPv4 router na pozorovanie paketových hopov**, nie vlastnosť satelitu.

## Architektúra a presná hranica modelu

```text
SUMO FCD → car0 Vanetza CAM/GN/BTP → ns-3.38 802.11p OCB broadcast
                                   ├→ car1: dekódovaný CAM
                                   ├→ car3: dekódovaný CAM
                                   └→ rsu0: dekódovaný CAM → 96 B ICB1
                                         → P2P RSU→UT→LEO IPv4 proxy→Nemea proxy→server
```

`src/editable-v2-ocb-geometry-e2e.cc` používa štyri samostatné rádiové ns-3 uzly. Konštantná poloha sa mení šesťkrát podľa FCD pri `t=20,0; 20,5; …; 22,5 s`. `car0` zakóduje platný 41 B ETSI CAM UPER s polohou, rýchlosťou a smerom z waypointu; Vanetza pridá 4 B BTP-B a GeoNetworking SHB na 85 B sieťový payload. Použije `Wifi80211pHelper` a `QosWaveMacHelper`, kontroluje `OcbWifiMac`, 5900 MHz, 10 MHz, dátovú rýchlosť 6 Mbps BW10, vysielací výkon 20 dBm, šumové číslo 7 dB a Friis s konštantnou rýchlosťou šírenia. Tieto rádiové parametre sú **výskumné nastavenia**, nie kalibrácia konkrétnej lokality alebo vozidla. Vanetza GN zabezpečenie a beaconing sú vypnuté; DCC, urban canyon, interferencia a reálne antény tu nie sú kalibrované. Poloha WGS84 vzniká z explicitnej lokálnej ENU kotvy, nie geodetickým zameraním cesty.

Každá prijímacia stanica dekóduje vlastný CAM a overí polia voči FCD waypointu. Len `rsu0` vytvára report **až z prijatých UPER bajtov**, nikdy z pripraveného report súboru. Formát ICB1 (v bajtoch): ASCII `ICB1` (4), verzia (1), big endian ID udalosti (8), čas prijatia RSU v µs od začiatku (8), big endian dĺžka CAM (2), SHA-256 CAM (32), presné CAM UPER (41). Spolu 96 B. Server overí magic/verziu, dĺžku, hash, čas, ID a CAM polia. Typ reportu je experimentálna aplikácia, nie štandard ani formát Globalstar.

`tools/prepare_editable_v2_globalstar_geometry_schedule.py` najprv vypočíta šesť UTC vzoriek a v každej uvedie eleváciu a jednosmerné vákuové oneskorenie RSU→objekt a objekt→Nemea proxy. `src` číta presnú 9-stĺpcovú schému `time_us,utc,catalog_id,omm_sha256,ut_elevation_deg,gw_elevation_deg,ut_delay_ns,gw_delay_ns,enabled`; kontroluje časy, UTC, ID, hash, nenulové oneskorenia a masku ≥10°. Runner navyše vyžaduje zhodu SHA-256 CSV s metadata, scenárom, waypointmi a hashom generátora. Chýbajúci alebo nezhodný plán zastaví beh.

Keď je pri **prijatom CAM** `enabled=1`, RSU nastaví nanosekundové `Delay` na abstraktných `UT→LEO` a `LEO→GW` P2P kanáloch a odošle 96 B UDP datagram. `RSU→UT` a `GW→server` majú nastavené nulové šírenie; všetky štyri P2P linky majú **zvolených 1 Gbps**. ns-3 zariadenia majú vlastné neoverené fronty; **nemáme kalibrované servisné fronty**, RF, retransmisie, terminálový MAC, beam, pozemnú core sieť ani spracovanie operátora. IP forwarding v umelom LEO proxy umožňuje získať PPP/IP/UDP stopu pre každý hop a **nie je tvrdením o onboard správaní Globalstar**. Brána sa vyhodnocuje pri vzorke CAM/RSU; nezohľadňuje zmenu viditeľnosti počas letu paketu.

## Reprodukcia, výstupy a kontrola

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_editable_v2_ocb_geometry_e2e.py
cat results/editable_v2_ocb_geometry_e2e/verification.json
```

Runner vyžaduje pripnuté SUMO, Vanetza, ns-3.38 WAVE/point-to-point, OpenSSL, archív a `.venv`; obnoví SUMO FCD, waypointy a oba plány, zostaví jeden C++17 binárny súbor a spustí kladný i blokovaný beh so semenom **314159**, run **1**. Nerobí paralelný build. Vstupom je `data/inputs/editable-road-v2/packet-subset.json`; predvolené výstupy sú v `results/editable_v2_ocb_geometry_e2e/`. Voliteľné CLI: `--scenario`, `--snapshot`, `--output`, ale táto sonda zámerne vyžaduje `car0/car1/car3/rsu0`, šesť časov, danú UTC epochu a ID 37741. Na rozšírenie na ľubovoľné editácie treba samostatné overenie parametrov.

V každom variante sú `schedule.csv`, `schedule.metadata.json`, `waypoints.csv`, `trace.csv`, `delivery.csv`, `ocb_mobility.csv`, `ocb_decoded.csv`, štyri surové `ocb-*-0.pcap`, `run.log` a `schedule.log`. `trace.csv` má každý stage, node ID, event ID, čas µs, počet bajtov a raw hex. Pri P2P stupňoch ide o skutočné 126 B PPP/IP/UDP rámce. `verification.json` a `run-manifest.json` uchovávajú hashe a výsledky; `build.log` zachováva kompiláciu. Žiadny report ani PCAP sa nepreberá z input fixture.

Checker [check_editable_v2_ocb_geometry_e2e.py](../../tools/check_editable_v2_ocb_geometry_e2e.py) overuje pre všetkých šesť ID: CAM UPER proti prijatiu u každého uzla, GN LPV polohu/rýchlosť/smer z 123 B QoS OCB PCAP proti FCD (tolerancia 1 jednotka celočíselnej reprezentácie), BSSID `ff:ff:ff:ff:ff:ff`, bytes reportu proti skutočne prijatému CAM, 4× P2P TX/RX bajtovú zhodu v rámci linky, UDP payload a modelový čas šírenia/serializácie ±2 µs. Null FCS v ns-3 PCAP nie je meranie FCS.

## Pozorované výsledky a neúspešné behy

Výsledok jedného overeného opakovania 22. 10. 2026: 6/6 CAM TX, `car1` 6/6, `car3` 6/6, `rsu0` 6/6, bez GN dropov v oboch variantoch. RSU vytvorila 6/6 ICB1 v oboch. Kladný plán poslal 6/6 a server overil 6/6; synteticky blokovaná gateway mala 6/6 explicitných blokov a 0/6 UDP reportov na serveri. Priemerný **modelový** čas od `RSU_REPORT_TX` po `SERVER_ACCEPT` v kladnom behu bol **18 404,5 µs**; šesť jednotlivých hodnôt `18 368, 18 383, 18 397, 18 412, 18 426, 18 441 µs` je v surovom overení. Rast sleduje rast predpočítaných vzdialeností, nie meranú latenciu služby.

**Záznam neúspešných/odmietnutých pokusov:**

| Pokus | Pozorovanie | Interpretácia |
| --- | --- | --- |
| Prvé manuálne spustenie kladného C++ behu | Prešlo: 6 CAM TX, 18 pozemných dekódovaní, 6 prijatých reportov. | Nebola potrebná úprava rádio/report vetvy po kompilácii. |
| Finálny runner, kladný plán | Prešiel celý checker: 6/6 reportov na serveri. | Funkčnosť v uvedenom obmedzenom modeli. |
| Finálny runner, synteticky blokovaná gateway | 6/6 CAM na RSU, 6 explicitných `GEOMETRY_BLOCK`, 0 UDP reportov. | Očakávaná negatívna kontrola, nie chyba simulátora. |
| Jednorazový zámerný zásah do kópie CSV: prvé `catalog_id` 37741→37742 bez zmeny metadata | `check_schedule` vyvolal `AssertionError` ešte pred ns-3. | Hashovo nezhodný plán je odmietnutý. Originálny archív ani výsledky sa nemenili. |

Pri vykonaní s optimalizovaným Python `-O` sa runner/checker odmietnu spustiť, aby sa nevypli kontrolné `assert` výroky. Nezaznamenali sme iné zlyhanie finálneho behu; `build.log`, `run.log` a surové súbory sú uchované. Tieto dva varianty s jedným pevným semenom **nestačia na štatistické porovnanie konštelácií, technológií ani efektívnosti**. Ďalší experiment musí pridať kalibrovaný RF/terminálový model, relevantné korektné gateway lokality, stochastické semená, dlhšie časové okno a handover pred tvrdením o reálnej sieti.

**Skúška editácie RSU:** z identického JSON sa v kópii `/tmp/editable-v2-rsu-shift.json` zmenilo iba `rsu0.x_m` z 490 na 495 m. Príkaz `.venv/bin/python tools/run_editable_v2_ocb_geometry_e2e.py --scenario /tmp/editable-v2-rsu-shift.json --output /tmp/editable-v2-rsu-shift-e2e` prešiel. Prepočítaná WGS84 dĺžka RSU sa zmenila z `17,103533981°` na `17,103601175°`, hash kladného geometrického plánu z `7d45936c…` na `03d5e8f4…` a prvý user-link čas z `9 276 983` na `9 276 967 ns`; checker aj v tejto variante potvrdil 6/6 správ serveru a 0/6 v blokovanej kontrole. Toto overuje prenos **jednej editácie polohy RSU** z návrhu cez georeferenciu do paketového behu, nie všeobecnú podporu ľubovoľných uzlov alebo trás.

## Pôvod parametrov

- SUMO FCD, seed, uzly, ENU kotva a UTC: [v2 packet subset](../../data/inputs/editable-road-v2/packet-subset.json) a jeho [metodika](editable-v2-cam-radio.md).
- Globalstar OMM, výber ID, maska, Nemea proxy, EOP, hash a oneskorenia: [geometrický plán](editable-v2-globalstar-geometry-schedule.md). Maska 10° a proxy sú výskumné predpoklady.
- ns-3.38 WAVE OCB: [zdrojový modul](../../vendor/ns-3.38-ocb-eval/src/wave/model/ocb-wifi-mac.cc); presný commit je v manifestoch. Model rádio nie je validovaný pre konkrétnu ulicu.
- Vanetza CAM/GN/BTP: lokálny pripnutý commit a závislosti v `run-manifest.json`; formáty a vlastné reportové polia sú v `src/editable-v2-ocb-geometry-e2e.cc`.
