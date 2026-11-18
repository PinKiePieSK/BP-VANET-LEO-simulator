# Read-only inšpektor OCB → Certus 100 IP obalu

**22. 10. 2026 UTC.** Inšpektor sprístupňuje pevný [auditovaný one-clock experiment](editable-v2-ocb-certus100-e2e.md) po jednotlivých `event_id`. Odkaz je v návrhovom editore, ale stránka `certus-packet.html` **nepoužíva aktuálne nakreslený scenár**, nespúšťa simuláciu a nič nezapisuje do pôvodného výsledku. Jej API `GET /api/editor/certus100-audit` prijíma iba pevný lokálny archív `results/editable_v2_ocb_certus100_e2e/`.

## Vstup a overenie pred vydaním dát

[`read_certus100_audit.py`](../../tools/read_certus100_audit.py) pripína SHA-256 `run-manifest.json` a porovnáva jeho verifikáciu so skutočným `verification.json`, referenčným scenárom, ns-3 C++ zdrojom, hlavičkou servisného obalu, orbitálnym generátorom, checkerom, waypointmi, manifestom archívu a komprimovanými Iridium-NEXT elementmi. Pre oba varianty porovná SHA-256 harmonogramu aj jeho metadát a presné SHA-256 **všetkých 16 PCAP súborov**. Potom zavolá už existujúci `check_case(...)` z [`check_editable_v2_ocb_certus100_e2e.py`](../../tools/check_editable_v2_ocb_certus100_e2e.py) priamo v pamäti. Táto funkcia overí CAM/GN, RSU ICB1 odvodený z prijatého CAM, geometriu, PPP/IPv4/UDP checksumy, bajty a poradie UL/DL, serverové prijatie a GRA1. Funkcia `main(...)`, ktorá zapisuje `verification.json`, sa **nevolá**. Výsledný súhrn sa musí zhodovať s uloženou verifikáciou. Ak ktorýkoľvek vstup zlyhá, endpoint vráti HTTP 409 bez surovej stopy.

## Zobrazenie a jednotky

Stránka ponúka šesť `event_id` a varianty `positive` a `blocked_user_leg_candidate`. Fázy sú pozemný OCB CAM, vytvorenie ICB1 na RSU, geometrický kandidát, uplink cez LAN a `synthetic IP service`, server, downlink a GRA1 prijatý na RSU. Každá fáza ukazuje názov udalosti, uzol, čas v **µs** od UTC origin, dĺžku v bajtoch a rozbaliteľný presný hex. PPP rámce dekódujú protokol `0x0021`, IPv4 zdroj/cieľ, TTL, IP dĺžku, UDP porty, dĺžku, checksum a presné bajty payloadu. ICB1 rozkladá 96 B report na event ID, čas RSU prijatia CAM, dĺžku a SHA-256 CAM a pôvodných 41 B. GRA1 rozkladá 46 B aplikačnú odpoveď na ID, SHA-256 celého ICB1 a status.

Pozitívny variant obsahuje 6/6 prijatých reportov na serveri a 6/6 GRA1 na RSU. Kontrolný variant má rovnakých 18 pozemných CAM príjmov a šesť vytvorených ICB1, ale **žiadny** UL/DL IP rámec, serverové prijatie ani GRA1. Pozitívny aplikačný round trip je 52 943 µs v nakonfigurovanom modeli; nie je to RTT operátora. Oba pohľady nesú označenia `synthetic IP service` a `geometry candidate only`. GRA1 je aplikačná odpoveď vytvorená serverom, **nie satelitný ACK**; na auto sa v tomto pilote nič nevracia.

## Reprodukcia kontrol UI/API

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 -m unittest discover -s tools -p 'test_certus100_audit_api.py' -v
python3 tools/scenario_server.py --port 8765
# http://127.0.0.1:8765/certus-packet.html
```

Dva cielené HTTP testy prešli: stránka a API vrátia očakávaných šesť udalostí; UL/DL dekódovanie obsahuje správne porty 45000/45003 a 45004/45001; GRA1 má status 0 na RSU; blokovaný variant nemá IP ani odpoveď. Test zároveň overí, že pôvodný `verification.json` zostal bajtovo nezmenený. Poškodená kópia `trace.csv`, servisného PCAP, manifestu alebo verifikácie vedie k HTTP 409; po obnovení kópie opäť HTTP 200. Syntax JavaScriptu prešla kontrolou Node.js, bez nového `g++` buildu. Vizuálna kontrola v hlavnom vlákne na porte 8782 prešla: pozitívny variant ukázal 41 B CAM, 96 B ICB1, 126 B UL PPP/IP/UDP, 46 B GRA1 a 76 B DL až po RSU. Po prepnutí na blokovaný variant zostali CAM/ICB1 viditeľné, zatiaľ čo UL, server, DL a odpoveď na RSU boli prázdne. Rozloženie a bajty boli čitateľné.

Rádiové obmedzenia experimentu zostávajú nezmenené: Iridium-NEXT objekt je len geometrický kandidát; IP servisná vetva je syntetický P2P obal bez satelitného RF/MAC, beam, gateway a kalibrovaného oneskorenia. Inšpektor overuje **uložené bajty a internú konzistenciu modelu**, nie komerčnú presnosť služby.
