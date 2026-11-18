# V8 — vykonávací a odovzdávací kontrakt

## Jedna vykonávacia cesta

`tools/bp_v8.py` je jediný vstup pre nový scenár schémy v3: `catalog`, `configure`, `validate`, `run`, `verify`, `analyze`, `verify-analysis`. `configure` vytvára nový súbor pod `config/`, zmení vybrané nezávislé parametre a použije presne ten istý `scenario_v3.preflight` a `run_scenario_v3_native.supported` ako `validate`. Nepodporovaný profil alebo tok vracia `UNSUPPORTED_OR_INVALID`, `schema_only_no_packets`, nenastartuje natívny beh a neprepisuje existujúci scenár. `run` vyžaduje nové ID výsledku pod `results/v3_runs/`. Katalóg `config/v8_catalog.json` uvádza príklady, spustiteľnosť a hranice editovateľných parametrov.

Natívna cesta je **ns-3.38/SNS-3 3.38, generické DVB, jedna vybraná RSU/UT, dve pripnuté LEO družice a proxy brána**. Operátorské v3 návrhy (napr. Iridium) sú len preflight/modelové vstupy iných vrstiev; V8 im neprisudzuje pakety tejto cesty. Webový editor má samostatný preflight uloženého v3 scenára cez rovnakú funkciu `bp_v8.validate_scenario`. Jeho kreslený návrh schémy v2 ostáva osobitnou deklaratívnou vetvou.

## Výsledok a vernosť

`verify` opäť číta raw CAM, PCAP, LAN/ISL, SNS-3 PacketTrace, event CSV, obsah reportu a návratový paket. `analyze` najprv vyžaduje úspešný checker. `events.jsonl` zachováva pri každom `event_id` vetvu, raw riadky, SHA-256 stopy a hash payloadu; `analysis.json` má pre každú metriku čitateľ, menovateľ alebo dôvod `null`, event keys, jednotku, rozsah a `model_only`. `verify-analysis` celý produkt z raw regeneruje a porovná bajtovo. Pri jednej krátkej deterministickej dávke sú p95 a p99 zámerne `null`. V8 neposkytuje terénnu kalibráciu ani nezávislé overenie operátorského výkonu.

## Prenosné vydanie

`scripts/v8_release.py pack` vytvorí `release/bp-v8-native-ubuntu24.04-20261026.tar.zst` a jeho SHA-256. `FILE-MANIFEST.json` v balíku pinuje obsah súborov, relatívne odkazy, Git revízie ns-3.38/SNS-3/Vanetza a presný diff dvoch projektových SNS-3 patchov. Git index sa nehashuje, pretože samotná kontrola Git diff obnovuje jeho stat cache; obsah zdrojov a patch sa kontroluje. Vylúčené sú aj build lock a `SimInfo.log`/`SimDiff.log`, ktoré SNS-3 generuje pri behu. Po obnove treba overiť SHA archívu a `verify-dir` pred aj po smoke behu. `scripts/v8_restore.sh` obnoví Python závislosti len z pribalených wheelov a preloží natívny runtime na Ubuntu 24.04 x86_64; `scripts/v8_smoke.sh` vytvorí nový štvorsprávový scenár a vykoná celý reťazec.

V balíku sú zdroje, malé potrebné vstupy, licencie/poznámky, piny a patch. Vylúčené sú historické raw výsledky, prenesené binárky/cache a voliteľné 3,2 GB externé fading traces. Tie patria do plného archívu obnovy; kompaktný balík nereprodukuje všetky staršie P0–P6 experimenty. `release/THIRD_PARTY.md` pomenúva priložené cudzie komponenty a ich licencie. Nový výsledok treba uchovať samostatne s vlastnými hashmi.

## Prijímacia brána

Na podporovanom Ubuntu musí ísť z presného archívu overiť piny, postaviť runtime bez siete, zmeniť aspoň tri nezávislé parametre, vykonať všetky tri vetvy, vysvetliť prijatie/zamietnutie z raw stopy a odmietnuť pozmenený raw alebo analytický súhrn. Konkrétny priebeh a hash artefaktu sú v `docs/experiments/v8-release-2026-10-26.md`.
