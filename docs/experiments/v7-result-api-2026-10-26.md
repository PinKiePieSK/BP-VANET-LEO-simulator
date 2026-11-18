# V7 — per-event výsledok, neistota a audit

**Vstupy:** zmrazený P5 natívny ns-3.38/SNS-3 3.38 raw beh a V6 servisný replay. **Výstup:** [`results/v7_result_api_20261026`](../../results/v7_result_api_20261026) s 966 per-event záznamami, 29 vetvami a jedným grafom s 12 auditovateľnými bodmi. Výsledky operátorov sú `sensitivity`; generický natívny model je `model_only`. Externá kalibrácia/validácia zostáva `null`. Rozhranie a metodika sú v [kontrakte V7](../decisions/v7-result-and-measurement-contract.md).

## Reprodukcia

V koreni aktívneho projektu, s projektovou `.venv`:

```bash
.venv/bin/python tools/analyze_v7_results.py --output results/v7_result_api_NEW_ID
.venv/bin/python tools/check_v7_results.py results/v7_result_api_NEW_ID
.venv/bin/python tools/test_v7_mutation.py
.venv/bin/python tools/test_v7_measurement_gate.py
```

Runner odmieta prepísať existujúci priečinok. Výsledný `manifest.json` obsahuje SHA-256 protokolu, zdrojových manifestov, overení, V6 kontraktu, analyzéra a štyroch produktov. Produktmi sú `events.jsonl`, `results.json`, `figure-data.csv` a `v7_service_sensitivity.png`.

## Dôkaz a interpretácia

- P5: **864** per-event natívnych záznamov; 4 skupiny × 3 vetvy × 12 seed/UTC jednotiek × 6 správ. V každej skupine S1 doručila 72/72, S0 a S2 0/72; dôvod S0 je explicitná experimentálna brána, S2 absencia modelovej ISL. Všetky tri vetvy majú CAM→RSU a `UT_LAN_REPORT_RX` raw riadok; výpadok satelitnej cesty sa nesmie prezentovať ako strata lokálneho CAM.
- V6: **102** servisných záznamov; 17 vetiev × 6 rovnakých natívnych aplikačných ID. Napríklad Iridium vysoká citlivosť má 3/6 vzdialených a 3/6 spätných prijatí; Globalstar `mt_unavailable` má 6/6 vzdialených a 0/6 spätných; Starlink vysoká citlivosť 5/6 a 2/6. Ide výhradne o vybrané modelové stavy.
- V6 identifikovateľnosť pri **predpokladanej dostupnej službe**, len z troch testovaných nastavení: Iridium 0,5–1; Globalstar 1–1; Starlink 0,8333–1. Pri neznámej dostupnosti je pre všetky tri služby poctivý bezpodmienečný rozsah **0–1**. Žiadna z uvedených frakcií nie je prevádzkový odhad.
- P5 95 % seed-klastrový bootstrap je označený `model_only`; dva časy vzdialené 92 s zostávajú v každom klastri spolu. V6 nemá replikačný interval. P95/P99 sú vo všetkých vetvách `null` s dôvodom nedostatku nezávislých chvostových jednotiek.

![Modelová citlivosť V7](../../results/v7_result_api_20261026/v7_service_sensitivity.png)

Každý stĺpec má riadok vo `figure-data.csv` s ID metriky a presnými event kľúčmi. Metrika obsahuje čitateľ, menovateľ a raw väzby v `events.jsonl`; bod je teda spätne kontrolovateľný až k pôvodnému paketu a konfigurácii.

## Kontroly

- **PASS:** read-only checker: 966/966 udalostí, 29/29 prípadov, 12/12 bodov grafu. Zhoduje raw CSV číslo riadku, čas, hash payloadu, menovateľ, deadline, dôvod vrstvy a produktové hashe. V6/P4 upstream geometria a payload audit opäť prešli. Všetky produkty boli znova vygenerované bajtovo rovnako.
- **6/6 odmietnutých mutácií aj po prepísaní manifestového hashu:** čas raw eventu, nesprávna frakcia, vymyslené p99, neoprávnený `externally_validated`, falošný bod grafu a zmenený PNG.
- **5/5 odmietnutých chýb meracej vstupnej brány:** nesprávny payload, iný koncový bod, duplicita, jediný deň bez held-out skupiny a zlý hash dôkazového logu. Kladný test používa výlučne syntetickú dočasnú CSV; výsledok zostáva `candidate_external_dataset_only`, nie operátorská validácia.

Strojovo čitateľné výsledky kontrol sú uložené ako [`verification.json`](../../results/v7_result_api_20261026/verification.json), [`mutation-verification.json`](../../results/v7_result_api_20261026/mutation-verification.json) a [`measurement-gate-verification.json`](../../results/v7_result_api_20261026/measurement-gate-verification.json). Autoritatívny výsledkový manifest pripína vstupy a štyri analyzované produkty; tieto dodatočné kontrolné výstupy sa dajú kedykoľvek znovu vytvoriť uvedenými príkazmi.

**Zostávajúca hranica:** nové skutočne vzdialené UTC dni, lokality a nezávislé prevádzkové merania musia pribudnúť pred kalibráciou, held-out chybou, percentilmi alebo tvrdením o dostupnosti. V5 dynamické CAM/rádio stále nie je paketovo spojené s touto P5/V6 satelitnou aplikáciou; API tento rozdiel nezakrýva. Nasleduje V8 odovzdanie univerzálnej platformy.
