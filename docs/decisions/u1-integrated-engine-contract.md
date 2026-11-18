# U1: jedna časová os pre CAM/DCC a generický DVB backhaul

**Stav:** implementované a paketovo kontrolované 26. 10. 2026. **Rozsah:** prvý vertikálny rez, jeden aktívny RSU a jeden pevný UT. C++ engine je [`src/u1-integrated-cam-leo.cc`](../../src/u1-integrated-cam-leo.cc), spúšťač [`tools/run_u1_integrated.py`](../../tools/run_u1_integrated.py), nezávislá kontrola [`tools/check_u1_integrated.py`](../../tools/check_u1_integrated.py).

## Vykonaná cesta

SUMO vytvorí polohu všetkých vozidiel každých 100 ms. Všetky autá sú v **tom istom procese ns-3.38** ako aktívne OCB uzly; Vanetza vytvorí ETSI CAM podmnožinu a GN/BTP obal. Každé auto používa V5 pohybový/periodický trigger a voliteľnú výskumnú DCC politiku z meranej obsadenosti PHY za poslednú sekundu. RSU vytvorí ICB1 **iba z CAM, ktorý naozaj dekódovalo**. Report sa odošle cez lokálny UDP hop na UT, generickú SNS-3 DVB cestu cez dva orbitálne objekty a diagnostické ISL na proxy bránu. Brána overí prijatý report a pošle GRA1; RSU vyšle I2V1 adresne do pôvodného auta. Spätné OCB rámce zaberajú kanál a môžu zmeniť merané CBR a ďalšie rozhodnutia DCC.

Identita CAM je 64-bitový SHA-256 prefix podľa U0 nad `(scenario_id, run_id, station_id, sequence, time_us, generationDeltaTime)`. RSU report má vlastné ID s parent CAM ID a RSU station ID; odpoveď má vlastné ID s parent report ID a príjemcom. `generationDeltaTime` sa nikdy nepoužíva osamote ako primárny kľúč. Raw `identity.csv` vytvára auditovateľnú mapu medzi pôvodným CAM a reportom/odpoveďou; `trace.csv` nesie skutočné bajty a časy na každom kroku. ICB1 má 96 alebo 98 B podľa 41/43 B CAM, pôvodný SHA-256 CAM a čas vytvorenia RSU. GRA1 obsahuje hash ICB1; I2V1 obsahuje pôvodné station ID a rovnaký hash.

Predchádzajúci V5 a V8 zdroj ostávajú nezmenené ako izolované referencie. Nový spúšťač používa overený V5 baseline a jeho identické SUMO/FCD/waypoint vstupy. Pripne orbitálny snapshot, EOP, anténne mapy, runtime commity, zdrojový kód, spúšťač, checker, binárku a raw artefakty. Checker znovu overí V5 baseline, samostatne audituje integrované CAM/DCC/CBR, OCB PCAP a byte lineage. Sám prepočíta všetky ID, ICB1/hash, príjemcu I2V1 a časové poradie. Porucha `blocked` zastaví ponuku na satelite; `no_isl` odstráni cestu medzi LEO objektmi. Lokálne CAM zostávajú aktívne.

## Hranice a ďalšia etapa

U1 má iba jeden aktívny RSU, jeden pevný UT a dve pripnuté orbitálne polohy/UTC. Nedefinuje politiku výberu medzi RSU ani frontovanie pri záťaži (U2), dynamický beam/attach/handover (U3), parametrickú RF/kapacitu (U4) alebo operátorský protokol. DCC je **research_cam_dcc_subset**, nie plná normová konformita. Dopravné dopyty sú syntetické; generický DVB, diagnostické antény, proxy brána a ISL nepredstavujú meranie Starlinku ani Iridia. Lokálne PDR v tejto LOS pilotnej geometrii je 1,0; nevyvodzuje sa z neho všeobecná spoľahlivosť mestského ITS-G5.

Pri `positive + dense_los_dcc` sa CAM ponuka zámerne nevyrovná izolovanému V5: skutočný návrat I2V1 obsadí kanál, zvýši CBR a DCC rozhodne o menšom počte CAM. Ekvivalentný izolovanému V5 je `blocked` alebo `no_isl` bez návratových OCB rámcov. Checker tento rozdiel vyžaduje a vysvetľuje; nefalšuje vstup RSU predvypočítaným PDR.
