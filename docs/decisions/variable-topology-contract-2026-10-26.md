# Počet áut, RSU a satelitov ako vstup scenára

**Rozhodnutie 26. 10. 2026.** Finálny simulátor nesmie mať na úrovni scenára zabudované názvy `cars03/cars12/cars24`, `rsu0/rsu1` ani dvojicu `SAT0/SAT1`. Počty sú odvodené z explicitných zoznamov uzlov. U0 normalizovaný plán má uviesť všetky zdrojové autá, všetky aktívne RSU, terminály, orbitálne objekty a ISL hrany s unikátnymi identifikátormi. Každý prijatý uzol sa musí objaviť v raw identite, packet trace alebo v explicitnom dôvode, prečo sa nepoužil.

„Ľubovoľný počet“ znamená **parametrický počet v overenej oblasti modelu**. Pamäť, čas, adresné rozsahy a fyzická platnosť vždy vytvárajú hranicu. Preflight má vrátiť názov limitu a skutočné vstupné počty; nesmie pri prekročení ticho orezať pole. Rozlišujeme: konfiguráciou prijatý počet, počet reálne vytvorených uzlov, počet dekódujúcich RSU, počet kvalifikovaných satelitných kandidátov a počet satelitov skutočne použitých paketom. Tieto menovatele nemožno zameniť.

## Aktuálne vykonaný rozsah

Pôvodný U2 experiment v `src/u2-multi-rsu-backhaul.cc` je nemenný dôkaz 1/2 RSU × 3/12/24 áut. Nástupnícky `src/u2-variable-rsu-backhaul.cc` odstránil **pevný dvojRSU guard**. Jeho `tools/run_u2_variable.py` a `tools/check_u2_variable.py` iterujú pomenované baseline prípady z konfigurácie, nie z pevnej šestice názvov. [Spoločná 26‑vetvová matica](../experiments/u2-variable-rsu-2026-10-26.md) prešla pri 1/2/3 RSU a 3/5/12/24 autách. Stále používa V5 pozemný vstup s technickým limitom 50 rádiových účastníkov, 20–100 vzoriek a jeden spoločný pevný UT. Tento rozsah je potrebné vo finálnej capability matici označiť ako aktuálny, nie sľúbiť viac bez ďalšieho behu. Satelitná vetva nástupníckeho U2 stále používa presne **dva** objekty a jeden ISL; tým nepreukazuje variabilný satelitný počet.

## Brána U3 pre satelity

Orbitálny vstup má byť zoznam objektov s katalogovým ID, zdrojom OMM/GP, epochou a kontrolou platnosti; ISL je samostatný graf hrán. Pre každého kandidáta sa počíta geometria UT a GW, beam gain, attach a skutočné rozhrania SNS-3. Routing vyberie kvalifikovanú doprednú aj spätnú cestu podľa grafu, nie podľa pevného indexu 0/1. Jediný satelit môže vytvoriť priamu trasu, dvojica jednu ISL a 3+ objekty alternatívne cesty; každá možnosť vyžaduje paketovú pozitívnu aj negatívnu kontrolu. Handover nemení identitu UT ani rodičovské CAM/ICB1 ID. Ak SNS-3 3.38 danú topológiu nevie vykonať, preflight vráti presné `unsupported` a nesmie ju predstierať replayom či geometriou.

## Brána škálovania a overenia

Po zrušení pevných pomenovaní treba otestovať netabuľkový počet áut a aspoň tri aktívne RSU v tom istom engine a tom istom checkeri. Každá vetva uvádza `generated_cam`, všetky fyzické RSU RX páry, jedinečné CAM, duplicity, reporty, ponuku, drop a návrat. Checker overí výber podľa skutočného RX, parent ID, FIFO a správne auto. Pre 1, 2 a 3+ satelity analogicky overí presný počet vytvorených orbitálnych uzlov, kvalifikované trasy, ISL payload a návrat. U8 potom zmrazí otestovaný rozsah výkonnosti, veľkosť výsledkov a preflightové limity; bez toho slovo „ľubovoľný“ neznamená neobmedzenú kapacitu.
