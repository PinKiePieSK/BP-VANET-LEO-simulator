# Pohyblivý CAM: SUMO → Vanetza GN/BTP → ns-3 rádio → RSU → IP server

Stav: overený ohraničený integračný experiment, 22. októbra 2026. Spustenie z koreňa repozitára:

```bash
bash tools/run_moving_cam_backhaul.sh
```

Výstupy sú v `results/moving_cam_backhaul/`; ich `manifest.json` viaže verzie a SHA-256 vstupov a kódu. Runner kompiluje najviac s jednou úlohou. Žiadny systémový balík neinštaluje. Tento variant nemení starší statický integračný experiment.

## Vstup a čas

Vstupom je archivovaný `data/derived/georeference/bratislava-synthetic-road-20261022.csv` spolu s jeho metadátami. Je to **syntetická cesta** SUMO, nie nameraná ulica Bratislavy. Pôvodný georeferenčný prevod mapuje SUMO bod `(800,675) m` na WGS84 `(48.1486°,17.1077°,0 m)`; lokálna os `+x` mieri na východ, `+y` na sever. Použitých je šesť uložených bodov `car0` v čase 29,0–31,5 s po 0,5 s. UTC počiatok simulácie aj Vanetza Runtime je `2026-10-22T12:45:00Z`; ns-3 a Vanetza plánujú udalosti z jedného diskrétneho času. RSU je na lokálnom bode `(800,675,0) m`. V pozitívnom variante má vozidlo pri každom odoslaní skutočnú pohyblivú ns-3 `ConstantPositionMobilityModel` polohu nastavenú podľa bodu; Vanetza GN dostane zodpovedajúcu WGS84 polohu s tým istým časom.

`tools/prepare_moving_cam_waypoints.py` kontroluje SHA-256 archívu a prevádza jednotky do `build/moving-cam-waypoints.csv`:

| Položka | Zdroj a jednotka CAM |
|---|---|
| Latitude/longitude | uložený WGS84 bod, zaokrúhlený na `10⁻⁷°` |
| Altitude | uložená výška v m → cm; v CAM je `altitudeConfidence=unavailable` |
| Speed | uložená SUMO rýchlosť m/s → cm/s; confidence je `unavailable` |
| Heading | dopredný konečný rozdiel susedných `(x,y)` za 0,5 s; `atan2(Δx,Δy)` dá stupne po smere hodinových ručičiek od severu, CAM ukladá desatiny stupňa; pôvodný FCD heading **nebol** archivovaný |
| `generationDeltaTime` | celočíselné uplynuté **TAI milisekundy** od epochy `2004-01-01T00:00:00 UTC`, modulo 65536; Astropy 7.1.1/ERFA 2.0.1.5 premení UTC na TAI |

