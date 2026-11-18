# V3 — časovo všeobecná LEO topológia a kvalifikované pripojenie

**Stav: HOTOVO 26. 10. 2026 pre explicitnú natívnu referenčnú podmnožinu.**
Kontrakt a presné hranice sú v
[rozhodnutí V3](../decisions/v3-leo-topology-contract.md). Výsledky sú
výskumný generický DVB model, nie meranie Starlinku, Iridia alebo
Globalstaru.

## Geometrická a vstupná brána

`results/v3_leo_geometry_v3_final_20261026` obsahuje osem
hashovaných preflightov a manifest. Každý prípad sa znovu prepočítal
príkazom `tools/v3_leo_geometry_matrix.py --check`; stav **PASS 8/8**.
Predbežný `results/v3_leo_geometry_v3_20261026` má `REJECTED.txt` po
spresnení hranice podporovaného ISL bitrate/kroku vzorkovania a nemá sa
citovať ako finálny dôkaz.

| Konfigurácia | Výsledok v okne 20–22,5 s | Čo skúša |
| --- | --- | --- |
| `v3_leo_bratislava_explicit.json` | `supported_reference`, 43253/43258 | Explicitný výber a proxy GW 65°N, 20°E. |
| `v3_leo_bratislava_auto.json` | `supported_reference`, 43253/43258 | Deterministický automatický výber. |
| `v3_leo_prague_auto.json` | `supported_reference`, 43253/43258 | Iná poloha UT a beam 32. |
| `v3_leo_afternoon_auto.json` | `supported_reference`, 43257/43072 | O 28 minút neskôr, proxy GW 35°N, 10°E, beam 31. |
| `v3_leo_cape_no_candidate.json` | `geometry_only`, `no_candidate` | Zvolená dvojica nemá viditeľnosť z UT pri Kapskom Meste; **nie** tvrdenie o celej konštelácii. |
| `v3_leo_bratislava_no_beam.json` | `unsupported`, `no_beam` | Kandidátna geometria nezakladá dostupný beam. |
| `v3_leo_bratislava_no_isl.json` | `unsupported`, `no_route` | Kandidát nemá povolenú modelovú ISL trasu. |
| `v3_leo_starlink_six_digit.json` | `unsupported`, `six_digit_tle_unsupported` | Šesťciferné GP ID 100004 sa nedostane do starého TLE adaptéra; žiadny falošný paketový beh. |

Pri všetkých troch natívnych intervaloch bolo 51 vzoriek po 0,5 s;
vstupný GP vek, ID, WGS84 a EOP stav boli kontrolované. Nezávislý
Skyfield prepočet vybraných elevácií sa od Astropy výpočtu líšil najviac
o **0,001228°**. Natívna výška SAT0 v šiestich paketových časoch sa od
nezávisle propagovanej OMM dráhy líšila najviac o **0,157 m**. EOP kód pre UT1 aj polárny pohyb bol vo všetkých troch
intervaloch **2 = predikovaný**, takže ide o geometrickú kontrolu
algoritmu s hashovanou tabuľkou, nie o geodetické meranie na mieste.

## Natívne paketové behy

Tri samostatné adresáre `results/v3_leo_native_v3_{bratislava,prague,afternoon}_20261026`
majú vlastný manifest, OMM→TLE round-trip chybu pod 2 m, generované
konštelačné/anténne vstupy, OSM/SUMO waypointy, raw CAM/ICB1/GRA1,
LAN/OCB PCAP, ISL IPv4/UDP, `PacketTrace.log`, `verification.json` a
`check.log`. **Všetkých 21 vetiev prešlo** opakovaným checkerom.

