# F3 — doložené antény a explicitná montáž terminálu

**Stav:** hotovo pre verejne doložené terminálové obálky, 1. 11. 2026. Zdroj: `tools/u9_antenna_envelope.py`; vykonanie v `tools/u9_dynamic_service.py`, `tools/bp_u9.py` a editore. Nový voliteľný profil scenára je `satellite.antenna_model="public-v1"`.

## Verejné fakty a hranice

| Služba a konkrétny terminál | Verejný podklad | Tvrdý smerový limit modelu | Neznáme |
| --- | --- | --- | --- |
| Starlink Flat High Performance / Performance Gen 2 | [Výrobca](https://starlink.com/public-files/specification_sheet_flat_high_performance.pdf) uvádza elektronickú fázovanú anténu a **140° zorné pole**. [FCC 22-91](https://docs.fcc.gov/public/attachments/FCC-22-91A1.pdf) uvádza podmienku 25° minimálnej elevácie pre príslušné Gen2 Ku prípady mimo polárnej oblasti. | Pri **explicitne zadanej montáži** sa testuje 70° od normály panelu; používateľská elevácia zostáva samostatným limitom. | Skutočná normála namontovaného panelu, generácia každého NORAD objektu, aktivácia lúča, jeho kontúra a priradenie používateľa. |
| Iridium Certus 9770 | [Výrobca](https://www.iridium.com/products/iridium-certus-9770) uvádza externú pasívnu všesmerovú anténu. | Žiadny vymyslený smerový prah; zostáva horizont a existujúca geometrická obálka. | Zisk konkrétneho kusu, montáž a tienenie karosériou, satelitný beam a prístup. |
| Globalstar RM200M | [Certifikát výrobcu](https://www.globalstar.com/getmedia/a4613a3c-9086-4cdf-b2c2-12cc2c3df169/rm200m-eu-type-certification.pdf) označuje keramickú patch anténu. | Žiadny vymyslený uhol patch antény; zachovaná dvojstranná geometria terminál–satelit–proxy brána bez ISL. | Meraná zisková krivka po integrácii, orientácia, satelitné spot beamy a ich aktivácia. |

Montáž je voľba **konkrétneho terminálu**, nie spoločný parameter konštelácie. `terminal_mounts` mapuje ID auta alebo RSU na `tilt_deg` (0–180° od zvislice), `azimuth_deg` (0–<360°) a `frame` (`north` alebo pri aute `vehicle`). Pri `vehicle` sa k azimutu pripočíta hlavička `heading_decideg` z overenej SUMO stopy. Smer k satelitu sa počíta v lokálnom ENU rámci z WGS84/ECEF. Bez explicitnej montáže zostáva staršia geometrická obálka; nejde o tvrdenie, že panel má automaticky správne natočenie. Editor ponúka tieto polia pri Starlink termináli každého zapnutého auta/RSU. Pokus o numerickú smerovú montáž Iridium alebo Globalstar sa odmietne, pretože chýba obhájiteľná krivka zisku.

`routes.json` pri novom profile ukladá zdroj antény, montáže, `geometry_candidate_count`, počet po anténnom profile a odchýlku aktuálneho serving satelitu od normály. `physical-timeline.json` naďalej znamená **geometrickú** možnosť. Paketový backend berie iba anténne prípustnú trasu, takže zmena montáže mení aj raw doručenie. Snapshot, plán, zdrojový kód, montáž a surové pakety sú hashované; verifier ich nezávisle prepočíta. Historické scenáre bez `antenna_model` nemenia výstupy.

## Overenie

| Beh v `~/Desktop/BP-Simulator-Workspace/runtime/results/u9_runs/` | Výsledok `run` a `verify` |
| --- | --- |
| `f3-antenna-starlink-20261101` | Pri 8° zvolenej montáži klesol počet kandidátov auta v prvej vzorke 79→74; 68/68 servisných paketov doručených, výstraha druhej RSU a autu. |
| `f3-antenna-starlink-inverted-20261101` | Zámerná negatívna kontrola s normálou panelov 180° od zvislice: 79 geometrických, **0** anténnych kandidátov auta pri štarte; 68 skutočných ponúk, **0** doručení, 68 explicitných dropov, 0 upozornených áut. |
| `f3-antenna-iridium-20261101` | Publikovaný všesmerový typ bez vymysleného cutoffu: 4→4 kandidáti v prvej vzorke, 68/68 doručení, výstraha druhej RSU a autu. |
| `f3-antenna-globalstar-20261101` | Patch bez publikovanej krivky: 2→2 kandidáti v prvej vzorke, 67/68 doručení bráne, 64 odpovedí; štyri pakety skončili pri hranici 6 s. Výstraha doručená. |

Čisté hraničné testy `tools/test_u9_antenna_envelope.py` kontrolujú panel hore/dole, otočenie auta o 180°, neplatnú montáž RSU vo vehicle rámci a odmietnutie smerového prahu pre Iridium/Globalstar: 2 testy PASS. Šesť historických F2b/F2c behov sa po zmene znovu overilo: 6/6 PASS. UI API a prenosný balík majú samostatnú finálnu kontrolu.

**Záver:** F3 spresňuje *možnosť terminálového výhľadu* tam, kde existuje číslo od výrobcu. Neurčuje aktívny satelitný lúč ani RF/link margin a nepredikuje komerčnú dostupnosť. Ďalšia práca F4 (budovy/terén) a F5 (obojsmerný link budget) ostáva samostatná.
