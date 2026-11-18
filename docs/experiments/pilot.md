# Pilot 01 — rovná cesta, V2V a abstraktný LEO backhaul

## Hypotéza a logika scenára

Dve vozidlá na jednom úseku cesty predstavujú najmenší prípad lokálnej výmeny správ. Prvé vozidlo tiež odosiela diagnostické pakety cez cestnú jednotku (RSU) do vzdialeného servera. Výpadok vložený len do backhaulu má znížiť doručenie vzdialeného toku; lokálne V2V má pokračovať. Ide o funkčný test architektúry a metodiky, nie o odhad kvality konkrétnej služby v teréne.

## Kontrola a varianty

- `ground`: iba lokálny V2V tok (50 × 300 B, 1 paket/s v sekundách 5–54).
- `nominal`: rovnaký V2V tok, diagnostický V2I tok a vzdialený tok (po 25 × 300 B, v sekundách 27–51; V2I o 100 ms neskôr) bez vloženého výpadku.
- `outage`: rovnaké vstupy ako `nominal`; paketový príjem na backhaul linke sa blokuje v intervale `[32,37)` s.

SUMO seed 42, ns-3 seed 42/run 1. Všetky varianty čítajú tie isté SUMO polohy. Parametre a obmedzenia sú v `docs/model.md`. Kontrolovaný výpadok nie je odvodený z TLE.

## Testovací protokol

Príkaz: `bash scripts/run_pilot.sh` z koreňa repozitára. Skript musí overiť SUMO bez kolízií a teleportov, predpísané počty paketov, kladné lokálne doručenie, menšie doručenie backhaulu pri výpadku a prázdne prijatie vo výpadkovom päťsekundovom okne. Uložiť aj surové FCD, CSV udalosti, per-packet CSV, súhrny JSON a graf.

## Záznam behov a neúspechov

| Čas UTC | Príkaz | Výsledok | Zistenie/oprava |
| --- | --- | --- | --- |
| 2026-10-22 08:56 | `netconvert ...; sumo -c scenarios/pilot/pilot.sumocfg --seed 42 ...` | SUMO prešiel; 120 krokov a 2 vozidlá v závere. | FCD následne previedol skript na 120 polôh `car0` a 116 polôh `car1`. |
| 2026-10-22 po inštalácii ns-3 | Kontrola `pkg-config --list-all` a `/usr/include/ns3` | Pôvodne plánovaný `Wifi80211pHelper`/WAVE modul v Ubuntu balíku ns-3.41 chýba. | Pilot upravený na dostupný `WIFI_STANDARD_80211p` s `AdhocWifiMac`; obmedzenie explicitne zapísané v modeli a texte práce. |
| 2026-10-22, pokus 1 | `bash scripts/run_pilot.sh` | SUMO, kompilácia aj V2V prešli, ale backhaul v `nominal` aj `outage` mal 0/25 prijatých; kontrola správne zlyhala. | Uložený `results/pilot/run-2026-10-22.log`. Pridaný diagnostický priamy V2I tok. |
| 2026-10-22, pokus 2 | `bash scripts/run_pilot.sh`, diagnostický V2I | Backhaul aj V2I mali 0/25. Paketový záznam ukázal ARP požiadavky na RSU v sekundách 20–23 bez odpovede, keď vozidlo bolo mimo úspešného dosahu. | Uložený `run-2026-10-22-attempt2.log` a PCAP v `results/pilot/attempts/attempt2/`. Posunutý začiatok toku do blízkosti RSU na 27 s; výpadok zmenený na `[32,37)` s, aby tvoril celé päťsekundové okno. |
| 2026-10-22, pokus 3 | `bash scripts/run_pilot.sh` | Kontrola prešla. | Uložený `run-2026-10-22-attempt3.log`; surové CSV/PCAP a JSON sú pod `results/pilot/`. |
| 2026-10-22, kontrolný opakovaný beh | `bash scripts/run_pilot.sh > results/pilot/run-final-2026-10-22.log 2>&1` | Prvý štart skončil 141 kvôli `pipefail` a `head` pri výpise verzie SUMO; simulácia sa nespustila. | Skript upravený na zachytenie celej verzie bez pipe; opakovaný beh prešiel (exit 0), výsledky zhodné s pokusom 3. Výstup `run-final-2026-10-22.log`. |

## Výsledky a interpretácia

| Variant a tok | TX / RX | PDR | Priem. oneskorenie (ms) | Priem. jitter (ms) | Dostupnosť 5 s |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ground` V2V | 50 / 50 | 1.00 | 0.784 | 0.198 | 1.00 |
| `nominal` V2V | 50 / 50 | 1.00 | 0.784 | 0.198 | 1.00 |
| `nominal` V2I | 25 / 10 | 0.40 | 0.590 | 0.000057 | 0.40 |
| `nominal` backhaul | 25 / 10 | 0.40 | 16.339 | 0.936 | 0.40 |
| `outage` V2I | 25 / 10 | 0.40 | 0.590 | 0.000057 | 0.40 |
| `outage` backhaul | 25 / 5 | 0.20 | 17.132 | 2.035 | 0.20 |

Z 25 vzdialených paketov sa v kontrolnom variante dostalo cez RSU len 10; po sekunde 36 sa už nedostávali ani priame V2I pakety. Táto strata vzniká na pozemnej časti pri vzďaľovaní vozidla od RSU, nie v LEO modeli. Vložený výpadok odstránil 5 paketov z dostupného okna 32–36 s a nezmenil V2I ani V2V výsledok. Vyšší priemerný delay/jitter zostávajúcich paketov vo variante `outage` nemožno interpretovať ako spomalenie linky: priemer sa počíta z inej podmnožiny doručených paketov. Prvý vzdialený paket v `nominal` mal 23.456 ms, ďalšie približne 15.5 ms; pri prvom sa prejaví aj nadviazanie ARP. Jeden deterministický beh umožňuje diagnostiku, nie intervaly spoľahlivosti ani zovšeobecnenie na iné cesty a rádiové prostredia.
