# Časový plán geometrickej brány pre budúci ns-3 paketový model

## Účel a hypotéza

Z [overeného časového radu jednej družice Iridium NEXT](orbit-geometry-gate.md) vytvoriť deterministické intervaly, ktorými môže **budúci** ns-3 scenár ovládať geometrickú prípustnosť úseku RSU/terminál ↔ družica a jeho jednosmerné vákuové oneskorenie. Hypotéza tohto kroku je úzka: pravidlo s maskou 10° správne zablokuje neznámy prechod cez masku a celú dobu pod horizontom. Kontrolou sú prvé intervaly, ktorých oba koncové body majú eleváciu nad 10°. Tento plán zatiaľ **nie je pripojený k ns-3** a nijaké pakety ním neprešli.

## Vstup a pravidlo

Vstup je `data/derived/orbit-geometry/iridium-43253-bratislava-20261022.csv` (SHA-256 `fb8c995cee050eb4697238bd5700c939e4c44059bc17a76697f59955b65db359`) spolu s jeho `metadata.json` (SHA-256 `37485eaee9f417961cc908ee7c17df79a8a11a3fa6ee5a919b8fb56fd233985f`). Nástroj overuje oba odtlačky, zhodu OMM/EOP/stanice/epochy, UTC krok 30 s, prepočítava príznaky horizontu a masky z elevácie a kontroluje, že zdrojové vákuové oneskorenie zodpovedá `vzdialenosť / c` v rámci zaokrúhlenia CSV. Nečerpá nové orbitálne dáta.

Pre susedné vzorky `i`, `i+1` definuje **polootvorený interval `[tᵢ,tᵢ₊₁)`**. `geometry_enabled=1` iba vtedy, ak *oba* konce majú eleváciu **≥10° a >0°**. Ak sa konce líšia v stave masky alebo horizontu, zablokuje **celý** interval. Okamih prechodu sa neinterpoluje. Ak sú oba konce nad maskou, konštantné `one_way_vacuum_delay_ns` je **väčšia z dvoch nameraných** hodnôt `r/c`, prevedená z ms na celé ns. Ide o konzervatívnu voľbu vzhľadom na **dve vzorkované hodnoty**, nie o matematický horný odhad oneskorenia vo vnútri intervalu. Medzi vzorkami sa ešte môže stať nepozorovaná zmena; na preukázanie súvislej viditeľnosti by bol potrebný hustejší výpočet alebo formálna hranica pohybu.

Pred `start_utc` a od `end_utc` je predvolený stav **zablokovaný**. Interval začínajúci v `t=150 s` je už zablokovaný, hoci samotná vzorka v `t=150 s` má 10,265132°: vzorka v `t=180 s` má len 7,757501°. Posledná vzorka v `t=360 s` neotvára ďalší interval.

## Výstup, jednotky a plánovaná väzba na ns-3

Výstup `data/derived/orbit-geometry/iridium-43253-bratislava-20261022.ns3-schedule.csv` obsahuje UTC konce, offsety od začiatku simulácie v **sekundách**, trvanie v **sekundách**, elevácie v **stupňoch**, priame vzdialenosti v **km**, príznak geometrickej prípustnosti, dôvod zamietnutia a jednosmerné vákuové oneskorenie úseku v **celých nanosekundách**. Pri zablokovanom intervale je pole oneskorenia prázdne, aby ho simulátor nemohol zameniť za nulové oneskorenie. Sprievodný `...ns3-schedule.metadata.json` obsahuje odtlačky zdrojov, parametre pravidla, počty a SHA-256 výstupu `eb8e7db952ea75859b8bd4f0ef7d1b857dee8f877ba970f1f42c716a8e9e40f6`.

Pri budúcej integrácii má ns-3 pred t=0 nastaviť tento jediný úsek ako neprípustný, pre každý `start_offset_s` prepnúť stav a pri prijatej geometrickej prípustnosti aplikovať `one_way_vacuum_delay_ns` na **jednu** cestu terminál–družica. Samotné čítanie CSV ešte nerozhoduje o správaní paketu rozpracovaného v okamihu vypnutia, o smere spätného spoja, o queue, RF chybách či inom úseku trasy; to musí implementácia výslovne definovať a overiť paketovou stopou. Tento plán nie je dokladom služby operátora, lúča, gateway, ISL ani dosiahnuteľnosti vzdialenej aplikácie.

## Výsledné intervaly

| UTC 22. 10. 2026 | Offset | Geometria | Jednosmerné vákuové oneskorenie | Dôvod |
| --- | ---: | --- | ---: | --- |
| 12:45:00–12:45:30 | `[0,30)` s | povolená | 5 222 076 ns | oba konce nad 10° |
| 12:45:30–12:46:00 | `[30,60)` s | povolená | 5 832 199 ns | oba konce nad 10° |
| 12:46:00–12:46:30 | `[60,90)` s | povolená | 6 459 252 ns | oba konce nad 10° |
| 12:46:30–12:47:00 | `[90,120)` s | povolená | 7 098 205 ns | oba konce nad 10° |
| 12:47:00–12:47:30 | `[120,150)` s | povolená | 7 745 555 ns | oba konce nad 10° |
| 12:47:30–12:48:00 | `[150,180)` s | blokovaná | — | prechod cez 10° v neznámom okamihu |
| 12:48:00–12:49:30 | tri 30 s intervaly | blokovaná | — | oba konce pod 10°, nad horizontom |
| 12:49:30–12:50:00 | `[270,300)` s | blokovaná | — | prechod cez horizont v neznámom okamihu |
| 12:50:00–12:51:00 | dva 30 s intervaly | blokovaná | — | oba konce pod horizontom |

Celkom **12 intervalov: 5 povolených, 7 blokovaných**, z toho 2 pre neznámy čas prechodu. Ide o historický offline replay: OMM epocha objektu 43253 je **2026-10-21 02:59:35,421792 UTC**, snapshot bol získaný až **2026-10-22 12:49:43,719531 UTC**, po simulovanom začiatku. Nie je to online predpoveď dostupná o 12:45. Parametre orientácie Zeme sú IERS-A predikcie; ich stav a SHA sú v zdrojových metadátach.

## Reprodukcia a skúšky

Nástroj používa štandardnú knižnicu Pythonu 3.12; vstupný geometrický CSV vznikol pomocou pripnutého `sgp4`/Astropy podľa [predchádzajúceho experimentu](orbit-geometry-gate.md).

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 tools/build_orbit_ns3_schedule.py \
  --geometry-csv data/derived/orbit-geometry/iridium-43253-bratislava-20261022.csv \
  --geometry-metadata data/derived/orbit-geometry/iridium-43253-bratislava-20261022.metadata.json \
  --output-csv data/derived/orbit-geometry/iridium-43253-bratislava-20261022.ns3-schedule.csv
sha256sum data/derived/orbit-geometry/iridium-43253-bratislava-20261022.ns3-schedule.csv
```

Druhý beh do `results/orbits/` vytvoril **bitovo rovnaké CSV**. Prešli testy presnej hranice **10,000000°** (povolená vzorka), **9,999999°** (zamietnutá), prechodu 10° v intervale `[150,180)`, prechodu horizontom v `[270,300)` a negatívnej elevácie. Zmena jediného čísla vo vstupnom CSV bez aktualizácie metadát bola odmietnutá kontrolou SHA-256. `py_compile` prešiel. Všetky výstupy sú odvodené z jedného archivovaného vstupu; pri zmene OMM, UTC, masky alebo vzorkovacieho kroku sa musí vytvoriť nový plán a nový experimentálny manifest.
