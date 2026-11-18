# U9: pracovný výrez, ručné budovy a rozklad paketov (2026-11-01)

## Rozsah

- Pracovný výrez má samostatnú šírku a výšku, 500–4 000 m. Editor, OSM import, raster terénu, hranice objektov a vstup behu používajú rovnaký obdĺžnik. Staršie scenáre s `extent_m` sa čítajú ako štvorcový výrez.
- Prázdny svet dovoľuje vložiť obdĺžnikovú budovu, nastaviť jej pôdorys a výšku. Budova sa odovzdáva modelu pozemného tienenia; jej výška je scenárový predpoklad. Pri zmene rozmerov prázdneho sveta sa objekty posunú so stredom. Reálna mapa sa pri zmene rozmerov znovu načíta.
- Kliknutie na cieľ vozidla a skupinový cieľ používa presný úsek cesty a odmieta príliš vzdialený bod.
- Detail paketu zobrazuje vrstvy, hodnoty a surový hex. CAM UPER dekóduje pripnutou knižnicou Vanetza Release 2, ktorou sa CAM vytvára. Obsahuje polohu WGS84, rýchlosť, smer, rozmery vozidla, neistoty, nízkofrekvenčný kontajner a ďalšie dostupné polia. GeoNetworking, BTP, IPv4/UDP a vlastné ICB1/GRA1/I2V1/C1/K1/A1 rámce sa rozkladajú podľa svojich potvrdených formátov. Neznámy obsah zostáva označený ako neznámy. Bitovo balené polia ASN.1 UPER zdieľajú bajtový rozsah, preto zvýraznenie nepredstiera samostatné bajtové hranice.

## Overenie

- Bratislava, OSM 4 000 × 4 000 m: 5 786 úsekov ciest, 12 977 budov, terén 142 × 142. Obdĺžnik 3 000 × 1 500 m: 2 252 úsekov, 5 680 budov, terén 109 × 59.
- Úplný beh `manual-building-rectangle-20261101`: 3 autá, 1 RSU, ručná budova, 4 s, 15 CAM TX, 16 RX, bez teleportu; `bp_u9.py verify` PASS.
- Historický zmiešaný pozemný/satelitný beh `ground-osm-service-20261101` a fyzikálny beh `f5-heightbudget-starlink-20261101`: `bp_u9.py verify` PASS po zmene zdrojov.
- 49 testov `test_u9*.py`: OK. Cieľové trasy: individuálny presný úsek, skupina na 12 m rozostupe, odmietnutie bodu mimo cesty: PASS.
- 15 skutočných CAM rámcov zo skúšobného behu dekódovaných knižnicou Vanetza; station ID a `generationDeltaTime` sa zhodujú so stopou. V prehliadači potvrdené rozbalenie GN/BTP/CAM a význam hodnôt konkrétneho paketu.
- Nezávislý 4 s beh v pracovnom runtime na ploche tiež prešiel `bp_u9.py verify`; používateľská adresa `127.0.0.1:8765/u9-simulator.html` zobrazuje dekódovaný CAM. Zmiešaný servisný rámec C1 na Starlink behu dekódoval vnorený CAM; historický ICB1 report takisto poskytol vnorený CAM. Prenosný ZIP má platný manifest a úspešnú kontrolu CRC.

## Hranice

- Dekóder prekladá prítomné polia vo vysielanom CAM, nenahrádza meranie skutočného vozidla. Hodnoty neistoty nastavené na „nedostupné“ sú takto zobrazené.
- Výška ručne vloženej budovy je vstup používateľa, nie údaj z mapy. OSM výšky a odvodené odhady zachovávajú svoju osobitnú provenienciu.
- Rozmer jedného výrezu je obmedzený na 4 km v každej osi kvôli vstupnej a výkonovej hranici súčasného importéra; obdĺžnik má ľubovoľný pomer strán v tomto rozsahu.

## Dodatočná kontrola: pozemné tienenie, ciele áut a výber miesta

- Párový kontrolný beh bez ručne vloženej budovy `manual-building-no-wall-control-20261101` zachoval všetky ostatné vstupy predchádzajúceho behu. Príjem CAM sa zvýšil zo 16 na 45; stanica 1001 mala za budovou 0 prijatých CAM a bez nej 21. Obidva behy majú `verify` PASS. Budova teda ovplyvňuje samotný pozemný prenos, nie iba kresbu.
- V prehliadači bol individuálny cieľ vybraný kliknutím na cestu a uložený. Editor teraz zobrazuje odhad času jazdy a upozorní, ak sa cieľ pri zvolenej dĺžke behu nestihne. Pri zmene smeru auta sa predchádzajúci cieľ zruší, aby nezostal na nesprávnej strane úseku. Cestný graf sa po editácii cesty obnoví.
- Skupinový cieľ mal potvrdenú chybu poradia. Pôvodné priradenie na rovnakom pruhu dalo zadnému autu vzdialenejší cieľ. Porovnávací 30 s beh `route-arrival-qa-20261101` (3 autá, 1 RSU) skončil s autami stojacimi za predným vozidlom na x=410,9; 418,4; 425,9 m. Po oprave sa cieľové polohy prideľujú v poradí vozidiel v pruhu: zadné auto dostane bližší cieľ, predné vzdialenejší. V prehliadači sa uložili ciele 315,6 / 327,6 / 339,6 m pre autá na počiatočných pozíciách 50 / 150 / 200 m. Samostatný 30 s beh `route-arrival-fixed-qa-20261101` s rovnakým poradím a cieľmi 326 / 338 / 350 m skončil na presne zodpovedajúcich fyzických pozíciách x=425,9 / 437,9 / 449,9 m, bez teleportov; `bp_u9.py run` PASS. Súradnica x obsahuje 100 m posun začiatku cesty.
- Tlačidlo „Umiestniť miesto“ na glóbuse zapne jednorazový výber. Skúška v prehliadači zmenila lokalitu kliknutím na 48,24490°, 17,36554° a režim sa vypol. Bežné kliknutie bez zapnutého výberu polohu nezmenilo. Pri zmene lokality sa zároveň zruší rozpracovaný individuálny aj skupinový cieľ.
- Tieto behy dokazujú plánovanie na jednom pruhu. Pri autách prichádzajúcich z rôznych ramien cestnej siete poradie pri zlúčení stále určuje SUMO; editor negarantuje, že každý člen skupiny do cieľa dorazí v zvolenom čase. Odhad času jazdy je informatívny a neobsahuje možné čakanie za inými autami.
