# Samovoľný posun stránky pri dočítaní ciest — 13. 11. 2026

Po zosúladení pracovnej verzie používateľ hlásil, že hlavná stránka simulátora pri rolovaní mimo mapy skáče hore. Presné miesto rolovania v používateľskom okne nebolo ešte potvrdené. V oddelenom headless Firefoxe sa pri načítaní reálneho výrezu zachytil súvisiaci samovoľný posun hlavnej stránky zo 700 na 761 px bez ďalšieho pohybu kolieska. Výška stránky sa pri asynchrónnom importe zmenila z 2 804 na 2 865 px; Firefox použil scroll anchoring.

Na koreň hlavnej stránky pribudlo `overflow-anchor:none`, aby zmena výšky mapového obsahu neposúvala polohu stránky. V skúške s aktualizovaným CSS zostala pozícia 700 px počas načítania všetkých 5 684 pracovných ciest; bežné rolovanie nadol mimo mapy ďalej fungovalo. Samostatné posuvníky panelu cesty, jeho zoznamov a paketových udalostí zostávajú. Skúška nepreukazuje, že všetky možné skoky v používateľskom okne mali tú istú príčinu.

Po spresnení, že sa problém prejavuje po obnovení pri rolovaní celej stránky, nasledovala druhá skúška presne týmto postupom: 22 po sebe nasledujúcich pohybov kolieska nad ľavým panelom a potom hlavnou stránkou počas importu. Poloha stránky postupne stúpala od 0 po dolnú hranicu 2 183 px a ani raz sa neznížila; zároveň sa načítalo 5 684 ciest. Načítaný štýl mal `overflow-anchor:none` bez ručného vkladania pravidla do prehliadača.

Aktualizované CSS a verziované HTML sú v zdrojovom projekte, pracovnom runtime aj prenosnom balíku. Bežiaci server vrátil nové bajty oboch súborov, ZIP sa otvoril bez chyby a manifest overil 10 231 súborov a odkazov. Študijná kópia aktívnych zdrojov prešla kontrolou.

## Druhá oprava po spätnej väzbe

Používateľ potvrdil, že aj po prvej oprave sa niekedy na **hlavnej stránke s mapou** pri rolovaní nadol vráti poloha hore. Prvá oprava preto nebola dostatočná. V rozložení boli dva konkurenčné zvislé posuvníky: ľavý panel mal vlastné `overflow:auto` a maximálnu výšku obrazovky, zatiaľ čo celá stránka mala ďalší posuvník. Ľavý panel je teraz súčasťou hlavnej stránky bez vlastného zvislého posuvníka. `simulator.js` pred načítaním scenára nastavuje `history.scrollRestoration='manual'`, aby oneskorené obnovenie polohy po refreshi nezasiahlo do nového rolovania.

V oddelenom prehliadači sa potvrdilo, že ľavý panel už nemá vnútorný posuvník a rolovanie nad ním posúva hlavnú stránku z 0 na 720, 1 440 a 2 068 px bez návratu hore. Toto je kontrola známeho konfliktu posuvníkov; občasný skok v používateľskom Firefoxe zatiaľ nebol priamo zachytený, preto účinok druhej opravy treba sledovať po obnovení používateľskej stránky. Súbory `simulator.css`, `simulator.js` a `simulator.html` sú zosúladené v zdroji, pracovnom runtime a ZIPe; balík a ZIP prešli kontrolou.

## Diagnostika po opakovanom hlásení

Používateľ potvrdil, že skok zostal aj po druhej oprave. Serverový log pri opakovaní neukázal ďalšie GET `/simulator.html`, preto sa stránka vtedy nenačítala znova. Do `simulator.js` bola dočasne pridaná diagnostika kolieska a hlavného posuvníka; zaznamená iba jeho polohu, výšku dokumentu a cieľ rolovania do lokálneho serverového logu. Po reprodukcii sa diagnostika odstráni a opraví sa potvrdená príčina.

## Zachytený skok a úprava kolieska

Po obnovení používateľ skok zopakoval. Diagnostika zachytila návrat hlavného posuvníka z 828 na 0 px pri nezmenenej výške dokumentu 1 867 px; ďalšie prípady z 414, 959 a 552 px. Log neukázal načítanie stránky v okamihu skoku. Pri postupnom rolovaní sa pod kurzor dostala pracovná SVG mapa, ktorej obsluha kolieska volala `preventDefault()` a menila mierku. Glóbus mal podobné ovládanie, MapLibre zachytával koliesko automaticky. Tento súbeh s asynchrónnym rolovaním Firefoxu je pravdepodobná príčina návratu, nie zatiaľ úplne potvrdená interná príčina prehliadača.

