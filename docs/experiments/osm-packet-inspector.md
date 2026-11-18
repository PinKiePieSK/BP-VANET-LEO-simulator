# Paketový inšpektor párového OSM replayu

Na hlavnej stránke otvor **OSM Bratislava · párový pozemný backhaul** a vyber variant. Sekcia **Paketový inšpektor** potom ponúkne päť `event_id`. Po voľbe ID ukáže 13 chronologických fáz od vytvorenia CAM po prijatie reportu modelovým serverom: čas od začiatku simulácie, rozdiel oproti predošlej fáze v ms, uzol, stage, dĺžku a druh stopy. Kliknutie na fázu otvorí celé `raw_hex` s bajtovými offsetmi. Riadok sa zvýrazní podľa polohy prehrávacieho času.

Vrstva CAM zobrazuje presných 41 B UPER a základnú hlavičku (verzia, message ID, station ID, generationDeltaTime). Poloha/rýchlosť/smer sú spárované s overeným FCD/Vanetza dekódovaním; UI samo neimplementuje plný ASN.1 UPER dekodér. Vrstva GN/BTP ukazuje 40 B GN hlavičku, 4 B BTP a 41 B CAM s kontrolou zhody CAM. Celý 121 B 802.11 MAC rámec je v overenom PCAP, **nie v JSON replayi**. Inšpektor preto správne označuje 85 B raw GN/BTP/CAM ako obsah prenesený cez pozemné rádio, nie úplný Wi-Fi rámec. Použitý ns-3 `AdhocWifiMac` nie je OCB.

RSU vytvorí **lokálny 96 B ICB1 aplikačný report**: `magic(4)`, `version(1)`, `event_id(8)`, čas RSU RX v µs `(8)`, dĺžka CAM `(2)`, SHA-256 CAM `(32)` a presný CAM `(41)`. Inšpektor ukáže tieto polia a priamo porovná CAM telo. LAN a vzdialený úsek zobrazujú 126 B `PPP(2)+IPv4(20)+UDP(8)+ICB1(96)`, IP adresy, porty, TTL, dĺžky a kontrolné súčty. Rozdiel LAN→vzdialený paket je uvedený po bajtových offsetoch; report ako UDP payload sa nemení. Overenie SHA, kontrolných súčtov, dĺžok a zhody surových stôp robí upstream checker/builder, nie samotný prehliadač.

Odznak `raw_packet` znamená presné bajty uložené v konkrétnom CSV stage. `model_service` znamená abstraktný ns-3 P2P serializér 22 kbit/s s nulovým zadaným propagačným časom; `model_ground` je 1 Gbit/s kontrolný serializér. Žiadny z nich nemá satelitný uzol, ISL, gateway, operátorské RF/MAC ani kalibrované RTT. Časy sú udalosti simulácie, nie merania operátora. Presný zdroj a stav overenia je opísaný v [párovom OSM replayi](osm-paired-viewer.md).

Kontrola z koreňa repozitára:

```bash
python3 tools/build_osm_paired_replay.py --check
python3 tools/check_osm_paired_viewer.py
/home/ubuntu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node viewer/test-packet-inspector.cjs
```

DOM test overuje oba varianty, všetkých päť ID, 13 fáz, zhodu CAM/report/UDP obsahu, výber raw hex a modelový odznak. Prehliadačový vizuálny test treba po obnovení hlavnej stránky vykonať v skutočnom UI.
