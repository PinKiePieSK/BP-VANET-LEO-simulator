# U7 – spoločné ovládanie a dohľadateľná správa

**Stav 27. 10. 2026:** dokončené v nižšie uvedenom otestovanom rozsahu. Jediný aktívny sieťový runtime je ns-3.38/SNS-3 3.38. U7 je spoločné ovládanie existujúcich overovaných motorov U2–U5 a výsledkového kontraktu U6; nejde o tvrdenie, že sú všetky implementované v jednom binárnom súbore alebo o externú validáciu operátorskej siete.

## Ako postupovať

V koreňovom priečinku projektu spusti `.venv/bin/python tools/scenario_server.py --port 8765` a otvor `http://127.0.0.1:8765/u7-simulator.html`. Editor vie načítať uložený scenár, skontrolovať jeho uskutočniteľnosť, uložiť ho, spustiť a analyzovať, znovu overiť beh a zobraziť cestu jednotlivej správy vrátane pôvodných riadkov. Môže otvoriť aj existujúci U7 beh podľa jeho ID. Na port pristupuj lokálne; súčasne smie server spustiť jeden U7 beh. Pôvodný kresliaci editor zostáva samostatný: nakreslená mapa sa automaticky nepremieta do U7; treba použiť vhodné uložené vstupy pod `data/inputs/`.

Rovnaký kontrakt JSON je použiteľný bez prehliadača. Nasledujúce príkazy sa vykonávajú v koreňovom priečinku projektu. Výstupný priečinok musí byť nový, priamy potomok `results/u7_runs/`:

```bash
.venv/bin/python tools/bp_u7.py preflight config/u7-scenarios/reference.json
.venv/bin/python tools/bp_u7.py save config/u7-scenarios/reference.json
.venv/bin/python tools/bp_u7.py execute config/u7-scenarios/reference.json results/u7_runs/moj_pokus
.venv/bin/python tools/bp_u7.py verify results/u7_runs/moj_pokus
.venv/bin/python tools/bp_u7.py verify-analysis results/u7_runs/moj_pokus
```

`run` iba spustí a uloží beh; `analyze` následne vytvorí analýzu. `execute` vykoná oba kroky. `event VYSTUP KLUC_UDALOSTI` poskytne jednotlivú stopu; kľúče sú v `analysis/events.jsonl`. `save` ukladá scenár podľa `scenario_id`, existujúci odlišný scenár neprepisuje. Príklady konfigurácií sú v `config/u7-scenarios/`. Výstup `analysis/results.json` obsahuje počty, menovatele, endpointy, deadline a pôvod udalostí. Manifesty viažu použité scenáre, vstupy, zdroje a raw výstupy; verifier znovu odvodzuje aplikované vstupy zo scenára a kontroluje raw dáta i projekciu výsledkov.

## Čo možno nastaviť a čo sa vykoná

Scenár určuje cestu k svetu a dopytu, referenčné auto a RSU, seed, číslo ns-3 behu, UTC, počet vzoriek, rádio `urban_los`/`friis`, výkon a šum, deadline a backhaul. Všetky autá v použitom dopyte vysielajú CAM; `source_id` je referenčný vysielač, nie filter ostatných vozidiel. `rsu_id` určuje satelitný terminál; reporty môžu vytvárať aj iné aktívne RSU.

* `local` a `ground`: paketový pozemný U2 model a jeho checker.
* `native_generic_dvb`: natívny satelitný model; jeden satelit používa U3, viac satelitov U4, vrátane definovaného handoveru a ISL.
* `service_boundary_replay`: servisný model U5 nad reportmi z natívneho behu s vybraným profilom a prípadom. Ide o model hranice služby, nie o natívnu implementáciu ani potvrdené správanie konkrétneho operátora. Servisný návrat končí na RSU (`RSU_RECEIPT_RX`), zatiaľ čo lokálny, pozemný a natívny návrat sa sleduje po vozidlo (`CAR_I2V1_RX`); výsledky preto nemožno bez vysvetlenia zamieňať.

Pri satelitných režimoch sa zadávajú katalógové ID, ISL hrany ako indexy v zozname satelitov, pôvodný/prípadný cieľový satelit, feeder, brána, maska a fyzikálne/kapacitné parametre. Preflight overuje aj dostupnosť a časovú platnosť orbitálnych vstupov a podporovanú topológiu. Viacsatelitná topológia je momentálne strom, ktorého hrany ležia na použitých trasách pred/po handoveri. Jednosatelitný U3 režim nemá ISL ani handover a v tomto rozhraní používa referenčný zisk 17 dBi a výkon 4 dBW. Podporované hranice sú aspoň 2 autá, 1–20 RSU a najviac 50 rádiových uzlov spolu; počet satelitov je variabilný v rámci kontrolovaných orbitálnych a topologických obmedzení, nie ľubovoľne veľký bez testu. Vzorky sú 20–100. Konkrétne povolené hodnoty a odmietnutia zobrazí preflight.

## Prijímacie dôkazy

Všetky tieto behy prešli `execute` vrátane overenia a analýzy. Sú to jednotlivé modelové realizácie, nie meranie reálnej služby ani odhad štatistickej neistoty.

| Beh v `results/u7_runs/` | Nastavenie | CAM / vytvorené reporty / včas vzdialene / včas návrat |
|---|---|---|
| `local_verified_20261027` | lokálny U2 | 35 / 35 / 35 / 35 |
| `20261027T144206Z700c0cf6` | lokálny U2, spustený z aktuálneho webového editora | 35 / 35 / 35 / 35 |
| `ground_verified_20261027` | pozemný U2 | 35 / 35 / 35 / 35 |
| `three_rsu_final_20261027` | 5 áut, 3 RSU, 3 satelity, natívny U4 | 50 / 50 / 33 / 33 |
| `one_service_test_20261027` | 1 satelit, servisná nedostupnosť | 35 / 35 / 0 / 0 |
| `service_friis_final_20261027` | Friis, zmenený zdroj, seed a UTC; model nedostupného MT | 30 / 30 / 30 / 0 |

CLI a lokálne API poskytli rovnaký normalizovaný plán a znovu overené metriky pre rovnaký scenár a beh. Vo webovom rozhraní bol načítaný existujúci servisný beh a jeho správa: CAM → ICB1 na RSU → nenastala ponuka pri `satellite_unavailable` → neprijatá vzdialenou aplikáciou → bez návratu. `tools/test_u7_contract.py` overil šesť neplatných vstupov, detail pôvodnej správy a odmietnutie pozmenenej udalosti a menovateľa aj po prepísaní hashov analýzy. Regresná sada `unittest discover` prešla 91 testami. UI sa už predtým použilo aj na vytvorenie úplného natívneho behu; tento skorší vývojový beh kvôli neskoršej zmene zdrojového kódu nie je súčasným reprodukčným dôkazom.

Jedna realizácia neposkytuje nezávislý interval spoľahlivosti ani p95/p99; chýbajúce hodnoty ostávajú `null`. U7 nezabezpečuje operátorskú kalibráciu, reálne výpadky, neobmedzenú škálovateľnosť ani automatický import nakreslenej mapy. Finálny čistý balík, škálovacie limity a súhrnný register zostávajú pre U8.
