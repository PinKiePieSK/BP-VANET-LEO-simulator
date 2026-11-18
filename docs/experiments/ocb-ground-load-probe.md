# Pozemný OCB test s dvoma súbežnými vysielačmi

**22. 10. 2026 UTC, izolovaný experiment; nejde o kalibráciu ITS-G5.**

## Hypotéza a scenár

Ak dve vozidlá ponúknu rovnaký počet rámcov v oveľa kratšom čase, doručenie na RSU a oneskorenie sa zhoršia aj pri rovnakej geometrii a rádiovom nastavení. To je kontrolovaný test súbežnej prevádzky, nie predpoveď výsledkov skutočnej dopravnej siete. Dve statické autá (`car0` na −10 m a `car1` na +10 m) vysielajú broadcast na RSU v 0 m. Statická geometria izoluje záťaž od pohybu. Každé auto ponúkne presne 600 rámcov, teda 1 200 v každom variante:

| Variant | Rozstup rámcov jedného auta | Posun druhého auta | Čas od prvej po poslednú ponuku |
|---|---:|---:|---:|
| `low` | 2 000 µs | 1 000 µs | približne 1,199 s |
| `high` | 100 µs | 0 µs | 0,0599 s |

Táto záťaž je syntetická; 100 µs nie je predpísaná CAM frekvencia. Presne rovnaký počet a obsah rámcov v oboch variantoch umožňuje sledovať efekt časového zhustenia. Vysielania sa spracúvajú v jednom ns-3 event clocku. Z dôvodu bezpečnej interpretácie sa `PhyRxDrop` callbacky nepovažujú automaticky za všetky stratené aplikované rámce ani za jednoznačný počet kolízií.

## Implementácia a vstupy/výstupy

[`ocb-ground-load-probe.cc`](../../src/ocb-ground-load-probe.cc) používa pripnuté ns-3.38 `Wifi80211pHelper`, `QosWaveMacHelper` s runtime kontrolou `OcbWifiMac`, 10 MHz kanál 180 pri 5,9 GHz, 6 Mbit/s, 20 dBm TX, 0 dB anténne zisky, 7 dB šumové číslo, Friis útlm a konštantnú rýchlosť šírenia. Semeno `314159`, run `1`, simulácia trvá 3 s. Rozostupy a polohy sú experimentálne voľby, rádiové nastavenie je zámerne zhodné s [integrovaným OCB pilotom](editable-v2-ocb-geometry-e2e.md), nie kalibrované meraním ulice. Výstup neobsahuje satelitnú vetvu.

`OLP1` je **experimentálny 128 B rámec** na L2 EtherType `0x88b5`, takže sa nevydáva za CAM/GeoNetworking. Offsety bajtov: `0–3` ASCII `OLP1`, `4` zdroj `0/1`, `5–8` sekvencia `uint32` big-endian, `9–16` čas ponuky v µs `uint64` big-endian, `17–127` deterministický vzor obsahu. Na MAC je broadcast 802.11 QoS data s wildcard BSSID. `events.csv` obsahuje každý ponúknutý ID a každý úspešne prijatý ID na RSU, oboje s časom v µs. Tri `ocb-*-0.pcap` sú surové simulované 802.11 rámce. Ich štyri nulové bajty FCS sú zástupný zápis ns-3, nie reálne vypočítané CRC.

[`check_ocb_ground_load_probe.py`](../../tools/check_ocb_ground_load_probe.py) nezávisle číta trace a PCAP: overuje 600 unikátnych ID od každého auta v každom variante, ich rozvrh, 128 B obsah, MAC zdroj, EtherType, OCB BSSID, identitu každého rámca prijatého RSU, časy a hash každého výstupu. `verification.json` rozlišuje `offered`, vlastné rámce vysielača v jeho PCAP a RX v RSU PCAP. `run-manifest.json` pripína commit ns-3, SHA-256 patchu, knižnice, zdroja, binárky a verifikácie. Niektoré ponúknuté rámce nemusia byť v odosielacom PCAP; tento rozdiel sám osebe nedokazuje konkrétny interný mechanizmus zahodenia.

## Reprodukcia

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
bash tools/setup_ns3_ocb38.sh
python3 tools/run_ocb_ground_load_probe.py
python3 tools/check_ocb_ground_load_probe.py
```

Prvý príkaz je potrebný len keď chýba pripnutá knižnica. Setup používa nanajvýš 2 build úlohy; tento samostatný program kompiluje jeden `g++` proces. Runner pred kompiláciou overuje commit `392e36833ce3c7e0ecde4188043f76345402d5a7` a presný zaznamenaný GCC patch. Súbory sú v `results/ocb_ground_load_probe/`. Build závisí od toho istého lokálneho ns-3.38 a jeho patchu ako ostatné OCB piloty; žiadny balík sa pri opakovanom behu neinštaluje.

## Nameraný výsledok v modeli

| Variant | Ponuka car0/car1 | Vlastné TX v PCAP car0/car1 | RSU RX car0/car1 | Celkové PDR | RSU `PhyRxDrop` callbacky | Priemerný čas ponuka→RSU RX |
|---|---:|---:|---:|---:|---:|---:|
| `low` | 600/600 | 600/600 | 600/600 | 1,000 | 0 | 274,037 µs |
| `high` | 600/600 | 573/579 | 519/525 | 0,870 | 108 | 203 436,199 µs |

V `high` je 27/21 ponúknutých ID bez vlastného odosielacieho rámca v PCAP a ďalších 54/54 vyslaných ID bez RSU príjmu. Tieto čísla sa sčítajú na 156 neprijatých ID z 1 200. Posledná ponuka vznikne po 1,0599 s, beh pokračuje do 3 s, preto vysoké oneskorenie zachytáva aj čakanie vo fronte. Počet 108 callbackov `PhyRxDrop` sa **nesčíta** s rozdielmi ID: ide o udalosti fyzickej vrstvy s inou granularitou. Overovač odvodzuje PDR iba z jednoznačných sekvenčných ID v RSU trace a PCAP.

Prvá kompilácia pomocného programu zlyhala na spoločnej C++ deklarácii dvoch rôznych typov (`uint8_t` a `uint32_t`); bola opravená oddelenými deklaráciami. Prvý pokus o `PhyRxDrop` callback zlyhal pri spustení na chýbajúcom argumente `WifiPhyRxfailureReason`; používa sa správna podpisová forma podľa pripnutého zdrojového kódu ns-3. Tieto pokusy nevstupujú do výslednej tabuľky.

## Obmedzenia a ďalšia validácia

Experiment nepotvrdzuje DCC, ETSI ITS-G5 aplikačnú sémantiku, pohyb, urban LOS/NLOS, tienenie, reálne antény ani správanie niektorého konkrétneho RSU. OLP1 sa používa len na kontrolu doručenia a obsahu pri záťaži. Aby bolo možné porovnávať dopravné scenáre, treba pridať mobilné uzly a skutočné CAM/DENM intervaly, rádiové parametre podložené meraním alebo citovaným modelom, frontové štatistiky a výsledky naprieč viacerými semenami. Jedno pevné semeno je reprodukovateľný funkčný test, nie interval spoľahlivosti.