Časový prevod má regresný test podľa príkladu ETSI: `2007-01-01T00:00:00Z` je `94 694 401 000` ITS milisekúnd, teda zahŕňa priestupnú sekundu od epochy. Náš dátum 2026 využíva tabuľku priestupných sekúnd pripnutej verzie Astropy. [ETSI CDD TimestampIts](https://forge.etsi.org/rep/ITS/asn1/cdd_ts102894_2/-/commit/9618642bc1b14620ac14dd870a11da82efc66280), [ETSI TS 103 900 V2.3.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf).

Konfigurácia editora udáva štartovaciu rýchlosť 15 m/s; v skutočnom archivovanom FCD zo SUMO 1.18.0 má `car0` pri t=29–31,5 s **23,71 m/s** a ten istý údaj je v CAM. Trať `forward` má v uloženom `road.edg.xml` limit 25 m/s, `vehicles.rou.xml` má `maxSpeed=25 m/s`, `accel=2 m/s²` a `departSpeed=15 m/s`. Súhrn pôvodného SUMO behu má počas celého behu nulové teleporty aj kolízie. Smer 75,9–76,0° je výsledok uvedeného konečného rozdielu, nie archivované meranie FCD heading.

## Čo prenáša model

`src/moving-cam-backhaul.cc` zostaví pre každý bod nový ETSI Release 2 CAM cez Vanetza v26.06 (commit `fb6c551030dcc12b924299bf401e35e5fe814713`). Pripnutá ASN.1 schéma je `build/vanetza-v26.06/asn1/release2/TS103900v231-CAM.asn`, zodpovedajúca [ETSI TS 103 900 V2.3.1 (2026-05)](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf). Hlavička má `protocolVersion=2`, `messageId=2`, `stationId=1001`. Obsahuje vyššie uvedený čas, polohu, výšku, rýchlosť a heading. Zvyšné povinné polia sú explicitné modelové predpoklady: osobné auto, dĺžka 5,0 m podľa uloženej SUMO definície vozidla, šírka 1,8 m ako predpoklad, nulová akcelerácia, krivosť a yaw rate; confidence pre heading/rýchlosť a výšku sa označuje ako nedostupná. Fixovaná polohová elipsa 1 m je ďalší predpoklad, nie známa presnosť syntetickej polohy. Každý CAM prejde validáciou ASN.1 a UPER kódovaním. Šesť zvolených CAM má po overení 41 B; report je v **tomto experimente** ohraničený na túto dĺžku.

Vanetza vytvorí BTP-B (`destinationPort=2001`, 4 B) a GeoNetworking single-hop broadcast. ns-3.48 (commit v manifeste) prenáša 85 B GN/BTP/CAM payload s EtherType `0x8947` cez dva skutočné simulované `WifiNetDevice`: 802.11p, `AdhocWifiMac`, kanál 180, 5900 MHz, 10 MHz, 6 Mbit/s, 20 dBm TX, Friis loss, 7 dB noise figure, seed 314159/run 1. `AdhocWifiMac` je režimu OCB podobný, ale **nie identický s OCB**; chýba plná ITS-G5 MAC/DCC prevádzka. [Oficiálna dokumentácia ns-3 WAVE](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) explicitne rozlišuje tieto režimy. Poskytuje to skutočnú modelovanú PHY/MAC cestu, nie UDP tunel pre GN. Radiotap PCAP pre 10 MHz v tejto verzii assertoval v skoršej sonde; raw IEEE 802.11 PCAP DLT 105 funguje a verifier dekóduje všetkých šesť rámcov.

RSU skutočne prijme GN/BTP, dekóduje CAM, porovná `stationId`, `generationDeltaTime`, latitude, longitude, altitude, speed a heading s príslušným uloženým riadkom a potom vytvorí nový 96 B aplikačný report: ASCII `ICB1` (4 B), verzia (1 B), event ID (8 B), čas prijatia RSU v mikrosekundách od začiatku simulácie (8 B), dĺžka CAM (2 B), SHA-256 CAM (32 B) a presných 41 B prijatého CAM. Event ID má horné bajty `ca...` a dolných 16 bitov z `generationDeltaTime`, teda je jednoznačné len v tomto krátkom šesťbodovom úseku. Report ide ako UDP/IPv4 cez simulovaný 1 Gbit/s LAN do UT aplikačného proxy a odtiaľ novou UDP správou cez **abstraktný** 22 kbit/s point-to-point servisný segment do servera. IPv4 aj UDP checksumy sú zapnuté. UT a server kontrolujú hash, identitu a dekódované CAM polia. Úplný report sa zachová naprieč hopmi; server ho neberie ako priamy satelitný CAM rámec.

## Hypotéza, kontrola a výsledok

Hypotéza: pri tomto krátkom priblížení k RSU dostane pozemné rádio šesť CAM a infraštruktúra dopraví šesť k nim priradených IP reportov. Pozitívny beh má 6/6 vyslaných a dekódovaných CAM a 6/6 prijatých reportov serverom. Každý rádio príjem nastal 266 µs po odoslaní; každý server report prijal 46 085 µs po vyslaní CAM. Tieto čísla platia len pre zvolený Friis kanál, jediného vysielača a 22 kbit/s službu s nulovým dodatočným oneskorením. Pri poslednom CAM trace hlási RSS −55,99 dBm a noise −96,98 dBm.

Negatívny kontrolný beh ponecháva rovnaký pohyb, pakety a seed, ale za Friis stratu pridá `RangePropagationLossModel MaxRange=1m`. Najmenší odstup auta od RSU v zvolenom úseku je približne 2,35 m, preto ide o **umelý vypínací test**, nie realistický limit 802.11p. Výsledok: 6 TX, 0 PHY RX, 0 dekódovaných CAM, 0 reportov. Chýbajúci RSU RX PCAP je tiež skontrolovaný.

`tools/check_moving_cam_backhaul.py` nezávisle číta vstupný waypoint CSV, `positive_decoded.csv`, surové per-hop CSV a PCAP. Kontroluje každý dekódovaný údaj oproti každému vstupnému riadku; presný CAM UPER cez auto, GN a RSU; EtherType `0x8947` a BTP port v 802.11 rámcoch; polia a SHA-256 reportu; presné UDP payloady v oboch point-to-point hopoch; IPv4 a UDP kontrolné súčty a usporiadanie udalostí. `verification.json` obsahuje oba výsledky. Pokus o pôvodný runner s absolútnou cestou obsahujúcou medzeru zlyhal, pretože parser ns-3 `CommandLine` ju skrátil; runner teraz v pracovnom adresári výsledkov používa relatívnu cestu bez medzier.

## Hranice vierohodnosti a ďalší krok

Archív obsahuje syntetický pohyb a vopred georeferencované body; simulácia nevolá živé SUMO v každej udalosti a neinterpoluje medzi 0,5 s vzorkami. CAM sa tu vysiela pevne 2 Hz podľa archívu, nie podľa celého štandardného dynamického trigger/DCC algoritmu. Confidence, rozmery vozidla, akcelerácia a podobné polia nie sú merané. Friis je idealizovaný priamy prenos bez prekážok, fadingu, kolízií, hidden node a rušenia. Report má vlastný účelový formát, nie štandardizovanú ITS aplikačnú správu.

Servisný segment modeluje len bitovú rýchlosť 22 kbit/s a IP prenos, **nie** konšteláciu, geometrickú viditeľnosť, satelitnú RF, handover, MAC operátora, Iridium/Globalstar/Starlink alebo inter-satellite link. Ďalší vývoj má napojiť reportovú vetvu na geometrický a sieťový model satelitnej cesty s explicitnými obmedzeniami parametrov. Žiadny výsledok tejto sondy sa nesmie prezentovať ako oneskorenie alebo spoľahlivosť reálnej satelitnej služby.
