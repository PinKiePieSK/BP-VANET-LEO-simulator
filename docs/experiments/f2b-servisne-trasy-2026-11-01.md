# F2b — servisne prípustné trasy pre tri LEO služby

**Stav 1. 11. 2026:** Dokončená časová vrstva výberu terminál–satelit–proxy brána, pripojená k novým výsledkom U9 a k informačnému panelu replay. **Natívny paketový engine U9 ju zatiaľ nepoužíva na každý handover.** Tento záznam preto neoznačuje F2 ako dokončenú na paketovej vrstve a neoznačuje žiadnu cestu za skutočné pripojenie operátora.

## Pravidlá podľa verejne dostupnej architektúry

| Služba | Doložené pravidlo | Implementovaná skúšobná cesta | Predpoklad |
| --- | --- | --- | --- |
| Iridium NEXT / Certus 9770 | Satelit má štyri RF crosslinky. | Priamy satelit–brána alebo najviac jeden geometricky priamy ISL k satelitu nad proxy bránou; stupeň použitej proxy siete najviac 4. | Skutočná susednosť, živá cesta a brána nie sú verejné. Jednohopový proxy graf nie je úplný mesh. |
| Globalstar / RM200M | Bent-pipe cez **ten istý** satelit viditeľný terminálu aj bráne, bez ISL. | Len spoločný satelit; bez neho žiadna cesta. | Brána je výslovne proxy, nie potvrdená aktívna brána Globalstar. Výstup nepredstiera IP službu RM200M. |
| Starlink / Performance/FHP | Priama brána; v sieti existujú optické ISL. | Predvolene iba satelit s priamym výhľadom na proxy bránu. Voliteľný jeden optický ISL je samostatný citlivostný predpoklad. | Verejný OMM nehovorí, ktorý satelit má v tej sekunde aktívny laser, beam alebo operátorskú trasu. |

Výber beží pre každú povolenú RSU a každé auto s priamym terminálom nezávisle po 0,5 s od logickej nuly do konca simulácie. Používa rovnaký hashovaný orbitálny archív a surové WGS84 waypointy ako F2. Handover má scenárovo určenú hysterezu 3° a minimálny pobyt 2 s; pri strate cesty sa odpojí hneď. Súbor `tools/u9_dynamic_service.py` zapisuje a opäť prepočítava hashovaný záznam; nový `bp_u9.py run` ho zapisuje pod `physical-timeline.json.service_routes` a `verify` ho nezávisle opätovne prepočíta. Replay ukazuje možnú servisnú cestu a označuje packet trace ako generický SNS-3 model. **Hystereza a proxy trasa nie sú publikovaný algoritmus operátora.**

## Overenie

Výsledky sú v `~/Desktop/BP-Simulator-Workspace/runtime/results/f2b-service-route-20261101/`; tri bežné varianty používajú pôvodné, stále verifikovateľné F2 scenáre a ich waypointy. `python -m unittest tools/test_u9_dynamic_service.py -v`: **5/5 PASS**, vrátane konzervatívneho priestorového filtra. Opätovný prepočet uložených plánov: **PASS**.

| Vstup 6 s | Terminály | Vzorky/terminál | Rôzne satelity v proxy trase | Chýbajúca proxy trasa |
| --- | ---: | ---: | ---: | ---: |
| Iridium | 3 | 13 | 1 | 0 |
| Globalstar | 3 | 13 | 1 | 0 |
| Starlink | 3 | 13 | 1 | 0 |
| Globalstar, brána presunutá do južného Pacifiku | 3 | 13 | 0 | 39 |

V zápornom prípade mal terminál spolu 78 používateľských geometrických kandidátov a brána 195 kandidátov v jednotlivých vzorkách, ale **ani jedna spoločná bent-pipe cesta neexistovala**. To kontroluje význam „rovnaký satelit“, nie iba horizont každého konca osobitne.

Samostatná 120 s skúška s **poslednou polohou 6 s stopy podržanou do konca** ukázala Iridium 1, Globalstar 1 a Starlink 5 satelitov vo vybratých proxy trasách. Starlink vykonal 15 počiatočných/prepínacích udalostí pre tri terminály. Ide o syntetickú skúšku časového plánovača, nie o 120 s dopravnú stopu.

Priestorový filter v plánovači necháva presný výpočet elevácie pre kandidátov a konzervatívne vyraďuje vzdialené satelity. Syntetický test **200 priamych terminálov + 2 RSU, 120 s, 48 682 záznamov** skončil za 21,42 s na tomto stroji; všetky terminály v teste boli zámerne položené na rovnaké miesto, takže nejde o dôkaz výkonu pri geograficky rozptýlenej flotile. Nové integrované 6 s behy `f2b-service-route-iridium-20261101`, `f2b-service-route-globalstar-20261101` a `f2b-service-route-starlink-20261101` prešli `bp_u9.py verify`; historické F2 behy všetkých troch skupín naďalej prechádzajú verifikáciou. Replay API Starlink behu vrátilo HTTP 200, spoločných 6 s a tri plánované terminály. Zmena ID satelitu v uloženom pláne bola pri nezávislom kontrolnom volaní odmietnutá.

### Natívna SNS-3 kontrola Globalstar topológie

Na kópii U9 experimentu sa odstránili všetky ISL. Dva satelity so štyrmi UT na satelite bez brány dali `SAT_OFFERED=30`, `GATEWAY_ACCEPT=0`, `ISL_RX_DEVICE_COUNT=0` ([log](/home/samuel-petrik/Desktop/BP-Simulator-Workspace/runtime/results/u9_noisl_probe_20261101/run.log)). Jediný satelit viditeľný terminálom i bránou dal `SAT_OFFERED=30`, `GATEWAY_ACCEPT=30`, `GW_GRA1_TX=30`, `RSU_GRA1_RX=30`, `ISL_RX_DEVICE_COUNT=0` ([log](/home/samuel-petrik/Desktop/BP-Simulator-Workspace/runtime/results/u9_noisl_positive_20261101e/run.log)). Oba behy použili rovnaký experimentálny binárny súbor (`SHA-256 c6dc98fd98a08e6490bb11f5afeb55509ee2ea99c334f4aedc533da123a11336`). V oboch výsledkových priečinkoch je hashovaný `probe-input-snapshot` vrátane zdrojovej kópie; experimentálny zdroj je uložený aj v `tools/legacy/u9-full-advanced-noisl-probe-20261101.cc`. Táto kontrola dokazuje realizovateľnosť bez-ISL cesty v SNS-3; stále používa **generický DVB/IP modem**, nie produktový RM200M MO/MT stack.

## Hranica v čase F2b a nadväzujúca implementácia

V čase ukončenia F2b aktívny `bp_u9.py run` ešte používal historický malý SNS-3 feederový strom a plánoval jednorazové handovery. **Starý Globalstar packet PASS sa nesmie interpretovať ako cesta siete Globalstar.** Na túto medzeru nadviazal [F2c servisný paketový backend](f2c-servisny-paketovy-backend-2026-11-01.md), ktorý spína modelové pakety na vybranú trasu v spoločnom ns-3 čase. Ani F2c nepozná aktívny beam, modem/MAC, skutočnú bránu a operátorskú latenciu či výpadky.
