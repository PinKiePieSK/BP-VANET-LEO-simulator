# Pokus o mobilný satelitný terminál — zatiaľ neúspešný

Stav 22. 10. 2026. Skúšobná vetva `codex/mobile-ut-handover-investigation`; zmeny na tejto vetve nie sú potvrdený experiment. Stabilná vetva `master` zostáva pri prvom úspešnom integrovanom pilote s pevnými UT.

## Hypotéza a zostava

Automobil `car0` získa samostatný palubný satelitný terminál. SUMO lokálne metre sa mapujú na WGS-84 okolo `(20°, 110°)` prvým rádom polomerov krivosti elipsoidu; 120 bodov po 0,5 s sa uložilo do `results/sns3_integrated/mobile_ut/trajectory`. Priamo v SNS-3 vznikol jeden nový `SatTracedMobilityModel` mobilný UT a jeden používateľský uzol. S autom je používateľský uzol spojený predpokladanou bodovou 1 Gb/s linkou s oneskorením 100 µs. Správy mali pokračovať cez DVB model do GW. Tieto súradnice sú zvolené kvôli testovaciemu scenáru, nie ako reálna geografická lokalita cesty.

## Priebeh a dôkazy

| Pokus | Konfigurácia | Pozorovanie |
| --- | --- | --- |
| A | Predvolené `SatHelper::HandoversEnabled=false`; modul handoveru len pre mobilný UT. | `satellites=2 ut_users=6 gw_users=1`. SNS-3 zastavil simuláciu o `4.109614103 s`: `SatNcc::MoveUtBetweenBeams`, „Inconsistent handover state: UT is neither in source nor destination beam; or in both“. |
| B | Podľa upstream `sat-handover-example.cc`: `HandoversEnabled=true`, `NumberClosestSats=2`. | Rovnaká chyba o `5.615275696 s`; beh bol výrazne pomalší. |
| C | Návrat k predvolenému nastaveniu a potlačenie odporúčania handoveru na nájdenom mobilnom UT. | Simulácia sa dokončila, no priamy tok doručil **0/25** paketov a overovací skript ju právom odmietol. Úplný záznam tohto behu sa neskôr zmiešal s paralelne spusteným návratom na hlavný pilot; jeho metriky nie sú použiteľné na kvantitatívny záver. Potlačenie handoveru teda nie je riešením. |

Skript pri každom behu používa ten istý ignorovaný adresár `results/sns3_integrated/`. Pokusy A a B skončili pred začiatkom priamych aplikačných paketov v 27 s. Pokus C odoslal 25 priamych paketov bez vzdialeného príjmu. Pri následnom chybnom súbehu s hlavným pilotom sa výstupy oboch behov zmiešali a `analyze_events.py` zistil duplicitné sekvencie; tento zmiešaný výstup sa nepoužíva. Na izoláciu behov treba jedinečný výstupný adresár alebo skriptový zámok. `core` súbor ani TLE dátový zdroj sa neupravovali. Základný SNS-3 3.48 checkout zostal pripnutý.

## Ďalší izolovaný test

Zostaviť čo najmenší upstream príklad pre presne tento dvojdružicový scenár s jedným mobilným UT a bez SUMO/Wi-Fi. Zaznamenať identitu UT, zdrojového/cieľového satelitu a beam pred volaním `MoveUtBetweenBeams`; preveriť, či v scenári `{43,30}` existuje príslušný plánovač a či UT patrí presne jednému z nich. Až po oprave alebo po voľbe scenára s funkčným handoverom opäť pripojiť vozidlo a posielať pakety. Oprava v SNS-3 by musela mať samostatný patch a regresný test; prosté umlčanie fatálnej kontroly by nezaručilo správnu trasu paketov.

V [otvorenom SNS-3 issue #63](https://github.com/sns3/sns3-satellite/issues/63) je hlásený iný problém s UT handoverom v scenári Telesat: po handoveri sa neobnoví dátová prevádzka. Nie je to dôkaz, že ide o tú istú príčinu ako tu; je to dôvod preveriť túto vlastnosť samostatným testom pred použitím na závery práce.
