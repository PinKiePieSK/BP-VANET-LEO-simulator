# GN/BTP/CAM na spoločnom čase Vanetza a ns-3

**Izolovaná integračná skúška, 22. 10. 2026.** Nadväzuje na [rozhodnutie o ITS stacku](its-stack.md) a [hlbokú analýzu](../hlbkova-analyza-komunikacie.md). Cieľ je preveriť technicky najrizikovejšie rozhranie Vanetza ↔ ns-3 bez zásahu do súčasného SNS-3 pilotu. Skúška používa dva skutočné ns-3 `CsmaNetDevice` uzly. CSMA je **káblový dôkaz prenosu rámca**, nie model ITS-G5/OCB rádia.

## Trasa skúšobného paketu

```text
pripnutý ETSI CAM Release 2 UPER (41 B)
  → Vanetza BTP-B hlavička, destination port 2001 (4 B)
  → Vanetza GeoNetworking SHB, hop limit 1, bez bezpečnostného obalu
  → ns-3 NetDevice::Send, EtherType 0x8947
  → ns-3 CSMA 6 Mbit/s, modelové oneskorenie kanála 10 µs
  → ns-3 ReceiveCallback, surové bajty a MAC odosielateľa
  → Vanetza Router::indicate → BTP PortDispatcher → ASN.1 Release 2 dekóder CAM
```

Vzorka CAM používa bajty z [codec testu](../../tools/its_codec_probe.cpp), stanica `1001`; odosielateľ ich pred vyslaním znovu dekóduje a kontroluje ASN.1 obmedzenia. Je to pevný testovací obsah, nie CAM generovaná z pohybu SUMO. GN a BTP hlavičky vytvára Vanetza, kým L2 rámec prenáša ns-3. `SimulatorRuntime` prekladá Vanetza `Clock::time_point` na `ns3::Simulator::Schedule` v mikrosekundách; na oboch uzloch používa rovnaký začiatok `2026-10-22 12:00:00` ITS času. Toto **nepreveruje** UTC/TAI konverziu podľa prestupných sekúnd pre skutočné experimenty.

## Prostredie a reprodukcia

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
tools/run_vanetza_ns3_probe.sh
```

Skript overí tag/commit Vanetza `v26.06` / `fb6c551030dcc12b924299bf401e35e5fe814713`, zostaví GN/BTP a ASN.1 Release 2 s najviac dvoma úlohami a pripojí ich k miestnemu `ns-3.48`. Tento ns-3 používa C++20. Na zostavenie Vanetza security závislosti sú potrebné OpenSSL hlavičky: skript stiahne presný `libssl-dev 3.0.13-0ubuntu3.16` a rozbalí ho **len** do ignorovaného `build/`, overí SHA-256 a knižnicu páruje s už nainštalovaným runtime `libssl3t64` rovnakej verzie. Symlink v `/tmp` obchádza medzeru v pracovnej ceste pri CMake `-I` prepínači. Systémový balík sa neinštaluje. GN bezpečnosť je v simulácii vypnutá; prítomnosť OpenSSL pri zostavení neznamená podpisovanie rámcov.

## Význam výsledku a ďalšia brána

Táto skúška potvrdila spoločný diskrétny čas a prenos GN/BTP/CAM cez nesatelitný ns-3 NetDevice. Návrh rádiovej vrstvy musí osobitne prejsť OCB/ITS-G5, PHY, rušením, frontami, DCC spätnou väzbou a pohybom SUMO. Miestny `ns-3.48` nemá `src/wave` ani `OcbWifiMac`. Ak port OCB nevznikne alebo neprejde nezávislou rádiovou validáciou, cestná časť sa má posúdiť v Artery/INET; jej previazaním so SNS-3 by bola nutná synchronizovaná kosimulácia so zachovaním identity, poradia a frontov paketov. Bez toho sa dve simulácie nesmú vydávať za jediný end-to-end experiment.

## Skutočný výsledok

Posledný vykonaný beh vyššie uvedeného skriptu skončil s návratovým kódom `0`:

```text
GN_L2_TX_BYTES=85 TX_TIME_US=100000
CAM_RX_STATION=1001 RX_TIME_US=100147
GN_BTP_CAM_OVER_NS3_NETDEVICE=pass DELAY_US=147
```

Na odosielanie sa použil `NetDevice::Send` s EtherType `0x8947`. Prijímač zaznamenal práve jeden taký L2 rámec, Vanetza GN ho nezahodil, BTP-B dispatcher potvrdil port `2001` a Release 2 dekóder potvrdil `stationId=1001`. Rozdiel `147 µs` vznikol v tomto konkrétnom 6 Mbit/s CSMA nastavení vrátane jeho modelových frontov/času prenosu; nie je to namerané rádiové oneskorenie. Rámec mal 85 B na úrovni payloadu `NetDevice::Send`: 41 B CAM + 4 B BTP-B + 40 B konkrétnych GN hlavičiek. Ethernetová hlavička/FCS ani fyzická preambula nie sú súčasťou tohto čísla. Test nevolal `Ipv4L3Protocol` ani UDP socket.

**Prechodová hranica:** toto overenie dáva dôvod pokračovať v adaptéri Vanetza do ns-3. Ešte neoveruje zhodu rádia, CAM generovanie z mobility, DENM stavovú mašinu, DCC, podpisy, rušenie ani napojenie na satelitný backhaul. V zdrojoch pripnutého Vanetza sa navyše `router.hpp` hlási k EN 302 636-4-1 v1.3.1, zatiaľ čo `data_indication.hpp` odkazuje na v1.4.1. Skutočný pokrytý podmnožinový profil preto stanovuje test a commit, nie jeden komentár v hlavičke. Ďalšia brána je pohybujúce sa auto→auto/RSU cez overené OCB rádio s generovaným CAM a udalosťovou DENM.
