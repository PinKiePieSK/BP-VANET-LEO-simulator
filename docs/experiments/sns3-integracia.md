# Integračný pilot SUMO + VANET + SNS-3

> **Revízia 22. 10. 2026:** Tento denník zachytáva pôvodný integračný beh. Neskorší nezávislý [geografický audit](geografia-a-orbity.md) zistil, že jeho doručený feeder spoj končil pri bráne pod geometrickým horizontom. Paketový priechod zostáva dôkazom funkcie simulátora, nie fyzikálne platnej trasy. Aktuálny editor používa explicitný scenárový variant `sns3-reference-geo`; pôvodné čísla v tomto denníku sa nesmú používať ako výsledok overeného orbitálneho modelu.

Stav 22. 10. 2026: implementácia v `src/vanet-sns3.cc` sa zostavila a jeden 60 s beh prešiel kontrolou `tools/verify_sns3_pilot.py`. Tento pilot je test prepojenia nástrojov, nie výsledok konkrétneho operátora.

## Hypotéza a reálna logika

Ak vozidlo doručí UDP správu RSU v dosahu pozemného rádia, aplikačná brána RSU má preniesť rovnakých 300 B cez lokálne káblové pripojenie do satelitného terminálu a ďalej cez LEO satelit do vzdialenej pozemnej brány. Kontrola V2V a V2I používa tie isté SUMO polohy, vysielací výkon a paketové intervaly. Pilot sa považuje za úspešný len keď PCAP/trace potvrdí prechod cez **skutočný SNS-3 user a feeder link** a vzdialený príjem má zodpovedajúcu sekvenciu a obsah. Samotný aplikačný log bez satelitného trace na toto nestačí.

## Moduly, vstupy a jednotky

| Časť | Vstup/algoritmus | Výstup | Predpoklad a obmedzenie |
| --- | --- | --- | --- |
| SUMO + `tools/fcd_to_waypoints.py` | Starý syntetický 2 km cestný pilot, seed 42, krok 0,5 s. | `waypoints.csv`: `time_s` v sekundách, `x_m,y_m` v metroch, `speed_mps`. | Cesta nie je validovaná reálna mapa. |
| `src/vanet-sns3.cc`: pozemný prístup | Dve vozidlá s waypointmi, RSU pri `(600,-1.6)` m, 802.11p profil 10 MHz/6 Mb/s, 20 dBm, log-distance 2,7, 47,86 dB pri 1 m. | PCAP Wi-Fi, V2V/V2I aplikačné udalosti. | `AdhocWifiMac` nie je úplné WAVE/ITS-G5 OCB. V lokálnom zdrojovom strome ns-3.48 nie je samostatný `wave` modul ani `OcbWifiMac`; pred implementáciou OCB treba overiť vhodnú kompatibilnú verziu/modul. Útlm nie je kalibrovaný. |
| Aplikačné správy | UDP, 300 B: `SeqTsHeader` a zvyšok deterministicky `byte[i]=(seq+i) mod 256`; každý tok má 50 alebo 25 pokusov. | Identický payload na aplikačných relé, sekvencia a čas odoslania. | Ide o diagnostický dátový profil, nie formalizovanú CAM/DENM správu. |
| RSU–UT | `PointToPointHelper`, 1 Gb/s, 100 µs, RSU aplikácia kopíruje prijatý paket do terminálového používateľského uzla. | PCAP bodovej káblovej linky (historický názov súboru `packet-ethernet-*`) a udalosti `rsu`, `terminal_user`. | 100 µs a 1 Gb/s sú explicitné laboratórne predpoklady. `PointToPointHelper` neimplementuje Ethernet PHY/MAC. Používa sa aplikačný proxy, nie transparentné L3 smerovanie. |
| SNS-3 | `ns-3.48` + `satellite/traffic/stats 3.48`; `constellation-leo-2-satellites`, SGP4, sieťová regenerácia, UT/GW, ISL a DVB linkové modely. | Paketový trace SNS-3, vzdialené UDP prijatia v gateway user, satelitné štatistiky. | Vstupné TLE pochádzajú z roku **2014**, satelity sú testovacie ISS-like a scenár používa DVB. Nie je to Starlink, Iridium ani Globalstar a nevypovedá o súčasnom pokrytí. Lokálne SUMO súradnice zatiaľ nie sú geograficky koregistrované so SNS UT; pri posudzovaní dopravnej polohy a satelitného pokrytia to treba opraviť. |
| `tools/analyze_events.py` | Páruje `tx` vozidla a `rx` gateway podľa toku/sekvencie. | PDR, jednosmerné oneskorenie, jitter a 5 s aplikačná dostupnosť v JSON/CSV. | Metriky opisujú koniec-koniec v zvolenom scenári. Nedodaný paket nemá oneskorenie/jitter; treba rozlíšiť stratu na pozemnom a satelitnom úseku podľa hop trace. |

