# Editovateľný dopravný scenár v2: reprodukovateľný SUMO základ

## Rozsah a hranica modelu

`tools/editable_scenario_v2.py` prijíma jediný verzovaný JSON a vytvorí obojsmerné cestné úseky, trasy ľubovoľného počtu vozidiel (limit 1–50) a voliteľné polohy RSU (0–20). Vykonáva **iba SUMO dopravnú simuláciu**. Polia `technologies` a `flows` sú kontrolovaná deklarácia zámeru; nespúšťajú ns-3, Vanetza ani SNS-3 a negenerujú žiadne sieťové pakety. `network_execution: "schema_only"` a `flows[].execution: "not_implemented"` sú povinné, aby export nebol zamenený za hotový sieťový experiment. Existujúci `tools/scenario_run.py` naďalej používa osobitnú staršiu schému s presne dvoma vozidlami; v2 nie je jeho vstupom.

Tento fixture je **syntetický kartézsky cestný graf**. Nedokazuje reálnu premávku, geografickú mapu, dosah rádia, skutočný prenos CAM/DENM ani prevádzku satelitného operátora. Reálne OSM a paketové piloty v projekte zostávajú samostatnými experimentmi.

## Kontrakt JSON a jednotky

Príklad: `data/inputs/editable-road-v2/scenario.json`. Schéma má `schema_version: 2`. Neznáme kľúče validátor odmieta, aby sa nestratili očakávané parametre. Identifikátory začínajú ASCII písmenom, potom obsahujú len ASCII písmená, číslice alebo `_` (max. 32 znakov); ID uzlov, úsekov, áut, RSU a tokov sú navzájom jednoznačné.

| Pole | Význam |
| --- | --- |
| `simulation.duration_s`, `step_s`, `seed`, `utc_origin` | Dĺžka a krok v sekundách, celé semeno SUMO, explicitný UTC počiatok. UTC sa ukladá ako metadáta; SUMO používa čas od nuly. |
| `georeference` | Povinná explicitná kotva `{frame:"WGS84_ENU",anchor_x_m,anchor_y_m,latitude_deg,longitude_deg,height_m}`. Lokálne x/y v metroch určujú bod, ktorému prislúcha WGS84 zemepisná šírka/dĺžka a elipsoidická výška. Samotný SUMO dopravný beh súradnice WGS84 nepoužíva. Podrobný kontrakt a test migrácie sú v `docs/experiments/editable-v2-wgs84-enu-anchor.md`. |
| `roads.nodes[]` | `{id,x_m,y_m}` v lokálnej rovine 0–2000 m. |
| `roads.segments[]` | `{id,from,to,shape,speed_limit_mps,lanes_each_direction}`. `shape` obsahuje oba koncové uzly. Z každého záznamu vzniknú dve jednosmerné SUMO hrany (`_forward`, `_reverse`) s opačnou orientáciou. Rýchlosť je m/s, počet pruhov platí v každom smere. |
| `vehicles[]` | `{id,depart_s,depart_speed_mps,depart_pos_m?,route,technologies}`. `route` je usporiadaný zoznam `{segment,direction}`; susedné kroky musia mať spoločný koncový/začiatkový uzol. `depart_pos_m` je od začiatku prvej **smerovanej** hrany, predvolene 0 m. `depart_speed_mps` je požadovaná rýchlosť pri vložení, nie trvalá rýchlosť vozidla. |
| `rsus[]` | `{id,x_m,y_m,technologies}`. V SUMO vzniká POI v tejto polohe, bez sieťového uzla. |
| `technologies` | Unikátny zoznam z `its_g5`, `cellular_v2x`, `ip_backhaul`, `satellite_terminal`. Je to **požadovaná schopnosť**, bez verzie protokolu, RF parametrov alebo implementácie. |
| `flows[]` | `{id,source,target,technology,message_type,execution}`. `target` je ID auta/RSU alebo `broadcast`; `message_type` je `CAM`, `DENM`, `IP_REPORT`, `CUSTOM`. Validátor overí existenciu zdroja/cieľa a príslušnú deklarovanú schopnosť. Pre broadcast vyžaduje aspoň jeden iný schopný uzol. `execution` musí byť `not_implemented`. CAM/DENM možno deklarovať iba s `its_g5` alebo `cellular_v2x`. |

