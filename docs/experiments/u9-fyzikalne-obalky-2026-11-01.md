# U9: prvá fyzikálna obálka troch konštelácií

**Dátum:** 1. 11. 2026. **Rozsah:** Iridium Certus 9770, Globalstar RM200M a Starlink Flat High Performance. Táto fáza vyhodnocuje *možnosť geometrického spojenia* konkrétneho terminálu a jeho verejne uvedené limity. Neodhaduje aktuálne zapnutý lúč, skutočný link margin ani dostupnosť komerčnej služby.

## Implementované

- `tools/u9_physical_coverage.py` definuje tri oddelené produktové profily a počíta z WGS84/SGP4 polôh eleváciu, vzdialenosť, odchýlku od nadiru, geometrický horizont, zorné pole terminálu a útlm vo voľnom priestore v reprezentatívnych stredoch používateľských pásem. Hodnota `link_margin_known=false` výslovne odlišuje vypočítaný útlm od úspešného spojenia. Nulová dolná elevácia pri Iridiu a Globalstare znamená chýbajúci doložený produktový limit, nie zaručený spoj pri horizonte.
- `tools/u9_constellation.py` pri automatickom výbere serving/handover satelitu uplatní verejnú obálku počas celého experimentu. Pre Starlink používame 140° zorné pole zvoleného terminálu a 25° eleváciu z konkrétneho povolenia Gen2; v zmiešanom katalógu nie je generácia každého satelitu samostatne potvrdená. Pre Iridium a Globalstar zostáva hranicou geometrický horizont. Fyzikálny kandidát na mieste experimentu je oddelený od feederového uzla, ktorý môže byť pri inom mieste.
- Nový editorový scenár a automatické prepnutie konštelácie nastavia používateľskú nosnú hypotetického priameho auto–satelitného kanála na príslušné pásmo: Iridium 1,62125 GHz, Globalstar 1,615 GHz, Starlink 14,25 GHz. Poznámka: ostatné parametre dopplerovskej kompenzácie, smerovania, zisku, výkonu a packet PHY nie sú týmto krokom kalibrované na operátora. Staršie uložené scenáre sa menia až pri novom výbere konštelácie v editore.
- Glóbus a obloha rozlišujú satelity nad maskou, fyzikálnych kandidátov a členov modelového paketového podgrafu. Voliteľná žltá obálka satelitu ukazuje maximálnu zemskú oblasť danú horizontom alebo 25° eleváciou, **nie skutočný aktívny beam**. Feederový satelit mimo obálky miesta experimentu je označený zvlášť.
- Pre Globalstar sa používateľská a feederová geometria vyhodnocujú oddelene. Feederu nepripisujeme používateľské pásmo ani zorné pole RM200M. Súčasná viditeľnosť toho istého satelitu z terminálu a proxy brány je iba nutnou geometrickou podmienkou bent-pipe prenosu.

## Prijímacie kontroly

`PYTHONPATH=tools .venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: **122 testov OK**. Zamerané negatívne kontroly: Starlink satelit pri elevácii 20° je mimo obálky a pri 30° v nej; protiľahlá brána Globalstar je pod horizontom; neplatná poloha satelitu sa odmietne. JavaScript súbory prešli `node --check`.

Automatický 30 s orbitálny výber nad uloženým bratislavským scenárom (epochu a OMM treba chápať ako historický snapshot, nie živú prevádzku):

| Profil | Platné objekty v archíve | Kandidáti pri štarte | Uzly paketového podgrafu | Kontrola |
| --- | ---: | ---: | ---: | --- |
| Iridium NEXT / 9770 | 79 | 4 | 3 | serving aj handover vo fyzikálnej obálke |
| Globalstar / RM200M | 30 | 2 | 2 | serving aj handover vo fyzikálnej obálke |
| Starlink / FHP | 10 627 | 69 | 3 | serving aj handover vo fyzikálnej obálke |

Výber a zobrazenie sa overili aj v lokálnom editore na oddelenom porte 8767 pri prepnutí všetkých troch konštelácií. Počty kandidátov sa môžu meniť s UTC, polohou a dĺžkou experimentu; neznačia počet aktívnych beamov ani rádio úspešnosť.

Rovnaké zdroje sú nasadené v pracovnom runtime `~/Desktop/BP-Simulator-Workspace/runtime`; jeho `/api/u9/editor/orbits` vrátil HTTP 200 a Starlink 69 kandidátov/3 paketové uzly. Server na porte 8765 bol po nasadení reštartovaný a hlavné HTML, JS aj nové editorové API vracajú HTTP 200. Prenosný adresár `~/Desktop/BP-Simulator` prešiel kontrolou 11 371 súborov/odkazov; jeho ZIP má SHA-256 `401039e0d821a126448923040e937a9ea21214deceea07c67b43482f9b6db327`. Predchádzajúca verzia zostala zachovaná v `~/Desktop/BP-Simulator-Workspace/package-pre-physical-20261101`.

## Čo ešte bráni vernej fyzikálnej predikcii

1. **Aktívne lúče:** satelitné beam contoury, orientácia a zapínanie v konkrétnej sekunde nie sú v OMM. Pre Iridium je verejne známe usporiadanie 48 lúčov, pre Globalstar viac lúčov, pri Starlinku elektronické smerovanie; ich okamžité priradenie/šírka v lokálnom pokuse zostáva neznáma. Dnešná obálka je preto hornou hranicou možnosti.
2. **Generácia Starlinku:** katalóg zahŕňa viac generácií a verejný výrez nie je spoľahlivým registrom anténneho typu každého objektu. Pravidlo 25° z povolenia Gen2 je deklarovaný scenárový predpoklad, nie potvrdená vlastnosť všetkých 10 627 objektov.
3. **Link budget:** z vypočítaného útlmu zatiaľ nerobíme prijímací prah, pretože chýbajú kompatibilné údaje o uhlovom zisku, EIRP, šume, potrebnom Eb/N0 a implementácii prijímača pre vybraný produkt. Bez toho nemožno tvrdiť, že kandidát naozaj komunikuje.
4. **Lokálne prekážky:** budovy na mape zatiaľ satelitný spoj netienia; výška OSM budov býva neúplná. Terén, stromy a počasie tiež nie sú zapojené do tejto vetvy.
5. **Architektúra paketovej siete:** U9 stále používa generický SNS-3/DVB feederový ISL strom aj pre Globalstar. Jeho fyzikálny bent-pipe predpoklad sa preto nesmie zameniť s výsledkom natívneho packet trace. Túto sieťovú vetvu treba riešiť samostatne.

Podklady: [Iridium 9770](https://www.iridium.com/products/iridium-certus-9770), [FCC Iridium beams](https://docs.fcc.gov/public/attachments/DA-16-875A1.pdf), [Globalstar RM200M certifikát](https://www.globalstar.com/getmedia/a4613a3c-9086-4cdf-b2c2-12cc2c3df169/rm200m-eu-type-certification.pdf), [Globalstar bent-pipe](https://www.globalstar.com/en-us/about/who), [Starlink FHP 140°](https://starlink.com/public-files/specification_sheet_flat_high_performance.pdf), [FCC Gen2](https://docs.fcc.gov/public/attachments/FCC-22-91A1.pdf).
