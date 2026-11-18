# Obmedzený E2E beh z návrhového editora a čisto čítacia paketová cesta

**Stav 22. 10. 2026:** editor môže spustiť overený pilot [OCB CAM → RSU → geometricky riadený P2P proxy](editable-v2-ocb-geometry-e2e.md) cez samostatné API. Časové okno má iba šesť vzoriek `t=20,0–22,5 s`. Výsledok sa v editore označuje **„geometrický P2P proxy“**. Nejde o simuláciu Globalstar rádiového rozhrania, prevádzkovej služby, terminálového protokolu ani onboard IPv4 smerovania satelitu.

## Použitie

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/scenario_server.py --port 8765
```

Otvoriť `http://127.0.0.1:8765/draft-editor.html`, zvoliť **„Načítať podporovaný E2E pilot“**, prípadne upraviť cesty alebo polohu `rsu0`, potom stlačiť **„Spustiť OCB CAM → geometrický P2P proxy“**. Po úspechu odkaz **„Otvoriť úplnú paketovú cestu“** zobrazí šesť udalostí a oba varianty. Každá udalosť má presný CAM UPER/GN/BTP/OCB rámec, prijatie u `car1`, `car3` a `rsu0`, ICB1 report odvodený z prijatého CAM, geometrický záznam, každý PPP/IP/UDP TX/RX hop a prijatie na serveri. Voľné zmeny modelu siete sa nevykonávajú týmto tlačidlom.

Ak sa upraví cesta alebo RSU, môže zlyhať SUMO dostupnosť vozidla vo všetkých šiestich vzorkách, spoločná viditeľnosť objektu, alebo pevné ID 37741, ktoré tento konkrétny pilot podporuje. Výsledkom je **zlyhaný** beh s worker logom, nie náhradný satelit či neoverené reporty. Pri zmene súradníc RSU sa plán vždy znovu prepočíta a archivovaný hash zaznamená. UI predvolene začína prázdnym návrhom; načítanie pilotu doplní správne ID a seed.

## Presné API a rozsah

| Volanie | Význam |
| --- | --- |
| `GET /api/draft-e2e-preset` | Vráti validovaný editovateľný v2 pilot `car0/car1/car3/rsu0`. |
| `POST /api/draft-e2e-runs` | JSON celej schémy v2; 202 s `run_id` alebo 400 s dôvodom nepodporovanej zmeny. |
| `GET /api/draft-e2e-runs/<id>` | `running`, `failed`, alebo až po worker exit 0 a kontrolách `complete`; súhrn a koniec logu. |
| `GET /api/draft-e2e-runs/<id>/packets` | Čisto čítací JSON zostavený z overených surových stôp; 409 pred dokončením alebo pri nesúlade. |
| `GET /api/draft-e2e-runs/<id>/pcap/<positive|blocked_gateway>/ocb-<0..3>-0.pcap` | Pôvodný ns-3 PCAP po rovnakej kontrole; 409 pri chybe. |

Server najprv vykoná úplnú v2 validáciu, potom prijme **presne** štyri rádiové ID v poradí `car0,car1,car3,rsu0`, zdroj `car0`, jeden `its_g5`/`CAM`/`broadcast` flow, seed `314159`, krok `0,5 s`, UTC origin `2026-10-22T12:45:00Z` a trvanie `>22,5 s`. Tvar cesty, trasy áut, georeferenčná kotva a poloha `rsu0` môžu byť zmenené v platnej schéme. Server neberie inú technológiu alebo flow ako „skrytý“ vstup E2E. Súčasne pripúšťa jeden E2E worker v jednej serverovej relácii.

Každý beh má oddelené `results/editable_e2e_runs/<id>/scenario.json`, `network/` a `worker.log`; neprerába výsledky pozemnej vetvy `/api/draft-radio-runs`. Worker spustí `.venv/bin/python tools/run_editable_v2_ocb_geometry_e2e.py --scenario <scenario.json> --output <network>`. Runner obnoví SUMO FCD, waypointy a dva geometrické plány, zostaví pripnutý ns-3.38/Vanetza program a vytvorí raw PCAP/traces, `verification.json` a `run-manifest.json`. Presná reprodukcia bez UI:

```bash
.venv/bin/python tools/run_editable_v2_ocb_geometry_e2e.py \
  --scenario data/inputs/editable-road-v2/packet-subset.json \
  --output results/editable_v2_ocb_geometry_e2e
```

