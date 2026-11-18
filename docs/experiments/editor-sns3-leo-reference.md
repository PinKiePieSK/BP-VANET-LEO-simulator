# Editorový dopravný scenár → spoločný OCB/CAM/LEO DVB beh

## Účel a hranica tvrdenia

Tento míľnik prepája aktuálne uložený návrh cesty a polohy RSU s už overenou paketovou cestou SUMO → Vanetza CAM/GN/BTP → ns-3.38 OCB/802.11p → RSU report ICB1 → modelová LAN → SNS-3 3.38 UT → pohyblivá družica → proxy GW. Model používa **jediný archivovaný GP objekt 37741**, predpísané UTC `2026-10-22T12:45:00Z`, výskumné user a feeder lúče DVB-S2/RCS2 a **hypotetickú** bránu. Nie je implementáciou konkrétnej služby Globalstar, Iridium alebo Starlink. Je to test paketovej integrácie pri zmenenej cestnej geometrii a pevne definovanej satelitnej geometrii.

UI odmieta nepodporované návrhy. Zatiaľ musí zostať štvoruzlový aktívny OCB podscenár (`car0`, `car1`, `car3`, `rsu0`), jeden zdroj CAM, semeno 314159, šesť vzoriek v čase 20–22,5 s po 0,5 s, UTC a `ip_backhaul` na RSU. Meniť možno geometriu cesty a pozíciu RSU v oblasti 32–54° N, 10–30° E za podmienky minimálnej 10° modelovej elevácie UT aj GW. Server navyše overuje, či posúvaná SNS-3 mapa obsahuje RSU aj pri inicializácii v t=0 a v každej polsekunde do t=25 s; geografický obdĺžnik sám teda nezaručuje prijatie návrhu. Ďalšie vozidlá v návrhu sa môžu zúčastniť SUMO dopravného výpočtu; táto satelitná sonda ich neprehlasuje za rádiových účastníkov. Editor preto zatiaľ nedokazuje porovnanie ľubovoľného počtu áut ani operátorských konštelácií.

## Algoritmus a dátový kontrakt

1. `tools/scenario_server.py` prijme JSON cez `POST /api/draft-leo-runs`, znovu ho validuje a uloží nemenný vstup behu do `results/editable_leo_runs/<id>/scenario.json`.
2. `tools/run_editable_v2_ocb_sns3_leo_reference.py` spustí SUMO z aktuálneho návrhu. `tools/prepare_editable_v2_cam.py` prevedie FCD do presne šiestich geodetických waypointov; `rsu0` musí byť stacionárne vo všetkých šiestich vzorkách. Vozidlové polohy sú v metroch ENU, geodetické súradnice vo WGS84 E7, čas v mikrosekundách.
3. Z polohy `rsu0` sa vytvorí UT súradnica. Runner skontroluje pripnuté commity ns-3, SNS-3 a Vanetza, archívny TLE/OMM a EOP; do izolovaného checkoutu vytvorí pomenovaný `ut_positions.txt` a dvojicu máp user/feeder. Ich obsah archivuje a hashuje v `network/leo_input/`. Boresight user lúča mieri pri t=20 s na UT, feeder lúča na proxy GW. Výskumný HPBW je 22°, vrchol približne 17,465 dBi a grid 0,25°. Počas krátkeho okna SNS-3 mapy posúva; samostatný 3D výpočet kontroluje rozdiel zisku do 0,5 dB. Guľová Zem SNS-3 sa porovnáva s WGS84, nejde o identické modely.
4. Zostaví sa jeden C++ program a spustia sa párované varianty `positive` a `blocked`. Oba používajú rovnaké waypointy/pozemné bajty. Blokovaný variant zakáže iba UT satelitné aplikačné odoslanie. V pozitívnom variante vznikne ICB1 až po prijatí konkrétneho CAM na RSU; report nesie presný CAM, ID, RSU čas a SHA-256. Všetky časy má jediný ns-3 event clock.
5. `tools/check_editable_v2_ocb_sns3_dvb_gate.py` overí šesť CAM, GN/BTP hlavičky, OCB PCAP, pôvod ICB1, prijatie na bráne, rovnosť bajtov pred a po satelitnom segmente, internú `PacketTrace` cestu a nulové doručenie v kontrole. Runner navyše overí šesť geometrií a uloží `verification.json`/`run-manifest.json` s hashmi.
6. `GET /api/draft-leo-runs/<id>/packets` pred každým zobrazením znovu skontroluje manifest, zdroj, runner, checker, vstupné mapy, SUMO FCD/waypointy, surové trace a PCAP aj bajtový audit. `viewer/leo-reference-packet.html` zobrazí originálne hexy každej fázy, pole ICB1 podľa offsetu, modelovú geometriu a vizuálne interpolovaný dopravný pohyb. Prehrávanie je iba zobrazenie šiestich uložených polôh a nespúšťa ďalší sieťový výpočet. Rovnakú kontrolu používa sťahovanie OCB PCAP.

