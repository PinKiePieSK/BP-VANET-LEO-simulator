# Prehliadanie jedného reportu na geometricky riadenej LEO ceste

**Účel:** vysvetliť konkrétny výsledok izolovanej [päťuzlovej paketovej sondy](osm-leo-hop-probe.md) bez zamieňania jej rámcov za proprietárne rádiové protokoly. Stránka `http://127.0.0.1:8765/leo-packet.html` zobrazuje RSU→UT→LEO proxy→gateway proxy→server, päť `event_id`, 11 fáz na správu v pozitívnom variante a jeden `GEOMETRY_BLOCK` na ID v syntetickej negatívnej kontrole.

**Algoritmus a jednotky.** `tools/build_osm_leo_hop_replay.py` najprv zavolá nezávislý `check_osm_leo_hop_probe.py`: overí zdrojové SHA-256, pôvod 96 B ICB1, IPv4/UDP kontrolné súčty, identitu UDP obsahu a r/c čas na oboch hranách. Potom z `schedule.csv` a `trace.csv` vytvorí read-only JSON a metadata s hashmi každého zdroja. `GET /api/osm-leo-hop/replay` pred podaním znovu kontroluje SHA-256 replayu a zdrojov; pri nesúlade vráti HTTP 409. JS používa `textContent` a dekóduje len overený formát: 96 B ICB1 alebo 126 B PPP+IPv4+UDP+ICB1. Čas stopy je celé µs od UTC `2026-10-22T12:45:00Z`, rozdiel fázy sa zobrazuje v ms, vzdialenosť v km, elevácia v stupňoch a modelové r/c v µs. `PHY_TX/RX` je názov ns-3 P2P callbacku; nie je to satelitný PHY rámec.

**Vstupy a výstupy.** Vstupmi sú verifikované `results/osm_leo_hop_probe/{positive,negative}/{manifest.json,schedule.csv,trace.csv}` a `verification.json`; pôvodný CAM/report a OMM snímka sú uvedené v manifeste sondy. Výstupy sú `data/derived/viewer/osm-leo-hop-replay.json` a `.metadata.json`; UI iba číta tieto dáta. Vybraná fáza ukazuje presné `raw_hex`, veľkosť, link, relatívny čas a rozklad PPP/IP/UDP alebo ICB1. Pri `GEOMETRY_ALLOW/BLOCK` sa zobrazí modelové rozhodnutie bez falošných bajtov.

**Predpoklady a hranice.** Ide o archívne GP objektu Globalstar 37741, RSU v Bratislave, **proxy centra mesta Nemea namiesto potvrdenej antény**, 10° výskumnú masku a štyri idealizované 1 Gb/s P2P hrany. Satelit je explicitný paketový uzol a per-event propagačný čas pochádza z dvoch geometrických vzdialeností. Nie sú implementované RF/MAC, beam/gateway assignment, registrácia terminálu, fronty, handover ani operátorský formát služby. PDR 5/5 a približne 18 ms jednosmerne platia iba v tomto otvorenom modeli. GP snímka bola získaná po čase zobrazovaných udalostí, preto je výsledok retrospektívny.

**Zopakovanie a záporné kontroly:**

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
bash tools/run_osm_leo_hop_probe.sh
python3 tools/test_osm_leo_hop_replay.py
.venv/bin/python tools/scenario_server.py --port 8765
```

Test kontroluje 5×11 fáz, byte identity, záporných päť blokov, HTTP 200 a HTTP 409 po zmene zdrojového CSV alebo replay JSON. Pri vizuálnej kontrole v prehliadači možno kliknúť `PHY_RX` na `UT_LEO`: zobrazuje 126 B, TTL 63 a rovnaký 96 B aplikačný obsah; prepnutie na záporný variant ukáže výhradne `GEOMETRY_BLOCK` bez paketového RX. Pôvodné neúspešné spustenie s cestou obsahujúcou medzeru a oprava runnera sú zaznamenané v denníku sondy.
