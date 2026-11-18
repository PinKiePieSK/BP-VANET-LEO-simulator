# Párový OSM Bratislava replay v prehliadači

## Účel a vstupy

Tento režim **prehráva už dokončené** párové experimenty `ground` a
`service` z `results/osm_ba_paired_backhaul/`. Nespúšťa novú simuláciu.
Zobrazuje jedno vozidlo `car0` v piatich po sebe idúcich polohách SUMO FCD
pri `t=5,6,7,8,9 s` a jednu pevnú, modelovú RSU. Päť bodov neznamená päť
súčasných vozidiel. Spojnica a pohyb medzi vzorkami sú len vizuálna
interpolácia, nie nová dopravná alebo sieťová simulácia.

Vstupné súbory: `build/osm-ba-cam-waypoints.csv`, surové CSV/PCAP stopy,
`comparison.csv`, `comparison.json` a `manifest.json`. Staviteľ
`tools/build_osm_paired_replay.py` kontroluje manifestové SHA-256, pôvodné
dekódované CAM polia, presné bajty 41 B CAM a 96 B RSU reportu, všetkých
13 fáz každého z piatich ID, PCAP a párovú rovnosť rádiových/LAN udalostí.
Ukladá `data/derived/viewer/osm-ba-paired-backhaul-replay.json` a sprievodné
`.metadata.json` so SHA-256 všetkých podkladov, ktoré prehliadač používa.
HTTP `/api/osm-paired/replay` pri každej požiadavke znova kontroluje SHA-256
replay súboru aj uvedených podkladov; pri nesúlade vracia `409`.

## Zobrazenie a význam metriky

Voľba **Modelová pozemná kontrola** má vzdialený P2P úsek 1 Gbit/s,
**Abstraktný servis** 22 kbit/s. Obe vetvy majú tie isté CAM a report bajty,
rovnaké udalosti až po UT; mení sa rýchlosť sériového odosielania na
vzdialenom IP P2P úseku. Propagačný čas na tomto úseku je v teste
predpokladaný ako 0 ms. Nejde teda o validovaný WAN ani o satelitnú linku.

Na termináli možno pre každý uzol a event ID otvoriť presné `raw_hex` danej
fázy. Pri fázach `LAN_PHY_*` a `SERVICE_PHY_*` sú to bajty pozemného PPP,
IPv4 a UDP paketu; pri CAM fázach GN/BTP/CAM, respektíve 41 B CAM UPER;
pri aplikačnom reporte 96 B payload. Detail tiež zobrazuje totožný CAM a
report, namerané rádio/LAN/vzdialené/celkové oneskorenie v **µs** a výsledok
servera. Nie sú to bity satelitného PHY rámca. Prehrávač používa existujúce
ovládanie rýchlosti, posuvníka a slučky. Zobrazenie je len na čítanie.

V aktuálnom overenom behu bolo v oboch variantoch prijatých `5/5` reportov.
Priemer od vygenerovania CAM do prijatia serverom bol `268 µs` pre modelovú
kontrolu a `46 085 µs` pre abstraktný servis; rozdiel vzniká najmä
sérializáciou 126 B pozemného PPP/IP/UDP rámca na 22 kbit/s úseku.
Tieto čísla nie sú satelitné OWD/RTT, operátorská dostupnosť ani výsledok
RF/MAC modelu. Samostatný variant `service_no_contact` je umelá 1 m rádiová
negatívna kontrola a nie je súčasťou dvojvariantového prehrávača.

## Reprodukcia a skúšky

```bash
python3 tools/build_osm_paired_replay.py
python3 tools/build_osm_paired_replay.py --check
python3 tools/check_osm_paired_viewer.py
python3 tools/scenario_server.py --port 8767
```

Otvoriť `http://127.0.0.1:8767/`, rozbaliť **OSM Bratislava · párový
pozemný backhaul**, načítať replay a prepnúť variant. Kontrola potvrdzuje
`65` surových fáz na variant, päť totožných ID/CAM/reportov, HTTP `200`
pri správnych podkladoch, HTTP `409` po zmene raw súboru alebo replay JSON
a odmietnutie pozmenenej surovej stopy pri opätovnom zostavení.

## Obmedzenia implementácie

Vizualizačný modul `viewer/osm-paired.js` iba kreslí vstupné súradnice a
prehľadáva zaznamenané udalosti. `tools/scenario_server.py` nevykonáva
simuláciu v tejto GET vetve. Nie je tu satelitný uzol, lúč, RF, MAC,
gateway, handover ani model reálnej služby. Neznáme satelitné oneskorenie
nebolo doplnené ani odhadnuté. Prípadné prepojenie s nezávislou orbitálnou
geometriou by bolo samostatné zobrazenie, nie dôkaz prenesenia paketov.
