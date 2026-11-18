# U8 – architektúra, register možností a obhajoba

## Priechod správy

```text
Scenár + dopyt + UTC → preflight → SUMO mobilita → ns-3 ITS-G5 / CAM
→ príjem na RSU → ICB1 report → lokálna / pozemná / generická LEO cesta
→ aplikácia na vzdialenom konci → odpoveď → auto
                                            └ servisný replay: potvrdenie na RSU
                         raw stopy + manifest → checker → udalosti a metriky
```

SUMO pripraví pohyb a U7 z neho vytvorí pozemnú realizáciu V5. U2 používa tento vstup pre lokálny a pozemný paketový model. U3 (jeden satelit) alebo U4 (viac satelitov, parametrická fyzika) používajú overené pozemné reporty. U5 dokáže aplikovať modelové servisné pravidlá na tie isté reporty. U6/U7 zachovávajú identitu udalosti, zdroje a menovatele výsledkov. Viac motorov so spoločným scenárom a kontrolami nie je jediný monolitický proces pre všetky režimy. U3/U4 majú jeden pevný UT pri zvolenej RSU a jednu bránu.

**CAM** je správa o stave vozidla. **ICB1** je projektový report vytvorený RSU z prijatej CAM. **GRA1** je projektová odpoveď vzdialenej brány a **I2V1** jej následné doručenie do vozidla. Názvy ICB1/GRA1/I2V1 sú projektové kontrakty, nie názvy normovaných operátorských protokolov. `generated_cam`, `report_created`, `remote_timely`, `return_timely` sa počítajú pre definovanú populáciu a deadline; podiel používa uvedený menovateľ, nie počet všetkých áut. Neprijaté, pozdné a nepozorované udalosti sa nesmú zamieňať. Servisný endpoint je RSU, paketový návrat je vozidlo.

## Register schopností

| Schopnosť | Stav a dôkaz | Hranica tvrdenia |
|---|---|---|
| ITS-G5, CAM, mobilita, viac áut a RSU | `implemented`: U2/U7 a raw checkery | Výskumná podmnožina CAM/DCC; U7 zapína DCC `false`. Nie úplná ETSI konformita ani kalibrácia konkrétnej križovatky. |
| Lokálna a pozemná vetva | `implemented`: U2 raw paketová cesta | Modelové parametre a deklarované endpointy; nejde o meranie existujúcej pozemnej siete. |
| LEO, obojsmerný ISL a prepnutie UT | `implemented`: U3/U4 generické SNS-3 DVB, kontrolované stopy | Jeden fixný UT/GW, podporovaný strom a geometria; OMM dáta sú historické a žiadna geometria nepotvrdzuje komerčnú dostupnosť. |
| Výkon/zisk, kapacita a fronta | `sensitivity`: U4 parametrický model a jeho analytické checkery | Hodnoty sú diagnostické predpoklady; nie sú potvrdením skutočnej RF/MAC prevádzky operátora. |
| Starlink/Iridium/Globalstar servisné profily | `implemented` ako `service_boundary_replay`; `sensitivity` | Model na hranici služby, návrat iba na RSU; dostupnosť, MAC, scheduling a výkon nie sú kalibrované voči operátorovi. Globalstar MO/MT sa nesmie vydávať za IP/ISL. |
| Externá kalibrácia a validácia služby | `calibrated`: **žiadna preukázaná operátorská kalibrácia** | Potrebné párované nezávislé merania rovnakého miesta, času, terminálu, služby a endpointov. |
| NLOS/budovy a DCC | `implemented` v starších V5 prípadoch s ich vlastnými checkermi | Priamy U7 scenár ponúka iba `urban_los` alebo `friis`, DCC vypnuté; nepripisovať ich automaticky každému U7 behu. |
| DENM, C-V2X, PKI, útoky, priame/mobilné UT | `unsupported` v overenej U7 ceste | Nevyvodzovať bezpečnosť, odolnosť proti útokom alebo vlastnosti priamych terminálov v autách. |
| Riadiaci účinok na dopravu | `unsupported` v overenej U7 ceste | Mobilita nie je spätne ovládaná výsledkom správy; nemožno tvrdiť pokles nehôd či zlepšenie plynulosti. |
| Všeobecný mix aplikácií a ľubovoľné toky | `unsupported` v spoločnom U7 scenári | Overený priechod je CAM → ICB1, nie generátor ľubovoľných aplikácií ani plnohodnotná prevádzková záťaž operátora. |
| Automatické prevedenie všeobecnej kreslenej mapy na U7 | `unsupported` | Použiť kompatibilný world/dopyt v `data/inputs`; kreslený návrh je samostatný. |

## Register parametrov spoločného scenára

Jednotným zdrojom pravdy je `tools/bp_u7.py:normalized`, šablónou `config/u7-scenarios/reference.json`; kontrola hraníc ďalších podmodelov je v `tools/run_v5_ground.py`, `tools/u3_preflight.py` a príslušných U2–U5 checkeroch. Žiadne číslo tu neznamená nameranú hodnotu operátora.

