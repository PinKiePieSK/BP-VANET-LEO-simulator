# U6: spoločné výsledky a výskumný protokol

**Prijímací výstup:** `results/u6_paired_verified_20261027/`, manifest SHA-256 `0cd951ac35c885016f2c9d4e6a3e156c9bc725411c741c1043d1917dee53ae2a`. Výsledok obsahuje 960 párovateľných záznamov v 59 vetvách: U2 local/ground, šesť natívnych generických U4 prípadov a 51 U5 servisných replay vetiev. Kontrakt je v `config/u6-result-protocol.json` a pinne manifesty všetkých troch zdrojov.

## Reprodukcia

```bash
.venv/bin/python tools/analyze_u6_results.py --output results/<novy-adresar>
.venv/bin/python tools/check_u6_results.py results/<novy-adresar>
.venv/bin/python tools/test_u6_results_mutation.py results/<novy-adresar>
```

Runner odmieta prepísať existujúci výstup. Pri vytvorení a kontrole znovu overí pôvodný U2 lokálny a ground paketový beh a úplný U5 replay; jeho checker následne overí úplnú U4 maticu. Prijímacia kontrola `check_u6_results.py` nezávisle prepočíta raw odkazy, menovatele, hodnoty metrík, deadline a párované rozdiely. `events.jsonl` je zoznam CAM udalostí s identitou, pôvodnou ICB1, zvolenou RSU, časmi, príjemcom, počtom pozorovaných aplikačných pokusov, príčinami a referenciami na konkrétne riadky zdrojových CSV. Počet pokusov nepredstavuje počet retransmisií PHY. `results.json` obsahuje strojovo čitateľné prípady, párovanie a neistotu; `metrics.csv` poskytuje rovnaké metriky v tabuľke. Manifest uchováva SHA-256 kódu, protokolu, vstupov a výstupov.

## Párovanie, vrstvy a deadline

Spoločná udalosť je určená identifikátorom stanice, presným časom vzniku CAM a hashom jej bajtov. U2 a U4 majú rovnakú mobilitu, CAM a vybranú RSU, no používajú vlastné interné ID; tieto ID sa neprepisujú. Čas vytvorenia reportu na RSU sa medzi natívnymi vetvami môže líšiť o jednotky mikrosekúnd. Každá vetva preto používa svoj skutočný čas a párovaný výsledok zaznamenáva aj jeho posun voči U2 ground. U5 pochádza z U4 baseline a má navyše presne rovnaké CAM/ICB1 ID, bajty a čas reportu. Výber U5 `n1`, `n4`, `all` sú vnorené podmnožiny reportov, nie ďalšie generované populácie ani nezávislé behy.

Primárny menovateľ je počet unikátnych `RSU_REPORT_CREATED` v danej vetve. Čitateľ `remote_timely` je počet rovnakých ICB1 prijatých vzdialenou aplikáciou najneskôr **60 s od vytvorenia reportu**; oneskorené doručenie má osobitný stav `late` a dôvod `deadline_exceeded`. Výsledok osobitne uvádza vytvorené CAM, reporty, všetky vzdialené príjmy a včasné príjmy, všetky návraty a včasné návraty. Každý podiel má čitateľa a menovateľ; každá priemerná latencia má súčet časov, počet použitých udalostí, ich event keys a pomenovanú populáciu. Pri nulovom počte je priemer `null`.

Latencie sú oddelené na CAM→RSU, prístupový TX→vzdialená aplikácia a vzdialená aplikácia→návrat, plus celkový čas CAM→aplikácia a RSU→aplikácia. Priemery vzdialeného príjmu sú podmienené včas doručenými správami a priemer návratu iba včasnými návratmi; straty sa do priemeru nevkladajú ako nulové časy. V local/ground/U4 je návratový endpoint **auto** `CAR_I2V1_RX`; v U5 je endpoint **RSU** `RSU_RECEIPT_RX`. Podiely návratu preto netvrdia totožnú koncovú službu. V U2 local je `GATEWAY_ACCEPT` lokálna modelová aplikácia, nie fyzická satelitná gateway.

Párovaný rozdiel latencie oproti U2 ground sa počíta iba pre konkrétne CAM, ktoré vzdialená aplikácia včas prijala v oboch vetvách. Výstup uvádza ich počet a obe event keys; rozdiel nie je neobmedzený priemer aj za stratené pakety. U4 mení aj konkrétne nastavenie fyziky či dávky a U5 je servisný replay od RSU, preto samotný rozdiel nie je empirickým účinkom reálneho operátora.

## Štatistický význam

Všetky použité vetvy vychádzajú z **jednej párovanej pozemnej realizácie** so spoločným seedom, časom a miestom. Správy, U4 citlivostné scenáre a U5 vnorené dávky nie sú nezávislé replikácie. Preto je interval spoľahlivosti `null`; p95 aj p99 sú `null` s dôvodom nedostatku nezávislých jednotiek. Protokol pre budúcu analýzu preberá konzervatívne minimá V7: 100 nezávislých jednotiek beh–deň–miesto pre p95 a 1 000 pre p99 spolu s pozorovanými chvostovými udalosťami; splnenie počtu samo osebe negarantuje reprezentatívny odhad.

U5 `base/sensitivity_low/sensitivity_high` dáva iba min–max **z týchto troch predpokladaných dostupných stavov**. Vzhľadom na neznámu dostupnosť je všeobecný rozsah 0–1; nejde o interval spoľahlivosti ani pravdepodobnosť výpadku. Kalibrácia a externá validácia zostávajú `null`. Budúce terénne meranie musí zachovať konkrétny payload, UTC deň, miesto, zariadenie, anténu, plán a endpoint a deliť kalibračné a overovacie údaje po nezávislých skupinách, ako uvádza [kontrakt V7](../decisions/v7-result-and-measurement-contract.md).

## Výsledok prijímacej matice

Počty sú `včas vzdialene / včas späť` z 35 vytvorených reportov; priemer je RSU→vzdialená aplikácia v ms, podmienený včasným príjmom.

| Vetva | Vzdialene / návrat | Návratový endpoint | Priemer včas prijatých |
| --- | ---: | --- | ---: |
| U2 local | 35 / 35 | auto | 1,001 ms |
| U2 ground | 35 / 35 | auto | 1,221 ms |
| U4 baseline | 24 / 24 | auto | 130,050 ms |
| U4 preťažený dopredný ISL | 1 / 1 | auto | 3 172,856 ms |
| U4 preťažený spätný ISL | 24 / 0 | auto | 2 457,937 ms |
| U5 Iridium base | 35 / 35 | RSU | 320,910 ms |
| U5 Globalstar MT nedostupné | 35 / 0 | RSU | 1 000,000 ms |

U4 `baseline` má 11 explicitných `handover_pending` strát po vytvorení reportu. U5 tieto reporty vyhodnocuje ako alternatívnu vetvu od RSU, preto môže mať 35 vzdialených prijatí. Preťažené U4 prípady zahŕňajú aj modelovú dávku reportov; ich priemery nie sú čistým meraním jedinej zmenenej veličiny.

Prijímacie kontroly: U2 úplná historická matica PASS, U6 checker PASS (960 udalostí, 59 vetiev, 1 jednotka), sedem sémantických mutácií ID/bajtov/času/príčiny/menovateľa/analýzy/CSV a mutácia pôvodu analyzéra zamietnuté. Samostatná skúška s deadline 1 µs potvrdila stav `deadline_exceeded`, nulový počet včasných prijatí a `null` priemer bez úspechov. Pôvodné U2/U4/U5 raw súbory sa neupravujú.
