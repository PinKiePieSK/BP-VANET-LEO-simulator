# Prejazd cez križovatky OSM — 13. 11. 2026

## Príčina

Editor plánoval trasu na orientovanom grafe podľa spoločného OSM uzla a zakázaných OSM odbočení. Exportér však doteraz zadal `road.con.xml` len pre hrany s explicitným zákazom. Pri ostatných nechal `netconvert` odhadnúť prepojenie podľa geometrie. V aktuálnom 4 km výreze Bratislavy preto editor povoľoval štyri ostré prechody medzi odlišnými OSM cestami, ktoré `netconvert` vynechal. Sú medzi nimi jednosmerné úseky Hummelovej a Blumentálskej. Ďalšie rozdiely boli priame otočenia z hrany na opačný smer toho istého úseku; tie plánovač nemal používať.

## Oprava

- `road.con.xml` teraz pre každú smerovú hranu výslovne uvádza všetky pokračovania na inú cestu v spoločnom grafovom uzle. OSM zákaz odbočenia sa vynechá. Hrana bez povoleného výjazdu dostane záznam bez atribútu `to`.
- Plánovač, ručne editovaná trasa auta, serverový validator a exporter používajú rovnaké pravidlo pre priame otočenie na opačnú hranu toho istého úseku: tento manéver v plánovanej trase nie je povolený.
- Po `netconvert` sa všetky externé spojenia z `road.net.xml` porovnajú s explicitným vstupom. Ak sa rozídu, simulačný beh sa zastaví pred SUMO a uvedie chýbajúce alebo nadbytočné dvojice hrán.
- Panel **Cestné vstupy SUMO** počíta aj zobrazuje všetky exportované spojenia a koncové hrany; technická stránka vysvetľuje ich význam.

## Dôkaz

Čerstvý OSM výrez v pracovnej mape: 5 722 ciest, 4 930 uzlov, 8 778 smerových hrán a 302 pravidiel zakázaného odbočenia. Pred opravou mala výsledná sieť oproti grafu štyri chýbajúce prechody medzi rôznymi cestami. Po oprave obsahuje `road.con.xml` 12 184 povolených spojení a 1 279 záznamov bez výjazdu. `netconvert` 1.25.0 vytvoril presne 12 184 externých spojení: nula chýbajúcich, nula nadbytočných a nula z 302 zakázaných. Štyri skúšobné autá v plnej sieti skutočne prešli príslušnou vstupnou aj výstupnou hranou podľa FCD. Cielený regresný test s ostrou križovatkou, importné OSM testy a kontrola študijnej kópie prešli; štyri uložené ukážkové scenáre prešli validáciou a ručný koridor vytvoril identickú množinu spojení v XML a sieti. Samostatný headless Firefox načítal 5 722 ciest, pri vybranej ceste zobrazil 13 463 záznamov `road.con.xml` (povolené prechody plus koncové hrany), naplánoval prechod cez Hummelovu a odmietol ručne zadaný priamy návrat po tej istej ceste.

## Hranice

Výslovné prechody riešia križovatky, ktorých cesty **už majú spoločný OSM uzol**. Ak sa dve kresby len približujú, križujú v odlišnej výške alebo v OSM chýba spoločný uzol, nevytvára sa automatické spojenie. Taký konkrétny prípad treba posúdiť podľa OSM ID, výškových tagov a reality, aby sa nevytvoril falošný prejazd cez most alebo koľaje. Priame otočenie po tom istom úseku je v plánovaných trasách konzervatívne vylúčené.

Kontrakt explicitných spojení vychádza z [oficiálnej dokumentácie SUMO PlainXML](https://sumo.dlr.de/docs/Networks/PlainXML.html); správanie otočení z [dokumentácie Turnarounds](https://sumo.dlr.de/docs/Simulation/Turnarounds.html).

Prenosný balík na ploche a pracovný runtime obsahujú zhodné zmenené aktívne súbory. `verify.py` overil 10 231 súborov a odkazov, ZIP prešiel kontrolou všetkých záznamov a `PACKAGE-ID` pracovného prostredia zodpovedá novému manifestu. Bežiace používateľské okno nebolo počas výmeny balíka zatvorené; nové skripty sa načítajú po obnovení stránky, serverový proces prevezme aktualizovaný validator pri ďalšom spustení.
