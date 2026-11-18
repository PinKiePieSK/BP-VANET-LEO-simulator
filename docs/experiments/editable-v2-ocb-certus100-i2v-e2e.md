# Prírastkový I2V návrat: serverové GRA1 → RSU → auto cez OCB

## Otázka a kontrolný variant

Cieľom tohto prírastku je zistiť, či možno v **tom istom ns-3.38 čase** poslať výsledok serverového overenia ICB1 od RSU späť do pôvodného auta. Východisková cesta zostáva CAM→RSU→terminál→syntetický Certus 100 IP servis→server→GRA1→RSU podľa [predchádzajúceho experimentu](editable-v2-ocb-certus100-e2e.md). Nový kód je samostatný experiment na tom istom modeli, nie druhý „finálny“ simulátor. Predošlý zdroj, checker, výsledky a manifest sa nemenia.

Pozitívny variant má šesť geometriou povolených reportov; syntetický negatívny variant blokuje satelitného kandidáta. V oboch musia byť zhodné CAM a ICB1 bajty. V zápornom variante nesmie existovať servisný frame ani I2V1 správa. Fixné RNG semeno je 314159, beh 1. Družica je len geometrický RSU user-leg kandidát a jej vypočítaná vzdialenosť ani vákuové šírenie sa **nepripočítavajú** k nepriehľadnému servisnému obalu.

## Formát a vrstvy