Technológia u oboch koncov nepreukazuje dosah, viditeľnosť, kompatibilné rádio, sémantiku správy ani doručenie. `satellite_terminal` je abstraktná voľba; z nej nemožno vyvodiť Starlink/Iridium/Globalstar rozhranie. `broadcast` neurčuje konkrétneho príjemcu, iba zámer vysielania.

## Algoritmus a vstupy/výstupy

Validátor kontroluje číselné medze a konečnosť, ID, koncové body tvaru (tolerancia 0,01 m), dĺžku úsekov (aspoň 30 m), pripojenosť trás, odchod v intervale simulácie, `depart_pos_m` najviac 20 m pred koncom prvého úseku a schopnosti deklarovaných tokov. Pre každú cestu zapisuje dve orientované hrany do `road.edg.xml`; uzly do `road.nod.xml`; trasy, typ a odchody vozidiel do `vehicles.rou.xml`; RSU body do `rsus.add.xml`. `netconvert` vytvorí `road.net.xml`, SUMO vytvorí `fcd.xml` (poloha/rýchlosť pri každom kroku) a `summary.xml`. Generátor navyše vyžaduje, aby SUMO vložilo všetky nakonfigurované vozidlá a aby sa ich ID objavili v FCD. Manifest ukladá SHA-256 zdroja a výstupov, verzie nástrojov, presné príkazy, posledný SUMO súhrn a deklarované technológie/toky.

Prístup s editovateľnými plain XML a `netconvert`, význam jednosmernej hrany, tvaru a rýchlosti vychádza z [oficiálnej dokumentácie SUMO PlainXML](https://sumo.dlr.de/docs/Networks/PlainXML.html). Formát trasy a odchodu opisuje [SUMO vehicle/route dokumentácia](https://sumo.dlr.de/docs/Definition_of_Vehicles%2C_Vehicle_Types%2C_and_Routes.html), RSU POI syntax [SUMO shapes](https://sumo.dlr.de/docs/Simulation/Shapes.html) a FCD obsah [SUMO FCD output](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html). V použitom prostredí majú `sumo` a `netconvert` verziu 1.18.0; presný výpis je aj v manifeste konkrétneho behu.

## Reprodukcia a výsledok fixture

Z koreňa repozitára:

```bash
python3 tools/editable_scenario_v2.py data/inputs/editable-road-v2/scenario.json
python3 tools/editable_scenario_v2.py data/inputs/editable-road-v2/scenario.json --output results/editable_scenario_v2
python3 tools/test_editable_scenario_v2.py
```

Výsledky sú v `results/editable_scenario_v2/`: `manifest.json`, vstupné XML, `road.net.xml`, `fcd.xml`, `summary.xml` a logy. Test porovná obe smerované hrany každého z dvoch úsekov, presné trasy, 2 RSU POI, štyri FCD prúdy a ich orientáciu, 40 m štartovací offset auta `car2`, `4` vložené/`4` dorazené autá, `0` kolízií a `0` teleportov. Osemnásť záporných validačných prípadov zahŕňa neplatnú verziu, deklarovanie neexistujúceho network runnera, nepripojenú trasu, neplatnú technológiu, chybný endpoint, duplicitné ID, neplatný offset, neplatný tok a chýbajúcu alebo neplatnú WGS84/ENU kotvu. Test kontroluje tiež zachovanie troch deklarovaných tokov a geografickej kotvy v manifeste. Sieťové PDR/oneskorenie/jitter z tohto výstupu neexistujú.

## Obmedzenia a ďalšie napojenie

Syntetické súradnice sú lokálne metre; povinná kotva umožňuje ich explicitné premietnutie do WGS84 v samostatnom paketovom adaptéri, ale nedokazuje existenciu cesty na zemskom povrchu. UTC počiatok v tomto čisto dopravnom behu nepoháňa ephemeridy. Validátor kontroluje grafové spojenie cesty, no nekontroluje dopravnú vierohodnosť geometrických križovaní, pravidlá odbočovania ani kalibráciu dopytu. SUMO môže upraviť požadovanú rýchlosť pri vložení podľa limitu cesty; FCD je skutočný simulačný stav. RSU sú iba POI. Paketový adaptér `tools/run_editable_v2_cam_radio.py` existuje iba pre prísne obmedzenú podmnožinu jedného CAM broadcast toku; ostatné `flows` zostávajú návrhom a explicitne sa odmietajú.
