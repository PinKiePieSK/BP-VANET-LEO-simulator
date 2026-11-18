# U2: dva aktívne RSU, deduplikácia a smerové fronty

**Rozsah:** jeden proces ns-3.38/SNS-3 3.38, jedna mobilita SUMO/FCD, jedno OCB rádio pre každého účastníka. Engine: [`src/u2-multi-rsu-backhaul.cc`](../../src/u2-multi-rsu-backhaul.cc). Prísny spúšťač: [`tools/run_u2_integrated.py`](../../tools/run_u2_integrated.py). Raw checker: [`tools/check_u2_integrated.py`](../../tools/check_u2_integrated.py).

## Pravidlá, ktoré kód skutočne vykonáva

Každé aktívne RSU dekóduje CAM nezávisle. Politika `first_actual_decode` vyberie prvé **skutočné** dekódovanie danej dvojice `(station_id, generationDeltaTime)`; ďalší prijímací callback je `duplicate_after_first_decode`. Vstup sa neposudzuje podľa predvypočítaného dosahu ani podľa poradia v scenári. `selection.csv` zapisuje každý RSU príjem, výber, duplicitu, čas a vzdialenosť. Vybraný RSU vytvorí jedno ICB1 s vlastným U0 report ID; `identity.csv` zachová parent CAM ID. Checker nezávisle znovu prejde poradie `rx.csv`, preto nemôže zameniť 512 príjmov dvoch RSU za 512 originálnych CAM.

Podporované sú **jeden alebo dva aktívne RSU**, obe viazané na **ten istý pevný UT0**. Každé RSU má vlastný 100 Mbps/100 µs bodový IP spoj do UT; pri návrate ide GRA1 cez linku vybraného RSU a I2V1 vysiela toto RSU adresne pôvodnému autu. `rsu_by_report` vo vykonanom kóde určuje oba smery. Toto nie je dvojica nezávislých UT ani handover terminálu.

Pred sieťovou ponukou je ohraničený FIFO `forward` s kapacitou v **reportoch** a časom obsluhy v µs. Až `dequeue` vytvára `LOCAL_REPORT_OFFER` alebo skutočný RSU UDP paket; `queue_full` je samostatný výsledok pôvodne vytvoreného ICB1. Po prijatí GRA1 na RSU funguje nezávislý ohraničený FIFO `reverse`, ktorý až pri obsluhe vyšle I2V1 na OCB. `queue.csv` obsahuje všetky `enqueue/dequeue/drop`, obsadenosť, kapacitu a dôvod. Checker znovu vykoná FIFO aj plán servisných časov a uzavrie identity `created = offered + forward_queue_drop`, resp. `response_arrived = I2V_offered + reverse_queue_drop`. Predvolená kapacita 512 a obsluha 1 ms nie sú kalibrovanou frontou terminálu; preťaženie 2 pozície/500 ms je kontrolovaný mechanizmus.

Tri párované vetvy používajú rovnaké CAM ID, SUMO polohy, aplikačný ICB1/GRA1/I2V1 formát, RSU politiku a logický endpoint:

| Režim | Skutočná cesta reportu |
| --- | --- |
| `local` | Obsluha v aplikácii na RSU, bez IP spätného spoja. |
| `ground` | RSU→UT po vlastnom IP spoji, UT→vzdialená aplikácia cez samostatný 100 Mbps/100 µs bodový IP spoj, potom rovnaká spiatočná cesta. |
| `satellite` | RSU→UT po tom istom IP spoji, UT→generický SNS-3 DVB→diagnostická ISL→proxy GW aplikácia, späť GRA1 cez kvalifikovanú trasu. |

Negatívne vetvy samostatne blokujú satelitnú ponuku, odstránia ISL, vypnú návratovú trasu alebo preťažia dopredný/návratový FIFO. `no_isl` nie je `no_return_route`: prvý nedoručí ICB1 bráne, druhý môže doručiť ICB1, ale nevytvorí GRA1. Čitatele a menovatele sú oddelené: CAM TX, RSU prijímacie páry, jedinečné dekódované CAM, deduplikované príjmy, vytvorené reporty, obslúžené/zahodené reporty, vzdialené prijatia, vytvorené odpovede, obslúžené/zahodené návraty a príjem v aute.

`no_return_route` je explicitná kontrolná brána pri aplikácii a zároveň nenasadí diagnostickú spätnú SNS-3 trasu; nepreukazuje mechanizmus reálneho routovacieho protokolu. Historický súhrnný názov `SAT_OFFERED` v U2 `run.log` znamená ponuku na vybranú vzdialenú cestu po UT; pri režime `ground` je to pozemný IP bypass. Rozhodujúca raw stopa má odlišné fázy `UT_GROUND_REPORT_TX` a `UT_SAT_REPORT_TX`, ktoré checker nezamieňa.

**Hranica modelu:** výber podľa prvého príjmu nie je optimalizácia pokrytia; oba RSU používajú spoločné rádio a jeden pevný UT. FIFO modeluje aplikáciu pred/po IP linke, nie proprietárny scheduler DVB alebo RF kapacitu. Dynamická LEO dostupnosť patrí do U3 a fyzikálne kapacity do U4. Syntetické vozidlá, LOS a generický DVB nemajú operátorskú kalibráciu.