`I2V1` je **vlastný experimentálny lokálny L2 receipt notice**, nie CAM, DENM, GeoNetworking/BTP aplikačná správa, ani Iridium rádiový ACK. Prenáša sa na OCB `WifiNetDevice::Send()` ako unicast RSU→`car0` s EtherType `0x88B5`. Tento EtherType je vedený ako „IEEE Std 802 – Local Experimental Ethertype“ v [registri IANA/IEEE](https://www.iana.org/assignments/ieee-802-numbers); [IEEE Registration Authority FAQ](https://standards.ieee.org/faqs/regauth/) vysvetľuje jeho použitie pri vývoji protokolu. OCB model v [oficiálnej dokumentácii ns-3](https://www.nsnam.org/docs/release/3.35/models/html/wave.html) umožňuje komunikáciu bez asociácie. Úspešný test dokazuje správanie nakonfigurovaného simulátora, nie terénnu spoľahlivosť PHY.

Presne 50 B I2V1, v sieťovom poradí bajtov:

| Offset | Dĺžka | Význam | Zdroj |
|---:|---:|---|---|
| 0 | 4 B | ASCII `I2V1` | náš experimentálny formát |
| 4 | 1 B | verzia `0x01` | náš formát |
| 5 | 8 B | event ID | overené GRA1 od servera |
| 13 | 4 B | cieľové `station_id=1001` (`car0`) | CAM/waypoint konfigurácia |
| 17 | 32 B | SHA-256 celého ICB1 | overené GRA1, ktoré ho prevzalo zo serverového výpočtu |
| 49 | 1 B | status `0` (lokálne „report prijatý serverom“) | overené GRA1 |

RSU vytvorí I2V1 **až po `valid_ack(GRA1)`**, ktoré kontroluje ID a SHA-256 reportu. V tomto kontrolovanom pilote sa vysielanie notice odloží na 22,600 až 22,650 s simulačného času po skončení šiestich CAM (rozstup 10 ms). Toto je explicitný experimentálny hold, **nie prevádzková reakčná doba služby**. Auto kontroluje verziu, typ, cieľový station ID a známe event ID vlastného CAM. Checker mimo simulovaného vozidla potom porovná celé I2V1 so serverovým GRA1 a presnými bajtmi v OCB PCAP. Týmto auditným porovnaním netvrdíme, že vozidlo samo pozná celý serverový ICB1 report. Cieľové mapovanie `station_id=1001`→MAC `car0` je v pilote známe priamo z konfigurácie; reálne ITS pseudonymy, objavovanie cieľa, bezpečnostné podpisy a oprávnenia nie sú modelované.

L2 unicast v pilote prešiel; broadcast fallback sa nepoužil. PCAP ukazuje 88 B QoS dátový OCB rámec: 26 B 802.11 MAC, 8 B LLC/SNAP s `0x88B5`, 50 B I2V1 a 4 B simulátorový FCS placeholder. Po unicaste vzniká samostatný 14 B **802.11 MAC ACK riadiaci rámec**. Tento MAC ACK potvrdzuje lokálne prijatie rámca v modeli; **nie je to GRA1**, ani nový I2V1 aplikačný ACK, ani potvrdenie služby Iridium.

## Reprodukcia, raw audit a výsledok

```bash
.venv/bin/python tools/run_editable_v2_ocb_certus100_i2v_e2e.py
```

Runner kompiluje jediným `g++` procesom s 90 s timeoutom, opakuje SUMO/waypoints, overuje SHA-256 scenára, archivovaného orbitálneho snapshotu, geometrie a generátora. Výstupy sú v `results/editable_v2_ocb_certus100_i2v_e2e/`: pre každú vetvu `trace.csv` s raw hex bajtmi a časmi, OCB/LAN/servis PCAP, geometria s metadata, `delivery.csv`, `run.log`; v koreni `build.log`, `check.log`, `verification.json`, `run-manifest.json`.

`tools/check_editable_v2_ocb_certus100_i2v_e2e.py` kontroluje presnú skladbu každej I2V1, SHA-256 voči GRA1 a ICB1, čas `RSU_ACK_RX < RSU_I2V1_TX < CAR0_I2V1_RX` a naplánovaný hold, cieľovú a zdrojovú MAC adresu, LLC/SNAP EtherType `0x88B5`, 50 B payload, oddelené 14 B MAC ACK rámce a neprítomnosť I2V pri zablokovaní. Porovná aj všetkých šesť ICB1 s verzovaným fixture z predošlého prijatia RSU CAM, takže regresia upstream bajtov test zlyhá.

Počiatočný okamžitý unicast fungoval 6/6, ale negatívny/pozitívny pár zlyhal pri audite upstream ICB1: lokálny 802.11 unicast a MAC ACK menili ďalší CAM backoff o 1–7 µs, teda aj bajty času prijatia v ICB1. Samotné pridelenie per-device RNG streamov nestačilo, pretože car0 zdieľa MAC stav medzi prijímaním I2V a neskorším CAM vysielaním. Oprava odkladá všetky I2V1 až po poslednom sledovanom CAM, takže v oboch vetvách sú CAM RX časy a celé ICB1 rovnaké ako vo verzovanom baseline fixture. Táto kontrola nehodnotí okamžitú I2V reakciu.

V overenom behu bolo 6 CAM TX, 18 CAM RX, 6 ICB1 serverových prijatí, 6 GRA1 na RSU a 6 I2V1 na `car0`. Synteticky zablokovaný variant mal 6 CAM TX, 18 CAM RX, identických šesť ICB1 vytvorených na RSU, 0 servisných frameov a 0 I2V1. Presné per-event časy a bajty sú v `trace.csv` (`SERVER_ACK_IP_TX`, `RSU_ACK_RX`, `I2V_HOLD_SCHEDULED`, `RSU_I2V1_TX`, `CAR0_I2V1_RX`) a `verification.json`. Čas CAM→I2V zahŕňa zámerný hold a nie je prevádzkovým oneskorením. Pre realistickejší okamžitý I2V treba samostatný experiment, v ktorom sa od pozitívnej a blokovanej vetvy nevyžaduje bitovo totožný neskorší MAC stav. Tento pilot vykazuje oddelene GRA1 server→RSU (v šiestich behoch po 7 015 µs), hold na RSU (96 842–2 546 837 µs) a lokálny I2V1 RSU→car0 OCB (166–176 µs). Ide o časy nakonfigurovaného simulátora, nie terénne merania.

## Hranice modelu

Pozemný OCB PHY/MAC beží pri nastavených 5900 MHz, 10 MHz, 6 Mb/s a Friis strate. Experiment nemodeluje mestské tienenie, interferenciu, DCC, ETSI I2V službu, dôveryhodné identity ani reálnu satelitnú PHY/MAC/beam/gateway cestu. I2V1 je iba lokálny dôkaz doručenia informácie o serverovom prijatí; nevydáva sa za implementáciu štandardného varovania pred dopravnou udalosťou.
