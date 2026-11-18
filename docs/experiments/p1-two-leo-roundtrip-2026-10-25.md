# P1: obojsmerná dvojdružicová referenčná cesta

**Stav 25. 10. 2026:** PASS. Jeden ns-3.38/SNS-3 3.38 event clock spája šesť skutočne dekódovaných SUMO/Vanetza CAM s RSU ICB1, dvojdružicovým modelom a spätnou odpoveďou GRA1/I2V1 až do auta. Finálny surový beh je v `results/native_two_leo_roundtrip_p1_final_20261025`; `run-manifest.json` obsahuje SHA-256 zdroja, runnera, vstupov a raw výstupov. Tento adresár neprepisovať. Prvý úspešný vývojový beh `results/native_two_leo_roundtrip_p1_20261025` je zachovaný, ale jeho zdrojový hash už nezodpovedá finálnemu C++ súboru.

## Cesta a meranie

`car0 CAM UPER 41 B → GN/BTP → 802.11p OCB → rsu0 → ICB1 96 B → 100 Mb/s LAN → UT → SNS-3 DVB user link → SAT0 → modelová P2P ISL → SAT1 → feeder → proxy GW → GRA1 46 B → SAT1 → opačná ISL → SAT0 → UT → LAN → RSU → experimentálne OCB I2V1 50 B → car0`.

GRA1 nesie pôvodné 8 B `event_id` a SHA-256 **celého presného ICB1**, ktorý vznikol až pri príjme CAM na RSU. I2V1 nesie rovnaké ID/hash, cieľovú stanicu 1001 a stav 0. GW odosiela GRA1 v callbacku prijatia reportu, bez držania do konca okna CAM. Preto sa surový OCB stav neskorších variantov môže legitímne líšiť; checker kontroluje pôvod každého variantu z jeho vlastného prijatého CAM.

| Variant | CAM TX / pozemné RX | RSU ICB1 / GW prijatie | Opačná ISL / auto I2V1 |
| --- | ---: | ---: | ---: |
| `positive` | 6 / 18 | 6 / 6 | 6 / 6 |
| `no_isl` | 6 / 18 | 6 / 0 | 0 / 0 |
| `blocked` | 6 / 18 | 6 / 0 | 0 / 0 |
| `no_return_route` | 6 / 18 | 6 / 6 | 0 / 0 |

`no_isl` mení jediný modelový ISL vstup z `1\n0 1\n` na `0\n`; `blocked` vypína iba UT satelitné odoslanie. Pri `no_return_route` sa nedovolí odoslať GRA1, lebo kvalifikovaná návratová cesta SAT1→ISL→SAT0 nebola nastavená. Ide o explicitnú aplikačnú politiku smerovania, nie dôkaz, že samotný SNS-3 routing pri fyzickom výpadku zlyhá. Kladný prípad nastavuje GW/ARP trasu na feeder SAT1 podľa skôr izolovane overeného `UpdateGwRoutes`; surový `PacketTrace` potom potvrdzuje SAT1 a SAT0 v tomto poradí.

Čas **CAM TX → I2V1 RX v aute** v kladnom variante: 0,164229; 0,147230; 0,145182; 0,145135; 0,145166; 0,145184 s. Medián 0,145183 s, maximum 0,164229 s. Všetkých 6/6 je pred výskumným deadline P0 60 s aj citlivostnými 1 s a 10 s. Medián od CAM po RSU príjem bol 0,216 ms, po UT LAN 0,327 ms, po GW prijatie 120,120 ms, po UT príjem GRA1 144,903 ms, po RSU príjem GRA1 145,009 ms. `roundtrip-verification.json` ukladá všetky časy a ID paketov po fázach; nevypočítavame p99 zo šiestich udalostí.

## Surový audit a reprodukcia

`tools/check_two_leo_roundtrip.py` znovu číta `trace.csv`, šesť OCB/LAN PCAP súborov, oba celé IPv4/UDP pakety z ISL callbackov, `PacketTrace.log` a manifest. V každom prípade porovná ICB1 s prijatým CAM, GRA1 s SHA-256 ICB1, I2V1 s GRA1, časy a kontrolné súčty IPv4/UDP. Páruje IP pakety na obe SNS-3 smerové trasy a odmieta priamy návrat mimo SAT1→ISL→SAT0. V záporných variantoch vyžaduje neprítomnosť odpovede. Test mení bajt v oboch ISL smeroch a overuje zlyhanie checksumu; ďalší zmení GRA1 hash v raw trace, aktualizuje manifest a vyžaduje zlyhanie sémantického checkera.

```bash
cd '/home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca'
.venv/bin/python tools/run_two_leo_roundtrip.py vendor/ns-3.38-ocb-eval results/MOJE_NOVE_UNIKATNE_P1_ID
.venv/bin/python tools/check_two_leo_roundtrip.py results/MOJE_NOVE_UNIKATNE_P1_ID
.venv/bin/python -m unittest discover -s tools -p 'test_two_leo_roundtrip.py'
```

Runner odmieta neprázdny cieľ. Pôvodné forward-only zdroje/výsledky zostali zachované, aby ich checker ďalej vedel prehrať. Nový C++ zdroj používa rovnaký pinned scenár a kód OCB/ICB1, doplnený iba o spätnú vetvu a jej kontrolu. Kompletná Python sada po P1: **51 testov OK**.

## Rozsah tvrdenia

Toto je **výskumný referenčný DVB model**, nie meranie Starlinku, Iridia ani Globalstaru: 17 dBi diagnostická anténa, ideálna modelová ISL, proxy brána a archívna orbita nepreukazujú aktívny lúč, komerčný MAC/scheduler ani reálnu dostupnosť služby. Jeden seed, jedna retrospektívna UTC epocha, šesť správ a jednoduchý Friis OCB nestačia na odhad produkčnej PDR, tail latencie či mestského účinku. Jeden trvalo pripojený UT v tomto behu nerobí handover. Tieto medzery patria do P2/P3/P4 podľa [pracovného plánu](../pracovny-plan-simulatora.md).
