# Simulátor VANET/LEO

## Účel

Simulátor je pracovný nástroj pre bakalársku prácu o pozemnej komunikácii vozidiel a prenose výstrahy cez LEO sieť. Umožňuje pripraviť scénu, spustiť jeden overiteľný paketový beh a prehrať polohy a doručené pakety. Scenáre a metriky pre samotnú prácu sa budú vyberať s vedúcim; tento balík slúži na ich návrh a kontrolu modelu.

Úplný návod a opis aktuálneho modelu sú v [TECHNICKA-SPRAVA.md](TECHNICKA-SPRAVA.md).

## Spustenie

Na Ubuntu 24.04 x86_64 rozbaľ `BP-Simulator.zip` a v priečinku balíka spusti:

```bash
bash setup.sh
```

Skript nainštaluje potrebné systémové balíky, zostaví Vanetza a ns-3.38/SNS-3 3.38, vykoná krátky pozemný beh a vytvorí ikonu na ploche. Zdroj zostáva v balíku. Scenáre, importy, logy a výsledky sú v samostatnom `BP-Simulator-Workspace` na ploche. Ikona otvorí lokálny editor a po zatvorení jej okna ukončí server.

Pripnutý mapový výrez Slovenska je súčasťou ZIPu, takže inštalácia nezávisí od dostupnosti historického odkazu na Geofabrik. Prvá príprava stále potrebuje prístup k balíkom Ubuntu, ak systémové závislosti nie sú nainštalované. Podporovaná čistá inštalácia je Ubuntu 24.04 x86_64; fungovanie na inej distribúcii alebo na inom Ubuntu zatiaľ nie je overené.

Pre reprodukovateľné behy z terminálu:

```bash
bash run.sh preflight config/simulator-starlink.json
bash run.sh run config/simulator-starlink.json starlink-pokus-1
bash run.sh verify starlink-pokus-1
```

Ďalšie pripravené vstupy: `config/simulator-iridium.json`, `config/simulator-globalstar.json` a pozemný `config/simulator-smoke.json`. Každý nový beh má nový identifikátor. CLI a editor ukladajú výsledky do `BP-Simulator-Workspace/runtime/results/simulations/`.

V zozname **Uložený scenár** sú štyri 60-sekundové porovnávacie scenáre: `realna-d1-pozemna`, `realna-d1-satelit`, `navrh-koridor-pozemna` a `navrh-koridor-satelit`. Každá dvojica má rovnaké cesty, autá, RSU, pohyb a DENM; satelitný variant zapína backhaul dvoch RSU. Prvá dvojica používa skutočné cesty D1 z OSM pri Bratislave, druhá kreslený mestský koridor. Autá, RSU a dopyt sú v oboch prípadoch experimentálne navrhnuté, nie merané. Pri overených príkladoch dostalo DENM na D1 bez satelitu 2 a so satelitom 5 áut; v kreslenom koridore 1 a 3 autá. Ide o výsledky konkrétnych behov, nie všeobecnú dostupnosť siete.

## Jeden dátový tok

```text
editor alebo JSON scenár
  → validácia vstupov
  → SUMO: polohy áut v čase
  → Vanetza: kódovanie CAM a DENM (ASN.1 UPER, GN/BTP)
  → ns-3.38: ITS-G5/WAVE 802.11p OCB
     └─ pri zapnutých RSU termináloch v tom istom ns-3 procese:
        SNS-3 3.38: používateľská DVB linka → brána → cieľová RSU
  → surové PCAP, paketové a RF stopy
  → nezávislý verifier bajtov, časov a manifestu
  → replay
```

Pozemný beh používa iba ns-3. Integrovaný beh používa jeden proces ns-3 so SNS-3. V aktuálnom behu nie je samostatný servisný paketový simulátor ani náhradný prenos pri neúspešnom SNS-3 prenose. Vlastný C++ kód vytvára aplikačné správy, rozhoduje o preposlaní DENM a pridáva deklarované fyzikálne podmienky do ns-3 kanála. Nie je to implementácia modemu operátora.

## Čo možno nastaviť

- Mapa: reálne cesty a budovy z OpenStreetMap alebo ručne kreslené cesty a budovy; šírka a výška výrezu, poloha na Zemi a UTC začiatok.
- Doprava: počet áut, trasy, rýchlosti a smer. Generátor zvýhodňuje hlavné cesty a podľa kategórie cesty vyberá rýchlosť. Ide o syntetickú premávku.
- Uzly: jednotlivým autám možno vypnúť ITS-G5 alebo obmedziť pozemné vysielanie na autá; každá RSU má vlastné pozemné rádio a voliteľný satelitný terminál.
- Správy: CAM vytvára každé auto so zapnutým ITS-G5 podľa zmeny pohybu a periód. Pri každom aute možno naplánovať viac DENM s časom na milisekundu, platnosťou, rozsahom, opakovaním, aktualizáciou a zrušením. Scenár môže mať aj nulový počet DENM. Zdrojová RSU môže prijatý DENM odovzdať cez SNS-3 cieľovej RSU a jej autám. Udalosť zápchy zatiaľ vzniká plánom scenára, nie automatickým rozpoznaním kolóny.
- Satelity: pripnutý orbitálny archív, konštelácia, poloha brány, výšková maska, montáž terminálov, anténne a Dopplerove predpoklady. Automatický paketový výber dnes vytvorí jednu družicu s výhľadom na aktívne RSU a bránu počas celého okna; explicitná pripojená viacdružicová topológia je samostatná voľba vstupu.
- Technická stránka umožňuje meniť parametre typu vozidla v SUMO (zrýchlenie, brzdenie, náhodnosť vodiča, rozmery, odstup, faktor rýchlosti a strop typu pre ručnú mapu). Rozmery auta sa prenesú aj do CAM. Pozemné rádio umožňuje zvoliť 10 MHz kanál 172–184, PHY rýchlosť 3/6/12/24 Mb/s, výkon, šumové číslo, zisky antén a voliteľné tieňovanie v mestskom modeli. Staršie scenáre majú pôvodné predvolené hodnoty.
- Reprodukovateľnosť: seed, číslo behu ns-3 a presné vstupné súbory sú zapísané v manifeste. SUMO, orbitálny výpočet a paketový beh začínajú v spoločnom čase 0; dĺžka replay je dĺžka simulácie.

