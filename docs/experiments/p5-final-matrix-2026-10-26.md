# P5 — konečná párovaná experimentálna matica, 26. 10. 2026

## Výskumná otázka a zafixovaný protokol

Primárna informácia je 96 B ICB1 vytvorený RSU z dekódovaného primárneho CAM. Primárna metrika je počet **unikátnych** ICB1 prijatých vzdialenou aplikáciou do 60 s od vytvorenia RSU, delený počtom ICB1 vytvorených RSU. Lokálna metrika používa páry primárny CAM–oprávnené auto; sekundárne sledujeme spätnú GRA1/I2V1 reakciu a delay len pri včas doručených správach. Deadline je výskumný prah z P0, nie záruka služby.

Pilot variability má samostatné výsledky `results/p5_native_variability_pilot_20261026` a `results/p5_service_variability_pilot_20261026`, po dvoch seedoch a dvoch UTC epochách. Vysokostratový profil Iridium sa medzi párovanými jednotkami menil od 4/6 po 6/6. Podľa vopred zapísaného pravidla v `config/p5_variability_pilot.json` preto vznikol **pred spustením finálneho behu** protokol `config/p5_final_matrix.json`: šesť nových seedov 314171–314176 a dva UTC začiatky 22. 10. 2026 12:45:00 a 12:46:32. Spolu je to 12 párovaných jednotiek. Časy sú od seba iba 92 s, preto nepredstavujú denné ani sezónne pokrytie. Ďalšie testované časy generického DVB zdroja padali na modelových aserciách, a preto sa nepoužili na tvrdenia o fyzickej nedostupnosti služby.

Každá jednotka má štyri skupiny: riedka/hustá doprava × nízka/vysoká CAM záťaž. Natívny ns-3.38/SNS-3 3.38 beh má v každej skupine tri párované vetvy: S0 blokovaná satelitná cesta, S1 generický DVB model s modelovou SAT0–SAT1 ISL, S2 rovnaký model bez ISL. Lokálne rádio beží vo všetkých troch vetvách. Pozemná WAN referencia a Iridium, Globalstar, Starlink sa prehrávajú na **servisnej hranici** z tých istých RSU vytvorených ICB1 bajtov/časov. Každý profil má základ, blokáciu a dve hodnoty citlivosti; Globalstar používa natívnu MO/MT správu bez IP a bez ISL. Geometria je vypočítaná z archivovaných OMM pre okamih každého reportu a modelové proxy brány; kandidát ani publikovaný limit nepreukazuje aktívny lúč, attach, prevádzkovú bránu alebo trasu.

## Reprodukcia

Príkazy spúšťať v koreni `obnova/Bakalarska praca/`. Natívny runner potrebuje výstup bez medzier v `/tmp`, lebo pôvodný C++ parser cesty s medzerou skracuje. Pre ďalší pokus zvoľte nové jedinečné ID; žiadny runner neprepisuje existujúci výsledok.

V aktuálnom `.venv` prešla kontrola `pip check`; balíky pre grafy sú pripnuté v `requirements-p5-analysis.txt` (vrátane NumPy 1.26.4 kompatibilného s orbitálnym stackom). Pri novej obnove ich pred vykreslením doinštalujte pomocou `.venv/bin/python -m pip install -r requirements-p5-analysis.txt`.

```bash
.venv/bin/python tools/run_p5_native_matrix.py config/p5_final_matrix.json vendor/ns-3.38-ocb-eval /tmp/p5_native_NEW_ID --workers 4
cp -a /tmp/p5_native_NEW_ID results/p5_native_NEW_ID
.venv/bin/python tools/check_p5_native_matrix.py results/p5_native_NEW_ID
.venv/bin/python tools/run_p5_service_matrix.py results/p5_native_NEW_ID results/p5_service_NEW_ID
.venv/bin/python tools/check_p5_service_matrix.py results/p5_service_NEW_ID
.venv/bin/python tools/analyze_p5_matrix.py results/p5_native_NEW_ID results/p5_service_NEW_ID results/p5_analysis_NEW_ID
.venv/bin/python tools/check_p5_analysis.py results/p5_native_NEW_ID results/p5_service_NEW_ID results/p5_analysis_NEW_ID
.venv/bin/python tools/check_p5_feedback_pairing.py results/p5_feedback_diagnostic_20261026
```

