# Metriky zo šesťsprávového CAM a modelového backhaulu

Stav 22. 10. 2026. Tento modul **analyzuje uložený beh**, nemení simulačné podmienky. Hypotéza: pri totožných šiestich CAM a pozemnej trase bude modelový dodatočný `r/c` zvýšiť jednosmerné oneskorenie na serveri oproti nebránenej kontrole a zámerný blok zmení doručenie konkrétnych reportov. Skutočný produkt Iridium, jeho handover a dostupnosť služby sa z tohto testu neodvodzujú.

## Vstupy, algoritmus a jednotky

Zdrojom sú tri bajtovo overené CSV `results/moving_cam_iridium_gate/{ungated,geometry_positive,geometry_block}.csv`. Analýza odmietne súbor s hashom odlišným od `raw_source_hashes` v `data/derived/viewer/moving-cam-iridium-gate-replay.metadata.json`; tento manifest vznikol po nezávislom audite CAM, GN/BTP, Wi-Fi PCAP, PPP/IP/UDP a gate udalostí. Časy `time_us` sú integer mikrosekundy na **jedných ns-3 hodinách** od `2026-10-22T12:45:00Z`. Každé `event_id` má šesť generovaných indexov t29,0–31,5 s. Receiver radio trace má v pôvodnom CSV nulové ID, preto sa pre analýzu používa `RSU_CAM_UPER` s overeným ID; žiadna udalosť sa nevymýšľa.

Pre index `i` sú definície:

| Metrika | Výpočet | Jednotka/interpretácia |
| --- | --- | --- |
| doručenie CAM k RSU | počet `RSU_CAM_UPER` / 6 `AUTO_CAM_UPER` | podiel iba tohto krátkeho behu |
| doručenie reportu na server | počet `SERVER_ACCEPT` / 6 `AUTO_CAM_UPER` | zahŕňa lokálne rádio aj abstraktný backhaul |
| lokálne oneskorenie | `RSU_CAM_UPER − AUTO_CAM_UPER` | ms, modelové 802.11p/GN/BTP |
| servisné oneskorenie | `SERVER_ACCEPT − SERVICE_PHY_TX` | ms, len **doručené** reporty; zahŕňa serializer 126 B pri 22 kbit/s a zvolený `r/c` |
| celkové oneskorenie | `SERVER_ACCEPT − AUTO_CAM_UPER` | ms, len doručené reporty; nepripočítava serverovú aplikáciu mimo ns-3 |
| absolútna zmena oneskorenia medzi susednými doručenými správami | `abs(D_i−D_{i−1})`, len keď sú oba **susedné pôvodné indexy** prijaté; `D_i` je celkové oneskorenie | ms; opisná veličina podobná jitteru, bez páru cez stratený index |
| modelová otvorenosť gate | integrál binárneho `enabled` z raw gate CSV v okne `[29,32)` s / 3 s | podiel modelového pravidla, **nie** dostupnosť služby operátora |

Výstup je `results/moving_cam_metrics/per_packet.csv` s 18 riadkami a `summary.json` s hashmi vstupov, presnou definíciou variation a min/mean/max. V `per_packet.csv` je `service_tx_us`/`server_accept_us` prázdne, ak daná udalosť nevznikla; `outcome` rozlišuje `accepted`, `blocked_before_service`, `dropped_in_flight`. Pre stratený paket sa **nevkladá** numerické oneskorenie 0 ani nekonečno. Absolútna zmena z dvojice nie je rozdelenie jitteru podľa reálneho Iridia a nezahŕňa stratové intervaly. Hashovaný gate CSV určuje iba podiel času, v ktorom **náš model** v trojsekundovom okne povoľoval link; z jedného zámerného 0,5 s bloku nemožno vyvodiť prevádzkovú dostupnosť služby.

## Reprodukcia a kontrola

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
bash tools/run_moving_cam_iridium_gate.sh
python3 tools/analyze_moving_cam_metrics.py
cat results/moving_cam_metrics/summary.json
```

Prvé spustenie môže znovu zostaviť Vanetza/ns-3 test; ak je uložená raw stopa prítomná a overená, stačí druhý príkaz. Parametre, SHA-256 a negatívne sieťové kontroly sú v [denníku pôvodného behu](../decisions/moving-cam-iridium-gate.md). Kontrola analytického skriptu: 18 riadkov (6 na prípad), výsledky servera 6/6, 6/6, 4/6; nebránený prípad má nulovú zmenu oneskorenia medzi piatimi susednými prijatými pármi, blokovaný prípad má iba dva také páry. Zámerne pozmenený raw trace CSV aj raw gate CSV boli samostatne odmietnuté ešte pred počítaním pre nezhodný SHA. Na vytvorenie súhrnu nie je potrebné `sudo` ani sieťové spojenie.

## Pozorovania

| Modelový variant | CAM pri RSU | Server | Modelová gate otvorená `[29,32)` | Lokálne oneskorenie | Celkové oneskorenie doručených | Priemerná absolútna zmena medzi susednými doručenými pármi |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `ungated` | 6/6 | 6/6 | 100 % | 0,266 ms | 46,085 ms | 0,000 ms (5 párov) |
| `geometry_positive` | 6/6 | 6/6 | 100 % | 0,266 ms | min 51,307; priemer 51,714; max 51,917 ms | 0,122 ms (5 párov) |
| `geometry_block` | 6/6 | 4/6 | 83,33 % | 0,266 ms | min 51,307; priemer 51,612; max 51,917 ms | 0,305 ms (2 páry) |

Rozdiel `ungated`→`geometry_positive` vznikol **implementovaným** jednosmerným geometrickým `r/c` navyše nad tým istým 22 kbit/s serializerom. `geometry_block` má rovnakú pozemnú CAM vetvu, ale jeden report UT zablokuje pred servisným TX a jeden rámec zahodí pri príjme počas umelého bloku. Jeho priemer oneskorenia je podmienený len doručenými štyrmi paketmi; nesmie sa čítať ako zlepšenie počas výpadku. Vzorka má jeden seed, šesť sekvenčných správ a deterministickú idealizovanú kanálovú podmienku, preto nevyjadruje interval spoľahlivosti ani sieťovú štatistiku pre vozovku či konšteláciu. Žiadna hodnota tu nevaliduje Starlink/Iridium/Globalstar ani komerčný QoS profil.
