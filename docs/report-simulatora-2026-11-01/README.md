# Technický report celého simulátora BP

**Pracovný stav: 1. november 2026.** Report má dve vrstvy: najprv pochopenie systému, potom technický výklad až ku kódu. Vznikol čítaním aktívneho projektu a kontrolou implementácie; nejde o úpravu simulátora ani pôvodného rukopisu.

## Odporúčané čítanie

- [1. Zrozumiteľný prehľad](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/report-simulatora-2026-11-01/01-zrozumitelny-prehlad.md>) — Celky, ich prepojenie, jedna správa od auta po bránu, rozdiel medzi modelom a službou, slovník.
- [2. Podrobný rozbor kódu](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/report-simulatora-2026-11-01/02-technicky-rozbor-kodu.md>) — Vstupy, server, SUMO, CAM/OCB, orbitálny plán, budovy, antény, servisné jadro, RF rovnice, historické SNS-3, výstupy, testy a replay.
- [3. Zdroje a overenie](</home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca/docs/report-simulatora-2026-11-01/03-zdroje-a-overenie.md>) — Klikateľné súbory a funkcie, rozsah vykonanej kontroly a tri znovu overené servisné výsledky.

Najpodstatnejšia zmena oproti reportu z 28. októbra: nové jednotné satelitné scenáre s `dynamic_physical=true` používajú servisný udalostný model nad skutočnými CAM bajtmi v ns-3 čase. Starší generický SNS-3 DVB engine ostáva samostatnou reprodukovateľnou vetvou. Nové C1/K1/A1 správy a staré ICB1/GRA1/I2V1 sa v reporte dôsledne rozlišujú.

Pri čítaní netreba poznať celý kód. Prvá časť vysvetlí význam pojmov. Druhá na tom stavia a ukazuje, ktoré funkcie rozhodujú, čo sa naozaj vykoná. Príklady sú výslovne odlíšené od nameraných či uložených výsledkov.

**Kontrola pri tvorbe:** 42 existujúcich cielených testov OK a opätovný servisný audit troch uložených behov PASS. Úplný rozsah a hranice overenia sú v tretej časti. Odtlačky prečítaných zdrojov sú v `audit-zdrojov.json`.