| Položka JSON | Jednotka / povolenie | Pôvod a použitie |
|---|---|---|
| `world_template`, `demand` | cesty pod `data/inputs/` | Vstup autora, validovaná mapa, technológie a dopyt; SUMO/V5. Označenie syntetický alebo meraný dopyt vyplýva zo vstupu. |
| `source_id`, `rsu_id` | existujúce ID | Referenčný vysielač a RSU s UT; všetky podporované vozidlá vysielajú CAM. |
| `seed`, `ns3_run` | celé číslo 1 až 2³¹−1 | Nastavenie náhodnosti; jedna realizácia nepostačuje na štatistickú neistotu. |
| `utc_origin` | UTC `YYYY-MM-DDTHH:MM:SSZ` | Autor; časová väzba orbitálnych vstupov, preflight posúdi podporu. |
| `sample_count` | 20–100 vzoriek po 0,1 s | V5 mobilita; začiatok vzorkovania je v U7 pevne 10 s. Nie je to automaticky počet úspešných správ. |
| `radio.mode`, `tx_power_dbm`, `noise_figure_db` | `urban_los`/`friis`; 0–33 dBm; 0–20 dB | V5 pozemné rádio; výskumné scenárové hodnoty. |
| `backhaul.mode` | `local`, `ground`, `native_generic_dvb`, `service_boundary_replay` | Výber U2/U3/U4/U5; žiadne tiché prepnutie režimu. |
| `service_profile`, `service_case` | podporované páry `config/v6_service_contract.json` | U5 modelové IP alebo MO/MT obmedzenia, pravdepodobnosti a stav; zdroj a citlivosť sú v servisnom registri a U5 manifeste. |
| `catalog_ids`, `isls` | identifikátory a dvojice indexov | Archivovaný OMM, overená geometria/čas, strom na použitých trasách; nemusí znamenať skutočnú operátorskú sieť. |
| `initial_serving_sat`, `handover_target_sat`, `feeder_sat` | indexy satelitov alebo `null` pre cieľ pri jednom satelite | Generický scenárový handover a trasa, nie skutočný attach/scheduler operátora. |
| `gateway`, `mask_deg` | zemepisná šírka a dĺžka v °, výška v m; elevačná maska v ° | Scenárová brána a viditeľnosť; preflight overuje geometriu. |
| `beam_gain_dbi`, `ut_power_dbw` | −10 až 50 dBi; −50 až 20 dBW | U4 generická RF citlivosť; U3 jeden satelit pevne 17 dBi a 4 dBW. |
| `forward_isl_bps`, `reverse_isl_bps` | 100 až 10¹⁰ bit/s, celočíselne | Smerová U4 kapacita; U3 referencia je 10⁹ bez ISL. |
| `forward_queue_packets`, `reverse_queue_packets` | 1–10 000 paketov | Smerová U4 fronta; U3 referenčné hodnoty 100 bez ISL. |
| `deadline_us` | 1–3 600 000 000 µs od vytvorenia RSU reportu | Autor; výsledkový U6/U7 kontrakt, nie vlastnosť operátora. |

Hard preflight limit je 2 a viac áut, 1–20 RSU a spolu najviac 50 rádiových uzlov. Otestované konkrétne veľkosti a časové/pamäťové náklady sú oddelené v prijímacom denníku U8; tento limit neprezentovať ako výkonovo otestovaný v celej kombinatorike. Nefixované topológie, dáta a profily podliehajú následným kontrolám.

## Obhajoba a zatiaľ nerozhodnutý rozsah G19–G22

Pozitívny modelový príklad a záporný príklad výpadku s presnými cestami, príkazmi a výsledkami sú v [U7 denníku](experiments/u7-unified-control-2026-10-27.md). Použi príslušný `bp_u7.py verify-analysis` a `event` alebo webový prehliadač správy; netvrď, že modelový príklad je meranie v teréne. Reprodukovateľné vydanie a hash sú v [U8 denníku](experiments/u8-release-2026-10-27.md).

G19 (úplná ETSI zhoda), G20 (dopravný účinok), G21 (DENM/C-V2X), G22 (bezpečnosť, útoky a priame UT) sú podmienené rozhodnutím o finálnej téme s vedúcim. Pre súčasné overené sieťové experimenty ostávajú mimo podporovaných tvrdení; táto voľba nie je schválením výskumnej otázky vedúcim. Pred záverečnou kampaňou treba dohodnúť aplikáciu, deadline, endpointy, scenáre a nezávislé epochy/semená.

Neznáme na získanie: skutočná topológia a priradenie beamov/brán v čase, účinné rádio a anténa konkrétneho terminálu, MAC/scheduler a záťaž, reálna dostupnosť a výpadky, SLA a veľkostné/latenciové limity konkrétneho SKU, miestne tienenie a nezávislé párované terénne stopy. Neznáme zostávajú predpokladom alebo intervalom citlivosti, kým sa nepreukážu meraním alebo relevantným verejným zdrojom.
