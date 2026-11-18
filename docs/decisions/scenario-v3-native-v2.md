# Natívny packet engine scenára v3 — kontrakt V2

**Stav:** V2 implementácia, 26. 10. 2026. Zdrojový scenár má schému 3 a musí prejsť [V1 kontraktom](scenario-v3-contract.md). Výstupná schéma 2 rozlišuje `execution_state=native_packets_v2` od `preflight_only_no_packets`. V2 vykonáva skutočné CAM/ICB1/GRA1/I2V1 pakety v projektovom **ns-3.38/SNS-3 3.38**; satelitná vetva je naďalej generický diagnostický DVB model s proxy bránou a modelovou ISL.

## Prípustný rozsah pred buildom

`tools/run_scenario_v3_native.py` spustí V1 preflight a potom samostatný `supported` gate. Ten prijíma iba dve archivované družice 43253/43258, referenčnú DVB topológiu, pripnutý OMM archív a proxy GW; Iridium/Globalstar/Starlink servisné profily odmietne. Pozemné rádio môže vybrať Friis alebo mestský 3GPP V2V LOS/NLOS, pri zachovaných 5900 MHz, 10 MHz, 6 Mb/s, 20 dBm, 7 dB NF a vypnutom shadowing. Čas modelu je obmedzený na 22. 10. 2026 12:00–14:00 UTC, deklarované CAM na 5–55 s, 1–100 správ s intervalom 0,1–1 s a najviac osem opakovaní. Generátor navyše odmietne neprítomné FCD body alebo kolíziu CAM `generationDeltaTime`. Toto je vykonateľná podmnožina všeobecnejšieho V1 kontraktu; neznáma kombinácia sa odmietne **pred** natívnym buildom.

Jeden scenár vyberá jedno zdrojové vozidlo a jedno spracúvajúce RSU s kolokovaným UT; vyžaduje aspoň dve autá a 3–50 rádiových uzlov. Ostatné autá a prípadné ďalšie RSU môžu CAM prijať, ale ďalšie RSU nevytvára ICB1. Identita zdroja, cieľového RSU, počet áut/RSU, ich polohy v pripnutom V2 svete, UTC, čas/počet CAM, seed, `ns3_run`, opakovania a vetvy sú deklarované. Jeden súbežný CAM zdroj je zámerná hranica V2; súbežné zdroje a politika medzi viacerými aktívnymi RSU potrebujú vlastný experimentálny kontrakt.

## Presný tok a udalosti

SUMO FCD sa vytvorí zo `world.staged-v2.json`; `tools/prepare_scenario_v3_cam.py` vyberie iba deklarované časy a zoradí zdroj na prvé, zvolené RSU na posledné miesto. Vanetza vytvorí 41 B UPER CAM, GN/BTP prenesie cez ns-3 802.11p OCB, RSU vytvorí 96 B ICB1 **až po dekódovaní CAM**. ICB1 nesie identitu udalosti, čas vzniku, pôvodný CAM a jeho SHA-256. LAN posunie report do UT; SNS-3 prenáša report cez SAT0 → modelovú ISL → SAT1 → proxy GW. Brána vráti 46 B GRA1 s SHA-256 presného ICB1 cez SAT1 → ISL → SAT0; RSU odošle 50 B I2V1 späť pôvodnému autu. `blocked` potlačí UT satelitnú ponuku; `no_isl` odstráni modelovú hranu, no lokálne CAM/ICB1 ostávajú aktívne.

`trace.csv` obsahuje presné bajty a časy jednotlivých packet fáz. `events.csv` má pre každý zdrojový CAM stav `offered`, pri dekódovaní `created`, pri RSU UDP odoslaní `queued`, pri UT satelitnej ponuke `sent`, pri bráne/návrate `received`. `dropped` v `blocked` je riadená experimentálna brána; v `no_isl` výsledok neprítomnej modelovej hrany; `radio_or_rsu_missing` a `unknown` sú **diagnostické výsledné klasifikácie**, nie vymyslené fyzikálne drop traces. Samostatné Wi-Fi PHY, LAN, ISL a SNS-3 PacketTrace údaje ostávajú raw dôkazom, keď sú dostupné.

`tools/check_scenario_v3_native.py` znovu vypočíta V1 vstup, skontroluje hash každého raw súboru, kódu a verzie knižníc, presný CAM v OCB PCAP, ICB1 v LAN PCAP a naprieč UT/ISL/GW, GRA1 v opačnej ISL ceste, I2V1 v OCB PCAP a poradí `PacketTrace`. Menovateľ je počet deklarovaných jedinečných zdrojových CAM; z neho sa vykazujú RSU vytvorené reporty, vzdialené doručenia pred deadline, návraty a páry CAM–oprávnený miestny príjemca. Bez RSU dekódovania sa report nesmie objaviť. Nezvolené RSU nesmie vytvoriť report.

## Spustenie a výstup

Z koreňa projektu s `.venv` a hotovým checkoutom:

```bash
.venv/bin/python tools/run_scenario_v3_native.py config/scenario_v3_reference.json results/v3_runs/MOJE_NOVE_V2_ID
.venv/bin/python tools/check_scenario_v3_native.py results/v3_runs/MOJE_NOVE_V2_ID
```

Runner odmietne existujúce ID. Každé opakovanie má `repNNN/world.json`, `sumo/`, `waypoints.csv`, pripnuté satelitné `inputs/` a samostatné vetvy s raw PCAP/trace/PacketTrace. `run-manifest.json` zahŕňa vstupné a zdrojové SHA-256, verzie Python/NumPy/Astropy/SGP4, ns-3/SNS-3 a Vanetza commity. SNS-3 parser pri niektorých argumentoch krátil cestu s medzerami: runner mu preto na čas behu predloží bezmedzerový symlink na **ten istý projektový výstup**. Nemení polohu ani obsah dôkazu a odkaz po behu odstráni.

Zachovaný P5 model je nedotknutý. [Prijímací denník](../experiments/v2-native-scenario-2026-10-26.md) porovnáva pôvodný šesťsprávový prípad s V2 bajt po bajte a uvádza ďalšie dve odlišné konfigurácie. V3 musí riešiť spojitú geometriu, beam, attach a route; V2 geometrický kandidát stále nie je dostupnosť komerčnej služby.
