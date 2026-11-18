# U9: diagnostika Starlinku a oprava zobrazenia — 30. 10. 2026

## Nájdený problém

Starlink sa v editore načítal a propagoval, ale 5 260 bodov na prednej pologuli sa pri hustej skupine kreslilo s polomerom menším ako jeden pixel a priehľadnosťou 0,28. V praxi ostal viditeľný najmä tyrkysový zhluk nad miestom pokusu, takže mapa vyzerala ako poškodená alebo neúplná. Druhá príčina dojmu: po prepnutí konštelácie sa zobrazil **navrhnutý** aktívny podgraf, no do scenára sa až do ďalšieho kliknutia na „Vybrať viditeľné satelity“ nezapísal; preflight správne odmietol spustiť starú konfiguráciu Iridium pod nápisom Starlink.

## Oprava

- Ostatné časovo platné satelity sa pri hustej konštelácii kreslia ako čitateľné jednobodové značky. Nad nimi sa kreslia satelity geometricky viditeľné z miesta pokusu a nakoniec vybraný paketový podgraf. Body z odvrátenej pologule ostávajú skryté až do otočenia glóbusu.
- Zmena konštelácie alebo limitu aktívnych satelitov teraz automaticky vyhodnotí a zapíše nový podgraf, ak geometria a validátor prejdú. Tlačidlo ručného opätovného výberu zostáva dostupné. Text rozlišuje navrhnutý a skutočne aktívny podgraf počas výpočtu.
- Zobrazenie vypnutej vrstvy satelitov už netvrdí, že sú body zakreslené na odvrátenej strane.

## Overenie

- V prehliadači na porte 8765: Starlink z archívu 11 121 položiek načítal 10 627 vekovo platných, z nich 5 260 na prednej pologuli a 5 367 na odvrátenej. Pohybový náhľad sa spustil, posunul čas a zastavil bez chyby. Náhľad neposkytuje dôkaz o dostupnosti skutočnej služby.
- Po zmene Iridium → Starlink sa bez ďalšieho kliknutia zapísal 4-satelitný podgraf; `Overiť aktuálny scenár` prešlo pre 24 áut, 31 RSU a 4 satelity. Spätný prechod Starlink → Globalstar vybral 2 satelity a preflight prešiel. Zmena limitu aktívnych satelitov spustila opätovný výber.
- Existujúci paketový skúšobný beh `constellation-starlink-smoke-20261030` bol znovu otvorený cez runtime API: status PASS, replay HTTP 200 a 275 udalostí. V tomto **staršom konkrétnom behu** 2 autá, 2 RSU a 4 satelity doručili 17/17 RSU reportov cez bránu, 5/5 priamych správ auta a upozornenie obom autám pri druhej RSU. Ide o generický DVB model, proxy bránu a hypotetický ISL strom, nie meranie služby Starlink.
- Syntax `viewer/u9-globe.js` a `viewer/u9-simulator.js` prešla kontrolou Node. Vizuálny dôkaz: `/home/samuel-petrik/Desktop/BP-Simulator-Workspace/u9-starlink-visible-20261030.png`.
- Rovnaké opravené zdroje sú v bežiacom runtime a v obnovenom prenosnom balíku `~/Desktop/BP-Simulator` a `~/Desktop/BP-Simulator.zip`. Kontrola balíka overila 11 520 súborov a odkazov; SHA-256 ZIP je `f7aaa70cbc87c79e197969c3522b8e4d59e106e92b2436edaa6812b85cca51cf`. Predchádzajúci balík bol presunutý do `~/Desktop/BP-Simulator-Workspace/package-prev-starlink-20261030`.

## Zostávajúca hranica

Archivované OMM so šesťmiestnym NORAD ID sú na glóbuse, ale 473 z 10 627 platných položiek Starlinku nie je možné zvoliť do súčasného natívneho TLE/SNS-3 paketového podgrafu. Ostatné satelity sú tiež len geometrickými kandidátmi; do jedného paketového behu sa podľa parametra vyberá obmedzený aktívny podgraf. Aktuálna simulácia nepozná skutočné prideľovanie lúčov ani prevádzkový stav konštelácie. Tieto hranice oprava vizualizácie nemení.