Analýza tvorí `summary.csv`, `local.csv`, dva PNG a dva PDF grafy. V každom grafe je menovateľ, počet seedov/epoch, 95 % percentilový bootstrap po **seed klastroch** (oba časy spolu) a označenie modelovej vernosti; CSV nesie aj min/max cez 12 jednotiek. Ide o interval neistoty nakonfigurovaného modelu. Šesť reportov v jednom behu neoprávňuje p99. P3 handover jedného UT zostáva osobitný jednoseedový doplnkový dôkaz bez intervalu a bez tvrdenia o operátorskom handoveri. Finálny výstup je `results/p5_analysis_final_20261026`; skorší grafický návrh je zachovaný v `results/p5_analysis_graph_v1_20261026`, pretože jeho krivky sa pri 100 % prekrývali.

## Výsledok a audit

**PASS:** natívny checker znovu prešiel nad projektovou kópiou `results/p5_native_final_20261026`: 12 párovaných jednotiek, 144 ns-3.38/SNS-3 behov a 864 udalostných riadkov. V každej zo štyroch skupín vzniklo 72/72 ICB1 vo vetve S1 a rovnaký počet vo vetvách S0/S2. S1 doručila včas 72/72 na GW a 72/72 odpovedí do auta v každej skupine; S0/S2 doručili 0/72 na GW. Lokálna vetva ostala aktívna: pri jednom z troch variantov 216/216 párov CAM–auto v každej riedkej skupine a 504/504 v každej hustej skupine. V testovanom rozsahu dodatočná CAM záťaž nespôsobila straty; nemožno z toho vyvodiť kapacitnú rezervu mimo tejto záťaže.

Párovanie drží **rovnaký ponúknutý CAM a vstupy**; ďalšie udalosti môžu reagovať na zvolenú vetvu. V 288 primárnych udalostiach mali S0 a S2 presne zhodné RSU ICB1 bajty/časy. S1 sa pri 234/288 líšila v RSU čase najviac o 9 μs, pretože jej obojsmerná odpoveď používa OCB kanál pred ďalším CAM. Diagnostický beh S1 so zakázanou spätnou odpoveďou dosiahol rovnakých 6/6 RSU ICB1 bajtov/časov ako S0. Skúšobné pripnutie OCB RNG streamov rozdiel neodstránilo; bolo vrátené bez zmeny finálneho zdroja. Ide o kauzálny účinok deklarovanej obojsmernej vetvy, nie o inú zdrojovú správu. Raw diagnostika, zhodne zostavená z finálneho zdroja, a nezávislý checker sú v `results/p5_feedback_diagnostic_20261026` a `tools/check_p5_feedback_pairing.py`. Servisné profily sú všetky prehrané z **toho istého S0 RSU ICB1** v každej jednotke, takže ich aplikačné bajty/časy sú medzi profilmi párované presne. Tento diagnostický beh je mimo preregistrovaných finálnych odhadov.

**PASS:** servisný checker zopakoval orbitálnu geometriu, bajty ICB1, GRA1 a IP/UDP kontrolné súčty aj časovanie pre `results/p5_service_final_20261026`: 12 jednotiek × 4 skupiny × 13 servisných variantov × 6 reportov = **3 744** riadkov. Každý profil mal 288/288 geometrických kandidátov v dvoch úzko blízkych UTC epochách pri experimente s 10° maskou; Iridium potrebuje kandidáta iba pri UT, Globalstar a Starlink toho istého kandidáta pri UT aj mestskej proxy brány. Takmer nepretržitá dostupnosť z týchto vzoriek sa **netvrdí**.

V každej skupine je menovateľ 72 unikátnych RSU reportov. Pozemná hypotetická WAN a základ každého zo všetkých troch servisných obalov doručili 72/72; explicitne blokované varianty 0/72. Vysoký citlivostný variant zmenil včasné doručenie takto (v zátvorke 95 % seed-klastrový bootstrap frakcie):

