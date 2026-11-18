# Editovateľný scenár v2: prvý skutočný lokálny paketový beh

## Cieľ a hypotéza

Tento izolovaný pokus spája editovateľný SUMO cestný graf s tým istým simulačným časom ns-3/Vanetza. Hypotéza je, že jedna Release 2 CAM vytvorená z konkrétneho FCD riadku auta prejde cez GeoNetworking/BTP a 802.11p rádiový model ku každému deklarovanému príjemcovi (`car1`, `car3`, `rsu0`) bez zmeny bajtov a v každom cieli sa dekóduje so správnym časom, polohou, rýchlosťou a smerom. Kontrola s explicitnou 1 m dosahovou bránou má zabrániť všetkým príjmom, pričom vysielanie ostane totožné. Tento beh **nepredstavuje satelitnú komunikáciu**.

## Podporovaný kontrakt a poctivé odmietnutie

Runner `tools/run_editable_v2_cam_radio.py` načíta v2 schému a pred spustením vyžaduje presne jeden tok `technology=its_g5`, `message_type=CAM`, `target=broadcast`, `execution=not_implemented`, so zdrojom vo vozidle vybavenom `its_g5`. Vyberie všetky vozidlá/RSU vybavené `its_g5`, celkovo 3–50 rádiových uzlov, aspoň dve autá a jednu RSU. Jediný aktívny vysielač je zdroj toku; ostatné vybavené uzly sú príjemcami. Ostatné `flows` vrátane DENM, unicastu, C-V2X, IP backhaulu a satelitných rozhraní sa **odmietnu s chybou**; nepremieňajú sa na UDP ani sa potichu neignorujú. Vozidlo bez `its_g5` zostáva v dopravnej SUMO simulácii, ale nie je rádiovým uzlom tohto behu. Požadovaná v2 hodnota `network_execution=schema_only` zostáva vo vstupnom návrhu; skutočné paketové vykonanie nastáva až explicitným spustením tohto samostatného runnera a je zaznamenané v `run-manifest.json`.

Súčasný overený variant pripína 0,5 s krok, počiatok `2026-10-22T12:45:00Z`, šesť FCD riadkov každého uzla v `t=20,0..22,5 s` a kladné celé RNG semeno. Počet rádiových uzlov sa môže meniť do 50, ale **kalibrovaný ani otestovaný škálovací výkon pre 50 uzlov netvrdíme**. Fixture `data/inputs/editable-road-v2/packet-subset.json` má 3 autá, jednu RSU a jediný CAM broadcast. Starší v2 fixture s tromi rozličnými tokmi sa úmyselne odmieta. SUMO dopravný beh v tomto fixture vložil a doručil 3/3 autá, bez kolízií a teleportov.

## Moduly, algoritmus, jednotky a zdroje parametrov

| Modul | Vstupy a postup | Výstupy a limity |
| --- | --- | --- |
| `tools/editable_scenario_v2.py` | JSON → SUMO plain XML → `netconvert` → SUMO FCD, semeno 314159. | `sumo/fcd.xml`, `summary.xml`, manifest; len pohyb. |
| `tools/prepare_editable_v2_cam.py` | FCD polohy v m, FCD `speed` v m/s a `angle` v navigačných stupňoch. Lokálny ENU graf sa registruje do WGS84 tangentnou transformáciou podľa povinnej `georeference` kotvy priamo v JSON scenári. SUMO x/y sú geometrické polohy prednej časti vozidla vo FCD, nie meranie GNSS. UTC z `simulation.utc_origin`; `generationDeltaTime` = uplynulé TAI milisekundy od 2004-01-01 00:00:00 UTC modulo 65536. Zaokrúhli polohu na 10⁻⁷ stupňa, výšku na cm, rýchlosť na cm/s, smer na 0,1°. | `waypoints.csv` a metadata SHA-256 vrátane použitej kotvy. Fixture zachováva pôvodné bratislavské hodnoty, teraz explicitne vo vstupe; georeferencovanie je stále iba registrácia **syntetickej** mapy. Kontrakt a regresný test sú v `docs/experiments/editable-v2-wgs84-enu-anchor.md`. |
| `src/editable-v2-cam-radio.cc` | Jeden spoločný ns-3 discrete-event čas a Vanetza `Runtime`; polohy každých 0,5 s aktualizujú `MobilityModel` aj GeoNetworking `PositionFix` vrátane FCD rýchlosti a kurzu. Zdroj vytvorí ETSI Release 2 CAM z vlastných FCD polí, ASN.1 UPER zakóduje, vloží BTP-B/CAM port 2001 a GeoNetworking single-hop broadcast. Ns-3 vysiela EtherType `0x8947` cez 802.11p `AdhocWifiMac`; každý prijímač volá Vanetza GN/BTP/CAM dekóder a porovná CAM polia s pôvodným zdrojovým riadkom. | Presné bajty a ns-3 časy každého TX/RX stupňa v `trace.csv`, dekódované polia v `*_decoded.csv`, pohyb, per-príjemca `delivery.csv`, surové PCAP. `event_id=0xCA00000000000000 | generationDeltaTime` je **mimopaketový korelačný identifikátor**, nie prenosové pole CAM. |
| `tools/check_editable_v2_cam_radio.py` | Nezávisle spáruje event ID, úplný UPER/GN/BTP hex, FCD polia, doručenia a 802.11 PCAP s LLC/SNAP `0x8947`. | `verification.json` a `packet-events.json` s konkrétnym TX obsahom a pozorovaným obsahom/časom každého príjemcu; pri dosahovej bráne akceptuje iba chýbajúci alebo prázdny RX PCAP; disektor overuje GN polohu, rýchlosť a smer oproti CAM vstupu. PCAP obsahuje nulový 4-bajtový FCS placeholder; skutočný FCS CRC teda neoveruje. |