| Prípad v každej zostave | Konečný stav jedného UT | ICB1 v GW | Dôkaz |
| --- | --- | ---: | --- |
| `stay_sat0` | `connected_old` | 6/6 | Priama SAT0 user/feeder trasa a spätný GRA1/I2V1. |
| `switch_sat1` | `confirmed_new` | 4/6 | 2 správy SAT0, 2 `pending` drop, 2 správy SAT1→ISL→SAT0; obojsmerná sonda pred potvrdením. |
| `no_target_channel` | `failed_old` | 6/6 | Injekcia `no_beam` zamietne cieľ; doručenie ostane na SAT0. |
| `no_target_gateway_or_isl` | `failed_old` | 6/6 | Fyzicky chýbajúca modelová ISL, cieľ bez GW. |
| `no_target_route` | `failed_old` | 6/6 | ISL fyzicky existuje, kvalifikačná politika zablokuje cieľovú trasu. |
| `attach_failed` | `failed_old` | 4/6 | Sonda dorazí do GW, odpoveď zadržaná; rollback kanálov/schedulera na SAT0. |
| `phy_drop` | `connected_old` | 0/6 | Natívny `PHY RTN DRP`, bez akceptovaného GW paketu. |

Kontrola P3 pre päť zdedených variantov opakovane parsuje bajty CAM,
GN/BTP, ICB1, GRA1/I2V1, IP/UDP checksumy, obojsmernú ISL a konkrétne
PacketTrace ID. V3 checker pridáva `no_target_route`, `phy_drop`,
päť oddelených stupňov udalostí a časový geometrický preflight. Ten istý
UT MAC `02-06-00:00:00:00:00:0b` a IP `250.1.0.2` sa zachovali cez
prepnutie a rollback vo všetkých behoch. Úspešný prenos po prepnutí bol
uznaný až po návrate sondy cez cieľový user link. Každý natívny výsledok
obsahuje **119** oddelených V3 udalostí; per-message doručenie pochádza
z raw gateway stopy, nie z geometrického preflightu.

Pražský beh **nepoužíva pražské OSM cesty**: overená bratislavská
SUMO/OSM lokálna trajektória sa synteticky premiestnila a manifest to
výslovne uvádza. Geograficky sa tak skúša satelitná topológia a WGS84
spracovanie, nie dopravná realita Prahy. Proxy GW, diagnostický
všesmerový zisk 17 dBi, vložená 1 Gbit/s ISL a retune/timeout sú
modelové predpoklady. Výsledok nemá operačnú interpretáciu PDR alebo
handover latencie žiadneho operátora.

## Reprodukcia a regresia

```bash
cd '/home/samuel-petrik/Documents/ChatGPT/Bakalarska praca/obnova/Bakalarska praca'
.venv/bin/python tools/v3_leo_geometry_matrix.py results/NEW_UNIQUE_GEOMETRY_ID
.venv/bin/python tools/v3_leo_geometry_matrix.py results/NEW_UNIQUE_GEOMETRY_ID --check
.venv/bin/python tools/run_v3_leo_native.py vendor/ns-3.38-ocb-eval results/NEW_UNIQUE_NATIVE_ID config/v3_leo_afternoon_auto.json
.venv/bin/python tools/check_v3_leo_native.py results/NEW_UNIQUE_NATIVE_ID
.venv/bin/python tools/test_v3_leo_native_mutation.py results/NEW_UNIQUE_NATIVE_ID
```

Výstupný adresár ešte nesmie existovať; runner odmietne existujúci.
Po V3 prešlo **86 Python testov**, štyri rehashované sémantické mutácie
(falošné GW prijatie, odstránený natívny PHY drop, zmenená geometrická
dvojica a posunutá natívna výška dráhy) boli odmietnuté a historický P3 read-only checker stále vrátil
PASS 5/5. Aktívny runtime zostáva výhradne ns-3.38/SNS-3 3.38.

Nasleduje V4: fyzikálne/queue parametre referenčného DVB modelu, ich
citlivosť a analytické hranice. V3 nepovyšuje kandidátnu geometriu na
operátorský attach ani nevypočítava reálnu komerčnú dostupnosť.