## Integrita a rozbor

`complete` vyžaduje `status=PASS` v oboch záznamoch, SHA-256 uloženého scenára, verifikácie, zdrojového C++ súboru, geometrického generátora, archívneho manifestu, waypointov, oboch plánov a oboch raw trace. Následne sa znovu spustí čisto čítacia kontrola každého variantu proti všetkým štyrom PCAPom: OCB rámce, GN LPV/CAM, report a čas/bajty všetkých hopov. Ak server drží objekt worker procesu, musí byť ukončený s návratovým kódom **0**; prebiehajúci alebo neúspešný proces sa nikdy neoznačí za `complete`, aj keby manifest existoval. Po reštarte API servera sa objekt procesu neobnoví, ale uložený beh možno znovu zobraziť **iba po úplnej kontrole manifestu, verifikácie a raw súborov**. Samotná existencia manifestu nestačí.

`tools/build_editable_v2_e2e_replay.py` nič neprepisuje. Vytvorí JSON priamo z verifikovaného `trace.csv`, `schedule.csv`, waypointov a zdrojového OCB PCAP pri GET. Zachová raw hex pre všetky vrstvy a časy v **µs od UTC originu**. PPP rámec má 126 B vrátane 2 B PPP, 20 B IPv4, 8 B UDP a 96 B ICB1; rozbor explicitne uvádza IP adresy, TTL, porty, dĺžky a checksum. Syntetická záporná brána stále zobrazuje všetky tri CAM prijatia a report na RSU, ale nemá P2P hopy ani server accept. Prehliadač zobrazuje hodnoty cez `textContent`, neprijíma z trace HTML.

Surový OCB PCAP má na konci 123 B rámca štyri nulové bajty ako **zástupný FCS ns-3**; nejde o skutočne merané alebo vypočítané CRC. Upozornenie je priamo pri hex zobrazení rámca.

## Cielené overenie a neúspešné cesty

Dňa 22. 10. 2026 prešiel jeden HTTP test na dočasnom localhost porte: nepodporovaný seed `42` → **400**; validný pilot → **202**, po dokončení `complete` so 6 CAM TX, šiestimi prijatiami na každom z troch uzlov, 6 server reportmi a 0 v blokovanej vetve; `/packets` → **200**, šesť udalostí na variant, štyri hopy v kladnej a nula v blokovanej udalosti; zdrojový PCAP → **200** a validná PCAP hlavička. Kontrolný pokus vyvolal `verified_e2e` s exit kódom `1` a s procesom, ktorý ešte beží; oba boli odmietnuté. Python `py_compile` a syntax oboch nových/menených JS prešli. Žiadne tvrdenie o operátorskej satelitnej službe sa z tohto UI testu neodvodzuje.

Samostatná prehliadačová kontrola na súkromnom porte `8779` overila načítanie preset scenára (2 cesty, 3 autá, 1 RSU, 1 flow), spustenie z tlačidla a beh `20261022T164241Z24bfe129`: status 6 CAM TX/18 pozemných dekódovaní/6 server reportov/0 v blokovanej vetve; prehliadač ukázal CAM→RSU→štyri P2P hopy, záporný variant bez hopov a upozornenie na FCS. Tento port je dočasný testovací server, nie súčasť konfigurácie simulátora.

Posledné cielené záporné kontroly použili **iba dočasnú kópiu výsledku**: zmena jedného bajtu v kladnom `trace.csv` aj samostatná zmena bajtu v prijímačskom `ocb-1-0.pcap` boli v `verified_e2e` odmietnuté. Originálny overený beh ostal bez zmeny. Odstránenie `car3` zo vstupnej kópie scenára vrátilo na `POST /api/draft-e2e-runs` **HTTP 400** s presným zoznamom požadovaných ID.

**Obmedzenia:** jeden zdrojový flow, šesť vzoriek a pevné ID 37741 v aktuálnej C++ sonde; simulácia nie je všeobecný dopravný a satelitný editor. Nemea je centrum mesta ako proxy, nie známa anténa; geografická kotva cesty je syntetická; P2P 1 Gbps a prístroje sú bez kalibrácie servisných frontov, RF/MAC, beamov, smerovania operátora a pokrytia terénom. Táto stopa je vhodná na demonštráciu vrstiev a koncepčný kontrolný experiment, nie na meranie spoľahlivosti Globalstar.
