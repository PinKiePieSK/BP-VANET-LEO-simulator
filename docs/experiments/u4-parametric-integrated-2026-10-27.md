# U4: parametrická fyzika a kapacity v jednom natívnom systéme

**Runtime:** iba projektový ns-3.38/SNS-3 3.38. **Aktívny zdroj:** `src/u4-parametric-leo-backhaul.cc`. **Vstup:** `config/u4-integrated-matrix.json`. **Spustenie:** `.venv/bin/python tools/run_u4_parametric.py --output results/<novy-adresar>`, potom `.venv/bin/python tools/check_u4_parametric.py results/<novy-adresar>` a `.venv/bin/python tools/test_u4_parametric_mutation.py results/<novy-adresar>`.

## Čo je integrované

Tento zdroj zachováva U1/U2/U3 cestu: natívne CAM z Vanetza/802.11p, prijatie na RSU, ICB1 cez LAN a SNS-3 UT, fyzický LEO prenos s handoverom, natívne ISL, gateway, GRA1 a I2V1 späť konkrétnemu autu. U4 pridáva parametrický zisk diagnostickej anténovej mapy, výkon vysielača UT, referenčné frekvencie a teploty, DVB/ACM/ARQ nastavenia, interval plánovača, obidve rýchlosti a kapacity fyzických ISL frontov. Každý prípad má totožný U3 pohyb, CAM bajty a satelitnú geometriu; mení len deklarované citlivostné polia. Záťaž `burst` drží prijaté ICB1 v aplikačnej fronte UT a uvoľní **tie isté bajty a ID** o 13,5 s.

Hodnoty v `sns3_reference` vychádzajú z generickej konfigurácie `SimulationHelper::SetDefaultValues`/`ConfigureLinkBudget` v SNS-3 a z V4 kontraktu. `beam_gain_dbi=17`, `ut_power_dbw=4`, `1 Gbit/s`, 100 paketov a ostatné čísla sú **výslovne deklarovaný diagnostický referenčný profil D**, nie parametre Starlinku, Iridia ani Globalstaru. GIS poloha gateway je proxy, zisk lúča je syntetická konštantná mapa. Stav A znamená len overený mechanizmus v kóde/meraní, nie zhodu s operátorom.

`SatPhy::Initialize()` prepočíta EIRP a uloží ho. Preto sa výkon UT nastavuje **pred vytvorením satelitného zariadenia** cez `SatUtPhy::TxMaxPowerDbw`; neskoršie volanie settera by zmenilo zobrazovaný atribút, nie výkon v kanáli. ISL rýchlosti a `DropTailQueue` sa naopak menia na existujúcich zariadeniach o 12,5 s, teda po potvrdení handover sondy. Tým citlivosť dátového smeru neskracuje riadiace TBTP rámce počas attach. Obe smerové fronty zdieľajú kapacitu aj s inou SNS-3 prevádzkou; raw `OTHER` stopy sa neinterpretujú ako konkrétny operátorský protokol.

| Parameter v U4 JSON | Pôvod a použitý mechanizmus | Status čísel |
| --- | --- | --- |
| `u3_case_id`, U3 matica a hash | U3 preflight, pôvod OMM/GP, CAM/RSU párovaný baseline | A pre pôvod a vykonanie; D pre proxy gateway/terminál |
| `beam_gain_dbi` | Generovaná všesmerová SNS-3 mapa s deklarovanou hodnotou v každom bode | D, syntetická anténa |
| `ut_power_dbw` | `SatUtPhy::TxMaxPowerDbw` pred `SatPhy::Initialize`; SNS-3 referenčne 4 dBW | A pre aplikovanie a Rx stopu; D pre terminál |
| `sns3_reference` frekvencie a Rx teploty | `SimulationHelper::ConfigureFrequencyBands`/`ConfigureLinkBudget`; nastavené po konštrukcii helpera | D, generické DVB bez operátorskej kalibrácie |
| `sns3_reference` ACM, ARQ, MODCOD, control slot a `SatQueue` | `SimulationHelper::SetDefaultValues`, SatLlc, SatBbFrameConf a SatWaveformConf | A pre použitie atribútu; D pre profil služby |
| `forward_isl_bps`, `reverse_isl_bps`, obe `*_queue_packets` | Živé `PointToPointIslNetDevice` a `DropTailQueue` na každej orientovanej hrane; pôvodný SNS-3 model 1 Gbit/s/100 paketov | A pre raw dequeue/drop; D pre optický ISL operátora |
| `apply_us`, `burst_release_us`, `burst` | Experimentálne oddelenie riadenia od dát a skutočná aplikačná dávka ICB1 | D, syntetická záťaž |