Na pracovnej mape a záložnom glóbuse teraz obyčajné koliesko stránku neblokuje. MapLibre glóbus používa `cooperativeGestures`, ktoré pre priblíženie vyžaduje Ctrl. Text v editore zobrazuje nové ovládanie. Dočasná diagnostika ostáva počas jednej používateľskej skúšky a potom sa odstráni.

## Smer vstupu a ochrana polohy

Rozšírený záznam potvrdil, že pred návratom hore prišla len séria kladných `deltaY=138` (koliesko nadol), výška dokumentu zostala 1 922 px a `workarea` nemala vlastný zvislý posun. Pred niektorými skokmi sa zameral horný odkaz Technické parametre; pred inými nie. Nezaznamenalo sa volanie `scrollTo`, `scrollBy` ani `scrollIntoView` z aplikácie. Keď používateľ skutočne otočil koliesko nahor, záznam mal záporné `deltaY=-138`, takže oba prípady sa dajú odlíšiť. Používateľ doplnil, že problém býva najmä hneď po obnovení a po interakcii s panelmi sa často prestane prejavovať.

Pridaná ochrana vráti predchádzajúcu polohu len pri samovoľnom posune hore do 350 ms po kladnom koliesku, stabilnej výške dokumentu a bez súčasného kliku alebo klávesu. Rozsah je obmedzený na štyri zásahy na jednu udalosť kolieska. Účinok v používateľskom Firefoxe ešte treba overiť.

Po skončení diagnostiky sa z aktívneho JavaScriptu odstránilo zapisovanie do lokálneho serverového logu. Zostala len podmienená ochrana polohy. V samostatnom Firefoxe sa synteticky vyvolal návrat z 500 na 0 px po kladnom koliesku a ochrana vrátila 500 px; pri zápornom koliesku zostal úmyselný návrat na 0 px. Používateľský Firefox zatiaľ po tejto poslednej úprave neposkytol potvrdenie účinku.

## Porovnanie s technickou stránkou a izolovaný pokus

Po spätnej väzbe boli pôvodné ovládacie gestá máp obnovené: koliesko na pracovnej mape aj glóbuse znova približuje. Technická stránka v tom istom viditeľnom Firefoxe rolovala plynulo, kým hlavná stránka po rýchlom rolovaní nad ľavým panelom spadla z približne 900 px na 0. Technická stránka používa obyčajný dokumentový posuvník a nenastavuje `history.scrollRestoration`; hlavný editor ho nastavoval na `manual` ako súčasť druhej opravy.

A/B pokus na tej istej hlavnej stránke a v tom istom viditeľnom Firefoxe, so 14 rovnakými udalosťami kolieska nad ľavým panelom: pri `manual` dvakrát po sebe skok približne 909→0 px; pri `auto` dvakrát bez skoku. Výška dokumentu sa zmenila iba o 15 px, čo nevysvetľuje návrat na nulu. Toto priamo spája skok s ručným nastavením histórie v danom reprodukovateľnom postupe. `manual` je zmenené na `auto` a neúčinná dočasná ochrana polohy bola odstránená. Ešte treba overiť novú verziu bez ochrany v používateľskom okne.

## Izolácia hlavného posuvníka

Kontrolné spustenie bez dočasnej ochrany ukázalo skok aj pri `history.scrollRestoration=auto`, takže predchádzajúci záver o tejto voľbe nebol správny. Vlastný viditeľný Firefox opakovane zachytil návrat koreňového posuvníka asi z 924 na 0/26 px. Technická stránka otvorená v rámci mala pri rovnakých 14 pohyboch kolieska monotónny posun z 0 na 1 801 px.

Izolačný pokus na hlavnom editore menil vždy iba jednu skupinu CSS pravidiel. Pôvodný koreňový posuvník skočil v 2/3 pokusov; zmena `overflow-anchor` na koreň/body a odstránenie overflow z pracovnej plochy neboli spoľahlivé (skok aspoň v jednom z troch opakovaní). Keď sa celá hlavná plocha pod hlavičkou stala jediným posuvným kontajnerom a koreň prestal rolovať, 3/3 pokusy prešli bez návratu hore. Nový štýl zodpovedá tomuto odskúšanému rozloženiu. Dočasné zásahy do `history.scrollRestoration` a ochrana cez `window.scrollTo` boli odstránené. Ovládanie kolieskom na oboch mapách je pôvodné.

### Kontrola nasadenej verzie

V samostatnom viditeľnom Firefoxe sa po nasadení presného CSS vykonalo 10 nových načítaní hlavnej stránky a pri každom 14 pohybov kolieska nad ľavým panelom. Koreňový dokument zostal na `scrollY=0`; hlavný panel došiel na približne 909 px a ani v jednej z 10 sérií neklesol o viac než 50 px. Po ďalších 3 s a dočítaní 5 722 ciest sa poloha zmenila iba o 15 px v súlade so zmenou výšky obsahu, nie návratom na začiatok.

