# Staré pokusy: čo z nich preberáme (2026-10-22)

Preskúmané čítaním, bez spúšťania starých inštalačných skriptov alebo zmeny ich súborov.

| Miesto | Zistenie | Rozhodnutie |
| --- | --- | --- |
| `/home/ubuntu/satellite-demo/sumo` | Malý diaľničný SUMO scenár a FCD výstup. | Referencia formátu; nový pilot má vlastný menší scenár a presný reprodukčný príkaz. |
| `/home/ubuntu/Desktop/PE` | Sieť Partizánskeho a trasy vytvorené pomocou `randomTrips.py`/`duarouter` v roku 2025. | Kandidát na neskorší realistickejší dopravný vstup. Pred použitím treba preveriť pôvod mapy, licenciu, kvalitu a výsledky SUMO validácie. |
| `/home/ubuntu/Desktop/globalstar.tle`, `/home/ubuntu/hypatia/.../tles` | Staršie TLE súbory. | Len formátová referencia. TLE je časovo viazané; bez dátumu epochy, pôvodu a propagácie nemožno predpokladať dnešnú orbitálnu polohu. |
| `/home/ubuntu/hypatia` | Hypatia: publikovaný rámec na generovanie stavu LEO siete a ns-3 simulácie; miestny checkout commit `0ac531c` (2022), obsahoval starý ns-3.31, lokálnu jednoriadkovú úpravu submodulu a veľké build/venv artefakty. | Odborná referencia; pôvodný checkout je v overenom archíve, z VM odstránený. Jeho `.git` a lokálna úprava sú v archíve, generované build/venv súbory sa nearchivovali. |
| `/home/ubuntu/Desktop/bakalarka/test1`, `test2` | Python skripty kreslia pohyb vozidla/satelitu, ale komunikáciu realizuje bodová linka s pevným oneskorením; prvý test používa výšku 35 786 km (GEO), hoci je v kontexte satelitu bez vysvetlenia. Druhý používa 500 km a 25 ms pevné oneskorenie bez výpočtu z geometrie. | Poučenie: oddeliť kreslený pohyb od skutočne modelovaného sieťového kanála. Neprenášať do nového projektu ako overený LEO model. |
| `/home/ubuntu/Desktop/projekt` | Dokumenty a kód Wi-Fi laboratória nesúvisia s dopravnou simuláciou. | Nepoužívať ani nemazať v rámci tejto práce. |

## Upratanie a možnosť obnovy

Pred odstránením vznikol lokálny archív `archive/legacy-2026-10-22.tar.gz` (210 MiB), jeho kontrolný súčet `archive/legacy-2026-10-22.tar.gz.sha256`, zoznam 17 649 položiek `archive/legacy-2026-10-22.contents.txt` a kontrolné súčty vybraných súborov. Prešiel `gzip -t`, overenie SHA-256 archívu aj porovnanie obsahu štyroch obnovených kľúčových súborov: `scratch/vehicle_satellite_sim.cc`, Hypatia `data/fcd.xml`, `Desktop/PE/map.osm` a `Desktop/globalstar.tle`. Archív uchováva pôvodný Hypatia repozitár a jeho lokálnu úpravu, staré TLE, SUMO dáta a pracovné skripty. Neobsahuje iba obnoviteľné Hypatia build a dve Python venv plus cache Waf. Obnovenie jednotlivého súboru: `tar -xzf archive/legacy-2026-10-22.tar.gz -C /home/ubuntu hypatia/...` s presnou cestou zo zoznamu.

Po overení sa skriptom `python3 scripts/cleanup_legacy.py --apply` odstránili: `/home/ubuntu/hypatia`, `/home/ubuntu/pybindgen`, `/home/ubuntu/satellite-demo`, `/home/ubuntu/Desktop/bakalarka`, `/home/ubuntu/Desktop/PE` a desať súvisiacich samostatných súborov na ploche, ktoré skript explicitne vypisuje. Prvý beh sa zastavil na rootom vlastnenom súbore `pybindgen/SOURCES.txt`; následný beh cez `sudo` dokončil zostávajúce položky. Po skončení znova prešla SHA-256 kontrola archívu, pôvodné adresáre chýbajú a nesúvisiace `/home/ubuntu/Desktop/projekt` zostalo. Archív je na **tom istom VDI** a nie je verzovaný Gitom; hostiteľskú návratovú kópiu VDI z VM nevieme nezávisle overiť. Pred zmenami, ktoré by ohrozili samotný VDI, treba archív preniesť mimo VM.
