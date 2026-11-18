# F1b — orbitálny archív pripnutý ku scenáru

**Dátum:** 1. 11. 2026. F1b uzatvára druhú bránu [plánu fyzikálnej vernosti](../plan-fyzikalna-vernost-2026-11-01.md). Scenár má voliteľné `satellite.orbit_snapshot` s relatívnou cestou a SHA-256 manifestu. Nový návrh automaticky vyberie najnovší kompletne overený archív; scenár bez tohto poľa používa pôvodný archív, takže staré scenáre zostávajú čitateľné.

## Vykonané spojenie vstupov

- `tools/u9_orbit_source.py` overí povolenú cestu, SHA-256 manifestu a všetky tri gzip/raw OMM súbory. Pri zvolenom UTC odmietne čas mimo 48-hodinového okna, pričom samotný OMM loader ďalej filtruje vek *každého* objektu.
- Editor zobrazuje archív a jeho krátky hash pri glóbuse. Prepnutie archívu pripne nové bajty a nastaví UTC na čas jeho stiahnutia; dátum sa dá potom zmeniť. Náhľad, pohyb glóbusu a preflight čítajú ten istý pin. Cache animácie rozlišuje hash snapshotu.
- `bp_u9` zapíše presný orbitálny konfiguračný odkaz do `inputs/orbit-reference.json`; U3/U4 a SNS-3 dostanú ten istý hash manifestu. Výsledkový manifest hashuje odkaz aj nové validačné zdroje. Natívna topológia preberá UTC scenára z mobility; hodnota UTC v pôvodnej referenčnej šablóne sa pri generovaní geometrie a TLE nahrádza týmto UTC.
- Pôvodná C++ poistka dovoľovala iba 22. 10. 2026 od 12:00 do 14:00. Aktívne tri natívne zdroje teraz kontrolujú syntax UTC; kvalifikáciu dráh robí hashovaný OMM vstup a geometrický preflight. Pôvodné bajty C++ a dotknutých verifierov sú odložené v `tools/legacy`, s presnými hashovými výnimkami pre historické manifesty.

## Overenie

Pri snímke `data/orbits/20261101T113716Z-celestrak`, SHA-256 `067b9f58d9cf14ffb16730535226cbb1cbcef0289c5fa7119a440bad8f013556`, vrátili výber satelitov a 13 rámcov pohybu pre všetky tri skupiny totožný hash. Počet platných objektov: Iridium NEXT **80**, Globalstar **33**, Starlink **11 140**; modelové aktívne podgrafy pri zvolenom mieste mali **3/2/3** satelity. Zlý hash sa odmietol a UTC 10. 11. 2026 vyvolal jasnú chybu o vekovom okne.

Natívne behy `f1b-orbit-pin-native-v2-20261101` (`combined_advanced`), `f1b-unified-pin-native-20261101` (`unified`), `f1b-native-generic-dvb-pin-20261101` a `f1b-combined-full-pin-20261101` v pracovnom runtime na ploche vrátili `PASS`; každý prešiel aj samostatným `bp_u9 verify`. Unified experiment trval 6 s, orbitálny hash v scenári, natívnej geometrii a výsledkovom manifeste sa zhoduje; replay API vrátilo HTTP 200, 480 polôh a 183 satelitných záznamov. Historický unified výsledok `replay-audit-direct-20261101` sa po zmene znovu overil `PASS`; starý scenár `u9-demo-blank-satellite` prešiel preflightom s pôvodným archívom `d28ad361...`. Automatická sada: **125 testov OK**. Editor na `127.0.0.1:8765` zobrazil dve voľby archívu a nový pin. Súhrnný audit, výstupy verifierov a testový log sú v `~/Desktop/BP-Simulator-Workspace/physical-f1b-20261101/`; celé natívne stopy sú v `~/Desktop/BP-Simulator-Workspace/runtime/results/u9_runs/`.

Prenosný priečinok `~/Desktop/BP-Simulator` prešiel `verify.py` s **11 387 súbormi a odkazmi**. ZIP SHA-256: `72de286f547a4446cc19b38f9d0886652aee2a30a4e024f9993f1b782cd75a40`. Predošlý balík je zálohovaný ako `~/Desktop/BP-Simulator-Workspace/package-pre-f1b-20261101`.

## Hranica výsledku

F1b zaisťuje totožný zdroj orbitálnych dát, čas scenára a detekciu starého či poškodeného vstupu. **Nerieši** šesťmiestne NORAD ID v paketovom engine (F1c), časovo meniaci sa výber všetkých terminálov (F2) ani skutočne aktívne lúče či obchodnú dostupnosť služby (F3–F6). Čas UTC v uloženom `orbit-reference.json` je šablónový; pri generovaní natívneho modelu sa vždy prepíše hodnotou `scenario.utc_origin` a natívny manifest túto skutočne použitú hodnotu zaznamenáva.
