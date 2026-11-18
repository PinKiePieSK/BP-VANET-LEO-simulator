# Smerový LEO lúč: kontrolovaný referenčný DVB pokus

**Stav:** reprodukovateľný neúspešný experiment, 22. 10. 2026. **Nie je to Globalstar, Starlink ani Iridium služba.** Cieľom je nahradiť zjavne nevhodnú [GEO anténnu mapu v predchádzajúcej sonde](sns3-338-leo-candidate-37741-failure.md) smerovou mapou viazanou na skutočnú 3D geometriu LEO a zistiť, či tým prejde referenčný paket pri zapnutom `EM_AVI` na oboch pozemných prijímačoch.

## Hypotéza, kontrola a svetový význam

Hypotéza: ak sa dopredný a návratový zisk satelitného lúča vypočítajú z uhla medzi smerom lúča a pozemným bodom pri LEO polohe, predtým zahadzované riadiace rámce aj 16 B UDP paket prejdú cez SNS-3 DVB UT/SAT/GW. Kontrolný variant je predchádzajúca 72-lúčová mapa s rovnakým GP objektom, UT, proxy GW, časom, modulačnými tabuľkami a seed/run. Porovnanie izoluje **zmenu anténnej mapy spolu so zmenou počtu lúčov**; nie je validačným porovnaním antén operátora. V reálnom systéme sú používateľský a feeder lúč spravidla oddelené antény/pásma. Táto sonda má **jeden široký, spoločný modelový lúč**, preto nie je návrhom produktovej antény.

## Algoritmus, jednotky a zdroje parametrov

Vstupný objekt je archívny OMM/GP záznam číslo 37741, presne hashovo zhodný s [predchádzajúcou sondou](sns3-338-leo-candidate-37741-failure.md). Začiatok je `2026-10-22T12:45:20Z`, paket pri t=1 s. `UT=(48,1480603° N, 17,1035340° E, 0 m)` je hypotetický pevný terminál pri RSU; `GW=(37,8167° N, 22,6667° E, 0 m)` je **centrum mesta Nemea**, nie overená anténa. Samostatne auditovaná geometria dáva pri t=1 s nad 10° eleváciu oboch koncov. Pôvod OMM, TLE a EOP je v manifeste.

GP snímka vznikla po začiatku modelovaného UTC intervalu, preto ide o **retrospektívny** experiment; nejde o predpoveď v reálnom čase ani o dôkaz, že tento katalogizovaný objekt poskytoval službu.

`tools/run_sns3_338_leo_directional_reference.py` vypočíta SGP4/TEME→ITRS polohu satelitu. Pozemné body pre **anténny výpočet** prevedie podľa skutočnej implementácie `GeoCoordinate` v SNS-3 3.38: guľa s polomerom **6 378 137 m**. To nie je WGS84 elipsoid; rozdiel je dokumentovanou hranicou nášho použitia SNS-3. Pri t=1 s je guľová šikmá vzdialenosť oproti WGS84 kratšia o **5,70 km na UT** a **13,41 km na proxy GW**; guľová elevácia je nižšia o **0,217°**, resp. **0,072°**. Oba konce však ostávajú nad experimentálnou 10° maskou. Toto je rozdiel dvoch modelov súradníc, nie empirická chyba predpovede dráhy. Poloha družice sa vyjadrí rovnakou guľovou šírkou, dĺžkou a výškou pre `GeoPos.in`. Z normalizovaných vektorov družica→UT a družica→GW pri začiatku sa vytvorí smer lúča ako normalizovaný súčet. Oba smerové vektory sú oddelené o **25,9473°**. Výber stredu medzi nimi je vopred určený geometrický návrh, nie optimalizácia podľa výsledného doručenia.