Priebežný `hops.csv` má `flow,seq,node,event,time_s,packet_uid,bytes,payload_fnv64`. Jednotkou času je sekunda simulácie. Pri každom aplikačnom bode sa celý payload skontroluje oproti vzoru `(seq+i) mod 256` a zapíše sa jeho FNV-1a kontrolný odtlačok; chyba obsahu zastaví simuláciu. `packet_uid` je interný identifikátor ns-3; pri proxy relé sa zachová aplikáciou vytvorený paket, ale nižšie vrstvy môžu vytvárať ďalšie rámce/fragmenty. Na identifikáciu obsahu sa preto používa tok, sekvencia a payload, nie iba UID. FNV-1a je diagnostický odtlačok, nie kryptografický dôkaz.

## Testovacie kroky

1. Zostaviť a spustiť upstream GEO `sat-cbr-example` a LEO `sat-constellation-example`, uložiť logy a skontrolovať úspešný príjem.
2. Zostaviť `vanet-sns3.cc` v tom istom pripnutom ns-3.48, spustiť s pevným SUMO výstupom. Uložiť úplný príkaz, log, PCAP a SNS trace.
3. Skontrolovať `v2v > 0`, `v2i > 0`, `satellite > 0`, postupnosť `car0 → rsu → terminal_user → gateway_user`, payload sekvencie a rozdiel času medzi TX/RX. Následne vytvoriť kontrolovaný výpadok satelitného segmentu a overiť, že vzdialený príjem klesne, zatiaľ čo V2V/V2I pokračuje.
4. Až po úspechu pridať mobilný UT vo vozidle, geografický prevod SUMO súradníc, handover a profilované topológie operátorov. Samostatne testovať optické/radiové ISL a Globalstar bez ISL.

## Denník pokusov

| Pokus | Stav | Výsledok/poučenie |
| --- | --- | --- |
| Získanie SNS-3 zdrojov `3.48` | overené | Päť commitov v `docs/reprodukcia.md`, submodule `data` na pevnom commite. |
| CMake konfigurácia | overené | Debug profil, potrebné moduly a závislosti rozpoznané. `python3-dev` chýba, Python bindings sa nepoužívajú. |
| Kompilácia | overené | `./ns3 build vanet-sns3 -j 4`, kompilátor a linker skončili bez chyby. |
| Prvý integračný beh | neúspešný | SNS-3 `CommandLine` skrátil absolútnu cestu pri prvej medzere v `Bakalarska praca`; nahradené relatívnymi cestami bez medzery. Druhý pokus so spustením binárky priamo mal tú istú chybu, kým sa nezmenili argumenty ciest. |
| Integračný beh po oprave | overené | `bash scripts/run_sns3_pilot.sh` skončil kódom 0. `v2v`: 50/50, priemer 0,764 ms; `v2i`: 10/25, 0,590 ms; vzdialený `satellite`: 10/25, 117,812 ms. Jitter príslušne 0,177, 0,000057 a 0,630 ms; 5 s dostupnosť 1,0/0,4/0,4. Tieto čísla platia iba pre uvedený 60 s pilot a seed 42/run 1. |
| Kontrola paketov a vrstiev | overené | `verification.json`: úplný 300 B payload a rovnaký FNV-1a odtlačok na každom aplikačnom hop-e pre všetkých 10 vzdialených doručení. Spoločné ns-3 `packet_uid` pri každom z desiatich paketov prepája aplikačný log a SNS PHY trace: UT 4 odoslal, SAT 1 prijal, SAT 0 odoslal a GW 3 prijal paket v tomto časovom poradí. Scenár má medzi SAT 1 a SAT 0 práve jednu definovanú ISL (`positions/isls.txt`), takže tento beh preukazuje prechod po nej. Trace neukladá plné bity ISL rámca. PCAP Wi-Fi aj bodovej káblovej linky je nenulový. |
| Obnova po mobilnom pokuse | najprv neúspešná | Omylom paralelné behy hlavnej a skúšobnej vetvy zapísali do toho istého výstupu; `analyze_events.py` právom zistil duplicitné sekvencie. Surové súbory označené `results/sns3_integrated/INVALID-MIXED.txt` sa nepoužívajú. Skript teraz používa `flock` a jedinečný adresár `runs/<run_id>`; súbežný pokus bol odmietnutý. |
| Čistá obnova | overené | `runs/20261022T102205Z-65450`: beh kód 0, presne pôvodné metriky a všetky aplikačné pakety overené; `latest` ukazuje na tento beh do ďalšieho úspešného spustenia. |

Vzdialený tok má rovnakých 10 prijatí ako V2I; straty 15 z 25 vznikli predovšetkým tým, že vozidlo odišlo z dosahu RSU. Z týchto čísel nemožno vyvodzovať dostupnosť satelitnej služby. Kontrolovaný satelitný výpadok v tejto integrácii ešte nebol vykonaný.

Presný príkaz pre nový izolovaný beh je `bash scripts/run_sns3_pilot.sh` z koreňa projektu. Skript vypíše `run_id` a uloží vstupy, PCAP, SNS trace, súhrn, overenie a SHA-256 do `results/sns3_integrated/runs/<run_id>/`; `results/sns3_integrated/latest/` ukazuje na posledný úplne úspešný beh. Vo VM musí byť nainštalovaný pripnutý build podľa `docs/reprodukcia.md`.