## Technické parametre

Stránka **Technické parametre** je dostupná z editora bez straty rozpracovaného scenára. Zobrazuje čas, vstupy SUMO, rýchlosti a trasy áut, cestné úseky, nastavenia jednotlivých pozemných rádií a RSU, udalosti DENM, orbitálny vstup, fyzikálne podmienky terminálu a argumenty satelitného paketového modelu. Pri veľkej cestnej sieti sa úseky prezerajú cez vyhľadávanie a stránkovanie. Tlačidlo **Stiahnuť vstupy JSON** uloží scenár, svet a dopravu.

Označenie **Tu** znamená, že hodnotu možno zmeniť na technickej stránke. Zmení sa otvorený návrh v editore, zneplatní sa starý replay a ďalší beh vyžaduje uloženie scenára. **Simulátor** označuje nastavenie, ktoré sa mení v mapovom editore. **Pevné** označuje hodnotu zakódovanú v aktuálnom modeli, nie voľbu experimentu. Diagnostický `link_budget` je zobrazený osobitne: neovláda natívny SNS-3 paketový kanál. Rozhodujúce hodnoty dokončeného pokusu sú v jeho `inputs/`, natívnom manifeste a surových stopách.

## Čo možno pozorovať

Pohyby vozidiel a družíc, lokálny príjem CAM, DCC obmedzenie, pozemné aj satelitné prijatie DENM, paketové stopy po jednotlivých spojeniach, chyby PHY, RF zamietnutia a kontrolu výhľadu. Detail paketu ukazuje surové bajty aj potvrdené polia CAM/DENM a IPv4/UDP. Pri bitovo balenom UPER môže viac významových polí zdieľať tie isté bajty; zobrazenie ich neoznačuje ako samostatné celé bajty.

Verifier porovnáva vstupy, zdroje, binárku, knižnicu SNS-3 a surové stopy. Samotné `PASS` potvrdzuje konzistenciu behu, nie úspešné doručenie; pri pozitívnom scenári treba osobitne skontrolovať prijatie v bráne a cieľových autách.

## Hranice

Tri pomenované konštelácie poskytujú verejne dostupné orbitálne údaje a odlišné fyzikálne profily. Paketový satelitný modem je vo všetkých prípadoch generický DVB model SNS-3. Nie sú známe skutočné operátorské lúče, plánovanie zdrojov, rušenie, prístupové politiky, presné brány ani dostupnosť služby. Grafický glóbus ukazuje celý orbitálny archív, zatiaľ čo paketový beh inštanciuje len zvolenú topológiu. Model preto nepredpovedá skutočnú dostupnosť Starlinku, Iridia ani Globalstaru.

Výšky budov pochádzajú z OSM, ak sú uvedené; inak sa použije zdokumentovaný odhad s nízkym/stredným/vysokým variantom. Syntetické trasy nie sú meraním reálnej premávky. Vozidlá zatiaľ nemenia jazdu po prijatí DENM. Nie je implementovaná autentizácia ETSI ani úplná conformance skúška CAM/DENM a DCC. Priamy terminál auta na družicu v aktuálnej verzii nie je.

## Orientácia v zdroji

- `engine/tools/simulator_cli.py` — aktuálny CLI vstup; validácia, beh a finálny manifest.
- `engine/tools/simulator_satellite_runner.py` — príprava polôh a jedného natívneho WAVE/SNS-3 procesu.
- `engine/tools/simulator_platform.py`, `simulator_coordinates.py`, `simulator_orbits.py`, `simulator_satellite_inputs.py`, `simulator_build.py`, `simulator_packet_trace.py` — zdieľané cesty, súradnice, orbity, vstupy SNS-3, preklad programu a čítanie raw stôp. Tieto funkcie už neimportujeme zo starých sond.
- `engine/tools/simulator_ground_runner.py` — pozemný WAVE proces bez satelitov.
- `engine/tools/simulator_satellite_verifier.py`, `engine/tools/simulator_ground_verifier.py` — overenie surových stôp.
- `engine/src/vanet-leo-network.cc`, `engine/src/vanet-ground-network.cc` — aktuálne C++ paketové enginy.
- `engine/viewer/` — editor, technické parametre a replay.
- `engine/vendor/ns-3.38-ocb-eval/` — pripnutý ns-3.38/SNS-3 3.38; `engine/build/vanetza-v26.06/` — knižnica ITS správ.

Historické experimenty, starý servisný model a ich výsledky zostávajú v pôvodnom vývojovom projekte. Nie sú súčasťou tohto balíka ani aktívneho behu.
