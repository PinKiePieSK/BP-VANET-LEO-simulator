# SNS-3 smoke testy (22. 10. 2026)

## Účel a kontrola

Hypotéza: kompatibilné tagy ns-3.48/SNS-3 3.48 sa na tejto VM zostavia a pôvodné príklady dokážu doručiť paket cez satelitný model. Kontrolný GEO príklad overuje základný terminálový prístup; LEO príklad overuje SGP4 dvojicu satelitov a ISL v dodanom historickom scenári. Test nevaliduje konkrétneho operátora ani dopravné správanie.

Presné príkazy sú v [reprodukcii](../reprodukcia.md). CMake profil `debug`, cielené príklady, najviac štyri úlohy. Zdrojové commity a závislosti sú v tom istom dokumente. Vstupné `data/scenarios/constellation-leo-2-satellites/positions/tles.txt` má epochu 2014-09-29 a používa dve ISS-like dráhy. Zdrojový scenár má `standard/DVB`, takže sa nedá označiť za Starlink/Iridium/Globalstar MAC.

## Priebeh vrátane neúspešného pokusu

Prvý pokus o presmerovanie GEO logu zlyhal ešte pred spustením programu: relatívny adresár `../../results/sns3_smoke` neexistoval (shell exit 1). Po jeho vytvorení ten istý simulačný príkaz skončil exit 0. LEO príkaz skončil exit 0. Oba behy vytvorili `PacketTrace.log` v submodule `data/sims/`; kópie sú uložené v `results/sns3_smoke/` s kontrolnými súčtami.

| Test | Skutočne pozorované | Obmedzenie |
| --- | --- | --- |
| `sat-cbr-example`, GEO, 11 s | Aplikácia vypísala odoslanie 512 B v čase 8, 9, 10 s a príjem 512 B v 8,31103 s. Packet trace zaznamenal linkové udalosti. | Nevyvodzovať PDR z troch logovaných riadkov ako reprezentatívnu mieru; príklad je len smoke. |
| `sat-constellation-example`, dve LEO, 30 s | `PacketTrace.log` obsahuje satelitné PHY RX v návratovom smere a UT PHY RX v doprednom smere. Súbor `stat-global-fwd-app-throughput-scalar.txt` má 75,4806 kb/s a `stat-global-rtn-app-throughput-scalar.txt` 126,693 kb/s. Počítadlá ISL drop-rate majú 1600/598 vzoriek a nulový súčet dropov. | Priepustnosť je výsledok dodaného syntetického testu s viacerými tokmi a 1 s intervalom, nie meranie reálnej služby. Nulový súčet dropov neznamená nulovú stratu na celej trase. |

## Interpretácia

Test potvrdzuje, že satelitný modul sa dá lokálne skompilovať a vykonať s paketmi a SAT/UT/GW stopami. Nepotvrdzuje ešte integráciu s vozidlami. Tú musí otestovať `src/vanet-sns3.cc` s rovnakou sada knižníc a samostatnou kontrolou všetkých hopov.
