# Jeden čas simulácie: OCB CAM → RSU → Certus 100 IP servisný obal → server → RSU

## Účel a hypotéza

Tento malý pilot overuje, že **skutočne prijatý** 41 B CAM na RSU možno v jednom ns-3.38 čase zakódovať ako 96 B experimentálny aplikačný záznam ICB1, odoslať ako konkrétne IPv4/UDP bajty na terminál a cez obmedzený IP servisný obal na server, a vrátiť 46 B aplikačné potvrdenie GRA1. Kontrolný variant synteticky vypne kandidáta RSU↔družica bez zmeny lokálneho OCB deja: v ňom nesmie existovať žiadna IP prevádzka servisnej vetvy.

**Toto nie je RF simulácia Iridium Certus.** V kóde je OCB PHY/MAC pre pozemnú komunikáciu, avšak RSU↔terminál P2P predstavuje iba dokumentované IP/Ethernet rozhranie a druhý P2P reprezentuje nepriehľadnú sieťovú službu. Produktové 22 kb/s uplink a 88 kb/s downlink sú publikované maximá pre Certus 100 a v modeli slúžia ako nastaviteľné horné stropy. P2P servis má nulový propagation delay: meraný čas zachytáva serializáciu/fronty a miestnu LAN, **nie komerčné RTT** ani vákuové šírenie cez orbitu. Štvorpaketové fronty sú experimentálny predpoklad; prevádzkové kapacity, RF chyby, lúče, handover, gateway a ISL zatiaľ nie sú overené.

Podklad voľby služby, terminálu SkyLink 5100, modemu 9770 a hraníc údajov: [rozhodnutie o službe](../decisions/satellite-service-implementation.md), [samostatný obal a overload test](certus100-icb1-ip-envelope-38.md). Geometriu tvorí oddelený [audit Iridium-NEXT user-leg](editable-iridium-user-leg-geometry.md): SGP4 nad archivovaným CelesTrak OMM iba identifikuje geometrického kandidáta nad experimentálnou 10° maskou. Katalógový objekt nad obzorom **nepreukazuje prístup k službe**. Vypočítaná vzdialenosť a vákuové one-way oneskorenie zostávajú v `schedule.csv` na audit a v tomto scenári sa nepripočítavajú k IP servisnému času.

## Presný sled a dátový kontrakt

1. SUMO v2 dodá súradnice `car0`, `car1`, `car3`, `rsu0`; šesť vzoriek po 500 ms od UTC `2026-10-22T12:45:20Z`. Vanetza pripraví CAM (41 B) a GN/BTP (85 B). ns-3.38 vysiela cez 802.11p OCB pri 5900 MHz/10 MHz, 6 Mb/s; ďalšie rádio predpoklady sú v pôvodnom [OCB pilote](editable-v2-ocb-geometry-e2e.md). Tri prijímače dekódujú po šesť CAM.
2. `rsu0` tvorí ICB1 **iba v callbacku prijatia CAM**: `ICB1` 4 B, verzia 1 B, big-endian event ID 8 B, čas prijatia `us` 8 B, dĺžka CAM 2 B, SHA-256 CAM 32 B, pôvodný CAM 41 B. Event ID `0xca00000000000000 | generationDeltaTime` umožňuje sledovať rovnaký paket vo všetkých vrstvách.
3. Gate číta šesťriadkový `schedule.csv` s Iridium-NEXT RSU user-leg. Pozitívny variant povoľuje RSU→terminál IP prenos; syntetický záporný variant `--force-block` znemožní odoslanie. Gate neinterpretuje dostupnosť komerčnej služby.
4. Model LAN: RSU→terminál 100 Mb/s P2P, 100 µs propagation, 4 paketová fronta, PPP/IPv4/UDP; port 45000. `terminal_receive` kontroluje celé ICB1 proti RSU záznamu a volá znovupoužiteľné API `Certus100IpServiceEdge::Submit(report,event_id,Simulator::Now())`.
5. Certus 100 IP servisný obal vytvorí IP/UDP port 45003 do servera cez syntetický 22 kb/s uplink a 88 kb/s downlink, oba s obmedzenými 4 paketovými device/queue-disc frontami. Server znova overí celé ICB1 a vytvorí GRA1: `GRA1` 4 B, verzia 1 B, event ID 8 B, SHA-256 celého ICB1 32 B a status 0 1 B. Toto je **lokálne aplikačné potvrdenie**, nie ACK rádiového systému.
6. `Reply(ack,event_id)` vráti GRA1 na terminál (UDP port 45004), odtiaľ LAN na RSU (45001). Terminál a RSU kontrolujú ID a SHA. Štyri PCAP súbory pre LAN/servis plus OCB PCAP a CSV `trace.csv` umožňujú nezávislý rozbor IPv4/UDP checksumov, bajtov, časov a ID.

