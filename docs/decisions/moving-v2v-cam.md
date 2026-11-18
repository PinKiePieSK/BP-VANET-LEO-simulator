# Pohyblivé auto→auto CAM: samostatný paketový test V2V

**Stav:** overený obmedzený experiment, 22. 10. 2026. Reprodukcia z koreňa projektu:

```bash
bash tools/run_moving_v2v_cam.sh
```

Runner vytvorí 12 vstupných bodov, skompiluje Vanetza v26.06 a nový `src/moving-v2v-cam.cc` maximálne jednou build úlohou, spustí dve varianty a nezávislý bajtový verifier. Výstupy: `results/moving_v2v_cam/positive.csv`, `no_contact.csv`, `*_mobility.csv`, `*_decoded.csv`, `*_phy.csv`, raw IEEE 802.11 PCAP, `verification.json` a `manifest.json` s verziami a SHA-256 kódu/vstupov. Pôvodné CAM→RSU a geometrické experimenty sa nemenia.

## Účel, hypotéza a vstupy

Hypotéza: na krátkom archivovanom úseku sa **šesť skutočne zakódovaných CAM** vyslaných autom `car0` cez GN/BTP/802.11p dostane k druhému pohybujúcemu sa autu `car1` a jeho aplikácia dekóduje rovnaké polia, aké boli v odosielajúcom riadku SUMO. Záporná kontrola má zachovať čas, pohyb, obsah aj seed, no vypnúť rádio umelým limitom dosahu 1 m; žiadny CAM sa vtedy nemá dekódovať.

Zdrojom sú [archivované georeferencované FCD body](../../data/derived/georeference/bratislava-synthetic-road-20261022.csv) a ich [metadáta](../../data/derived/georeference/bratislava-synthetic-road-20261022.metadata.json) zo syntetickej cesty SUMO 1.18.0. Kotva je `(800,675) m` → `(48,1486° N,17,1077° E,0 m)`, `+x` východ, `+y` sever, UTC počiatok `2026-10-22T12:45:00Z`. Ide o hypoteticky umiestnenú cestu pri Bratislave, nie skutočne zameranú ulicu. `tools/prepare_moving_v2v_waypoints.py` overí SHA-256 archívu a vyberie pre obidve autá presne t=29,0–31,5 s v kroku 0,5 s. `car0` má uloženú rýchlosť 23,71 m/s, `car1` 23,79→23,76 m/s; štartovacích 15 m/s v editore nie je aktuálnou rýchlosťou týchto bodov. Archivovaná trať má limit 25 m/s a pôvodný SUMO súhrn nemá teleporty ani kolízie.