## Dôkazové brány

Checker nezávisle rekonštruuje U3 orbitálnu geometriu a TLE, pozície UT/GW, ISL hrany aj diagnostický anténový zisk. Páruje CAM→ICB1→GRA1→I2V1 podľa ID, rodiča, bajtov a PCAP. Pri každom natívnom ISL hop-e porovná čas `dequeue→receive` s `d/c + L·8/R` zo SGP4 vzdialenosti a skutočnej rýchlosti v danom čase. Pre prijaté reporty tiež kontroluje dolnú svetelnú medzu celej trasy a voľnopriestorový útlm návratového používateľského pásma. Na skutočných `DropTailQueue` stopách vyžaduje buď `Enqueue→Dequeue`, alebo `DropBeforeEnqueue`; ID stratených ICB1 a GRA1 musia zodpovedať explicitným dôvodom v `events.csv`. Citlivosť zisku aj výkonu sa overuje na raw Rx power stope v dB a na paketovom výsledku. Manifest pinne konfiguráciu, zdroj, runner, checker, generátor, binárku, U3 vstupný kontrakt, základný ground manifest a všetky raw súbory.

## Rozsah a otvorené hranice

Jeden U4 JSON vyberá kvalifikovaný U3 scenár; počet vozidiel/RSU a satelitov pochádza z jeho vstupov, nie z natvrdo vloženej 3/1/3 slučky v motore. Tento overovací balík používa 3 autá, 1 RSU, 3 satelity a stromové ISL `0–1,0–2`; iný U3 scenár možno zvoliť v JSON a musí prejsť tým istým preflightom. Smerovanie ISL v U4 vyžaduje hrany smerujúce podľa počtu hopov k feederu; bočné hrany v rovnakej hĺbke sa v tomto kontrakte odmietnu. Jedno UT a jeden feeder/GW sú súčasná hranica U3/U4 satelitnej vetvy. Šesť prípadov je citlivostná diagnostika, nie kalibrácia ani pravdepodobnosť služby reálneho operátora. Výstup U4 stále nie je servisný adaptér U5 ani zjednotená vedecká analýza U6.

## Prijímací výsledok 27. 10. 2026

Úplný natívny beh: `results/u4_parametric_full_20261027/` (manifest SHA-256 `7c5649ee122fb6657acd01f70d5e95eb85902a7e9ba9fe84f9b01f8f964351fa`). Šesť prípadov prešlo `check_u4_parametric.py` s overením všetkých raw hashov; regresný `check_u3_dynamic.py results/u3_dynamic_full_20261027final` tiež prešiel. `test_u4_parametric_mutation.py` zamietol päť významových zmien (rodič reportu, natívne queue ID, čas dequeue, dôvod návratovej straty, fyzikálny Rx výkon) aj štyri neplatné scenárové vstupy. Diagnostické pilotné adresáre nie sú prijímací dôkaz.

| Prípad | ICB1 vytvorené / vyslané | Gateway / návrat autu | Handover pending | Natívny ICB1 / GRA1 ISL drop | Iné rádiové straty |
| --- | ---: | ---: | ---: | ---: | ---: |
| Referencia | 35 / 24 | 24 / 24 | 11 | 0 / 0 | 0 |
| Zisk lúča 7 dBi | 35 / 13 | 0 / 0 | 22 | 0 / 0 | 13 |
| UT výkon −50 dBW | 35 / 17 | 12 / 12 | 18 | 0 / 0 | 5 |
| Dávka, rýchly ISL | 35 / 24 | 12 / 12 | 11 | 12 / 0 | 0 |
| Dopredný ISL 10 kbit/s | 35 / 24 | 1 / 1 | 11 | 23 / 0 | 0 |
| Spätný ISL 10 kbit/s | 35 / 24 | 24 / 0 | 11 | 0 / 24 | 0 |

V referencii checker vyhodnotil 70 fyzických ISL hopov; ukážkový `dequeue→receive` čas 13 458 µs sa zhoduje s orbitálnym `d/c + L·8/R`. Analytický FSPL návratového používateľského pásma pri 10 s je 184,912 dB. Zisková citlivosť znižuje raw prijatý výkon približne o 10 dB a výkonová citlivosť približne o 54 dB, v súlade s deklarovanými zmenami. Počty nižšieho výkonu sú ovplyvnené aj dlhším potvrdením handoveru; `pending` je preto uvedený samostatne, aby sa nezamieňal s čisto rádiovou stratou dát.