## Reprodukcia a surové dôkazy

Z koreňa projektu:

```bash
.venv/bin/python tools/run_editable_v2_ocb_certus100_e2e.py
```

Runner kontroluje pripnuté verzie nástrojov, scenár, FCD a waypoint SHA-256, archivovaný snapshot a Iridium-NEXT gzip hash, generátor aj geometrické CSV/metadata. Kompiluje **jedným** `g++` procesom s 90 s timeoutom; na 8 GB VM sa ďalší veľký build nemá spúšťať súčasne. Dva behy sú `results/editable_v2_ocb_certus100_e2e/{positive,blocked_user_leg_candidate}/`. V každom zostane `schedule.csv`, metadata, `trace.csv` so všetkými surovými hex bajtmi, OCB/LAN/servis PCAP, `delivery.csv`, `ocb_decoded.csv`, `run.log`; koreň výsledkov obsahuje `build.log`, `check.log`, `verification.json`, `run-manifest.json` s hashmi.

Audit `tools/check_editable_v2_ocb_certus100_e2e.py` kontroluje 6 CAM, 18 prijatí, celú 96 B skladbu ICB1 odvodenú z RSU CAM, zhodné ID a bajty na každom hop-e, kompletnú 46 B odpoveď, PPP/IPv4/UDP dĺžky a checksumy v PCAP, zachovanie času/poradia a nulové dropy. Záporný variant musí mať identické OCB a ICB1 SHA-256 ako pozitívny, 0 servisných frameov a 0 serverových/RSU ACK. Toto nie je kalibrácia reálneho oneskorenia.

Overený beh s fixným semenom 314159 prešiel: pozitívny variant 6/6 serverových ICB1 a 6/6 GRA1 na RSU; zablokovaný variant 0 servisných frameov. Audit vypočítal 52 943 µs pre miestny aplikačný round trip každého z šiestich reportov. Hodnota je dôsledkom nakonfigurovaných 22/88 kb/s, frontov a LAN; **nesmie sa čítať ako RTT Iridium**. Aplikačná odpoveď končí na RSU, nevysiela sa späť autu.

## Jednotky, predpoklady a otvorené hranice

- `time_us`: ns-3 čas od UTC origin, µs; `one_way_vacuum_delay_ns`: geometrický výpočet, ns, **nie aplikovaný servisný delay**; `elevation_deg`: výška nad horizontom, stupne; `range_km`: vzdialenosť, km.
- Jediný CAM vysielač, jeden RSU, jeden terminál a jeden server; doprava len 3 s / 6 správ, žiadna saturácia servisnej vetvy v tomto pilote. Pre oddelený záťažový/drop test pozri `certus100-icb1-ip-envelope-38.md`.
- OCB používa Friis bez budov, vozidlového tienenia a reálneho rušenia. Servis neimplementuje 9770 modem, Iridium RF, link adaptation, mobility handover, beam, crosslink, feeder gateway, autentizáciu, šifrovanie ani skutočné servisné RTT. Tieto časti nemožno označiť za validované; na fyzikálne porovnanie služieb treba dokumentované PHY/MAC alebo terénne merania/kalibráciu konkrétnej služby.
- Porovnanie Starlink/Iridium/Globalstar týmto pilotom **nie je vykonané**. Nie je vhodné preniesť Certus 100 IP obal na ich odlišné terminály a architektúry bez samostatného modelu a zdrojov.
