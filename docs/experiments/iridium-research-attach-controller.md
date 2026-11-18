# Výskumný attach kontrolér pri zmene geometrického kandidáta

**22. 10. 2026 UTC.** Tento pokus overuje jednu chýbajúcu *kauzálnu podmienku* abstraktného servisného modelu: po zmene najvyššieho geometrického kandidáta sa nemá automaticky odoslať nový paket, kým model explicitne nepotvrdí priradenie. Je to **výskumný kontrolér nad IP proxy**, nie Iridium rádiový attach, beam handover ani inter-satellite handover v SNS-3. Zdrojový audit hranice SNS-3 je v [rozhodnutí](../decisions/sns3-338-handover-scope.md).

## Hypotéza a logika scenára

Pevná bratislavská RSU s hypotetickým satelitným terminálom generuje 300 B syntetický report a pri zmene vybraného objektu by uplink mal závisieť od potvrdenia nového priradenia. Kontrolný variant po úspešnom potvrdení sa porovná s variantom bez potvrdenia. Rozdiely pri 0, 200 a 500 ms skúmajú *citlivosť na predpokladanú dobu riadiaceho procesu*, nie jej odhad pre Iridium. Reporty odoslané počas čakania sa podľa **výslovnej modelovej politiky zahodia pred servisnou frontou**; reálny terminál ich môže bufferovať odlišne.

[Iridium opisuje svoju LEO sieť a používateľské spojenie](https://www.iridium.com/network). [CelesTrak GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php) poskytuje orbitálne elementy pre propagáciu, nie telemetriu attachu, stav lúča či potvrdenie služby. Archív OMM a geografická poloha sú rovnaké ako v [jednosekundovom teste](iridium-one-second-candidate-guard.md). Vyberá sa najvyššia elevácia pri experimentálnej maske 10°; 43253 platí pred konzervatívne blokovaným `[113,114)` s a 43258 po ňom. Pravidlo výberu **nie je deklarovaná politika Iridia**.

## Presná technická špecifikácia

Modul [`certus100-e2e.cc`](../../src/certus100-e2e.cc) prijíma CSV jednosekundového kandidátskeho plánu, `--researchAttach=1`, `--attachDelayMs` v milisekundách, voliteľné `--suppressAttachConfirmation=1` a cestu `--attachTrace`. Na začiatku prvého povoleného intervalu predpokladá priradenie k 43253 (`initial_attachment_assumed`), bez simulácie jeho úvodnej signalizácie. Po novom ID sa zapisuje `attach_requested` a naplánuje `attach_confirmed` po presne nastavenom čase. Negatívna kontrola potvrdenie vynechá. Ak sa kandidát pred potvrdením vráti k aktívnemu ID, čakajúca požiadavka sa zruší; generácia požiadavky zabráni účinku starého časovača. V tomto konkrétnom vstupe také vrátenie nenastane.

Pri prijatí reportu z LAN kontrolér najprv uplatní geometrický interval a potom porovná `activeCatalogId` s vybraným ID. Ak nie sú zhodné, `attach_pending_tx_block` nesie dôvod a paket **nevstúpi** na modelový servisný uplink. Po potvrdení sa používa existujúca kontrola ID pri príchode na server: starý paket čakajúci vo fronte sa stále nemôže vykázať ako doručený cez nové ID. Výstupné CSV obsahuje čas v sekundách od začiatku, udalosť, zdrojové a cieľové katalógové ID a textový dôvod. Vstupný report má 300 B; `event_id` a FNV-1a hash slúžia na overenie identity a bajtov, nie ako Iridium protokol. Modelová servisná rýchlosť 22 kbit/s je maximum produktovej triedy použité ako *envelope*, nie zaručený goodput.

Fyzický úsek v tomto programe zostáva abstraktný ns-3 point-to-point kanál s geometriou riadeným oneskorením. Po `attach_confirmed` sa **neprepína skutočný satelitný PHY, beam, gateway ani trasa**; mení sa len identita v riadiacom stave proxy. Preto výstup nemožno spájať s [integrovanou dvojdružicovou PHY/ISL sondou](two-leo-isl-icb1-e2e.md) ako s jedným potvrdeným handoverom.

## Testy a výsledky

Päť reportov za sekundu znamená 12 kbit/s čistých aplikačných 300 B, pod nastaveným 22 kbit/s servisným stropom; zámerne sa tak neporovnáva zároveň preťaženie frontu. Každý beh používa pevný plán, deterministický začiatok 114,05 s a 1 s lehôtku. Všetky časové varianty majú rovnaký obsah reportov.

| Prípad | Ponuka | Doručené v lehote | Blokované počas attachu | Význam |
| --- | ---: | ---: | ---: | --- |
| 112,5 s pred zmenou, 200 ms | 1 | 1 | 0 | Staré ID 43253 je aktívne. |
| 114,05 s počas čakania, 200 ms | 1 | 0 | 1 | Požiadavka začala v 114,000 s; potvrdenie príde v 114,200 s. |
| 114,25 s po potvrdení, 200 ms | 1 | 1 | 0 | Nové ID 43258 je aktívne. |
| 114,25 s bez potvrdenia | 1 | 0 | 1 | Negatívna kontrola nedovolí falošné doručenie. |
| Päť reportov od 114,05 s; 0 ms | 5 | 5 | 0 | Okamžité hypotetické potvrdenie. |
| Rovnakých päť; 200 ms | 5 | 4 | 1 | Jeden report pred potvrdením. |
| Rovnakých päť; 500 ms | 5 | 2 | 3 | Tri reporty pred potvrdením. |

Účtovná rovnica `doručené + attach_pending_tx_block = ponuka` platí vo všetkých siedmich behoch. [`check_iridium_research_attach.py`](../../tools/check_iridium_research_attach.py) najprv prekompiluje model a kontroluje šesť pôvodných regresných behov. Potom overuje hash pripnutého plánu, presné časy a poradie riadiacich udalostí, ID 43253→43258, úplné 300 B aplikačné bajty a hash tela na všetkých zaznamenaných etapách, dôvod blokovania, terminálne účtovanie a neprítomnosť serverového prijatia pri nepovolenom stave. Surové `*-attach.csv`, paketové `*.csv`, `*-payloads.csv` a manifest sú v ignorovanom `results/iridium_research_attach/`.

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/check_iridium_research_attach.py
```

Prvý ručný štart skončil shell chybou, pretože absolútna cesta obsahovala medzeru a nebola citovaná; po použití relatívnej binárnej cesty boli všetky cielené prípady úspešné. Táto chyba sa netýkala simulovaného prenosu.

## Obmedzenia a ďalšia brána

Výpadok `[113,114)` s je daný rozlíšením geometrického plánu; hodnoty 0/200/500 ms sú výlučne výskumné nastavenia. Služobný výpadok by vyžadoval poznať terminál, reálny beam, anténnu orientáciu, prah pripojenia, scheduler, gateway, riadiace správy a retry/buffer politiku. Z výsledkov preto nemožno odvodiť dostupnosť, latenciu ani efektívnosť Iridia, nieto poradie Starlink/Iridium/Globalstar. Pred takým porovnaním treba v jednej PHY simulácii vytvoriť dva skutočné user linky, prepínať príslušné satelitné/beam/route objekty, sledovať kontrolnú signalizáciu a overiť ich parametre alebo ich explicitne klasifikovať ako intervaly hypotéz.
