# Nezávislá kontrola orbitálneho náhľadu — 22. 10. 2026

## Cieľ a rozsah

Overiť výpočet geometrickej polohy, elevácie a vzdialenosti v `tools/orbit_preview.py` bez sťahovania ďalších orbitálnych dát. Podľa [hĺbkovej analýzy](../hlbkova-analyza-komunikacie.md) ide o validačnú bránu pred tým, ako by viditeľnosť družice ovplyvňovala paketový scenár. **Táto kontrola nepreukazuje skutočnú polohu satelitu ani dostupnosť služby.**

Sú tu dve rôzne kontroly:

1. Python `sgp4` s gravitačnými konštantami WGS72 sa porovná s publikovanými testovacími vektormi 00005 v [Vallado et al., AIAA 2006-6753 Rev. 2, prílohy D/E](https://celestrak.org/publications/AIAA/2006-6753/AIAA-2006-6753-Rev2.pdf). Ide o referenčný test implementácie propagátora na historickom TLE.
2. Tri objekty z uloženého GP/OMM snapshotu sa propagujú tým **istým** balíkom `sgp4`, ale TEME → ITRS → WGS84 vykoná `Astropy` a lokálnu eleváciu/azimut/vzdialenosť vypočíta samostatný ECEF → ENU postup v `tools/validate_orbits.py`. Produkčný náhľad používa `Skyfield`. Tým je nezávislá **transformácia súradníc a topocentrická geometria**, nie propagácia, vstupné elementy alebo časový zdroj. Voľba TEME → ITRS a upozornenie na topocentrickú geometriu sledujú [dokumentáciu Astropy pre družice](https://docs.astropy.org/en/stable/coordinates/satellites.html).

## Vstupy, algoritmus a výstupy

Vstupný snapshot je `data/orbits/20261022T124815Z-retlector/`; manifest sa overuje cez SHA-256 a každá použitá gzip aj surová skupina cez jej uložené odtlačky. Náhľad je deterministický `results/orbits/bratislava-20261022T124500Z.json` pre WGS84 stanicu **48,1486° N, 17,1077° E, výška 0 m**, začiatok **2026-10-22 12:45:00 UTC**, 60 s, krok 10 s a hranicu 10° elevácie. Výstupný validačný JSON je `results/orbits/bratislava-validation.json`; oba sú generované a ignorované Gitom.

Skript kontroluje zhodu odtlačku manifestu, verzie SGP4, ID objektov, epoch elementov a zhody `UTC = začiatok + offset`. Vyberá tie isté tri katalógové ID v časoch **0, 10 a 60 s**. Z OMM cez `sgp4` získava polohu TEME v **km** a rýchlosť v **km/s**. `Astropy` ju premení do ITRS. Polohu stanice z WGS84 transformuje na ECEF. Rozdielový vektor družica–stanica rozloží do osí východ/sever/hore; z nich vypočíta eleváciu a azimut v **stupňoch** a šikmú vzdialenosť v **km**. Náhľadom zaokrúhlenú WGS84 polohu družice prevedie späť na ECEF, aby porovnal vzdialenosť polôh v **km**; tým sa vyhne nejasnému porovnaniu stupňov zemepisnej dĺžky medzi rôznymi šírkami.

Pri transformácii je sieťové obnovovanie EOP vypnuté. `Astropy 7.1.1` použilo zabalenú tabuľku `astropy-iers-data 0.2026.10.19.0.52.1`, súbor `finals2000A.all`, SHA-256 `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`. Pre uvedený čas hlásilo `UT1−UTC = −0,0431723125 s`, polárny pohyb `x = 0,15367471875″`, `y = 0,3220594375″` a stav **2 = IERS-A predikcia**. [Dokumentácia IERS_Auto](https://docs.astropy.org/en/stable/api/astropy.utils.iers.IERS_Auto.html) uvádza použitie zabalených dát pri vypnutom sťahovaní. Predikčné EOP nie sú finálne hodnoty a zdrojom nie je priame meranie satelitnej polohy. Produkčný `Skyfield` používa vlastnú zabalenú časovú škálu bez tejto tabuľky; [jeho dokumentácia](https://rhodesmill.org/skyfield/accuracy-efficiency.html) opisuje, že aplikácia polárneho pohybu vyžaduje pripojenie tabuľky IERS. Preto sa odlišné transformácie nebudú numericky rovnať na milimetre.

## Vzorky a namerané rozdiely

| Skupina, katalógové ID | Epocha OMM (UTC) | Vek pri t=0 | t (s) | Rozdiel ECEF (m) | Rozdiel vzdialenosti (m) | Rozdiel elevácie (°) | Rozdiel azimutu (°) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Starlink 64434 | 2026-10-21 05:09:16,997184 | 31,595 h | 0 | 36,944 | 0,666 | 0,000181 | 0,022397 |
| Starlink 64434 | rovnaká | 31,598 h | 10 | 36,383 | 2,030 | 0,003366 | 0,028635 |
| Starlink 64434 | rovnaká | 31,612 h | 60 | 33,553 | 11,289 | 0,001497 | 0,004253 |
| Iridium NEXT 43253 | 2026-10-21 02:59:35,421792 | 33,757 h | 0 | 27,181 | 4,028 | 0,000186 | 0,001285 |
| Iridium NEXT 43253 | rovnaká | 33,760 h | 10 | 26,499 | 3,896 | 0,000118 | 0,001148 |
| Iridium NEXT 43253 | rovnaká | 33,773 h | 60 | 23,042 | 3,384 | 0,000025 | 0,000828 |
| Globalstar 37190 | 2026-10-21 03:44:59,000352 | 33,000 h | 0 | 50,712 | 27,966 | 0,000595 | 0,000860 |
| Globalstar 37190 | rovnaká | 33,003 h | 10 | 50,970 | 27,010 | 0,000617 | 0,000905 |
| Globalstar 37190 | rovnaká | 33,017 h | 60 | 52,331 | 24,568 | 0,000517 | 0,001026 |

Maximálny rozdiel veľkosti rýchlosti je **4,52 × 10⁻⁶ km/s** (zaokrúhlený výstup náhľadu má päť desatinných miest). Všetkých **9/9** vzoriek splnilo prahy konzistencie 100 m v ECEF a vo vzdialenosti, 0,01° v elevácii, 0,1° v azimute a 0,00002 km/s v rýchlosti. Tieto prahy len oddeľujú významný nesúlad transformácie od pozorovaného rozdielu časových/EOP postupov a zaokrúhlenia; **nie sú intervalmi skutočnej chyby obežnej dráhy**. Pri Starlinku blízko nadhlavníka je azimut zvlášť citlivý na malý rozdiel polohy.

Publikovaný príklad 00005 dal pri epoche rozdiel polohy **6,82 × 10⁻⁹ km** a rýchlosti **6,38 × 10⁻¹⁰ km/s**; pri +360 min **5,93 × 10⁻⁹ km** a **3,85 × 10⁻¹⁰ km/s**. Ide o zhodu s *zaokrúhlenými testovacími vektormi* z článku, nie o nezávislú validáciu súčasných komerčných dráh.

## Reprodukcia a testy

Na Ubuntu 24.04, CPython 3.12 a x86_64:

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-orbits.txt
.venv/bin/python -m pip install -r requirements-orbit-validation.txt
.venv/bin/python -m pip check
.venv/bin/python tools/orbit_preview.py \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --at 2026-10-22T12:45:00Z --lat 48.1486 --lon 17.1077 \
  --duration-s 60 --step-s 10 --min-elevation-deg 10 \
  --output results/orbits/bratislava-20261022T124500Z.json
.venv/bin/python tools/validate_orbits.py \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --preview results/orbits/bratislava-20261022T124500Z.json \
  --output results/orbits/bratislava-validation.json
```

Overený beh v tomto pracovnom prostredí skončil `status=pass`, `cases=9`, `pip check` nehlásil chyby. Po inštalácii Astropy 7.1.1 a ponechaní `numpy==1.26.4` pôvodný `tools/orbit_preview.py` vytvoril **bitovo rovnaký** JSON ako pred inštaláciou, SHA-256 `6509f9be6fabb554a39134832ffd4280c007740e83b57290d579ddb0b7b9f86a`. Prvý pokus s Astropy 8.0.2 automaticky zvýšil NumPy na 2.5.4, čo odporovalo nášmu pripnutiu; túto kombináciu sme neponechali. Zvolená a overená kombinácia je v samostatnom `requirements-orbit-validation.txt`.

## Výklad a ďalšia validačná brána

Súradnicová konverzia a lokálna geometria nemajú na týchto deviatich vzorkách hrubý nesúlad. Približne 23–52 m rozdiely zemských súradníc medzi knižnicami však nie sú dôkazom centimetrovej presnosti. OMM elementy sú staré približne 32–34 h a pre geometriu pri ďalšom experimente treba časovo príslušnú novú snímku, finálne alebo konkrétne predikčné EOP, merané/operátorom potvrdené dráhy alebo ďalší nezávislý orbitálny podklad. Až potom možno kvantifikovať chybu polohy alebo citlivosť hranice viditeľnosti. Pri orbitálnom náhľade sa neoveruje aktívna konštelácia, lúč, terminál, gateway, satelitné ISL, RF podmienky ani doručenie paketu.
