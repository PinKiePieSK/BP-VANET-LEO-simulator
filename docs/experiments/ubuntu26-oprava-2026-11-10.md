# Oprava simulátora po aktualizácii na Ubuntu 26.04 — 10. 11. 2026

## Príčina

Po aktualizácii ukazovala pôvodná `.venv/bin/python` na systémový Python 3.14, hoci
balíky boli inštalované pre Python 3.12. Server editora preto pri požiadavke na
orbitálny náhľad zlyhal na chýbajúcom `astropy`; v prehliadači sa to prejavilo ako
chyba siete. Wi-Fi adaptér bol počas diagnostiky pripojený. Po oprave Pythonu sa
ukázali ďalšie chýbajúce systémové hlavičky Boost a staré natívne knižnice
ns-3/Vanetza zviazané s knižnicami z Ubuntu 24.04. Pripnutá tabuľka EOP navyše
prekročila predvolený tridsaťdňový limit pre predikované riadky Astropy.

## Oprava

- Python 3.12.14 je uložený v `~/Documents/BP-Simulator-Runtimes/python-3.12.14`.
  Aktívny projekt a pracovné prostredie prenosného balíka majú nanovo vytvorené
  `.venv`; staré prostredia zostali ako `.venv-before-ubuntu26-repair-20261110`.
  Závislosti sa nainštalovali z pripnutých offline wheelov; `pip check` prešiel.
- Doinštalované systémové balíky `libboost1.90-dev`, `libboost-date-time-dev` a
  `osmium-tool`. Vanetza a ns-3.38/SNS-3 3.38 boli preložené na Ubuntu 26.04.
  Pri starej ns-3.38 sa vypnulo `NS3_WARNINGS_AS_ERRORS`, lebo GCC 15 hlási
  upozornenie v upstream kóde ako chybu. Sieťový model sa nemenil.
- `tools/simulator_orbits.py`, `tools/u9_constellation.py` a
  `tools/u9_native_editor.py` používajú tú istú pripnutú EOP tabuľku bez
  kalendárneho limitu `auto_max_age`. Automatické sťahovanie zostáva vypnuté;
  čas mimo rozsahu tabuľky sa odmieta a jej SHA-256 zostáva v proveniencii.
  Tieto tri súbory boli prenesené aj do aktuálneho pracovného prostredia
  `~/Documents/BP-Simulator-Pracovny-parove-20261103/runtime/tools/`.
- Pokazený historický symlink `vendor/ns-3.38-ocb-eval/scratch/vanet-sns3.cc`
  bol zachovaný v `results/ubuntu26-repair-20261110/`; bránil konfigurácii CMake.
- Opravené orbitálne moduly sú aj v aktualizovanom ZIPe na ploche. Predošlé
  vydanie je zachované v `~/Documents/BP-Simulator-Archiv/20261110-pred-opravou-zip/`.
  Manifest pracovného prostredia bol zosúladený s aktualizovaným balíkom.
- Pôvodný `setup.sh` sťahoval `slovakia-261031.osm.pbf` z adresy, ktorá
  10. 11. 2026 vracala HTTP 404. Pripnutý PBF, oficiálny MD5 a polygon sú teraz
  v `release/osm/` a v ZIPe; skript ich skopíruje do workspace a overí MD5 aj
  SHA-256. Zmena je aj v `scripts/package_simulator.py` pre ďalšie vydania.

## Overenie

| Kontrola | Výsledok |
| --- | --- |
| Pozemný scenár `repair-ground-20261110b` v prenosnom pracovnom prostredí | PASS; 92 CAM TX, 233 CAM RX, 7 DENM príjmov |
| Satelitné scenáre `repair-iridium-20261110`, `repair-globalstar-20261110`, `repair-starlink-20261110` | Všetky natívne behy a samostatný verifier PASS; každý 92 CAM TX, 1 DENM príjem na bráne, 2 vzdialené príjmy |
| Zdrojový projekt `ubuntu26-repair-iridium-20261110` | Natívny beh a verifier PASS |
| Python testy aktívneho projektu | 38 testov OK |
| Editor a API | Stránka, načítanie reálnej mapy a 80 družíc Iridium, overenie uloženého scenára `realna-d1-satelit`, otvorenie overeného behu: HTTP 200 |
| Desktopový spúšťač | Štart a ukončenie lokálneho servera prešli s testovacím prehliadačom `BP_SIM_BROWSER=/bin/true` |
| Študijná kópia zdroja | `refresh_study_code.py --check`: PASS, 64 súborov |
| Aktualizovaný ZIP | `verify.py`: 10 230 súborov a odkazov PASS; `unzip -t`: bez chyby; SHA-256 súboru ZIP: `7280a5e73f309fa9b30c686aef0bf27250c32abf186490cf4c0838e2d4a88a67` |
| Rozbalený ZIP | Po rozbalení do dočasného priečinka prešiel `verify.py` nad skutočne vytiahnutými súbormi: PASS |

Overené satelitné behy sú **generický DVB model SNS-3** s jednou vybranou
paketovou družicou; nie sú meraním komerčných služieb operátorov. Aktualizovaný
prenosný ZIP je určený na čistú inštaláciu na Ubuntu 24.04 x86-64 s Pythonom
3.12. Jeho integrita bola overená, ale čistá inštalácia na druhom počítači
zatiaľ nie. Opravené pracovné prostredie a desktopový spúšťač fungujú na tomto
Ubuntu 26.04; čistú inštaláciu ZIPu na inom Ubuntu 26.04 toto overenie netvrdí.