Pôvodné koliesko na pracovnej mape stále zmenilo jej `viewBox`. Otvorenie a zavretie Technických parametrov zachovalo polohu hlavného panelu 500 px; ich samostatný rám sa posunul na 690 px. Objektový panel vybranej cesty mal výšku 736 px a obsah 1 121 px; koliesko nad jeho vonkajšou časťou posunulo vlastný posuvník na 386 px bez posunu hlavnej plochy. Balík a ZIP prešli kontrolou manifestu 10 231 súborov a odkazov.

## Neskorý skok po dočítaní a oprava

Používateľ spresnil, že návrat hore sa objaví až neskôr po načítaní. V samostatnom viditeľnom Firefoxe sa po 5–8 s a pri rolovaní len kladným kolieskom skok opakovane zachytil: `.layout.scrollTop` stúpol na 690–964 px a potom spadol na 0–21 px. `scrollHeight` zostal 1 831 px. V okamihu pádu nebol `wheel` so záporným smerom, klik ani mutácia obsahu. Skok sa zopakoval aj v statickej kópii hlavného panelu bez aplikačného JavaScriptu a pôvodného CSS; nejde teda o výpočet scenára, vykreslenie ciest ani volanie `scrollTo` z aplikácie. Presný mechanizmus vo vnútri Firefoxu sa týmto nepotvrdil.

Celostranový iframe sa v dlhšej skúške ukázal ako nespoľahlivý (skok v 2 zo 4 opakovaní), preto nebol nasadený. Ochrana je priamo na hlavnom posuvníku: najviac 800 ms po kladnom koliesku obnoví poslednú dosiahnutú polohu, iba ak poloha klesne o viac než 80 px pri takmer nezmenenej výške obsahu. Firefox pri jednom skoku niekedy nastaví nulu dvakrát, preto je povolených najviac osem korekcií počas jedného kolieska. Záporné koliesko, klik, kláves alebo dotyk ochranu vypnú. Mapa má pôvodné ovládanie kolieskom.

Nasadený `simulator.js` a nový verziovaný odkaz v `simulator.html` prešli šiestimi novými načítaniami vo viditeľnom Firefoxe: pri každom 13 kladných pohybov kolieska nad hlavným panelom a žiadny spätný skok. Opačné koliesko vrátilo panel z 964 na 0 px; pracovná mapa zmenila `viewBox` a Technické parametre sa otvorili a zavreli. Účinok v používateľskom existujúcom okne treba potvrdiť po obnovení stránky.

Následný 20-sekundový pokus odhalil ešte krátky návrat počas presunu fokusu z tlačidla `loadSaved` na pole `scenarioId`, po ktorom pôvodná ochrana obnovila polohu až pri ďalšej `scroll` udalosti. Oprava preto obnovuje polohu už pri `focusin` a predĺžila okno na 800 ms. Tri ďalšie nezávislé načítania s čakaním 20 s pred rolovaním a s 13 kladnými pohybmi kolieska skončili bez návratu hore. Aj keď Firefox znovu presunul fokus na `scenarioId`, vzorky polohy zostali na dolnej hranici 964 px.

## Fokus ľavého panelu a pevné umiestnenie

Používateľ potvrdil, že predošlá ochrana nestačila a pri práci s mapou sama zasahovala do správania. Ochrana v `simulator.js` bola preto úplne odstránená; koliesko mapy sa znovu riadi len pôvodným ovládaním mapy. Izolovaný test bez aplikačného JavaScriptu ukázal, že samotný Firefox počas série kladných `wheel` udalostí presunie fokus na tlačidlo `newReal` bez `pointerdown` či `keydown`. Keď tlačidlo pri rolovaní odišlo nad viditeľnú oblasť, `.layout.scrollTop` klesol napríklad z 672 na 0 px. V používateľskom okne sa súčasne prejavovalo preskakovanie zvýraznených prvkov v ľavom paneli. Podobné presunutie fokusu môže vo Firefoxe vyvolať asynchrónny posun predkov; presný interný mechanizmus tohto konkrétneho prípadu však nie je doložený natívnym profilom Firefoxu.

Ľavý panel je teraz na širšej obrazovke `position:sticky; top:0` v jedinom hlavnom posuvníku. Ovládacie prvky zostávajú viditeľné, aj keď Firefox zmení fokus, takže ich zobrazenie už nemusí ťahať celý hlavný obsah späť hore. Panel má vlastný posuvník iba vtedy, keď je vyšší než dostupná výška okna. Mapa a jej koliesko sa nemenia.

