# P0: spoločný experimentálny kontrakt a register dôkazov

**Stav:** dokončená príprava kontraktu, 25. 10. 2026. Tento míľnik nemení simulačný C++ model a neprodukuje nové meranie siete. Určuje, čo presne majú následné runnery merať a aké tvrdenie ich dôkazy dovoľujú.

## Pripnuté vstupy a účel

- [Kontrakt v1](../../config/bp_experiment_contract_v1.json) pripína aktívny ns-3.38/SNS-3 3.38 runtime, päť profilov, štyri SHA-256 kontrolované lokálne vstupy, UTC, seed/run, význam aplikácie a metriky. [Register dôkazov v1](../../config/bp_service_evidence_v1.json) priraďuje každému verejnému údaju zdroj, jednotku, význam a zoznam stále neznámych položiek. [Validator](../../tools/validate_bp_experiment_contract.py) je čítacia kontrola týchto súborov.
- P1 použije už overený `data/inputs/editable-road-v2/packet-subset.json` so šiestimi CAM pri t=20,0–22,5 s a efektívnym UTC `2026-10-22T12:46:32Z`. Pôvodný JSON má `12:45:00Z`; existujúci dvojdružicový runner ho pri príprave scenára **výslovne posúva**. Kontrakt preto ukladá zdrojový hash aj efektívny čas osobitne.
- Kandidát finálnej geografie je existujúca OSM cesta v Bratislave s piatimi bodmi FCD pri t=5–9 s, UTC `2026-10-22T12:45:00Z` a hypotetickou RSU približne `48,1482680685° N; 17,1085884807° E`. OSM geometria nie je meraný dopravný dopyt; `randomTrips` a umiestnenie RSU sú výskumné vstupy. Orbitálna snímka z existujúcich pokusov je retrospektívny kandidát, nie predpoveď služby. [OSM experiment](osm-ba-cam-rsu.md).

## Jednotka porovnania a metriky

RSU vytvorí **96 B ICB1 až po dekódovaní CAM**. ICB1 nesie `event_id`, čas prijatia, SHA-256 a pôvodný 41 B CAM. Satelit prenáša novú aplikačnú informáciu vytvorenú RSU; pôvodný 802.11p rámec sa na satelit neposiela. Spoločná úloha je doručiť tú istú informáciu vzdialenej aplikácii. Iridium a Starlink kandidáti používajú IP servisný model; Globalstar RM200M vyžaduje vlastnú MO/MT správu s overením použiteľných bajtov a rozhrania.

**Primárny menovateľ** je počet unikátnych ICB1 vytvorených RSU z CAM prijatých v meracom okne. Úspech vyžaduje zhodné `event_id` a hash ICB1 na vzdialenej aplikácii do **60 s od `RSU_REPORT_CREATED`**. Hranica 60 s je vopred zvolený *výskumný prah pre vzdialený dopravný stav*, nie ETSI bezpečnostná lehota ani záruka operátora; 1 s a 10 s sú vopred určené citlivostné prahy. Zmena prahu po výsledku vyžaduje novú verziu kontraktu.

Lokálne CAM sa hodnotia osobitne podľa oprávnených dvojíc `(CAM, prijímač)` určených scenárom v čase vyslania. Oneskorenie `remote RX − RSU_REPORT_CREATED` sa uvádza len pri úspešných unikátnych reportoch; nedoručená správa má delay `null`. GRA1 návrat viazaný na rovnaké ID/hash je samostatná metrika; prijatie autom je ďalší samostatný stupeň. Geometrickú viditeľnosť, pripojený terminál a aplikačné doručenie nesčítavať do jedného „pokrytia“. Neznámy dôvod straty zostáva `unknown`. Krátky pilot 6/6 nedáva prevádzkovú PDR ani p95/p99.

## Register parametrov a hranica tvrdenia

