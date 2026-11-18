# Vzorkovaní geometrickí kandidáti nad editovateľnou RSU

**Stav:** 22. 10. 2026 UTC. **Účel:** pripraviť kontrolovateľný orbitálny vstup pre budúce testy výberu družice. Výsledok **nie je** handover, rádiové spojenie ani predpoveď dostupnosti služby Globalstar. Kód: [`tools/analyze_editable_globalstar_candidates.py`](../../tools/analyze_editable_globalstar_candidates.py), testy: [`tools/test_analyze_editable_globalstar_candidates.py`](../../tools/test_analyze_editable_globalstar_candidates.py).

## Vstupy, algoritmus a jednotky

Vstupom je schéma v2 [`packet-subset.json`](../../data/inputs/editable-road-v2/packet-subset.json) s editovateľnou polohou `rsu0`, explicitnou WGS84/ENU kotvou, UTC začiatkom `2026-10-22T12:45:00Z` a 0,5 s krokom. Druhý vstup je hashovaný archív GP/OMM [`20261022T124815Z-retlector`](../../data/orbits/20261022T124815Z-retlector/manifest.json), označený ako cache pôvodných CelesTrak GP dát. Archív bol získaný **po** simulovanom začiatku, teda ide o retrospektívny výpočet. Každý OMM záznam má svoj hash a elementy staršie než 48 h do konca 360 s auditovaného intervalu sa vyradia. K výpočtu treba pripnuté `sgp4`, `astropy`, `astropy-iers-data`, `erfa` a `numpy` z projektovej `.venv`; metadáta zaznamenávajú verzie i hash použitej tabuľky EOP. Transformácia je `OMM→SGP4/TEME→ITRS→topocentrická elevácia/vzdialenosť` voči obom bodom.

RSU sa prevedie z lokálnych metrov na WGS84. Druhý bod je **centrum mesta Nemea** `37,8167° N, 22,6667° E, 0 m`, iba proxy lokality [oznámeného pozemného uzla v Grécku](https://investors.globalstar.com/news-releases/news-release-details/globalstar-completes-expansion-greece-ground-station-marking-key). Nie je to zameraná anténa, pridelená gateway ani dôkaz jej prevádzkového stavu. Pri každom z 121 časov `t=0…60 s` nástroj ráta počet archívnych objektov nad skúšobnou maskou 10° pri RSU a proxy osobitne a ich prienik pre **ten istý objekt**. Z prieniku volí najvyššiu hodnotu `min(elevácia_RSU, elevácia_proxy)`; presná rovnosť sa rieši menším katalógovým ID. Maska a toto pravidlo sú výskumné predpoklady, nie parametre Globalstaru. Výstup obsahuje šikmé vzdialenosti v km a súčet dvoch jednosmerných vákuových `r/c` časov v ms (`c=299792,458 km/s` podľa [BIPM](https://www.bipm.org/en/si-base-units/metre)). Neobsahuje modemový, MAC, gateway ani core čas.

## Hypotéza, kontrola a pozorovanie

Hypotéza: pri rovnakom archivovanom stave môže zmena polohy RSU alebo plynutie času zmeniť geometricky preferovaný objekt; takú zmenu možno zaznamenať bez predstierania prevádzkového handoveru. Kontrola pôvodu overuje hash scenára, manifestu, OMM záznamu, EOP, generátora a CSV; fyzikálna kontrola nezávisle počíta `r/c` zo zaokrúhlených výstupných vzdialeností. Pri 21,5 a 22,0 s sa vybrané objekty 37741 a 37190 nezávisle prepočítali cez pripnutý **Skyfield 1.55** (`EarthSatellite.from_omm`, jeho vlastný Earth-orientation podklad): odchýlka oboch elevácií bola <0,001° a oboch vzdialeností <0,05 km. Je to kontrola implementácie transformácie pri dvoch vzorkách, nie presnosť skutočnej orbity. Záporne zadaný názov brány sa odmietne. Samostatná kópia scenára s `rsu0.x_m += 5` zmenila hash CSV z `9806aa…` na `b07f76…`, bez zmeny počtu kandidátskych prechodov.

| Čas od začiatku | Vybraný katalógový objekt | Spoločných geometrických kandidátov | Dva úseky `r/c` |
| ---: | ---: | ---: | ---: |
| 20,0 s | 37741 | 2 | 18,364383740 ms |
| 21,5 s | 37741 | 2 | 18,408112563 ms |
| 22,0 s | 37190 | 2 | 17,426235847 ms |
| 22,5 s | 37190 | 2 | 17,417631933 ms |

Pri 0,5 s vzorkovaní sa poradie dvoch kandidátov zmenilo **medzi 21,5 a 22,0 s**. Obaja zostali nad maskou, takže to nie je geometrický výpadok. Skutočné prepnutie terminálu, beam, MAC prerušenie, opätovná registrácia a paketová strata sa z tohto faktu **nedajú odvodiť**. Starší šesťpaketový integrovaný pilot úmyselne používa jediný objekt 37741 počas celého krátkeho okna; tento nový geometrický audit jeho paketové výsledky nemení. Skok vo vypočítanom `r/c` pri zmene vybraného objektu nie je merané zlepšenie latencie služby.

## Opakovanie a výstupy

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/analyze_editable_globalstar_candidates.py \
  --scenario data/inputs/editable-road-v2/packet-subset.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --gateway-proxy nemea-city-proxy \
  --output-csv data/derived/editable-globalstar-candidates/rsu0-60s-20261022.csv
.venv/bin/python -m unittest discover -s tools \
  -p 'test_analyze_editable_globalstar_candidates.py' -v
```

CSV má 121 riadkov a SHA-256 `9806aa7513b15898059a018e197793d68b08c54af28a491cc22d91066fca1bab`. Vedľajší `.metadata.json` obsahuje jednotky, verzie, zdroje, časový interval prechodu, všetky relevantné hashe a obmedzenia. Štyri cielené testy prešli; prvý pokus aj výsledný beh boli úspešné, neúspešná skúška vstupu s neznámou bránou bola zámerne odmietnutá. Žiadne údaje o dostupnosti terminálu, anténe, lúči, handover protokole, skutočnom feeder RF, stratách či servisnej latencii neboli merané. Ďalší experiment musí modelovať konkrétny terminál a oddeliť jeho stavovú mašinu od geometrického výberu kandidáta.