Priestorový zisk sa ráta `G_dBi(θ) = G_peak − min[12(θ/β)^2, 25 dB]`, kde `θ` je skutočný 3D odklon od stredu v **stupňoch**, `β=22°` je výskumný full half-power beamwidth a `25 dB` je výskumný limit útlmu postranného smeru. Uhlový parabolický pokles je výslovne **3D adaptáciou** otvoreného [parabolického anténneho modelu ns-3](https://www.nsnam.org/docs/models/html/antenna.html); nie je opisom skutočného payloadu. `G_peak = 10 log10(27000/β²) = 17,4652 dBi` viaže zvolenú šírku na približný vzťah pre kruhovú apertúru a účinnosť okolo 0,65, uvedený v [ITU-R príručke o satelitnej komunikácii, príloha 2.1](https://www.itu.int/dms_pub/itu-r/opb/hdb/R-HDB-42-2002-PDF-E.pdf). Použitie tohto vzťahu pre **hypotetickú** satelitnú anténu je náš modelový predpoklad. Šírka 22°, zisk a 25 dB strop nie sú parametrami Globalstar.

Generátor vytvorí mriežku `32–54° N`, `10–30° E` po `0,25°` so ziskom pre lúč 30 a časovým kotviacim `GeoPos.in`. SNS-3 3.38 pri pohybe mapu **iba posúva** podľa zemepisnej šírky/dĺžky. Preto skript porovná hodnoty z C++ anténneho objektu v t=1 s s nezávislým priamym výpočtom z novej 3D polohy: rozdiel bol **−0,0275 dB pri UT** a **+0,0350 dB pri proxy GW**. Tolerancia testu je 0,5 dB, platí však iba pre toto štvorsekundové okno a tieto body. Neznamená presný pohyb lúča pri dlhom lete, zmene sklonu, handoveri alebo inom regióne. Nezávislý SGP4/ITRS→guľová výška sa v t=1 s líši od SNS-3 výšky o **0,310 m**; to kontroluje konzistenciu dvoch výpočtových ciest, nie orbitálnu pravdu.

## Pozorovanie

Pri zapnutom `EM_AVI` v oboch smeroch sonda namerala modelový satelitný zisk **13,3194 dBi pri UT** a **13,2975 dBi pri proxy GW**. V pôvodnej posunutej GEO mape to bolo **7,5442** a **8,8191 dB**. Dopredný user-link SINR pri t≈1,019 s stúpol z **−0,1299** na **5,5949 dB**. Nový `NS_LOG` má **39 dopredných rozhodnutí bez PHY chyby**; `PacketTrace.log` obsahuje paket ID 9 na `UT PHY RTN`, `SAT PHY/ND RTN` a `SAT PHY RTN`. Spätný user-link SINR pri družici je asi **8,27 dB**, ale na GW sa zaznamenáva `PHY RTN DRP` pre ID 9. Všetky **štyri** zachytené návratové `EM_AVI` rozhodnutia na feeder prijímači vrátane tohto rámca majú v referenčnej tabuľke **BLER=1**; `Eb/N0` približne **0,26–0,29 dB**. GW aplikácia neprijala žiadny paket. Hypotéza o úplnom priechode bola teda **vyvrátená**; smerová mapa odstránila konkrétnu doprednú blokáciu, nie návratovú.

Úspech na FWD a neúspech na GW dokazujú iba správanie uvedenej SNS-3 konfigurácie. Nie sú dôkazom komerčnej dostupnosti ani odhadu PDR/latencie operátora. Nasledujúci model musí oddeliť **user** a **feeder** anténu, ich frekvencie, výkon, citlivosť/šum, boresight a priradenie brány. Žiadny z týchto parametrov sa nesmie zvýšiť len preto, aby paket prešiel. Pre nepublikované parametre bude potrebný interval citlivosti a validácia na oddelených meraniach.

## Technická špecifikácia, vstupy/výstupy a reprodukcia

Skript číta archivovaný OMM a hashovaný predchádzajúci scenár; odmieta zmenené pripnuté Git commity, archív a existujúci odlišný generovaný vstup. Vytvorí jeden antenný súbor a `GeoPos.in` v pracovnom SNS-3 checkoute, zostaví `src/sns3-338-leo-candidate-probe.cc` a spustí ho s `--singleBeam=1`, `--scenarioFolder=bp-leo-directional-reference-37741`, `--patternFolder=BpLeoDirectionalReference37741`. Sonda používa tie isté UDP bajty, seed `314159`, run `1`, štyri simulačné sekundy, sieťovú regeneráciu a pôvodné SNS-3 DVB-S2/RCS2 kanály. Vstupný výstupný adresár musí byť prázdny. Exit procesu `1` je **očakávaný** dôsledok nedoručenia; runner skončí kódom `0` iba pri presne overenej FWD úspešnej a GW PHY neúspešnej ceste.

```bash
.venv/bin/python tools/run_sns3_338_leo_directional_reference.py \
  /tmp/ns3-sns3-338-feasibility /tmp/novy-leo-smerovy-referencny-beh
```

Uložený `results/sns3_338_leo_directional_reference_37741/` obsahuje surový anténny súbor, `GeoPos.in`, štyri scenárové vstupy, `run.log`, celý `PacketTrace.log`, SINR/RX-power, `verification.json` a hashový `manifest.json`. Checker samostatne kontroluje modelový zisk, približnú presnosť posúvania mapy, výšku, rozhodnutia BLER a jednotlivé PHY skoky ID 9. Kód, vzorec, jednotky, seed, zdroj každého rozhodnutia a hranice platnosti sú preto overiteľné. Tento model **ešte neumožňuje** porovnávať tri operátorské konštelácie podľa výkonnosti.