| Doprava / lokálna CAM záťaž | Iridium vysoký zásah | Globalstar vysoký zásah | Starlink vysoký zásah |
| --- | ---: | ---: | ---: |
| Riedka / nízka | 64/72 (0,819–0,944) | 72/72 (1–1) | 66/72 (0,875–0,958) |
| Riedka / vysoká | 65/72 (0,847–0,958) | 72/72 (1–1) | 58/72 (0,736–0,861) |
| Hustá / nízka | 63/72 (0,847–0,903) | 72/72 (1–1) | 65/72 (0,847–0,972) |
| Hustá / vysoká | 67/72 (0,847–0,986) | 72/72 (1–1) | 65/72 (0,833–0,972) |

Pre riedku/nízku skupinu je **priemer iba z včas doručených**: pozemná kontrola 10,1 ms; generický DVB S1 122,2 ms; základ Iridium 301,1 ms, Globalstar 1 017,1 ms, Starlink 33,3 ms. Pri vysokom citlivostnom zásahu má Iridium 846,2 ms, Globalstar 5 433,8 ms a Starlink 103,4 ms. Sú to následky zvolených servisných predpokladov, nie merania operátorov; porovnanie absolútnych hodnôt medzi profilmi preto nie je dôkazom poradia služieb. Kompletné počty, delay, intervaly a min/max jednotiek sú v `results/p5_analysis_final_20261026/summary.csv` a `local.csv`.

**PASS:** analytický checker znovu vygeneroval z raw odvodených metrík všetkých 64 transportných a 4 lokálne súhrny, oba PNG a oba PDF grafy s bajtovo rovnakým hashom. Pred finálnym uzavretím prešlo 69 Python testov a `pip check`. Tri korupčné skúšky v dočasných kópiách zmenili natívny ICB1, servisný vzdialený ICB1 a PNG graf, pričom bol prepísaný aj zodpovedajúci manifestový hash; každý príslušný checker zmenu odmietol. Žiadna produkčná stopa sa pri skúške nemenila.

| Autoritatívny súbor | SHA-256 |
| --- | --- |
| Natívny `run-manifest.json` | `702f645c9e4a04b1cf26f8c99545fa6411dbd60d4792c7a403d8b37bdb24be65` |
| Natívny `verification.json` | `2725be07c3b16e5f2ddc5dc36a3f3b2f6c6c664cfe4800ccceebaca76f28c612` |
| Servisný `run-manifest.json` | `449a16eb3cb2e6e88fdb3510f040395138c986838a6b129e4c84aaf89ba63746` |
| Servisný `verification.json` | `2957fe5b05a6a5d246b1aff24638860ee61b0a528d312ff250d44a9e5303d90b` |
| Analytický `manifest.json` | `33b8100e95d3eb2578762e96824db13bdf5fc503cddd1c0603865fd45b75607d` |
| Analytický `verification.json` | `fe76924eb379c89886a86f40386bae551bc4730211fa74fd1210a94269026de3` |
| Diagnostický `manifest.json` | `eca623944973c3da323193602cbc139faec413012bd30e382d3e78030ae1624c` |
| Diagnostický `verification.json` | `1699a54b368d17ead3a3f0c02e05456ee2bb5f84c842b8782dbdd39ac1af59f4` |

## Hranica tvrdenia

Hustota a zaťaženie sú výskumné SUMO/OSM scenáre, nie kalibrovaný bratislavský dopyt. Mestské rádio a generický DVB/ISL používajú výskumné parametre. Servisné obaly používajú hypotetické straty/oneskorenia a proxy gateway; archivované OMM bolo získané retrospektívne. Chýba porovnateľné externé raw meranie presného terminálu, plánu, geografického času a koncových bodov, aj oddelená nezávislá validácia. Výsledky preto nemožno zoradiť ako skutočný výkon Starlinku, Iridia a Globalstaru. Kalibrácia a nezávislá validačná sada v manifeste zostávajú `null`.
