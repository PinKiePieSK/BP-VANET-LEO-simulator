# Smerové pruhy v editore ciest — 11. 11. 2026

Panel cesty ponúka pre obojsmerný úsek samostatný počet pruhov od začiatku ku koncu a opačne (1–6). Pri jednosmerke sa zobrazuje len prvá voľba; opačný počet zostáva uložený pre prípad obnovenia obojsmernej prevádzky. Nová ručne kreslená cesta má oba počty explicitne nastavené na 1. Historické `lanes_each_direction` zostáva v rozsahu 1–3 ako záložná hodnota pre staršie scenáre; export `road.edg.xml` používa smerové hodnoty ako `numLanes`.

Pri opätovnom načítaní OSM sa ručné nastavenie pruhov zachová pre každý smer samostatne, aj keď sa úsek nahradí kvôli hranici pracovného výrezu. Staršie nesmerové úpravy naďalej platia pre oba smery.

## Overenie

- V samostatnom headless Firefoxe bola nakreslená cesta `road0`, nastavené 4 pruhy vpred a 2 späť. Panel vstupov SUMO zobrazil `road0_forward: 4` a `road0_reverse: 2`. Pri prepnutí na jednosmerku sa odstránila opačná hrana; po návrate na obojsmernú cestu zostali 2 pruhy späť. Pôvodný test kontroloval pri opačnom ovládači len príznak `hidden`; skutočnú viditeľnosť overuje až oprava nižšie.
- `tools.simulator_sumo.make_inputs` vytvoril v `road.edg.xml` dve hrany s `numLanes=4` a `numLanes=2`; pri jednosmerke iba hranu vpred so 4 pruhmi.
- Upravený uložený scenár `realna-d1-pozemna` s 5 683 aktívnymi cestami a 6 autami odovzdal hodnoty 4/2 cez pracovnú aj globálnu kópiu. `/api/simulator/editor/check` vrátil HTTP 200. Uložený scenár sa neprepisoval.
- Študijná kópia aktívneho kódu bola obnovená a kontrola `scripts/refresh_study_code.py --check` prešla.

## Oprava zobrazenia po spätnej väzbe

Pôvodné nastavenie `hidden` na štítku opačného smeru prepisovalo pravidlo `display:block` v CSS. V skutočnom prehliadači bol preto ovládač stále viditeľný, hoci DOM hlásil `hidden=true`. Zároveň bol prehľad vstupov SUMO na širokej obrazovke `position:sticky`, takže pri rolovaní prekryl editor cesty. Špecifické pravidlo teraz skryje opačný ovládač a prehľad SUMO sa posúva v bežnom toku nad editorom. Pri jednosmerke má zostávajúca voľba popis „Pruhy v povolenom smere“.

Overené v headless Firefoxe: pri jednosmerke má opačná voľba vypočítané `display:none` a viditeľná je presne jedna voľba pruhov; pri obojsmernej sú viditeľné dve. Na širokej aj úzkej obrazovke je spodok prehľadu SUMO vždy nad vrchom editora, aj po posunutí objektového panelu. CSS sa načítalo s verziou `20261111-directional-lanes2`.
