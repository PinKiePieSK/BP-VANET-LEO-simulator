# Geometria používateľského úseku pre editovateľnú RSU

**Stav:** 22. 10. 2026 UTC. **Rozsah:** výlučne poloha RSU → katalogizovaný objekt skupiny Iridium NEXT. Nejde o rádiový link, skutočne pridelený satelit, Certus 100 službu ani kompletnú trasu do gateway. Kód: [`tools/prepare_editable_v2_iridium_user_geometry.py`](../../tools/prepare_editable_v2_iridium_user_geometry.py), [testy](../../tools/test_prepare_editable_v2_iridium_user_geometry.py).

## Účel, algoritmus, vstupy a jednotky

Služba [Iridium Certus 100](https://www.iridium.com/services/iridium-certus-100) a [terminál SkyLink 5100](https://naltec.com/products/skylink-5100/) sú konkrétnymi kandidátmi pre budúci IP servisný model. Tento experiment zatiaľ neobsahuje terminál ani jeho príjem. Jeho úlohou je georeferencovať `rsu0` editovateľného scenára a vypočítať iba dolnú fyzikálnu hranicu jedného prípadného úseku k družici, aby sa model Certus nemiešal s dvojkoncovým scenárom Globalstaru.

Vstupy: [`packet-subset.json`](../../data/inputs/editable-road-v2/packet-subset.json) s WGS84/ENU kotvou a RSU v miestnych metroch; archivovaná [GP/OMM snímka](../../data/orbits/20261022T124815Z-retlector/manifest.json) skupiny `iridium-NEXT`; lokálna pripnutá EOP tabuľka. Snímka cache deklaruje pôvod v [CelesTrak GP](https://celestrak.org/NORAD/documentation/gp-data-formats.php) a bola získaná po UTC začiatku scenára, teda ide o **retrospektívne** prehratie. SHA-256 manifestu, gzip, surových OMM, každého vybraného záznamu, EOP, scenára, generátora a výstupu sa zapisujú do metadát. Z 80 archívnych záznamov prešlo 48 h vekovým filtrom 79; počet archívnych objektov nie je počet prevádzkovaných satelitov.

Každý z časov 20,0–22,5 s po 0,5 s používa rovnaký UTC základ ako SUMO. OMM sa propaguje cez SGP4 v TEME; Astropy s miestnym EOP prevedie bod do ITRS. Pre topocentrický RSU v WGS84 sa vypočíta elevácia v ° a vzdialenosť v km. Z kandidátov nad výskumnou 10° maskou sa zvolí najvyššia elevácia, pri presnej rovnosti nižšie katalógové ID. Maska nie je publikovaným prahom terminálu ani operátora. Jednosmerný vákuový čas v ns je `round(šikmá_vzdialenosť_km / 299792,458 km/s × 10⁹)`. Nie je to celé spojenie, RTT ani servisné oneskorenie. Experiment nepozná priradenú gateway, polohu ďalšieho satelitu na prevádzkovej crosslinkovej ceste, beam, RF link budget, MAC, attach ani skutočný handover.

## Výsledok a kontrolné varianty

V šiestich vzorkách bol nad experimentálnou maskou vybraný katalogizovaný objekt **43253**. Elevácia klesla z 25,861331° na 25,446430°; geometrická vzdialenosť stúpla z 1506,155660 km na 1520,946143 km. Výpočtový jednosmerný vákuový čas stúpol z 5 023 995 na 5 073 330 ns. To nie je pozorovanie rádiového spojenia ani dostupnosti Certus. Výstupné CSV má SHA-256 `1acb2c8fb3b21ce5d0ec07c49d6bbee971ec71e5259596646a7b6e5dcd6db546`.

Tri cielené testy kontrolujú presné časy, pôvod OMM, `r/c`, konzistentný katalógový objekt, negatívny blok a hash výstupu. Dva hraničné časy sa nezávisle prepočítali cez pripnutý Skyfield 1.55; rozdiel vybranej elevácie bol <0,001° a vzdialenosti <0,05 km. Rozdielne podklady orientácie Zeme znamenajú, že nejde o potvrdenie skutočnej orbitálnej presnosti. `--force-block` je **syntetická** záporná kontrola: pôvodné uhly a vzdialenosti zostanú, `enabled=0` pre všetkých šesť riadkov, takže žiadny model nesmie vysvetľovať blok ako fyzikálny výpadok. Prvý pozitívny beh, negatívny beh a testy skončili úspešne; žiadne neúspešné simulačné dáta sa nezahadzovali.

## Opakovanie

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/prepare_editable_v2_iridium_user_geometry.py \
  --scenario data/inputs/editable-road-v2/packet-subset.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --output-csv data/derived/editable-iridium-user-leg/rsu0-20261022.csv
.venv/bin/python -m unittest discover -s tools \
  -p 'test_prepare_editable_v2_iridium_user_geometry.py' -v
```

V testovacom negovanom variante pridaj `--force-block --output-csv /tmp/editable-iridium-user-blocked.csv`. Výsledok je iba **vstup** k budúcemu servisnému modelu. Z tejto geometrie nie je dovolené dopočítať neznáme Iridium crosslinky, feeder bránu či prevádzkovú latenciu. Ak sa neskôr kalibruje celkový servisný čas z merania, treba zamedziť dvojitému započítaniu tohto `r/c` úseku.
