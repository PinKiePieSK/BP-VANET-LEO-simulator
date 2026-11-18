# P3 — jeden UT medzi SAT0 a SAT1

**Stav:** overený pilot ns-3.38/SNS-3 3.38; dôkaz je v
`results/p3_single_ut_verified_20261026/verification.json`. Tento experiment
testuje prijímací kontrakt v `docs/decisions/sns3-338-single-ut-inter-sat-contract.md`.
Nie je to meranie operátorského handoveru.

## Topológia a zmena modelu

- Jediný `SatNetDevice` UT pri RSU v Bratislave má tú istú MAC a IPv4 adresu
  počas celého behu. SAT0 a SAT1 sú dve archivované LEO dráhy, obe s user
  beam 30. Diagnostická anténa má konštantný zisk 17 dBi; beam 1 s veľmi
  nízkym ziskom obsluhuje len neplatnú fallback pozíciu pod horizontom.
- GW na 65° N, 20° E je pripojená k SAT0. SAT1 nemá priamo pripojenú GW;
  jej cesta ku GW potrebuje modelovú ISL SAT1→SAT0. Pôvodná cesta
  UT→SAT0→GW funguje aj v kontrole bez ISL.
- Patch `patches/sns3-338-single-ut-inter-sat.patch` pridáva atómové
  preladenie PHY Tx/Rx kanálov na `(satId, beamId)`, zmenu oboch MAC
  identifikátorov satelitu a lúča, vyprázdnenie starého TBTP stavu a
  prepojenie mobility observera na nový satelit. Runner zároveň presúva
  rovnakú UT MAC v NCC scheduleri a `SatGeoNetDevice`/`SatIdMapper`, obnovuje
  ARP/IP trasu ku stále tej istej GW a nastavuje timing advance na nový
  user link a pôvodný feeder link. Bez každého z týchto krokov nie je
  samotné `SetSatId` handover.
- Riadenie má stavy `connected_old → pending → await_probe → confirmed_new`
  alebo `failed_old`. V `pending`/`await_probe` sú nové ICB1 zahodené bez
  frontu. Potvrdenie vyžaduje reálnu sondu z toho istého UT cez SAT1/ISL do
  GW a návrat odpovede cez SAT1 user kanál. Zlyhaná odpoveď spustí návrat
  na SAT0. Presun scheduler/PHY/mapy a odlišný timing advance sa logujú
  spolu s časom a kontrolujú v C++.

## Spúšťanie a raw audit

```bash
cd '/home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca'
.venv/bin/python tools/run_p3_single_ut.py vendor/ns-3.38-ocb-eval results/NEW_UNIQUE_P3_ID
.venv/bin/python tools/check_p3_single_ut.py results/NEW_UNIQUE_P3_ID
```

Runner odmieta neprázdny výstup a porovnáva živý SNS-3 diff s pripnutým
patchom. Manifest ukladá presný zdroj, piny, OMM/TLE pôvod, OSM/CAM vstup,
anténu, scenáre, seed a SHA-256 všetkých raw stôp. Checker číta CAM UPER,
GN/BTP, 96 B ICB1, GRA1/I2V1, OCB/LAN PCAP, ISL IPv4/UDP s kontrolnými
súčtami a `PacketTrace.log`. Ku každému doručenému ICB1 priraďuje unikátne
PacketTrace ID a rozlišuje SAT0 user/feeder cestu od SAT1 user→ISL→SAT0
feeder cesty. Overuje aj spätný smer, časové poradie a zákaz doručenia
paketov zahodených počas `pending`.

Finálny `verification.json` má `status=PASS` pre všetkých päť variantov;
nezávislý opakovaný checker aj migračný preflight prešli. Historický P2 raw
checker po zmene spoločnej SNS-3 knižnice opäť prešiel v 8/8 prípadoch.
Skorší skúšobný adresár `results/p3_single_ut_20261026` je označený
`REJECTED.txt`, pretože sa počas jeho tvorby ešte menil zdroj a checker.

| Variant | Konečný stav | ICB1 v GW | `pending` drop | Cesta doručených ICB1 |
| --- | --- | ---: | ---: | --- |
| `stay_sat0` | `connected_old` | 6/6 | 0 | SAT0 |
| `switch_sat1` | `confirmed_new` | 4/6 | 2 | prvé 2 SAT0, posledné 2 SAT1→ISL→SAT0 |
| `no_target_channel` | `failed_old` | 6/6 | 0 | SAT0 |
| `no_target_gateway_or_isl` | `failed_old` | 6/6 | 0 | SAT0 bez ISL |
| `attach_failed` | `failed_old` | 4/6 | 2 | prvé 2 a posledné 2 SAT0 |

V kladnom behu je syntetická žiadosť v 20,900 s, retune v 21,200 s a
sonda sa odošle v 21,250 s; potvrdenie prišlo v 21,941938 s. Timing advance
sa po prepnutí zmenil z 6 422 857 ns na 6 982 198 ns. Potvrdenie je až po fyzickom obojsmernom
paketovom priechode. Čas žiadosť→retune **300 ms** je parameter citlivosti;
čas po sonde vzniká z tohto konkrétneho DVB plánovača a topológie. Nie je
to nameraný čas pripojenia Iridium, Starlink ani Globalstar.

`no_target_channel` je explicitná porucha kvalifikácie cieľového kanála pri
preflight; kanálový objekt zostáva v zostavenej topológii. Overuje, že pri
neprípustnom kanáli sa prepnutie neuskutoční a nevznikne falošné doručenie
cez SAT1. `no_target_gateway_or_isl` používa fyzicky odlišný scenár s nulou
ISL a nepripojenou SAT1 GW. `attach_failed` nechá paketovú sondu dôjsť do
GW, zadrží iba jej potvrdenie a obnoví staré kanály a scheduler. Tieto
zásahy sú kontrolované modelové poruchy, nie frekvencie reálnych chýb.

## Rozsah platnosti

Referenčná satelitná vrstva je generický DVB-S2/RCS2. Diagnostická anténa,
proxy GW na severe, 1 Gbit/s modelová ISL a retune/timeout nie sú
kalibrované na konkrétny terminál alebo komerčnú službu. Šesť ICB1 v
jednej archivovanej epoche a jednom semene neodhaduje distribúciu PDR,
handover tail latency ani dostupnosť. P4 musí vytvoriť oddelené profily
služieb s vlastnými zdrojmi a vernostnými štítkami.