SUMO opisuje [FCD polohu, rýchlosť a navigačný uhol](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html). Release 2 CAM definíciu zodpovedajúcu pripnutému súboru Vanetza `TS103900v231-CAM.asn` opisuje [ETSI TS 103 900 V2.3.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf). Rozdiel `AdhocWifiMac` a `OcbWifiMac` výslovne uvádza [ns-3 WAVE dokumentácia](https://www.nsnam.org/docs/release/3.35/models/html/wave.html). Kladný kanál používa [Friis voľný priestor](https://www.nsnam.org/docs/models/html/propagation.html), negatívny ten istý kanál s dodatočným `RangePropagationLossModel(MaxRange=1 m)`. Je to **umelá kontrola**, nie odhad reálnej straty.

## Rádiové a paketové podmienky

Pin: SUMO `1.18.0+dfsg-3build5`, ns-3 `3.48` commit `d2add90b452d600cfb4859baed8e9ea633519447`, Vanetza `v26.06` commit `fb6c551030dcc12b924299bf401e35e5fe814713`, lokálny OpenSSL runtime `3.0.13-0ubuntu3.16`. Model: `WIFI_STANDARD_80211p`, kanál 180 pri 5900 MHz, 10 MHz šírka, `OfdmRate6MbpsBW10MHz`, 20 dBm TX, 0 dB TX/RX zisk, 7 dB RX noise figure, Friis, konštantné šírenie. Vanetza MIB má vypnuté GN security a beaconing; prijímače nedostávajú iné aplikačné správy. Pohyb sa mení len pri 0,5 s FCD vzorkách, bez interpolácie v tomto adaptéri. Bez tienenia budov, fadingu, zmien počasia, kolízií viacerých CAM vysielačov, certifikátov, DCC zaťaženia a overenia regionálneho spektra. `AdhocWifiMac` sa iba podobá OCB; tento pokus **nepreukazuje úplnú ITS-G5/OCB zhodu** ani kalibrovanú PDR v skutočnej ulici.

V konkrétnom behu mala CAM UPER `41 B`; GeoNetworking `40 B` + BTP-B `4 B` + CAM `41 B` tvorilo `85 B` rámec nad EtherType `0x8947`. Rádiový PCAP má 24 B 802.11 MAC hlavičku, 8 B LLC/SNAP, 85 B GN/BTP/CAM a 4 nulové FCS placeholder bajty. Full raw hex je v stopách, napríklad prvý CAM TX a každý z troch RX majú rovnaký `event_id=ca00000000005a88`. Tester porovnáva úplné aplikačné a GN/BTP bajty, nie iba dĺžky alebo hashe.

## Reprodukcia, výsledok a neúspešné pokusy

Z koreňa repozitára bez `sudo`:

```bash
python3 tools/run_editable_v2_cam_radio.py data/inputs/editable-road-v2/packet-subset.json --output results/editable_v2_cam_radio
python3 tools/test_editable_v2_cam_radio.py
```

Runner používa existujúcu lokálnu `.venv` pre Astropy/TAI, vstupný JSON a FCD ukladá s hashmi; C++ kompiluje jedným `g++` procesom (`-O0`, žiadny paralelný build) a pri nezmenenom zdroji/knižniciach používa kontrolovanú binárnu cache. Výstupné `run-manifest.json`, `waypoints.metadata.json`, `verification.json` zachovávajú verzie, SHA-256 vstupov/zdroja/binárky a raw výstupov. `packet-events.json` je index podľa event ID s presnými TX bajtmi a výsledkom každého príjemcu. `positive/trace.csv`, `positive/delivery.csv`, `positive/positive_decoded.csv`, `positive/*.pcap` a rovnako `no_contact/` umožňujú kontrolu jednotlivého paketu v inspectore.

Kladný výsledok: `6` CAM vyslaných autom `car0`; `car1`, `car3` a `rsu0` prijali a dekódovali po `6`, teda `18/18` očakávaných doručení v tomto malom bezkolíznom fixture. Záporný variant: rovnakých `6` TX a `0/18` RX, pretože všetky polohy príjemcov boli viac ako `1 m` od vysielača (minimum `24,68 m`) a bol zapnutý dosahový model. Stĺpec `drop_reason=configured_1m_range_gate` označuje **konfiguráciu kontrolného variantu**, nie nezávisle zistenú príčinu individuálneho PHY dropu. Pri inom scenári by neprítomný RX zostal `not_observed_no_inferred_reason`. Kontrola vstupu odmietla šesť nepodporovaných prípadov: ďalší tok, DENM, satelitnú technológiu bez capability, menej ako dve vybavené autá, chýbajúcu ITS-G5 RSU a iný UTC počiatok. Prvý pokus spustiť runner systémovým Pythonom skončil `ModuleNotFoundError: astropy`; runner teraz automaticky použije projektovú `.venv` bez inštalácie balíka do systému.

## Ďalší dôkaz potrebný pre plný simulátor

WGS84/ENU kotva je teraz explicitná v JSON; pred pridaním satelitnej linky treba osobitne určiť výšku antén, sprístupniť ďalšie časové okná a per-node generátory paketov, otestovať súbežných vysielačov, zvoliť a overiť OCB alebo presne pomenovať zostávajúcu aproximáciu. Až potom možno viazať prijatý CAM z RSU na IP report a konkrétne paketové satelitné vrstvy. `satellite_terminal` v tomto behu zostáva iba deklarovaná schopnosť.
