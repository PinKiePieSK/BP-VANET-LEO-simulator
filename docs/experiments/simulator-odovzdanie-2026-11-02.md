# Kontrola simulátora pred odovzdaním vedúcemu — 2026-11-02

## Rozsah

Kontrola sa týka aktuálneho toku scenár → SUMO → Vanetza → ns-3.38/SNS-3 3.38 → surové stopy → verifier → replay. Starý servisný prenos sa z aktívneho príkazu `run` odstránil. Výsledky pôvodných experimentov zostali v zdrojovom projekte na historické porovnanie; prenosný balík obsahuje len aktuálne vstupy a závislosti.

## Nové natívne behy

Všetky čísla sú z nových behov v `results/simulations/`. Každý beh prešiel samostatným príkazom `verify` nad uloženými surovými stopami.

| Beh | Paketový model | CAM TX | DENM v bráne | DENM vo vzdialených autách | Výsledok |
| --- | --- | ---: | ---: | ---: | --- |
| `handoff-smoke-20261102` | pozemný ns-3 | 93 | — | 3 pozemné príjmy | PASS |
| `handoff-example-60s-20261102` | pozemný ns-3, 60 s | 878 | — | 7 pozemných príjmov | PASS |
| `handoff-v2v-20261102` | pozemný ns-3, bez RSU | 93 | — | 1 pozemný príjem | PASS |
| `handoff-starlink-20261102` | spoločný ns-3/SNS-3 | 93 | 1 | 2 | PASS |
| `handoff-iridium-20261102` | spoločný ns-3/SNS-3 | 93 | 1 | 2 | PASS |
| `handoff-globalstar-20261102` | spoločný ns-3/SNS-3 | 93 | 1 | 2 | PASS |
| `handoff-lifecycle-20261102` | spoločný ns-3/SNS-3 | 93 | 3 | 8 | PASS |
| `handoff-radius-20261102` | mimo satelitného dosahu | 93 | 0 | 0 | PASS |
| `handoff-building-20261102` | zatienený satelitný výhľad | 93 | 0 | 0 | PASS |

`PASS` pri negatívnych kontrolách znamená konzistentnú stopu bez doručenia. Pri troch kladných konšteláciách sa zvlášť overilo, že prijatie v bráne a autách je nenulové. Regresná sada `PYTHONPATH=tools .venv/bin/python -m unittest test_u9_cam_denm test_u9_active_server` prešla šiestimi testami vrátane zámerne poškodených paketových bajtov.

## Editor a replay

Načítanie nového behu Starlink cez editor v prehliadači: 5 áut, 3 RSU, 1 aktívny satelit, 211 udalostí, 244 paketových spojení. Časová os dosiahla `6.00 / 6.00 s` a orbitálny čas rovnako 6 s. Detail surového CAM zobrazuje kroky aj polia dekódované z 43 bajtov UPER, vrátane polohy, rýchlosti a Station ID. Technické parametre sa menia bez zahodenia rozpracovaného editora.

## Prenosný balík

`BP-Simulator.zip` bol rozbalený a jeho 11 261 súborov a odkazov bolo nezávisle porovnaných s manifestom. Následná čistá inštalácia na Ubuntu 24.04 zostavila Vanetza, ns-3.38 a SNS-3 3.38, prešla pozemným smoke behom (93 CAM TX, 3 DENM príjmy) a vytvorila `READY` aj `PACKAGE-ID`. V tomto čistom runtime potom samostatné `run` a `verify` pre Starlink, Iridium NEXT a Globalstar dosiahli vždy 93 CAM TX, 1 DENM príjem bránou a 2 vzdialené príjmy. Replay všetkých troch načítal 211 udalostí a 244 spojení. Test spúšťača s okamžite končiacim skúšobným prehliadačom ukončil aj lokálny server. Po zatvorení starého okna sa pôvodný workspace archivoval; štandardná cesta `BP-Simulator-Workspace` teraz ukazuje na overený runtime. Ikona aj `run.sh` boli cez túto cestu opäť otestované.

## Interpretácia

Starlink, Iridium NEXT a Globalstar používajú rôzne orbitálne vstupy a fyzikálne podmienky, ale spoločný generický DVB paketový model SNS-3. Beh nedokazuje presné pokrytie skutočnej operátorskej služby. Aktuálny pozitívny dôkaz zahŕňa jednu aktívnu družicu v podgrafe; rozsiahle handovery a škálovanie na plný aktívny paketový graf zatiaľ nie sú touto sadou preukázané. Vozidlá po príjme DENM nemenia jazdu. Tieto hranice treba uviesť pri návrhu experimentov s vedúcim.
