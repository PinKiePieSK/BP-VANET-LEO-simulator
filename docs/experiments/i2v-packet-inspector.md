# Read-only inšpektor I2V1 návratu do auta

**22. 10. 2026 UTC.** Samostatná stránka [`i2v-packet.html`](../../viewer/i2v-packet.html) v návrhovom editore otvára iba uložený [one-clock I2V experiment](editable-v2-ocb-certus100-i2v-e2e.md). Nevykonáva nový SUMO/ns-3 beh, nemení starý Certus inšpektor a nepoužíva aktuálne nakreslené cesty či RSU. API `GET /api/editor/certus100-i2v-audit` je pevný read-only pohľad na `results/editable_v2_ocb_certus100_i2v_e2e/`.

## Overenie pôvodu a bajtov

[`read_certus100_i2v_audit.py`](../../tools/read_certus100_i2v_audit.py) pred vydaním dát kontroluje pripnutý SHA-256 `run-manifest.json`, hash `verification.json` v manifeste, SHA-256 scenára, C++ zdroja, servisnej hlavičky, checkeru, generátora, archívneho manifestu/Iridium-NEXT gzip, waypointov, šesťreportového ICB1 fixture, oboch harmonogramov/metadát a presných SHA-256 všetkých **16 PCAP** súborov. Volá čistú funkciu `check_case(...)` z existujúceho checkeru v pamäti; nevolá jeho zapisujúci `main(...)`. Takto nanovo kontroluje CAM, ICB1, GRA1, I2V1, OCB frame/ACK a porovná vypočítané výsledky s uloženou verifikáciou. Tiež porovná šesť ICB1 s nemenným fixture a spoločné CAM RX časy oboch variantov. Pri nesúlade endpoint vráti HTTP 409 bez surovej stopy.

## Per-event zobrazenie

Výber zahŕňa šesť rovnakých `event_id` v pozitívnom a synteticky blokovanom variante. Každý záznam uvádza UTC, CAM TX a RSU RX v µs, presných 41 B CAM a 96 B ICB1, geometrický katalógový objekt a uhol v stupňoch. Pozitívna vetva ďalej ukazuje 46 B serverový GRA1 a jeho prijatie na RSU, čas naplánovania a **zámerný hold**, presný 50 B I2V1, čas RSU TX / car0 RX a miestne OCB oneskorenie. Zvlášť ukazuje presný **88 B 802.11 OCB unicastový dátový rámec**: 26 B MAC, 8 B LLC/SNAP EtherType `0x88B5`, 50 B I2V1 a 4 B nulový FCS placeholder ns-3. Nasleduje oddelený **14 B 802.11 MAC ACK riadiaci rámec**. Jeho MAC adresa smeruje späť na RSU; nemá aplikačné GRA1 telo. Surové bajty sú v rozbaliteľnom hexe a polia I2V1 sú rozdelené na verziu, event ID, cieľové station ID 1001, SHA-256 celého ICB1 a status.

GRA1 je odpoveď serverovej aplikácie doručená RSU; MAC ACK je lokálne riadiace potvrdenie jedného OCB unicastu. **I2V1 je vlastný experimentálny miestny L2 receipt notice, nie CAM, DENM, GN/BTP alebo ACK Iridium.** Čas CAM→car zahŕňa naplánovaný hold 96 842–2 546 837 µs po okne šiestich CAM. Nenazývame ho reakčnou dobou služby. Miestny RSU→car0 OCB čas je podľa verifikácie 166–176 µs; zvyšok závisí od modelu a od výslovného zadržania. V blokovanom variante zostanú CAM/ICB1, ale serverový/RSU GRA1, hold, I2V1 aj obidva jeho 802.11 rámce chýbajú.

## Reprodukcia a testy inšpektora

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 -m unittest discover -s tools -p 'test_certus100_i2v_audit_api.py' -v
python3 tools/scenario_server.py --port 8765
# http://127.0.0.1:8765/i2v-packet.html
```

Tri cielené HTTP testy prešli: šesť pozitívnych a šesť blokovaných identít; zhoda I2V1 s GRA1 hashom a s 88 B rámcom; samostatný 14 B ACK; správny hold; nulový návrat v blokovanom variante. Kontroluje sa aj bajtová nemennosť pôvodného `verification.json`. Poškodené kópie manifestu, verifikácie, trace a oboch OCB PCAP, zmenený scenár alebo checker zdroj dávajú HTTP 409. HTML/JS statické súbory vracajú HTTP 200 a syntax JavaScriptu prešla Node.js kontrolou. Žiadna kompilácia sa pri implementácii inšpektora nespustila. Vizuálna IAB kontrola v hlavnom vlákne prešla: pozitívny event ukázal GRA1, hold 2 546 837 µs, 50 B I2V1, 88 B OCB rámec a samostatný 14 B MAC ACK; blokovaný variant ukázal 0/6 a chýbajúci návrat.

Údaje na stránke dokazujú internú konzistenciu uloženého modelu, nie RF presnosť Iridium. Satelitný PHY/MAC, beam, gateway, autentizácia a terénna kalibrácia zostávajú otvorené.
