# Časová závislosť strát v nezávislej mobilnej stope Starlinku

**Stav 22. 10. 2026 UTC.** Táto kontrola pracuje s [verejnými dátami autorov Laniewski, Lanfer a Aschenbruck](https://github.com/sys-uos/Starlink-on-the-Autobahn) z jazdy po nemeckej diaľnici. Merali `ping` z mobilného klienta Flat High Performance ku gateway `100.64.0.1`. Ide o **ICMP round-trip pozorovanie celej tejto trasy**, nie o meranie jednosmerného satelitného úseku, vlastnej RSU, UDP reportu ani PHY. Surový ZIP je licencovaný [CC BY-SA 4.0](https://github.com/sys-uos/Starlink-on-the-Autobahn#license) a zostáva mimo Gitu. Zdroje, terminál, tarifný stav a pôvodné percentily sú v [rozhodnutí o empirických dátach](../decisions/empiricka-kalibracia-konkretnych-sluzieb.md).

## Hypotéza a kontrolný variant

Hypotéza: nezávislý Bernoulliho model s jedinou pravdepodobnosťou straty nezachytí súvislé výpadky v tejto konkrétnej stope. Kontrola je **IID model** fitovaný len na prvých 70 % chronologických sond. Jednoduchý konkurenčný model má dva stavy podľa výsledku predchádzajúcej sondy; pravdepodobnosti `P(loss | success)` a `P(loss | loss)` sa fitujú na tom istom prvom úseku. Posledných 30 % zostáva do vyhodnotenia nedotknutých. Nejde o tvrdenie, že dvojstavový model je fyzikálna príčina strát alebo optimálny model operátora.

## Technická špecifikácia a použitie

`tools/validate_mobile_starlink_loss_memory.py` číta `RTT_Loss.csv` z jediného ZIP člena. Vstup musí mať SHA-256 `88f1905dcc9ac15022039c6d3c6857728e83eaa93cf0ac4eb6dc652c25c1af6e`, cieľ `100.64.0.1`, chronologicky neklesajúci `Time(sec)`, platné 16-bitové `icmp_seq`, `lost=True/False` a pri úspechu konečné nezáporné RTT. Iný ZIP, chybné polia a protirečivé `lost/time` sa odmietnu. Žiadna časová zóna sa z textového `timestamp` neodvodzuje; časové rozdiely sú z relatívneho stĺpca `Time(sec)` v sekundách.

Za susedný pár sa považuje iba `icmp_seq` s inkrementom **1 modulo 65536**. Medzera v sekvencii rozdelí sériu a pár sa nezapočíta do skóre. Tréningové a testovacie páry sa počítajú oddelene; hraničný pár medzi 70 % a 30 % sa nepoužije. Empirické pravdepodobnosti majú Jeffreysovo vyhladenie `(straty + 0,5)/(pozorovania + 1)`, aby vzácny stav nespôsobil nekonečné testovacie logaritmické skóre. Skóre je priemerné negatívne logaritmické skóre na **susedný pozorovaný pár**, v nat/pár; nižšia hodnota je lepšia. Dĺžka série je počet po sebe označených stratených sond; `observed_first_to_last_s` je rozdiel relatívnych časov prvej a poslednej sondy, nie presná dĺžka nedostupnosti medzi nimi.

Výstupom je JSON s hashom vstupu, definíciou trasy, počtami, tréningovými pravdepodobnosťami, testovacími prechodmi, sériami a oboma skóre. Skript nepoužíva žiadne číslo ako parameter ns-3; jeho účelom je odhaliť, akú dynamiku strát by budúca servisná vrstva musela pri **porovnateľnom meranom úseku** rešpektovať. Nevyžaduje novú kompiláciu.

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 tools/mobile_fhp_gateway_rtt_percentiles.py \
  --zip results/calibration_sources/starlink_autobahn/RTT_Loss.zip --download \
  --output results/calibration_sources/starlink_autobahn/summary.json
python3 tools/test_mobile_starlink_loss_memory.py -v
python3 tools/validate_mobile_starlink_loss_memory.py \
  --zip results/calibration_sources/starlink_autobahn/RTT_Loss.zip \
  --output results/calibration_sources/starlink_autobahn/loss_memory_validation.json
```

## Skutočný výsledok a overenie

Zo 379 963 sond pripadlo 265 974 do tréningu a **113 989** do neskoršej testovacej časti. Tréning mal 8 932 označených strát. Jeho IID odhad bol `0,033584`; podmienený odhad po úspechu `0,002980` a po strate `0,913801`. V testovacej časti bolo **1 873/113 989** strát (`1,643 %`) a 113 947 platných susedných párov. Z nich bolo 1 692 prechodov strata→strata, 180 úspech→strata a 179 strata→úspech. Jediný podiel strát teda nepopisuje ich zhlukovanie.

Na zadržanej časti malo IID skóre **0,089354 nat/pár**, podmienený model **0,017307 nat/pár**. Tento rozdiel platí pre túto jednu chronologickú jazdu a túto definíciu sondy; je to prediktívna kontrola proti IID, nie nezávislá validácia pre iný región, dátum, terminál alebo aplikáciu. Zaznamenaných bolo 181 strátových sérií, z toho 32 s aspoň desiatimi po sebe chýbajúcimi odpoveďami. Najdlhšia obsahovala **720 sond**; prvá a posledná mali relatívny rozstup **7,750721 s**. Neznamená to, že každý UDP tok bol po celý tento interval nedostupný.

Tri cielené testy prešli: (1) 16-bitové pretečenie sekvencie zachová sériu, zatiaľ čo medzera ju preruší; (2) testovacia časť ani rozhranie splitu nesmú zmeniť tréningové pravdepodobnosti; (3) zmenený ZIP zlyhá pred čítaním. Produkčný výpočet prešiel na pripnutom ZIP. Neúspešný vstup v teste je zámerná negatívna kontrola, nie zamlčaný experiment. Raw JSON je v `results/calibration_sources/starlink_autobahn/loss_memory_validation.json` (lokálny ignorovaný artefakt); skript ho vie znovu vytvoriť.

## Hranice tvrdenia a ďalšia brána

`lost=True` je výsledok ICMP sondy podľa autorov, nie dôkaz konkrétnej RF príčiny. Sekvenčné medzery môžu znamenať chýbajúce záznamy; rozdelenie sérií na nich je konzervatívne. Časový split v rámci jednej jazdy je slabší než nová meracia kampaň. Dataset nepodporuje kalibráciu 96 B `ICB1` UDP RSU→server, Starlink Performance Gen 3, Iridium ani Globalstar. Rozdiel tréningovej a testovacej miery straty zároveň ukazuje nestacionaritu, takže dokonca tento jednoduchý podmienený model treba chápať len ako diagnostiku.

Ďalšia brána pre operátorské porovnanie je paketový log s **tým istým terminálom, plánom, trasou a aplikáciou**, kalibrácia na jednej kampani a vyhodnotenie na druhej. Potrebné sú identifikátory a veľkosti správ, TX/RX časy a synchronizácia, výhľad/tienenie, ponúkané zaťaženie, duplicity a definícia dostupnosti. Dovtedy je správne ukazovať citlivosť modelu na zhlukovanie strát, nie tvrdiť reálnu PDR alebo dostupnosť vybraného operátora.