Výstupný CSV nesie pre každé auto `x/y` v metroch, WGS84 polohu v `10⁻⁷°`, výšku v cm, rýchlosť v cm/s a heading v desatinách stupňa. Heading sa odhaduje **dopredným konečným rozdielom** ďalšieho bodu `atan2(Δx,Δy)` po smere hodinových ručičiek od severu; pôvodný FCD heading archivovaný nebol. Čas CAM `generationDeltaTime` je uplynutý čas v TAI milisekundách od `2004-01-01T00:00:00 UTC` modulo 65536, konvertovaný Astropy 7.1.1/ERFA 2.0.1.5. Prevod má regresný príklad [ETSI TimestampIts](https://forge.etsi.org/rep/ITS/asn1/cdd_ts102894_2/-/commit/9618642bc1b14620ac14dd870a11da82efc66280): 2007-01-01 UTC → 94 694 401 000 ms. Obidve autá majú pri každom indexe totožný UTC čas/GDT, no **vlastnú** polohu a vlastnú rýchlosť. Sú vzdialené 31,684854→31,512655 m.

## Vrstvy, obsah a spôsob pohybu

`car0` s `stationId=1001` vytvorí pri každom archivovanom čase nový Release 2 CAM podľa pripnutej ASN.1 schémy Vanetza `asn1/release2/TS103900v231-CAM.asn`, ktorá zodpovedá [ETSI TS 103 900 V2.3.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf). Dekódovaný obsah zahŕňa jeho `stationId`, `generationDeltaTime`, latitude, longitude, altitude, speed a heading. Povinné zvyšné polia sa priznávajú ako predpoklady: osobné auto, dĺžka 5,0 m podľa SUMO route, šírka 1,8 m, nulová akcelerácia/krivka/yaw rate, poloha s predpokladanou elipsou 1 m a nedostupné confidence pre výšku/rýchlosť/heading. Obsah je 41 B UPER. Vanetza ho prenesie cez BTP-B port 2001 (4 B), GeoNetworking single-hop broadcast (spolu 85 B na EtherType `0x8947`) a ns-3.48 `WifiNetDevice` s 802.11p PHY a `AdhocWifiMac`.

Obidve autá majú **vlastné** `ConstantPositionMobilityModel`. V každej 0,5 s udalosti sa najprv posunie `car1` podľa jeho riadku SUMO a aktualizuje jeho Vanetza WGS84 fix, potom sa posunie `car0` podľa jeho riadku, aktualizuje vlastný fix a vyšle CAM. Všetko plánuje rovnaký ns-3 diskrétny čas a Vanetza runtime s uvedeným UTC počiatkom. V ns-3 sa medzi vzorkami neinterpoluje; úvodná pozícia je prvý vybraný bod a hodnotí sa iba okno t29–31,5 s. `car1` má vo vstupnom CSV pridelené `stationId=1002`, ale v tomto experimente **iba prijíma** a nevytvára vlastný CAM. Jeho aplikácia po GN/BTP dekódovaní porovná každé CAM pole so zodpovedajúcim riadkom `car0` a vlastnú okamžitú ns-3 polohu s riadkom `car1`.

Rádio: kanál 180, 5900 MHz, šírka 10 MHz, 6 Mbit/s, 20 dBm TX, nulový anténny zisk, noise figure 7 dB, `FriisPropagationLossModel` a `ConstantSpeedPropagationDelayModel`, seed 314159/run 1. [Dokumentácia ns-3 WAVE](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) hovorí, že `AdhocWifiMac` je OCB podobný, **nie identický s OCB**; tento test preto nedokazuje úplnú ITS-G5/OCB zhodu. [ns-3 dokumentácia propagácie](https://www.nsnam.org/docs/models/html/propagation.html) definuje Friis ako idealizovaný voľný priestor. Pri zápornom behu je za Friis pridaný `RangePropagationLossModel MaxRange=1m`, ktorý pre skutočný odstup >31 m umelo potlačí všetok príjem. Táto hranica nie je modelovanou hranicou V2V prevádzky.

## Pozitívny a negatívny výsledok

| Variant | CAM TX `car0` | PHY/GN/CAM RX `car1` | Význam |
|---|---:|---:|---|
| `positive` | 6 | 6 | Všetkých šesť obsahov dekódovaných v pohybujúcom sa aute. |
| `no_contact` | 6 | 0 | Umelý 1 m gate odlíši správne odoslanie od príjmu. |

Každý pozitívny CAM došiel po **266 µs** v tomto konkrétnom malom nastavení. RSS sa menilo od **−57,881858 do −57,834523 dBm** pri zmene odstupu, noise bolo **−96,976285 dBm**. Kód a nezávislý verifier porovnávajú RSS s `20 dBm − 20log₁₀(4πdf/c)` pre každú archivovanú vzdialenosť; absolútna odchýlka je <0,01 dB. Je to vnútorná fyzikálna kontrola zvoleného Friis modelu, nie validácia reálneho mestského kanála.

`tools/check_moving_v2v_cam.py` kontroluje: všetkých 12 pohybových záznamov proti vstupnému CSV; rozdielne polohy oboch áut; šesť dekódovaných CAM oproti času/WGS84/rýchlosti/smeru `car0`; presné 41 B CAM pri odoslaní aj prijatí; 4 B BTP-B a presných 85 B GN payloadu; EtherType `0x8947` a zhodu vyslaného/prijatého raw 802.11 PCAP; časovú následnosť; šesť RSS proti Friis; a v negatívnom prípade neprítomnosť RX PCAP, PHY trace a dekódovaných CAM. Raw DLT 105 sa používa preto, že v predošlej ns-3.48 sonde 10 MHz Radiotap PCAP vyvolal assertion. Prvé vývojové spustenie úspešne vykonalo oba simulované behy, no runner skončil na ešte nevytvorenom verifieri; po jeho doplnení kompletný runner prešiel s exit 0. [Manifest](../../results/moving_v2v_cam/manifest.json) uchováva presné verzie a hashe vstupov/kódu.

## Obmedzenia a pokračovanie

Šesť paketov, jeden vysielač, jeden prijímač, krátky úsek a idealizovaný voľný priestor **nedávajú kalibrovanú PDR ani realistické rozdelenie latencie/jitteru**. Nie sú modelované budovy, vozidlá ako prekážky, multipath, shadowing, interferencia, rušné zaťaženie kanála, bezpečnostné obálky/podpisy, úplný DCC a dynamické pravidlo frekvencie CAM. Pozície sú zo syntetickej cesty a heading je odvodený, nie meraný. Nasledujúci obhájiteľný krok je pridať riadené viacvozidlové zaťaženie a zdôvodnený rádiový kanál, potom samostatne porovnať V2V/V2I dostupnosť s reportovaním cez vzdialený servisný backhaul. V2V CAM tu neprechádza satelitom.