| Profil | Zdrojované dnes | Neznáme alebo výslovne výskumné |
| --- | --- | --- |
| Pozemná WAN kontrola | Dopravná informácia a príjemcovia sú z rovnakého vstupu ako satelitné varianty. | Finálna referenčná kapacita a oneskorenie ešte nie sú vybrané; toto nie je kalibrovaný internet. |
| SNS-3 DVB referencia | Skutočná paketová cesta a source pin v [dvojdružicovom pilote](two-leo-isl-icb1-e2e.md). | 17 dBi konštantná mapa, 1 Gbit/s P2P ISL a Nemea proxy sú explicitné diagnostické predpoklady. |
| Iridium SkyLink 5100 / Certus 100 | [Iridium 9770](https://www.iridium.com/products/iridium-certus-9770) publikuje 22/88 kbit/s maximá a 1616–1626,5 MHz rozsah modulu; [Iridium Network](https://www.iridium.com/network) opisuje crosslinkovú architektúru. | Aktivovaný plán, montáž antény, serving beam/satelit, brána, MAC/scheduler, straty a latencia rovnakej zostavy. Maximá nie sú garantovaný goodput. |
| Globalstar RM200M | [Produktový list](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet1.pdf) uvádza MO 9–144 B a MT 9–128 B; [Globalstar](https://www.globalstar.com/en-us/about/our-technology) opisuje bent-pipe prenos do vhodnej brány. | Skutočná brána/API/účtovanie payloadu, retry a per-message doba doručenia. Model nesmie pridať ISL ani transparentný UDP socket. |
| Starlink Performance | [Hardvérový list](https://starlink.com/public-files/specification_sheet_performance.pdf) uvádza 140° zorné pole; [podmienky pohybu](https://starlink.com/fi/support/article/50e933eb-54f5-1a77-cc85-c6c8325564cf) viažu použitie na hardvér/plán/miesto; verejný opis [optickej siete](https://starlink.com/public-files/starlinkProgressReport_2025.pdf). | Presná generácia/SKU, aktívny plán, beam, dynamická trasa, scheduler a porovnateľné merania. Verejná mobilná FHP [stopa](../decisions/empiricka-kalibracia-konkretnych-sluzieb.md) meria iný terminál a gateway RTT, preto je len externý kontext. |

Zdroje boli skontrolované k dátumu registra; dynamické produktové stránky nemajú v tomto projekte archivovanú nemennú verziu. Pred finálnou kampaňou sa preto znovu overí aktuálna revízia a presný terminál/plán. [CelesTrak GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php) poskytne časovo označenú geometriu, nie servisné priradenie družice.

V1 prijíma iba označenie **`planning_contract_only`**. Požiadavka `operator_prediction` skončí chybou pre každého operátora, lebo chýba aktivovaný plán, porovnateľné raw kalibračné a nezávislé validačné dáta, odborná kontrola ich koncových bodov a hotový validovaný profil. Nové merania ani zmena produktového listu sa nesmú „odomknúť“ iba ručným prepnutím statusu; vyžadujú novú verziu kontraktu a kontrolu porovnateľnosti. Existujúci `config/operator_profiles.json` je starší **architektonický prehľad**, nie tento vykonávací a metrický kontrakt.

## Kontrola

```bash
.venv/bin/python tools/validate_bp_experiment_contract.py
.venv/bin/python tools/validate_bp_experiment_contract.py --profile iridium_certus100_skylink5100 --claim operator_prediction
.venv/bin/python -m unittest discover -s tools -p 'test_bp_experiment_contract.py' -v
```

Prvý príkaz má vrátiť `PASS`, štyri skontrolované hashe a päť profilov. Druhý musí skončiť nenulovým návratovým kódom s presne uvedenými chýbajúcimi dôkazmi. Negatívne testy menia hash/cestu vstupu, hranicu metriky, názov DVB profilu, transport/ISL Globalstaru a zdroj parametra; validator ich odmietne. Tým je **P0 dokončené ako kontrakt pre budúcu prácu**, bez tvrdenia, že P1–P6 už bežia.
