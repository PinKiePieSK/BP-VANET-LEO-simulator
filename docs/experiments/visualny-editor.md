# Vizuálny editor scenárov — prvý funkčný rez (2026-10-22)

> **Revízia geografie:** Pôvodných osem satelitných doručení nižšie pochádza zo scenára, v ktorom bola prijímajúca brána pod geometrickým horizontom. Sú to diagnostické paketové čísla, nie fyzikálne overený výsledok. Opravený referenčný beh `20261022T133000Zgeo4` už prešiel kontrolou všetkých ôsmich doručených horizontových trás. V editore je aj oddelený náhľad časovo označených GP/OMM dráh. Presné výsledky, obmedzenia a postup sú v [geografickom denníku](geografia-a-orbity.md); odseky nižšie opisujú starší prvý rez editora.

## Účel a hranice

Lokálna stránka na `http://127.0.0.1:8765` umožňuje nakresliť **jednu obojsmernú lomenú cestu**, umiestniť jednu RSU, určiť smer a počiatočnú rýchlosť **dvoch áut** jednotlivo alebo spoločne. Simulácia sa spúšťa ako samostatný proces na pozadí. Po dokončení sa prehráva uložených 60 sekúnd simulovaného času v slučke pri 0,25× až 8× rýchlosti. Prehrávanie je vizualizácia dokončeného behu, nie riadenie bežiaceho simulátora. Prehliadač interpoluje polohy iba na zobrazenie medzi skutočnými vzorkami. Časovo synchronizované terminály uzlov zahŕňajú aj SAT0/SAT1 PHY udalosti odvodené z overených `PacketTrace.log` trás. Ich úplné rádiové rámce nie sú v UI dekódované; po kliknutí na PHY udalosť sa zobrazí priradený **aplikačný** obsah podľa UID.

Výber siete je momentálne obmedzený na overenú referenčnú dvojicu LEO v SNS-3. Starlink, Iridium a Globalstar sú viditeľné ako budúce ciele, ale ich položky sú deaktivované. Historická konštelácia SNS-3 sa nevydáva za dnešné orbitálne dráhy ani proprietárne protokoly operátorov. Priamy spoj vozidlo–satelit zatiaľ nie je implementovaný. Fyzická poloha lokálnej cestnej mapy nie je zladená so zemepisnou polohou satelitného terminálu; satelitná mapa má samostatnú projekciu. Z týchto dát sa **nesmie** vyvodzovať aktuálna viditeľnosť satelitu nad cestou.

## Reprodukcia

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 tools/scenario_server.py --port 8765
```

Otvor `http://127.0.0.1:8765`. Tlačidlo **Spustiť simuláciu** uloží JSON scenára a spustí `tools/scenario_run.py`. Pre každý beh vznikne samostatný adresár v `results/visual_runs/<run-id>/`. Tam sú `scenario.json`, vstupy a FCD SUMO, waypointy, aplikácie a paketové stopy ns-3, PCAP, `PacketTrace.log` SNS-3, súhrn, `verification.json`, `replay.json`, logy, kontrolné súčty vstupov a `reproduce-command.txt`. Konkrétny beh opakuj príkazom zapísaným v jeho `reproduce-command.txt`; pred opakovaním vytvor nový identifikátor alebo archivuj pôvodné výsledky, pretože SNS-3 výstup v rovnakom adresári prepisuje. Závislosti a seed 42 sú pripnuté a overené v skripte.

## Tok dát a moduly

| Modul | Algoritmus a vstup | Výstup a jednotky | Obmedzenie |
|---|---|---|---|
| `viewer/app.js` | SVG editor lokálnych súradníc, dva smery vozidiel; interpolácia pri prehrávaní | JSON scenára; 2D poloha v m; čas v s | Len jedna cesta, 2 autá, 1 RSU |
| `tools/scenario_server.py` | Validuje HTTP požiadavku, spúšťa samostatný proces, hlási stav | ID behu a stav; iba localhost | Žiadny shell z webu; po reštarte servera sa rozbehnutý proces zobrazuje ako „unknown“, výsledky ostanú |
| `tools/scenario_run.py` | Z lomenej čiary vytvorí obojsmerné hrany SUMO, načíta FCD do ns-3, spustí analýzu a kontrolu | XML, CSV, PCAP, SNS log, JSON; m/s, s | SUMO autá sledujú jednu trasu, maximálne 25 m/s; priebeh rýchlosti určuje SUMO |
| `src/vanet-sns3.cc` | Skutočné UDP pakety cez 802.11p Adhoc MAC, RSU→UT Ethernet, SNS-3 DVB, ISL, brána; zaznamenáva úplné aplikačné bajty a zemepisnú polohu satelitov | udalosti/hopy v s, obsah 300 B hex, polohy satelitov v °/m | Bez proprietárnych rámcov, plánovačov a priameho satelitného terminálu v aute |
| `tools/build_replay.py` | Spojí SUMO vzorky, ns-3 udalosti a SNS-3 vzorky | `replay.json`; sekundové časové značky, metre, stupne | Zobrazenie nie je dodatočná fyzikálna simulácia |

