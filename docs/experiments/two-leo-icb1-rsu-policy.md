# SUMO CAM → RSU ICB1 → riadený výber dvoch fyzických LEO ciest

**Stav 22. 10. 2026 UTC: prešlo.** Ide o prvý spoločný diskrétny čas ns-3.38/SNS-3 3.38, v ktorom sa šesť pohybových CAM z editovaného cestného návrhu spracuje na RSU a **jeden RSU UDP zdroj** vyberá medzi dvoma fyzicky oddelenými statickými satelitnými terminálmi. Archívne GP objekty 43253 a 43258 tvoria dve modelové pohyblivé LEO družice. Nie je to handover jedného rádia ani profil Iridium Certus: použité sú generické DVB-S2/RCS2 PHY/MAC, diagnostická všesmerová anténa 17 dBi, jedna manuálna 1 Gbit/s P2P ISL hrana a hypotetická pozemná GW.

## Hypotéza, scénar a párované kontroly

Výskumná otázka: pri spoločnom SUMO→CAM→RSU toku dokáže explicitná politika RSU vypustiť len správy zvoleného fyzického terminálu, zastaviť správy počas prestávky a zachovať na druhej trase presný aplikačný obsah? Model odpovedá na sieťovú a programovú otázku redundantnej RSU infraštruktúry. Nehovorí, či komerčný operátor v danom okamihu povolí attach, beam alebo crosslink.

Všetky behy používajú tú istú kreslenú cestu, SUMO seed **314159**, šesť WGS84 waypointov a CAM od `car0` v intervale **20,0–22,5 s**, UTC počiatok **2026-10-22 12:46:32Z**, ns-3 seed **314159/run 1**. `car1`, `car3` a `rsu0` prijímajú CAM cez `OcbWifiMac` 802.11p. RSU z *vlastného prijatého* 41 B UPER CAM vytvára nový **96 B ICB1** s ID udalosti, časom príjmu v µs, SHA-256 CAM a celým pôvodným CAM. Pozemná LAN k dvom UT má **100 Mbit/s** a zadané jednosmerné oneskorenie **100 µs**. UT0/SAT0 potom potrebujú modelový ISL do SAT1/feeder GW; UT1/SAT1 ide na feeder GW bez ISL.

| Variant | ISL SAT0→SAT1 | Potvrdenie výskumnej RSU trasy | Očakávaná GW prijatá informácia | Politika RSU |
| --- | --- | --- | --- | --- |
| `positive` | Áno | Áno | CAM udalosti 0, 1, 4, 5 | udalosti 2, 3 zahodené |
| `no_isl` | Nie | Áno | udalosti 4, 5 cez UT1 | udalosti 2, 3 zahodené; 0, 1 nemajú ďalšiu trasu |
| `no_confirm` | Áno | Nie | udalosti 0, 1 cez UT0 | udalosti 2–5 zahodené |

Výskumný stavový automat pri **20,700 s** zapíše `candidate_observed` z pevného scenárového harmonogramu, pri **20,800 s** `attach_requested` a prepne RSU do `Switching`, pri **21,600 s** buď `attach_confirmed`, alebo `attach_failed`. Počas **800 ms** `Switching` správy nezaraďuje do frontu ani nepreposiela; generované ICB1 sa označia `RSU_POLICY_DROP_SWITCHING` pred LAN. `attach_confirmed` znamená iba rozhodnutie *nášho RSU routera* používať už existujúci UT1. Nie je to udalosť rádiového pripojenia ani nameraná doba výpadku Iridia. Obe UT majú od začiatku vlastný modelový user PHY a statické priradenie cez `ut_sat_ids.txt`.

## Implementácia a dôkazový kontrakt

[`editable-v2-ocb-two-leo-rsu-policy.cc`](../../src/editable-v2-ocb-two-leo-rsu-policy.cc) prijíma CSV waypointy z editovaného scenára. Pri každom RSU dekódovanom CAM volá `make_report`: vstup sú pôvodné CAM bajty a ID, výstup 96 B ICB1. `offer_rsu_report` vyhodnotí `Sat0`/`Switching`/`Sat1` a pošle ICB1 **jediným RSU UDP socketom** do `10.91.0.2:45000`, zahodí, alebo pošle do `10.92.0.2:45000`. Na UT sa kontroluje obsah ICB1 a vytvorí sa nový UDP/IP datagram do GW. Funkcia serverového príjmu overuje ICB1 a zhodu vnútornej CAM s waypointom. Pasívny callback na prijímacom ISL zariadení ukladá **celý 124 B IPv4/UDP paket**; nie sú to proprietárne rádiové bajty. Výstup `trace.csv` obsahuje každú etapu, ID, µs čas, dĺžku a hex, vedľa `PacketTrace.log` a 802.11/PPP PCAP.

[`run_two_leo_icb1_rsu_policy.py`](../../tools/run_two_leo_icb1_rsu_policy.py) odvodí RSU WGS84 UT polohu zo SUMO waypointu, rekonštruuje TLE z hashovaného OMM, kontroluje pripnuté ns-3/SNS-3/Vanetza commity a presný [patch priradenia dvoch UT](../../patches/sns3-338-static-ut-sat-id.patch). Oba konštelačné vstupy sú bitovo rovnaké okrem `isls.txt`; `no_confirm` používa pozitívnu topológiu. Ukladá road JSON, FCD, waypointy, anténnu mapu, satelitné textové vstupy, build log, binárny program, všetky stopy a SHA-256 manifest. Pri opakovaní sa nový výstup musí písať do prázdneho adresára.

