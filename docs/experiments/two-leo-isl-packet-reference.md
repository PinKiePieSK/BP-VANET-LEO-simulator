# Paket cez dve pohyblivé LEO družice a modelový ISL

**Stav 22. 10. 2026 UTC.** Tento izolovaný experiment dokazuje, že pripnutý **ns-3.38/SNS-3 3.38** vie v jednom simulačnom čase doručiť konkrétne aplikačné bajty po trase `terminál → družica 0 → ISL → družica 1 → modelová brána`. Družice používajú archivované GP/OMM objekty **43253 a 43258** zo skupiny Iridium NEXT. Model však používa **generický SNS-3 DVB-S2/RCS2 user/feeder spoj a idealizovaný P2P ISL**, nie rádiové rámce či prevádzkové smerovanie Iridia. [CelesTrak GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php) identifikuje orbitálne elementy pre SGP4; [Iridium](https://www.iridium.com/network) potvrdzuje architektonickú existenciu crosslinkov, ale nepublikuje presnú aktívnu hranu 43253–43258 ani jej paketové parametre.

## Hypotéza a párovaná kontrola

Hypotéza: ak má pozemný používateľ modelovú user cestu na družicu 0 a brána feeder cestu na družicu 1, vložená hrana `0 1` umožní prenos jedného identického obsahu. Kontrola ponechá **tie isté TLE, UTC, terminál, bránu, anténnu mapu, paket a seed**, ale `isls.txt` zmení z `1\n0 1\n` na `0\n`. V nej nemá existovať alternatívne doručenie. Nejde o test reálneho Iridium ISL výberu ani handoveru terminálu.

## Technická špecifikácia

[`run_two_leo_isl_reference.py`](../../tools/run_two_leo_isl_reference.py) overí pripnuté Gity ns-3/SNS-3, SHA-256 archívu Iridium OMM a EOP, vyberie presne oba katalógové záznamy a exportuje TLE pre SNS-3. Pri UTC 12:46:52 a pri príjme ISL rekonštrukcia TLE proti zdrojovému OMM odchýlila objekt 43253 o menej než 0,001 m a objekt 43258 o približne **0,598 m**. TLE je vstupná kompatibilitná konverzia; pôvodný OMM ostáva hashovaným zdrojom. Archív získaný po štarte modelovaného okna je retrospektívna rekonštrukcia.

Pevný terminál má WGS84 bod **48,1486° N, 17,1077° E, 0 m**. Druhý pozemný bod **37,8167° N, 22,6667° E** je **centrum mesta Nemea ako hypotetická brána tohto testu, nie anténa ani brána Iridia**. Simulácia sa začína UTC **22. 10. 2026 12:46:52**, trvá 4 s a používa seed **314159**, run **1**. Pri príjme ISL je vypočítaná WGS84 elevácia terminál→družica 0 **13,760°** a družica 1→proxy brána **36,667°**, obe nad výskumnou 10° maskou. Družice sú približne **4 034,319 km** od seba; spojnicu od stredu Zeme delí najbližšie **6 860,272 km**, teda asi **482,135 km** nad konzervatívnou guľou s polomerom 6 378,137 km. Táto kontrola rieši iba zemský zákryt, nie smerovanie antén, akvizíciu alebo vhodnosť komerčného ISL.

[`two-leo-isl-reference.cc`](../../src/two-leo-isl-reference.cc) nastaví sieťovú regeneráciu, vytvorí dva pohyblivé satelitné uzly z TLE, jednu modelovú user a feeder cestu a zapne pôvodné SNS-3 PHY error modely. **Všetkými smermi konštantná mapa 17 dBi** je čisto diagnostická, výslovne neplatný profil prevádzkovej Iridium antény. Jej súbor je uchovaný a hashovaný. `PointToPointIslNetDevice` má v tejto SNS-3 verzii predvolený **1 Gbit/s** serializér a kanál počíta propagačný čas ako vzdialenosť družíc delenú rýchlosťou svetla; nemá Iridium RF crosslink PHY/MAC, pointing, framing či skutočnú kapacitu. Experimentálny obsah je pevný 16 B `4c454f47454f31000000000112345678`, nie CAM ani `ICB1`.

Paketový `PacketTrace` zachytí UT a satelitný PHY/MAC/ND, ale **nezachytáva bajty ISL**. Preto C++ registruje pasívny promiscuous callback priamo na prijímacom `PointToPointIslNetDevice` družice 1. Ten uloží celý **IPv4 paket po odstránení PPP hlavičky**; príjem potom pokračuje do SNS-3 normálnou cestou. [`check_two_leo_isl_reference.py`](../../tools/check_two_leo_isl_reference.py) samostatne preverí IPv4/UDP dĺžky, obidva checksumy, adresy, port, celý obsah a časové poradie. Jednobajtová zmena payloadu v negatívnej kontrole zlyhá na UDP checksume.

## Surové pozorovanie a rozbor bajtov

V kladnom variante odoslala UT aplikácia obsah v **1,000000 s**; SAT0 mala sieťový príjem interného ID 9 v približne **1,10136 s**. ISL prijímač družice 1 videl celý 44 B IPv4 paket v **1,114815 s**, SAT1 vyslala do feeder PHY v približne **1,11483 s**, GW PHY prijala v približne **1,11917 s** a GW aplikácia overila presných 16 B v **1,128173 s**. Rozdiel SAT0 ND→ISL RX zo zaokrúhlenej stopy je **13,455 ms**; nezávisle vypočítaná vákuová dolná hranica pre 4 034,319 km je **13,457 ms**. Porovnanie má toleranciu 0,1 ms, lebo interný `PacketTrace` vypisuje kratšie časové údaje a SNS-3 používa vlastnú guľovú geometriu.

```
45 00 00 2c 00 00 00 00 3f 11 77 ba fa 01 00 02 0a 02 00 02
c0 01 b3 55 00 18 0d d6 4c 45 4f 47 45 4f 31 00 00 00 00 01 12 34 56 78
```

| Offset v ISL zachytení | Význam |
| --- | --- |
| 0–19 | IPv4, dĺžka **44 B**, protokol UDP `17`, zdroj `250.1.0.2`, cieľ `10.2.0.2`, platný IPv4 checksum. |
| 20–27 | UDP port **49153 → 45909**, UDP dĺžka **24 B**, platný UDP checksum. |
| 28–43 | Presných **16 B** experimentálneho aplikačného obsahu; zhodné s UT TX aj GW RX. |

V kontrolnom variante bez hrany ISL sú všetky riadky UT→SAT0 pre ID 9 v `PacketTrace` zhodné, ale na SAT1/GW nenastane príslušný dátový PHY príjem a GW aplikácia prijme **0/1**. To je kauzálny dôkaz modelovej závislosti od vloženého ISL. **128,173 ms** UT aplikácia→GW aplikácia je výsledok tejto hypotetickej konfigurácie, nie predikcia oneskorenia Iridia.

Nezávislý topocentrický a medzisatelitný výpočet Skyfield oproti Astropy potvrdil ISL vzdialenosť a zemskú rezervu prakticky na zhodnom čísle; najväčšia elevančná odchýlka v dvoch pozemných bodoch bola asi **0,001014°**. Obe cesty používajú tie isté OMM a jadro SGP4, takže kontrolujú transformáciu a geometriu, nie skutočnú orbitálnu presnosť.

## Reprodukcia, surové súbory a neúspešné pokusy

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_two_leo_isl_reference.py \
  /tmp/ns3-sns3-338-feasibility results/two_leo_isl_reference_repeat
.venv/bin/python tools/check_two_leo_isl_reference.py results/two_leo_isl_reference_repeat
```

Výstup musí byť pri spustení prázdny. Runner uloží generované TLE, dva scenáre, anténnu mapu, build log, dva `PacketTrace.log`, aplikačné logy a hashovaný manifest do ignorovaného `results/two_leo_isl_reference/`; checker vytvorí `verification.json`. Výsledný checker vrátil `status=pass`. Počas vývoja prvá kompilácia skončila na názve API `GetGeoSatNodes` (správne `GeoSatNodes`). Prvý generačný pokus odhalil rozdiel v staršej anténnej kotve z automaticky sťahovanej EOP; finálny profil používa **pripnutý lokálny EOP**, starú mapu nemení a neúspešný vstup zachoval v `results/two_leo_isl_reference_failed_input/`. Druhý pokus zlyhal, pretože parser SNS-3 delí cestu s medzerou v pracovnom adresári; runner spúšťa simuláciu v krátkej dočasnej `/tmp` ceste a až potom kopíruje raw výstup do projektu. Aj neúspešný čiastočný výstup ostal v `results/two_leo_isl_reference_failed_space_path/`.

## Hranice pred použitím v závere práce

Čisté opakovanie v `results/two_leo_isl_reference_repeat/` dalo rovnaké časy aj bitovo zhodné `PacketTrace.log` v kladnom a kontrolnom variante. Výstupný názov v príkaze vyššie je preto nový prázdny priečinok; existujúci výsledok runner zámerne neprepíše.

**Dosiahnuté:** dva skutočné archivované orbitálne objekty, zmysluplná geometria UT a proxy feeder bodu, kontrola zemského zákrytu, SNS-3 user/feeder PHY/MAC referencia, skutočný modelový ISL sieťový hop, presné IPv4/UDP bajty na ISL a kauzálna negatívna kontrola.

**Stále chýba:** overenie, že oba objekty boli v tejto chvíli prevádzkové a navzájom crosslinkované; skutočná Iridium gateway a jej anténa; Certus 100 L-band user PHY/MAC a rádiový rozpočet; reálny ISL rádiový plánovač, priepustnosť a smerovanie; výber lúča, attach/handover a kalibrácia na zhodnom termináli. Konštantných 17 dBi, manuálna ISL hrana a Nemea sa nesmú stať „Iridium výsledkom“. Nasledujúca implementačná brána je pripojiť **96 B `ICB1` vytvorené z RSU prijatého CAM** k tomuto dvojdružicovému referenčnému scenáru a potom oddelene riešiť časový výber a handover.