V samostatnom viditeľnom Firefoxe prešlo päť bezprostredných a tri pokusy po 20-sekundovom čakaní. V každom prišlo 13 kladných fyzicky emulovaných pohybov kolieska; hlavná poloha rástla monotónne na približne 964 px. V dvoch oneskorených pokusoch Firefox presunul fokus medzi `loadSaved` a `scenarioId`, ale hlavná poloha neklesla. Po nasadení prichyteného (`sticky`) panelu prvé dve 20-sekundové skúšky prešli, no tretia klesla z približne 964 na 590 px. Toto rozloženie preto nebolo ponechané ako finálne. Používateľ navyše hlásil skok pri práci s mapou po predchádzajúcej ochrane kolieska, ktorá už bola odstránená.

## Prirodzený dokument a pevný ľavý panel

Technické parametre používajú jeden prirodzený dokumentový posuvník. Hlavná stránka predtým rolovala vnorený `.layout` a ľavý panel bol jeho potomkom. Pri presune fokusu na tlačidlo v ľavom paneli preto Firefox mohol posunúť celý `.layout` späť. Nové rozloženie používa prirodzené rolovanie dokumentu, hlavičku ponecháva navrchu a ľavý panel umiestňuje pevne pod ňu mimo posuvnej plochy. Pracovná plocha je explicitne v druhom stĺpci CSS gridu. Bez tohto posledného pravidla mala SVG mapa nulovú šírku; problém bol zachytený kontrolou jej rozmerov a opravený pred dokončením.

Vlastný viditeľný Firefox 159.0.1: tri bežné a tri 20-sekundové pokusy s izolovaným pravidlom, potom tri 20-sekundové pokusy s presným nasadeným CSS po oprave stĺpca. V každom z finálnych troch pokusov 16 kladných pohybov kolieska nad ľavým panelom posunulo koreň dokumentu monotónne z 0 na približne 964 px; panel zostal na `top=76` px. Opačné koliesko znížilo polohu z 964 na 550 px. SVG mapa mala šírku približne 721 px a jej `viewBox` sa po koliesku zmenil zo šírky 4 000 na 3 333 m bez posunu stránky. Technické parametre sa otvorili a zavreli. Vizuálna kontrola vrchnej aj posunutej stránky neukázala prekrývanie panelov.

Aplikácia nezasahuje do kolieska mapy ani neopravuje polohu posuvníka JavaScriptom. Presun fokusu vo Firefoxe môže ďalej zmeniť zvýraznenie poľa alebo tlačidla, ale pevný panel bráni tomu, aby kvôli nemu odskakovala pracovná plocha. Používateľský Firefox treba overiť po načítaní nového CSS; výsledok jeho karty nie je zahrnutý do izolovaných skúšok.

## Záznam používateľského okna a pevná hlavička

Na používateľskom zázname z 13. 11. 2026 o 16:52–16:53 je vidieť hlavný editor pri dolnej časti mapy a potom návrat k horným ovládačom. Farebný rámik fokusu sa v zázname objavil najprv na tlačidle „Nový z reálnej mapy“ a neskôr na odkaze „Technické parametre“ v hornej lište. Odkaz je potom zvýraznený, keď je stránka znovu hore. Záznam potvrdzuje, že posledná úprava pevného ľavého panelu sama o sebe používateľský skok neodstránila; samotný interný dôvod zmeny fokusu vo Firefoxe však z videa nemožno dokázať.

Hlavička bola dovtedy `sticky`, teda stále súčasť posúvaného dokumentu. Na širokej obrazovke je teraz `fixed` a dokument má odsadenie 76 px podľa jej výšky. Ľavý panel je pri dostatočnej výške okna tiež pevný. Pri výške okna do 850 px sa panel vracia do toku dokumentu bez vlastného zvislého posuvníka, aby sa dva posuvníky pri pohybe kolieska nestriedali. Ovládanie mapy v JavaScripte sa nemenilo.

V oddelenom headless Firefoxe 159 pri rozmeroch 1920 × 1080 bola hlavička na `top=0`, panel na `top=76`, mapa široká 747 px a 16 kladných pohybov kolieska posunulo dokument monotónne z 0 na spodných 985 px. Pri 1000 × 650 bol ľavý panel súčasťou dokumentu bez vlastného posunu; rovnakých 16 pohybov posunulo dokument z 0 na 2208 px. Programový presun fokusu na horný odkaz pred úpravou ani po nej v izolovanom teste skok nevyvolal. Nový používateľský pokus zostáva potrebný, lebo test nevynútil samovoľnú zmenu fokusu zachytenú na videu.

Zdroj, pracovný runtime a prenosný balík majú rovnaké bajty HTML/CSS. Bežiaci server vrátil zhodné súbory, študijná kópia 64 aktívnych súborov prešla kontrolou, balíkový manifest overil 10 231 súborov a odkazov a ZIP nemá poškodený záznam. Test aktívneho servera prešiel.
