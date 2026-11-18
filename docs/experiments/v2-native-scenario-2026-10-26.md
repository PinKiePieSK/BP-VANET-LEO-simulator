# V2 — natívny scenárový CAM → RSU → LEO → návrat

**Stav:** HOTOVO 26. 10. 2026 pre [definovanú bránu V2](../plan-univerzalny-verny-simulator-2026-10-26.md). **Vykonaný runtime:** projektový ns-3.38/SNS-3 3.38. **Význam:** pravdivé pakety generického diagnostického DVB modelu, nie validácia služby Starlink/Iridium/Globalstar. [Vykonateľná podmnožina a udalosťový kontrakt](../decisions/scenario-v3-native-v2.md) presne opisujú podporu a hranice.

## Nový engine a dôkazová cesta

- `src/v3-native-cam-leo.cc` je **nová** odvodená jednotka; zmrazený `src/p5-urban-matrix.cc` zostal s pôvodným SHA-256 `500b00a6359b695a5612f5ba5b0a14672ea4c53a4631408699a01895698dac81`. Nový engine prijíma zdroj/RSU, 1–100 CAM, časy, uzly, seed/run a vetvy. Vybrané RSU jediné vytvára ICB1; počet správ sa nevynucuje šiestimi aserciami. Udalosti sú v `events.csv`.
- `tools/prepare_scenario_v3_cam.py` používa konkrétny V1 scenár a SUMO FCD na prípravu iba deklarovaných CAM časov; odmieta chýbajúce vozidlo a kolíziu `generationDeltaTime`. `tools/run_scenario_v3_native.py` pred buildom odmieta nepodporovaný operátorský profil, fyzikálne parametre, čas a veľkosť prípadu. Pre projektovú cestu s medzerami vytvorí iba dočasný bezmedzerový alias k tomu istému výstupu; skúšobné zlyhanie parsera v `v2_reference_probe_20261026` je zachované.
- `tools/check_scenario_v3_native.py` kontroluje manifest, pripnuté zdroje, SUMO/waypoint, plán, presné bajty CAM/ICB1/GRA1/I2V1 v `trace.csv`, OCB a LAN PCAP, obe modelové ISL a poradie SNS-3 PacketTrace. Rozlišuje ponúknuté CAM, RSU vytvorené ICB1, doručenie pred deadline, návrat a miestne páry CAM–príjemca; kontrolné vetvy nesmú uniknúť k bráne.

## Prijímacie výsledky

Každý odkaz je skutočný manifest so stavom `native_packets_v2`, individuálnymi hashmi všetkých raw súborov, kódu, závislostí a commitov. Pri každej pozitívnej vetve `x/y` znamená unikátne ICB1 doručené bráne a vrátené autu z `y` reportov vytvorených RSU. Negatívne vetvy mali rovnaký počet lokálnych reportov, vzdialené doručenie **0** a návrat **0**.

| Vstup a zmena | Plán | Kladná vetva | Negatívna kontrola | Raw dôkaz |
| --- | --- | --- | --- | --- |
| [Pôvodná zostava](../../config/scenario_v3_reference.json): `car0`, `rsu0`, 4 uzly, 6 CAM, 12:45 UTC | 1 opakovanie × `positive/blocked/no_isl` | 6/6, miestne páry 12/12 | `blocked` 0/6; `no_isl` 0/6 | [Manifest](../../results/v3_runs/v2_reference_release_20261026/run-manifest.json), 77 raw súborov, checker PASS |
| [Zmenené ID](../../config/scenario_v3_v2_short.json): `carA`, `relayA`, 3 uzly, posunuté RSU, 4 CAM, 12:45:05 UTC | 1 × 3 vetvy | 4/4, miestne páry 4/4 | 0/4 a 0/4 | [Manifest](../../results/v3_runs/v2_short_release_20261026/run-manifest.json), 74 raw súborov, checker PASS |
| [Dve RSU](../../config/scenario_v3_v2_multi_rsu.json): `van2`, cieľové `relayB`, ďalšie pasívne `rsuAux`, 5 uzlov, 8 CAM, 12:45:10 UTC | 1 × 3 vetvy | 8/8, miestne páry 16/16 | 0/8 a 0/8; pomocné RSU nevytvorilo ICB1 | [Manifest](../../results/v3_runs/v2_multi_rsu_release_20261026/run-manifest.json), 80 raw súborov, checker PASS |
| [Friis a opakovania](../../config/scenario_v3_v2_repeat_friis.json): `carA/relayA`, 4 CAM, iný pozemný profil | 2 seedy/runy × `positive/blocked` | 4/4 a 4/4 | 0/4 a 0/4 | [Manifest](../../results/v3_runs/v2_repeat_friis_release_20261026/run-manifest.json), 119 raw súborov, checker PASS |

