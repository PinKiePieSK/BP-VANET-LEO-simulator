# Grafický návrh scenára v2

## Čo editor skutočne robí

Stránka `/draft-editor.html` vytvára JSON pre [dopravný generátor v2](editable-scenario-v2.md). Vie nakresliť dvojsmerné úseky, pridať vozidlá a RSU, určiť smer a trasu auta, deklarovať schopnosti uzlov a komunikačné zámery. Tlačidlo **Spustiť iba dopravu v SUMO** odošle JSON na `POST /api/draft-runs`; stav číta z `GET /api/draft-runs/<run_id>`. Server vykoná len SUMO dopravný beh a vráti počty vložených a dorazených vozidiel, kolízií a teleportov. Export/import JSON nevyvoláva beh.

`network_execution: "schema_only"` a `flows[].execution: "not_implemented"` sú povinné. Voľba technológie je požadovaná schopnosť, nie zapnutie rádia. Flow pomenúva zámer zdroj–cieľ–technológia–typ správy; nedefinuje obsah paketu, interval vysielania, fyzický kanál, príjemcu broadcastu ani doručenie. Z tejto stránky sa nespúšťa ns-3, Vanetza, SNS-3 ani satelitná služba. Overený dvojvozidlový paketový editor je dostupný cez odkaz **Overený simulátor** na hlavnej stránke.

## Postup v rozhraní

1. Otvor `http://127.0.0.1:8765/draft-editor.html` pri bežiacom `tools/scenario_server.py`.
2. V režime **Dvojsmerná cesta** klikni na body polyčiary a zvoľ **Ukončiť úsek**. Začiatok alebo koniec do 20 m od existujúceho uzla sa k nemu pripojí. Každý úsek má opačnú hranu automaticky, no trasu auta treba zadať smerovane.
3. V režime **Vozidlo na úsek** vyber smer, odchod, počiatočnú rýchlosť, schopnosť, počet 1–50, vzdialenosť ďalších nástupných bodov a časový rozstup; klikni do 50 m od úseku. Poloha kliknutia nastaví prvé `depart_pos_m` od začiatku smerovanej hrany, ďalšie autá vzniknú na tom istom smerovanom úseku s uvedenými rozstupmi. Dávka sa vytvorí atomicky: prekročenie 50 áut, použiteľnej dĺžky úseku alebo trvania behu ju celú odmietne. V režime **Vybrať** možno upraviť trasu ako `seg1:forward,seg2:reverse` a ďalšie polia.
4. Podľa potreby pridaj RSU. Pre čistý V2V scenár môže zostať počet RSU nulový.
5. Pridaj aspoň jeden **komunikačný zámer**. Editor kontroluje ID a deklarovanú schopnosť na oboch koncoch unicastu; broadcast potrebuje aspoň jedného ďalšieho schopného uzla. CAM/DENM povoľuje iba s deklarovanou pozemnou V2X technológiou.
6. Nastav trvanie, krok, semeno a UTC počiatok. Stiahni JSON pre archiváciu alebo stlač **Spustiť iba dopravu v SUMO**. Po dobehnutí pozri súhrn na stránke a `fcd.xml`/manifest v adresári behu na serveri.

Import prijíma v2 JSON do 1 MiB a validuje ho pred nahradením aktuálneho návrhu. Neplatný súbor ponechá rozpracovaný návrh. Dodaný overovací vstup je `data/inputs/editable-road-v2/scenario.json`.

## Limity a význam geometrie

Validátor na tejto 8 GB VM povoľuje 2–100 križovatiek, 1–100 úsekov, 1–50 vozidiel, 0–20 RSU a 1–100 flow záznamov. Úsek potrebuje 2–30 bodov a dĺžku aspoň 30 m; trasa vozidla má 1–30 napojených krokov. Súradnice sú lokálne metre v štvorci 0–2000 m. Tieto medze sú limity vstupnej schémy a rozumnej veľkosti prototypu, nie kapacita skutočnej dopravnej alebo satelitnej siete.

Editor pripája len koncové body k existujúcim križovatkám. Vizuálne kríženie uprostred dvoch úsekov **nevytvorí grafovú križovatku**. Potrebné odbočenie navrhni ako samostatné úseky s rovnakým koncovým uzlom. Kresba sama nekontroluje dopravné pravidlá ani fyzikálnu vierohodnosť; vloženie a pohyb vozidiel ukazuje až FCD zo SUMO.

Počiatočný priestorový alebo časový rozstup dávky je len požiadavka na vstup SUMO. Nezaručuje nekolidujúce vozidlá, rovnakú rýchlosť počas jazdy ani realizovateľné rádiové spojenie. Pri dávke s viac ako jedným autom musí byť nenulový aspoň jeden z rozstupov; SUMO súhrn a FCD zostávajú rozhodujúcou kontrolou priebehu.

## Overenie

```bash
python3 tools/test_editable_scenario_v2.py
python3 tools/editable_scenario_v2.py data/inputs/editable-road-v2/scenario.json --output results/editable_scenario_v2
```

Ručný UI smoke test: jeden úsek, dve autá v opačných smeroch, žiadna RSU, jeden broadcast CAM flow, SUMO tlačidlo. Server vrátil 2 vložené, 2 dorazené, 0 kolízií a 0 teleportov. To overuje dopravný tok editora, nie sieťový prenos. Import dodaného fixture (4 autá, 2 RSU, 3 deklarované flows) a odmietnutie neplatného flow boli kontrolované samostatne.
