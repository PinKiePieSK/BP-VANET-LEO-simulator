# Globalstar RM200M: skúška nášho aplikačného správového obalu

**Stav:** 22. 10. 2026 UTC. **Kód:** [`src/globalstar_rm200m_message.py`](../../src/globalstar_rm200m_message.py), [`tools/run_globalstar_rm200m_message.py`](../../tools/run_globalstar_rm200m_message.py). **Fixture:** [`rm200m-icb1-report.hex`](../../data/fixtures/rm200m-icb1-report.hex). **Surové pokusy:** `results/globalstar_rm200m_message/attempts.csv` a `manifest.json`.

## Motivácia a rozsah

[Oficiálny produktový list Globalstar RM200M](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet.pdf), označený `9150-0215-01 R-3`, uvádza veľkosť satelitnej správy **MO 9–144 B** a **MT 9–128 B**. Zdroj bol znovu kontrolovaný 22. 10. 2026; PDF mal SHA-256 `d5c2423e82955e99d3ed4066ab1c44790b921e303a97ffaabaa10e86ddc34d03` a server vtedy hlásil HTTP `Last-Modified: Mon, 24 Feb 2025 16:29:47 GMT`. Produktový list zároveň uvádza obojsmerný modul, L/S pásma a nutnosť certifikovať riešenie pre sieť Globalstar. Tieto údaje **neurčujú** IP zásobník, latenciu, úspešnosť jedného pokusu ani formát servisnej hlavičky dostupný aplikácii. [Produktová stránka](https://www.globalstar.com/en-gb/products/iot/rm200m) uvádza, že jej odhad pokrytia počíta s pôvodným pokusom a dvomi opakovaniami; odhad nie je meraním nášho scenára.

Vstupom je **náš** 96 B `ICB1 v1` report, ktorý už vytvorila RSU po overení prijatej CAM v [integrovanom CAM teste](../decisions/integrated-cam-backhaul.md). Presné bajty sú uložené vo fixture; v aktuálnej VM sa zhodujú s `RSU_REPORT_TX` v `results/integrated_cam_backhaul/positive.csv`. Zmyslom tejto sondy je overiť, že rovnaká informácia sa **veľkosťou** zmestí do jednej správy MO RM200M a že náš prijímač vie spoľahlivo identifikovať, odmietnuť poškodenie a evidovať lokálne opakovanie. Žiadna správa sa neodosiela do modemu ani satelitu.

## Formát a algoritmus

`ICB1` je **lokálny výskumný aplikačný formát, nie Globalstar protokol**. Všetky celé čísla sú big endian. Presné polia:

| Offset | Bajty | Pole | Jednotka alebo pôvod |
| ---: | ---: | --- | --- |
| 0 | 4 | `ICB1` | Naša magic hodnota. |
| 4 | 1 | verzia `1` | Naša verzia. |
| 5 | 8 | `event_id=ca000000000003e9` | Identita RSU udalosti odvodená v skoršom teste od `stationId=1001`. |
| 13 | 8 | `100266` | Čas prijatia CAM v RSU v **simulačných µs**, nie UTC. |
| 21 | 2 | dĺžka CAM `41` | Bajty. |
| 23 | 32 | SHA-256 CAM | Kontrola neúmyselnej zmeny bajtov; nie podpis/autentifikácia. |
| 55 | 41 | CAM UPER | Presne bajty prijaté RSU v skoršom teste. |

Celok má 96 B; SHA-256 celého reportu je `886ed11b35ba55ada3b9a8ef03e18532ae7babbaf8a2c91f28db70b5fc2ad1f7`. Prijímač kontroluje dĺžku, magic/verziu, pole dĺžky a SHA-256 vložených CAM bajtov. Tento samostatný Python kód **znovu nedekóduje ETSI ASN.1**; to bolo overené v skoršom Vanetza teste a tu sa fixture porovnáva s jeho uloženým RSU výstupom. `event_id` a SHA-256 celého 96 B reportu tvoria kľúč lokálnej deduplikácie. Rovnaký ID s iným správne hashovaným telom sa vykáže ako konflikt identity, nie ako ďalšia nová udalosť. Hash nie je ochrana proti úmyselnej zámene celého reportu.

`native_size_guard(direction, payload)` kontroluje iba publikované hranice veľkosti tela správy; nevolá API výrobcu a netvrdí, koľko interných riadiacich bajtov modem používa. Naša voliteľná odpoveď `GRA1 v1` má **46 B**: 4 B magic, 1 B verzia, 8 B event ID, 32 B SHA-256 96 B reportu, 1 B lokálny status `0`. Zmestí sa do MT limitu. Je to **náš návrh aplikačného potvrdenia** vytvorený len pri prvom lokálnom prijatí, nie potvrdenie siete Globalstar, rádiový ACK alebo dôkaz možnosti spätného doručenia.

## Pokusy, kontrola a výsledky

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 tools/run_globalstar_rm200m_message.py
```

Skript nezávisle skladá fixture z polí a porovnáva všetkých 96 B, overuje dekódovanie/návratové kódovanie, veľkosť 96 B MO, 46 B našej MT odpovede a presné hex bajty každého pokusu v `attempts.csv`. Hraničné veľkosti 9/144 B MO a 9/128 B MT prejdú **iba veľkostnou kontrolou**, bez tvrdenia o platnom aplikačnom formáte. Správy MO 8/145/300 B a MT 8/129 B sa odmietnu. **300 B report z prvého IP pilotu nemôže byť jedna natívna MO správa RM200M.** Segmentácia tu nie je implementovaná.

| Deterministická lokálna sekvencia | Pokusy | Prijaté unikátne | Duplicitné | Poškodené | Konflikt ID |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pôvodná 96 B správa + dve rovnaké lokálne opakovania | 3 | 1 | 2 | 0 | 0 |
| Jeden zmenený CAM bajt bez opravy hasha, potom platná správa a jej opakovanie | 3 | 1 | 1 | 1 | 0 |
| Platná správa a nové platne hashované telo s rovnakým ID | 2 | 1 | 0 | 0 | 1 |

Poškodená správa nedostane lokálnu odpoveď. Pri jedinom prvom prijatí má `GRA1` odpoveď 46 B, dekóduje sa späť na pôvodné ID a SHA-256 reportu. Opakovania a konflikt nevytvoria novú odpoveď. `attempts.csv` nesie **celý aplikačný hex**, status a prípadný hex našej MT odpovede; `manifest.json` nesie zdrojové URL, revíziu, dátum, SHA-256 vstupov a kódu, počty a obmedzenia. V aktuálnej VM sa fixture tiež porovnáva s existujúcim `positive.csv`; skript zostáva spustiteľný aj bez ignorovaného výsledkového priečinka, pretože fixture je verzovaný.

## Interpretácia a ďalšie brány

Táto skúška dokazuje iba **veľkostnú prípustnosť a lokálnu konzistenciu nášho 96 B aplikačného obsahu** vzhľadom na publikované hranice. Neimplementuje RM200M API/firmware, mechanizmus pokusov operátora, IP/UDP, rádiové rámce, orbitálnu geometriu, súčasnú viditeľnosť gateway, prenos, latenciu, pravdepodobnosť úspechu ani skutočné MO/MT doručenie. Tri pokusy sú nami zvolená deterministická sekvencia na audit počítadiel; [poznámka výrobcu o pokrytí](https://www.globalstar.com/en-gb/products/iot/rm200m) ju nemení na meranie siete. Na predikciu treba dokumentované modemové API, konkrétny plán/certifikovaný terminál, pokrytie a súčasnú geometriu zariadenie–satelit–gateway, RF parametre a merania služby.
