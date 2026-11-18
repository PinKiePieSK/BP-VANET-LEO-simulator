# V1 — scenárový kontrakt a nezávislý preflight

**Stav:** HOTOVO 26. 10. 2026. **Rozsah dôkazu:** validácia vstupu, explicitný plán a reprodukovateľná geometrická diagnostika. **Počet vykonaných sieťových paketov:** 0. Natívny paketový engine začne až vo V2.

## Zostava

- [Kontrakt a návod](../decisions/scenario-v3-contract.md): uzavretá schéma 3, jednotky, rozsahy, žiadne skryté defaulty a hranice tvrdení.
- [Validátor/CLI](../../tools/scenario_v3.py) má SHA-256 `829e3696fa184dbd0476941e524a473abc3c31d1fcfbdd521561c321b331cf64`. Kontroluje editorový V2 svet, CAM role/časy, profilovú topológiu a limity, zdroje/hashe, EOP/OMM/SGP4 a geometriu. Nesúlad odhalí pred nákladným natívnym buildom. `convert-v2` je prísny CAM adaptér.
- [Profily](../../config/scenario_v3_profiles.json) majú SHA-256 `ac0c61285157745e0ea4edcf8f2e469513b7244f1151be28b0c8a41e3f2ce1e3`. [Register](../../config/scenario_v3_parameter_register.json) má SHA-256 `bc939d1aa150eeee2e2ce225918bd74c4fb00d08883e21c859cbada3cfb99a49` a 48 presných položiek; každá aktívna profilová hodnota musí sedieť s registrom a jej zdrojovým súborom.
- [Register generácií](../../config/simulator_generation_registry.json) oddeľuje `universal-scenario-v3`/`results/v3_runs/` od zmrazených P0–P6; stav novej generácie je iba `v1_preflight_only_no_packet_runner`.

## Štyri odlišné platné scenáre

Každý výstup obsahuje `scenario.normalized.json`, `world.staged-v2.json`, `plan.json`, `run-manifest.json`; `verify` znovu vypočítal všetky štyri. Všetky majú `execution_state=preflight_only_no_packets`, `packet_trace_count=0` a `require_geometry_candidate=true`. Kandidát je kvalifikovaný len na dvoch vzorkovaných časoch; číslo nie je aktívny beam, route ani doručenie.

Manifest navyše zapisuje verzie Pythonu, NumPy, Astropy, `astropy-iers-data` a SGP4; opätovný checker ich porovná. Dva súbory s pripnutými orbitálnymi závislosťami sú v inventári vstupov.

| Vstup | UTC, CAM, profil | Plánované opakovania × vetvy | Kandidáti na vzorkách | Výstup, overenie |
| --- | --- | --- | --- | --- |
| [DVB referencia](../../config/scenario_v3_reference.json) | 22. 10. 2026 12:45 UTC, 6 CAM; dve vybrané LEO, model ISL | 1 × 3 = 3 | 1 / 1 | [Manifest](../../results/v3_runs/v1_reference_release_20261026/run-manifest.json), PASS, 16 pripnutých vstupov |
| [Iridium hranica](../../config/scenario_v3_iridium.json) | 12:50 UTC, 10 CAM; user-only Certus hranica | 2 × 2 = 4 | 1 / 1 | [Manifest](../../results/v3_runs/v1_iridium_release_20261026/run-manifest.json), PASS, 17 vstupov |
| [Globalstar hranica](../../config/scenario_v3_globalstar.json) | 13:15 UTC, 4 CAM; spoločná viditeľnosť UT/proxy GW, bez ISL | 3 × 2 = 6 | 1 / 1 | [Manifest](../../results/v3_runs/v1_globalstar_release_20261026/run-manifest.json), PASS, 17 vstupov |
| [Starlink hranica](../../config/scenario_v3_starlink.json) | 12:45 UTC, 6 CAM; spoločná viditeľnosť UT/proxy GW | 1 × 2 = 2 | 200 / 200 | [Manifest](../../results/v3_runs/v1_starlink_release_20261026/run-manifest.json), PASS, 17 vstupov |

`Starlink 200` znamená počet archivovaných objektov spĺňajúcich dve geometrické masky v daných okamihoch, nie 200 použiteľných komerčných spojení. Referenčný a Starlink plán varujú, že archív bol stiahnutý až **po modelovanom UTC**. Ide o retrospektívny výskumný preflight. Iridium testuje iba UT eleváciu; výstup preto nedokazuje vhodnú bránu. Proxy gateway pri Globalstar/Starlink nie je verifikované prevádzkové miesto.

## Negatívne kontroly a regresia

`.venv/bin/python -m unittest discover -s tools -p test_scenario_v3.py -v` prešlo **10/10**. Testy odmietli chybný SHA-256, duplicitný JSON kľúč, ne-UTC čas, CAM mimo okna, chýbajúce povinné metriky, nulový počet opakovaní, nesúhlas registra s profilom, nepovolený DENM/výber flow, neplatný profilový zásah `no_isl`, nepravdivú kalibračnú deklaráciu, chybný typ príjemcu a nulovú požadovanú geometriu. Výpadková konfigurácia s `require_geometry_candidate=false` prešla iba s explicitným nulovým počtom kandidátov. Adaptér prijal jediný CAM flow a odmietol DENM. `verify` odmietol úmyselne zmenený `plan.json`, verziu závislosti aj starý P0–P6 manifest; `validate` odmietol prepísanie existujúceho ID.

Celá Python regresia po V1: `.venv/bin/python -m unittest discover -s tools -p 'test_*.py'` prešla **79/79**. `git diff --check` prešiel. `python3 tools/v0_history.py validate` znovu potvrdil 464 archivovaných členov a pôvodný hash `58bde6846ba0777841e46e7ec40abec36894207e2231645adc034bdd56ef06c6`. Pôvodné raw P0–P6 výsledky sa nemenili. Vývojové výstupy `v1_*_preflight_20261026`, `_final_20261026` a `_accepted_20261026` zostali zachované ako priebežné s pôvodnými hashmi; prijímací dôkaz sú štyri vyššie uvedené unikátne adresáre `_release_20261026`.

## Presná hranica pri prechode do V2

V1 scenár stále číta konkrétny validovaný editorový V2 svet s jedným CAM broadcastom; meniť možno deklarovaný čas, počet CAM, role v rámci sveta, rádio, servisnú hranicu, seed, počet opakovaní, metriky a kontrolné vetvy. Staging sveta prenesie čas a seed do samostatného súboru, ale zatiaľ ho nespotrebúva všeobecný ns-3 runner. Meranie medzi vzorkami, viac vozidiel/RSU ako zdrojov, natívne ICB1/GRA1 a presná bajtová kontrola patria do V2/V3. Tri operátorské profily majú stále úroveň `scenario/sensitivity`, nie nezávislú validáciu.