Spolu **13 natívnych vetiev**. Päť kladných vetiev doručilo a vrátilo **26/26 RSU reportov**; osem kontrolných vetiev vytvorilo 44 lokálnych reportov a doručilo vzdialene 0. Ide o krátke deterministické integračné vstupy, nie odhad prevádzkovej PDR alebo p95/p99 služby. Každý beh má vlastný seed, `ns3_run`, normalizovanú konfiguráciu, plán a samostatnú raw stopu.

## Bajtová spätná kompatibilita a poškodenie

`tools/check_v2_legacy_equivalence.py results/v3_runs/v2_reference_release_20261026` prešiel: nový šesťsprávový `waypoints.csv` je **bajtovo rovnaký** ako zmrazený P5 sparse pilot `seed314159_124500`; po čisto názvovej normalizácii `CAR_I2V1_RX` → `CAR0_I2V1_RX` je rovnakých **258/258** raw trace riadkov vrátane bajtov a mikrosekundových časov v `positive/blocked/no_isl`. **18/18 OCB a LAN PCAP súborov** je bajtovo identických. Pôvodný P5 manifest a jeho raw hashe sa pri porovnaní znovu kontrolujú; starý zdroj ani výsledky sa neprepisujú.

`tools/audit_v2_corruption.py results/v3_runs/v2_reference_release_20261026` prešiel **3/3** sémantické mutácie na dočasnej kópii: zmenený bajt ICB1, chýbajúca `created` udalosť a poškodený OCB PCAP sa nezávisle odmietli. Výsledkový manifest kontroluje aj hash každej raw stopy. Cielené unit testy odmietli operátorský profil a nesúlad OCB parametrov pred buildom a overili oneskorené priradenie návratového PacketTrace ID pri väčšej záťaži.

## Regresia, obmedzenia a pokračovanie

`.venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: **81/81 PASS**. `python3 tools/v0_history.py validate`: pôvodných 464 členov a SHA-256 `58bde6846ba0777841e46e7ec40abec36894207e2231645adc034bdd56ef06c6` PASS. V1 `verify` referenčného prijímacieho výstupu PASS. `git diff --check` PASS. Lokálne odkazy nových dokumentov boli skontrolované.

V2 je univerzálnejší **vo vymedzenej referenčnej paketovej ceste**: vie meniť identitu zdroja/RSU, počet a čas CAM, počet áut/RSU, polohu RSU, rádio Friis/urban, seed/run/opakovania a kontrolné vetvy. Stále používa dve vybrané družice, pevné referenčné beamy, proxy GW, generický DVB, jednu aktívnu RSU a jedného súbežného CAM zdroja; geometria sa vo V1 testuje vo vzorkách, nie ako spojité pripojenie. Operátorské servisné profily zostávajú `scenario/sensitivity` bez nezávislej kalibrácie. **V3** musí oddeliť časovú viditeľnosť od beamu, attachu, trasy a skutočného doručenia; V2 tieto chýbajúce úrovne nedeklaruje za reálnu službu.