## Výstupy a interpretácia

`network/waypoints.csv` má dopravné a RSU polohy. `network/{positive,blocked}/trace.csv` obsahuje `stage,node_id,event_id,time_us,bytes,raw_hex`; bajty CAM a ICB1 sú aplikačné bajty v uvedených fázach. `ocb-*.pcap` sú surové pozemné rádiové rámce. `PacketTrace.log` zaznamenáva interné PHY/MAC udalosti satelitného úseku a ID paketu, **neobsahuje bajty satelitného PHY payloadu**. Korelácia ID PacketTrace s jedným riadeným tokom je časový dôkaz priechodu, kým zhodu obsahu potvrdzuje porovnanie aplikácie na UT a GW. `leo_input/` uchováva presný satelitný vstup a obe anténne mapy. `verification.json` obsahuje metriky v µs a geometriu v stupňoch, kilometroch a dBi. Ani úspech všetkých šiestich nezaťažených správ nie je meraním reálnej PDR, komerčnej latencie alebo mobility terminálu medzi družicami.

## Opakovanie

Z koreňa projektu, s pripnutým izolovaným checkoutom a pripravenými lokálnymi závislosťami:

```bash
.venv/bin/python tools/run_editable_v2_ocb_sns3_leo_reference.py \
  /tmp/ns3-sns3-338-feasibility /tmp/moj-editor-leo-beh \
  --scenario data/inputs/editable-road-v2/packet-subset.json
.venv/bin/python tools/check_editable_v2_ocb_sns3_dvb_gate.py \
  /tmp/moj-editor-leo-beh leo
```

Výstupný priečinok musí byť nový alebo prázdny. Pre UI spusti `.venv/bin/python tools/scenario_server.py --port 8765`, otvor `/draft-editor.html`, uprav scénu a použi tlačidlo „Spustiť OCB CAM → LEO DVB user/feeder“. Po dokončení otvor odkaz na paketovú stopu; API výsledok odmietne, ak sa ktorýkoľvek sledovaný vstup alebo surová stopa medzičasom zmení.

## Kontrolné varianty a zistené obmedzenia

Rovnaký runner bol spustený na predvolenom a upravenom návrhu. Upravený návrh posunul RSU z `x=490` na `495 m` a zmenil stred cesty z `y=600` na `610 m`. Tým sa zmenila WGS84 dĺžka UT, FCD/waypointy i hash lúča, pričom rovnaký satelitný kandidát a dátová schéma umožnili izolovať dopad editácie. Oba modelové varianty doručili šesť správ a v blokovanej kontrole nula. Hodnoty sú funkčnou kontrolou prenosu, nie porovnaním výkonnosti konštelácií. V ďalšom míľniku treba dodať zdokumentované terminálové, kapacitné a servisné profily a viacsemenné experimenty pred výrokmi o efektívnosti.

HTTP beh upraveného návrhu je uložený pod `results/editable_leo_runs/20261022T200332Zbef19892/`. API oznámilo `cam_tx=6`, `radio_cam_decodes=18`, `rsu_reports=6`, `gateway_reports=6`, `blocked_gateway_reports=0` a priemerný aplikačný čas **113 329 µs**. Rozbor v prehliadači zobrazil všetkých šesť udalostí, presný 96 B ICB1 vrátane 41 B CAM a SHA-256, šesť modelových geometrií a oba varianty OCB PCAP. Zmena cesty zmenila prvú polohu `car0` z `(428,23; 598,40)` na `(427,91; 602,01) m`; posun RSU zmenil UT dĺžku z `17,1035340` na `17,1036012° E`. SHA-256 user mapy sa zmenil z `3e8935ca…` na `97d0b225…`; feeder mapa ostala identická, lebo proxy GW sa nemenila. Kópia behu s jedným pridaným bajtom v pozitívnom `trace.csv` bola odmietnutá; POST s iným semenom vrátil HTTP 400. Pôvodný výsledok ostal nezmenený.
