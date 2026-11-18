# Globalstar: súčasná geometria terminálu a hypotetickej brány

**Stav:** 22. 10. 2026 UTC. **Kód:** [`tools/globalstar_two_endpoint_geometry.py`](../../tools/globalstar_two_endpoint_geometry.py) a [`tools/check_globalstar_two_endpoint.py`](../../tools/check_globalstar_two_endpoint.py). **Výstupy:** [`bratislava-nemea-20261022T124500Z.csv`](../../data/derived/globalstar-two-endpoint/bratislava-nemea-20261022T124500Z.csv) a [metadáta](../../data/derived/globalstar-two-endpoint/bratislava-nemea-20261022T124500Z.metadata.json). Tento míľnik počíta iba geometriu z GP/OMM, bez paketového prenosu.

## Zdroj brány a hranica overenia

[Globalstar opisuje svoju architektúru ako transparentný „bent-pipe“ so signálom vedeným cez pozemnú gateway](https://www.globalstar.com/en-us/about/our-technology). Pri takomto profile samotná viditeľnosť družice z terminálu nestačí: **ten istý objekt musí byť súčasne geometricky viditeľný aj z vhodnej brány**. [Správa Globalstar z 21. 9. 2026](https://investors.globalstar.com/news-releases/news-release-details/globalstar-completes-expansion-greece-ground-station-marking-key) potvrdzuje stanicu Globalstar pri teleporte OTE v Nemea, tri skôr inštalované antény a dokončenie ďalších troch; rozšírenie bolo vtedy v štádiu uvádzania do prevádzky. Neuvádza presné súradnice antény ani overiteľný aktuálny stav služby RM200M, ktorým by sa konkrétny paket priradil k tejto bráne.

Preto je `nemea_city_proxy` **výslovne hypotetický bod**, nie poloha antény alebo potvrdená operačná brána. Používa `37,8167° N, 22,6667° E` z [Getty Thesaurus of Geographic Names pre mesto Neméa](https://www.getty.edu/vow/TGNFullDisplay?english=Y&find=&nation=&place=&subjectid=5001999), s **predpokladanou** WGS84 výškou `0 m`. Skutočný teleport je mimo tohto bodu a jeho výška/terén tu nie sú potvrdené. `distant_west_sensitivity_control` je úplne syntetický bod `37,8167° N, 100° W, 0 m`, zvolený len na test citlivosti spoločnej geometrie. Ani jeden bod sa nesmie vydávať za funkčnú Globalstar gateway.

## Hypotéza, vstupy a algoritmus

Hypotéza: pozorovanie „zariadenie vidí satelit“ a „brána vidí nejaký satelit“ je slabšie než **súčasná viditeľnosť toho istého satelitu**. Kontrolný výpočet používa Bratislavskú pevnú polohu terminálu pri RSU `48,1486° N, 17,1077° E, 0 m`, oba scenáre brány, UTC začiatok **2026-10-22 12:45:00**, 360 s a krok 30 s. Testovací prah je **10° na oboch koncoch**; nie je to publikovaná minimálna elevácia RM200M alebo Globalstar gateway.

Vstupom je [archivovaná snímka Globalstar GP/OMM](../../data/orbits/20261022T124815Z-retlector/manifest.json) získaná z označenej cache CelesTrak dát. Manifest eviduje, že cache pri získaní hlásila `Stale`. Skript overí SHA-256 gzip aj surového JSON, presný počet 36 katalógových záznamov, unikátnosť ID a epochu každého prvku; iba 30 prvkov je mladších než 48 h až do **konca** výpočtového okna, šesť sa zamietne. To nie je počet aktívnych satelitov. SGP4 `2.27` používa WGS72 pre GP, Astropy `7.1.1` premieňa TEME→ITRS s lokálne hashovanou EOP tabuľkou `astropy_iers_data 0.2026.10.19.0.52.1`. Sieťové aktualizácie EOP sú vypnuté. Časová transformácia a SGP4 mali skôr [oddelenú validačnú skúšku](orbit-validation.md).

V každom čase sa z rovnakej ITRS polohy každého prijatého objektu vypočíta topocentrická elevácia a šikmá vzdialenosť pre terminál a zvolený bod brány. Kandidát existuje iba ak **ten istý katalogizovaný objekt** spĺňa `elevácia > 0°` a `elevácia ≥10°` na oboch koncoch v tej istej vzorke. Ak ich je viac, vyberá sa najväčšie minimum z dvoch elevácií; zhodu rozhodne menšie číselné katalógové ID. Je to deterministické analytické pravidlo, nie algoritmus Globalstar. `two_legs_vacuum_ms_only = (r_terminál + r_brána)/299 792,458 km/s` je súčet dvoch priamych časov vo vákuu, **nie latencia správy**. Výpočet nerieši kontinuitu medzi 30 s vzorkami.

CSV má 26 riadkov (13 časov × 2 citlivostné polohy). Obsahuje UTC/sekundy, scenár, počet objektov nad prahom pri oboch koncoch a ich prienik, prípadne vybrané ID/názov, obidve elevácie v stupňoch, vzdialenosti v km, dvojúsekový `r/c` v ms, epochu a SHA-256 OMM záznamu. Metadáta uchovávajú presné polohy, pravidlá, verzie, zdrojové URL a SHA-256 OMM, manifestu, EOP, kódu a CSV.

## Výsledok, negatívny variant a skúšky

| Vzorka | Bod brány | Terminál ≥10° | Brána ≥10° | **Rovnaký objekt na oboch** | Vybraný objekt | Dvojúsekové `r/c` |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 s | hypotetický bod mesta Nemea | 2 | 2 | **2** | 37741 | 17,789433093 ms |
| 0 s | vzdialený syntetický bod | 2 | 1 | **0** | — | — |
| 180 s | hypotetický bod mesta Nemea | 2 | 1 | **1** | 37190 | 15,748240922 ms |
| 360 s | hypotetický bod mesta Nemea | 2 | 1 | **1** | 37190 | 16,707231497 ms |

V 13/13 vzorkách má hypotetický bod Nemea aspoň jedného spoločného **geometrického** kandidáta. Vzdialený bod má 0/13, hoci terminál aj vzdialený bod **samostatne** vidia nad 10° aspoň jeden z archivovaných objektov v každej vzorke. To overuje rozdiel medzi dvoma oddelenými počtami a prienikom podľa *toho istého ID*. Nezaručuje dostupnosť v Nemea ani výpadok nejakej reálnej vzdialenej brány. Prvé vybrané ID 37741 je výsledkom max-min pravidla, hoci pri samotnom termináli bol najvyšší iný objekt; takýto výber nie je priradenie operátora.

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/globalstar_two_endpoint_geometry.py \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --output-csv data/derived/globalstar-two-endpoint/bratislava-nemea-20261022T124500Z.csv
.venv/bin/python tools/check_globalstar_two_endpoint.py
```

Checker overí zdrojové a výstupné SHA-256, časové riadky, unikátne ID, pôvod vybraných OMM, počty a vzorec `r/c`. Dva opakované výpočty vytvoria **identické bajty** CSV aj metadát. Negatívny vstupný test poškodí gzip bajt a musí sa zastaviť pred výstupom na chybe SHA; druhý mení všetkých 36 epoch na rok 2020, pritom aktualizuje hashe manifestu, a musí sa zastaviť na vekovom filtri. Výsledok checkeru: `status=pass`, 26 riadkov, 13/0 spoločných vzoriek, SHA-256 CSV `346487a3fd7ad9d0dc11ef93fac56b0116109dcb939f94bc2f887cc8fb3654a6`.

**Denník výpočtu:** Prvá pokusná citlivostná poloha `37,8167° N, 22,6667° W` mala napriek veľkému odstupu v tomto okne **11/13** spoločných vzoriek; nebola vhodná ako negatívna kontrola. Po zistení sa zvolil explicitne vzdialený syntetický bod `100° W`, pre ktorý je prienik 0/13. Pôvodný pokus bol len diagnostický, jeho surové CSV bolo pri opakovaní prepísané a nie je predložené ako výsledný dataset.

## Limity a ďalší krok

Ani pozitívny geometrický prienik neznamená zapnutý Globalstar satelit, funkčnú gateway, RM200M službu, oprávnený terminál, vhodný lúč, rádiový link budget, prístup ku kanálu alebo úspešné doručenie. Neznáme sú skutočné súradnice antén, výška, terénny profil, prevádzkové priradenie služby a aktuálna konfigurácia siete. Model **neobsahuje ISL** ani paketový prenos. Pred napojením na [96 B aplikačný report](globalstar-rm200m-message.md) treba získať overiteľný profil terminálu/gateway alebo ponechať výsledok ako široký citlivostný experiment s explicitným neistým vstupom. Vzorkovaná dvojkoncová geometria je nutná brána fyzikálnej možnosti transparentnej cesty, nie dôkaz prevádzkového spojenia.
