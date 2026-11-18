# Návod na použitie aktuálneho simulátora

Aktívny projekt je `obnova/Bakalarska praca/`. Jediný aktuálny runtime je ns-3.38 so SNS-3 3.38. Tento návod opisuje aktuálny editor a CLI; historické pokusy sú v `docs/experiments/`.

## Editor

Vo vývojovom projekte spusti `.venv/bin/python tools/simulator_server.py --port 8765` a otvor `http://127.0.0.1:8765/simulator.html`. V prenosnom balíku použi `bash setup.sh` a ikonu na ploche, prípadne `bash run.sh server`.

1. Vyber **Nový prázdny návrh** alebo **Nový z reálnej mapy**. Reálna mapa načíta jazdné cesty a budovy z pripnutého slovenského OSM výrezu.
2. Pridaj aspoň dve autá, prípadne RSU. Skontroluj trasy, odchody, rýchlosti, súradnice a dĺžku simulácie. Rozpracovaný návrh zobrazuje editor; výsledok vznikne až po behu.
3. V **Parametroch objektu** nastav každému autu pozemnú komunikáciu a každej RSU pozemné rádio a prípadný satelitný backhaul. CAM zostáva lokálna. DENM môže prejsť cez RSU do vzdialenej oblasti.
4. V **Technických parametroch** nastav typ vozidla, rádio, udalosti DENM, konšteláciu, bránu a predpoklady terminálu. Meniteľná hodnota sa prenesie do ďalšieho scenára; diagnostické zobrazenie samo o sebe neovláda paketový kanál.
5. Klikni **Overiť aktuálny scenár**, **Uložiť nový scenár** a **Spustiť simuláciu**. Výsledok otvor podľa ID v **Prehrávaní paketov**. V stope odlišuj vytvorenie, odoslanie a skutočný príjem paketu.

Štyri pripravené 60-sekundové príklady sú `realna-d1-pozemna`, `realna-d1-satelit`, `navrh-koridor-pozemna` a `navrh-koridor-satelit`. Tvoria dve porovnateľné dvojice s rovnakým pohybom a udalosťou; satelitný variant povoľuje backhaul medzi RSU. Premávka a RSU sú experimentálne navrhnuté.

## Terminál

Z koreňa aktívneho projektu:

```bash
.venv/bin/python tools/simulator_cli.py preflight config/simulator-iridium.json
.venv/bin/python tools/simulator_cli.py run config/simulator-iridium.json results/simulations/moj-pokus
.venv/bin/python tools/simulator_cli.py verify results/simulations/moj-pokus
```

V prenosnom balíku po `setup.sh`:

```bash
bash run.sh preflight config/simulator-iridium.json
bash run.sh run config/simulator-iridium.json moj-pokus
bash run.sh verify moj-pokus
```

Ďalšie aktuálne vstupy sú `config/simulator-smoke.json` (iba zem), `config/simulator-starlink.json` a `config/simulator-globalstar.json`. Každému novému behu daj nové ID. `PASS` pri verifikácii znamená konzistentné vstupy a stopy; doručenie konkrétnej výstrahy musíš overiť podľa etáp `DENM_UPER_TX`, `GATEWAY_DENM_RX` a `DENM_UPER_RX` v cieľovom aute.

## Čo je výsledok a čo je predpoklad

SUMO počíta pohyb. Vanetza kóduje ITS správy a GeoNetworking/BTP. Ns-3 modeluje 802.11p OCB, príjem a straty; SNS-3 v tom istom procese modeluje generický satelitný DVB úsek. Vlastná aplikácia vytvára CAM/DENM, nastavuje politiky uzlov a rozhoduje o premostení DENM. Orbitálny katalóg, budovy a RF parametre sú vstupy modelu, nie meranie konkrétnej komerčnej služby. Uložené surové stopy a manifest sú dôkaz konkrétneho modelového behu.

Úplný výklad všetkých vrstiev, vstupov, rozhodnutí a limitov je v [BP-KOMPLET-NA-2-DNI.md](BP-KOMPLET-NA-2-DNI.md). Prenos a podporované prostredie opisuje [simulator-odovzdanie.md](simulator-odovzdanie.md).