[`check_two_leo_icb1_rsu_policy.py`](../../tools/check_two_leo_icb1_rsu_policy.py) kontroluje: pôvod scenára a archívu; celé 802.11 PCAP vrátane GN/BTP/CAM; zhodu 41 B CAM na odosielateľovi a RSU; 96 B ICB1, jeho ID/čas/SHA-256; rovnaké CAM/reporty v troch párovaných behoch; predpísané RSU drop/admit udalosti; všetky PPP LAN IPv4/UDP dĺžky, checksumy, čas a rovnaký RSU zdrojový port; UT satelitné `PacketTrace` ID a SAT0/SAT1/GW osud; celý ISL IPv4/UDP obsah a negatívnu jednobajtovú mutáciu checksumu. Pre prvé dva ISL pakety nezávisle prepočíta UT/SAT0, SAT1/GW a zemský zákryt; pre oba priame UT1/SAT1 pakety kontroluje UT a GW eleváciu nad **výskumnou 10° maskou**. Skyfield/Astropy používajú rovnaké GP elementy, a preto táto kontrola nie je nezávislou validáciou orbity alebo aktívneho beamu.

## Surový výsledok a interpretácia

| Veličina | `positive` | `no_isl` | `no_confirm` |
| --- | ---: | ---: | ---: |
| CAM odoslané `car0`; pozemné dekódované príjmy | 6; 18 | 6; 18 | 6; 18 |
| ICB1 vytvorené RSU | 6 | 6 | 6 |
| RSU vpustené do LAN/UT/satelitnej ponuky | 4 | 4 | 2 |
| RSU politikou zahodené pred LAN | 2 | 2 | 4 |
| Modelová ISL nesie celý ICB1/IP/UDP | 2 | 0 | 2 |
| GW prijaté z 6 RSU reportov | **4/6** | **2/6** | **2/6** |
| CAM TX→GW úspešné časy v µs | 127 114; 122 130; 106 056; 105 708 | 113 033; 105 716 | 127 114; 122 130 |
| Priemerná absolútna zmena susedných úspešných časov v µs | 7 135,3 | 7 317 | 4 984 |

Posledná metrika je presne definovaná z doručených sekvencií; strateným správam sa oneskorenie nepriraďuje. Pri 4 alebo 2 úspešných správach z jediného nezaťaženého seedu to nie je odhad prevádzkového jitteru ani predikcia operátora. Rozdiel v úspešnom čase UT1 medzi `positive` a `no_isl` sa nesmie vykladať ako čas ISL na UT1 trase: tá ISL nepoužíva. Je to iba konkrétne časovanie dvoch generických DVB behov po zmene topológie.

V kladnom `PacketTrace` sú ID **494, 520** na UT3/SAT0 a **579, 601** na UT5/SAT1; prijímací ISL callback zachytil presný ICB1 prvých dvoch reportov. `no_isl` ponechala rovnaké vstupné CAM a RSU ICB1, ale SAT0 reporty sa nedostali na GW; UT5/SAT1 doručila posledné dva. `no_confirm` nevytvorila na druhej LAN žiadny aplikačný rámec. Geometria prvých dvoch ISL paketov dala eleváciu UT→SAT0 približne **13,809–13,861°** a SAT1→proxy GW **36,465–36,566°**. Pri priamych UT1 paketoch bola UT→SAT1 **13,755–13,807°** a SAT1→proxy GW **36,845–36,946°**. Maska je scenárový parameter, nie operátorská servisná záruka.

Prvý návrh checkera zlyhal pri párovaní ID, pretože `PacketTrace` čas zaokrúhľuje a v jednom PHY riadku môže niesť viac ID. Kontrola bola upravená na malé zdokumentované časové okno a vyhľadanie ID aj v zbalenom PHY riadku; C++ simulácia, CAM/report bajty a počty doručení sa pri tejto oprave nemenili. Predchádzajúci 16 B [izolovaný test politiky](two-leo-dual-ut-rsu-policy.md) ostáva samostatnou menšou kontrolou.

## Reprodukcia, jednotky a hranice

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_two_leo_icb1_rsu_policy.py \
  /tmp/ns3-sns3-338-feasibility results/two_leo_icb1_rsu_policy_repeat
.venv/bin/python tools/check_two_leo_icb1_rsu_policy.py \
  results/two_leo_icb1_rsu_policy_repeat
```

Overené stopy sú v ignorovanom `results/two_leo_icb1_rsu_policy_verified_v2/` a `verification.json`; manifest hashoval vstupy, zdroje, binárny súbor a surové výsledky. Časy v logu sú **µs** od uvedeného UTC začiatku, WGS84 súradnice sú **stupne/metre**, vzdialenosti orbity **km**, rýchlosti LAN/ISL **bit/s**. Satelitný model má statické user PHY priradenie, bez meranej registrácie/hand-over signalizácie, dynamického beamu, kalibrovaného RF link budgetu, skutočnej Iridium gateway/core cesty, služby či meraného výpadku. Výsledok preto zatiaľ môže porovnávať iba **presne definované výskumné topológie**, nie efektívnosť Starlinku, Iridia a Globalstaru v reálnej sieti. Ďalším krokom je preskúmať single-radio PHY/MAC prechod alebo priznať dvojterminálovú architektúru ako samostatnú vetvu, potom modelovať zaťaženie, fronty a merať/citlivo ohraničiť konkrétnu terminálovú službu.