Kritérium overenia: `verification.json` musí potvrdiť konzistentnosť všetkých odoslaných paketov; pri doručených satelitných paketoch aj skutočný priechod cez ISL. Nulové doručenie je platný výsledok pre zle umiestnenú RSU, nie zlyhanie spustenia. Sledované sú PDR, jednosmerné oneskorenie, jitter a dostupnosť v päťsekundových oknách podľa `tools/analyze_events.py`. Úplný 300 B aplikačný paket sa porovnáva na aplikačných hopoch a kontroluje sa aj jeho hexadecimálny záznam; voľbou riadku v konzole je obsah viditeľný. Pre úroveň rádiových rámcov slúži PCAP a SNS-3 `PacketTrace.log`.

## Hypotéza a reálny význam prvého behu

Po zmene geometrie cesty alebo smeru vozidiel sa zmení vzdialenosť voči RSU a vozidlu 1, teda aj počet doručených lokálnych paketov. Kontrolou je nemenená cesta so smerom oboch áut dopredu. Súčasný model nesimuluje zatienenie budov, prevádzkovú sieť operátora ani anténu auta pre priamy satelitný uplink. Hypotézu je možné testovať rozdielom medzi dvoma uloženými behmi s rovnakým seedom, pričom zmenený vstup musí byť explicitne uvedený v `scenario.json`.

### Skutočne vykonané behy

Pri prvom nakreslenom scenári s RSU na `(1000,730)` m sa simulácia dopočítala, ale V2I ani satelitný tok nedoručili paket: 0/25, zatiaľ čo V2V doručilo 50/50. RSU bola mimo dosahu na začiatku V2I prevádzky; neskorší prechod vozidla bližšie k RSU neobnovil lokálne doručenie v danom nastavení. Prvý spúšťací skript mylne označil nulové doručenie za chybu overenia. Tento pokus a oprava sú zachované v `results/visual_runs/20261022T000001Zbbbbbbbb/`; ďalší rovnaký beh v `20261022T115642Z5224cfdf/` bol vyvolaný cez webové rozhranie a tiež bol po oprave overovača spracovaný na prehrateľný výsledok. Pôvodné `failed.txt` sa uchováva spolu s poznámkou o obnove.

Po posunutí RSU na `(800,675)` m prešiel celý reťazec pod `results/visual_runs/20261022T000002Zcccccccc/` (exit 0). Pri 60 s, SUMO seed 42, ns-3 seed 42/run 1 bolo V2V 50/50, V2I 8/25 a vzdialený tok 8/25. Priemerné jednosmerné oneskorenie vzdialeného toku bolo 117,930 ms, jitter podľa definície analyzátora 0,805 ms a dostupnosť v päťsekundových oknách 0,4. Overenie potvrdilo identitu celého 300 B aplikačného paketu vo všetkých hopoch, hexadecimálny záznam odoslaných paketov a pre všetkých osem doručených vzdialených paketov postup UT→SAT1→SAT0→GW vrátane ISL. To sú výsledky jedného syntetického behu, nie charakteristika komerčnej služby.

Po commite `dea1e4e` bol ten istý scenár spustený cez HTTP rozhranie ešte raz v `results/visual_runs/20261022T120812Z50c64131/`. Skončil stavom `complete`; metriky aj osem overených ISL trás sú zhodné. Sedem SHA-256 vstupov v `input-sha256.json` sa po dokončení presne zhodovalo s aktuálnymi zdrojmi. Skript teraz zapisuje hash vstupov pred behom a zmenu zdrojov počas behu považuje za chybu reprodukovateľnosti.

Samostatný päťsekundový SUMO test s opačnými smermi (`/tmp/vanet-reverse-test/`) potvrdil klesajúce `x` vozidla `car0` na spätnej hrane a rastúce `x` vozidla `car1` na prednej hrane. V prehliadači bolo overené načítanie výsledku, posun na koniec časovej osi, rýchlosť 4×, návrat na začiatok pri zapnutej slučke, výpis úplného 300 B paketu a otvorenie časovo synchronizovaného terminálu uzla. Test zamietnutia nepodporovaného profilu Starlink vrátil HTTP 400 s vysvetlením.

## Čo doplniť po overení

Sieť ciest s križovatkami a skupinami vozidiel, geografické previazenie cestnej oblasti so satelitným terminálom, časovo aktuálne ephemeridy s uloženým epochom, kontrola viditeľnosti a rádiového rozpočtu, modely rozhraní jednotlivých operátorov iba tam, kde sú dostatočné verejné údaje. Pred zavedením priameho auto–satelitného spojenia treba určiť konkrétny terminál, pásmo, anténu a protokol.
