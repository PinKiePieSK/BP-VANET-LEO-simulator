# Viditeľnosť cestných vstupov SUMO — 11. 11. 2026

Prehľad cestných vstupov SUMO sa zobrazuje pri vybranej ceste alebo aktívnom nástroji kreslenia cesty. Pri aute, RSU, budove a prázdnom výbere s iným nástrojom je skrytý. Nová prázdna mapa aktivuje kreslenie cesty, preto sa na nej prehľad ukáže okamžite. Prepnutie nástroja aktualizuje viditeľnosť bez potreby zmeny scenára; výber objektu ju aktualizuje pri prekreslení. Obsah XML vstupov ani export SUMO sa nemenia.

## Overenie

V samostatnom headless Firefoxe mal panel pri úvodnom prázdnom výbere `hidden=true` a vypočítané `display:none`. Po zapnutí kreslenia cesty bol viditeľný, po prepnutí na výber bez označenej cesty sa skryl. Výber cesty v zozname ho zobrazil aj pri nástroji auta; po zrušení výberu a po vložení auta bol znovu skrytý. Skutočný načítaný skript mal verziu `20261111-road-input-visibility1`.
