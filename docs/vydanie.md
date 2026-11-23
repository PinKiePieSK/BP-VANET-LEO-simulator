# Distribúcia simulátora

Aplikačný kód sa distribuuje cez Git repozitár. GitHub Release poskytuje archív zdrojov runtime a vstupných dát potrebných na zostavenie: ns-3.38/SNS-3 3.38, Vanetza, Python wheels a mapový výrez. Inštalátor `scripts/setup_single_folder.py` určuje značku vydania, názov archívu a jeho SHA-256.

## Podporovaná verzia

Podporovaná je inštalácia z aktuálnej vetvy `main`. Jej inštalátor stiahne pripnutý závislostný archív z GitHub Release a pripraví ho v adresári klonu. Postup inštalácie a aktualizácie je v [návode](instalacia-a-pouzitie.md); obsah a kontrolný súčet archívu sú uvedené pri [aktuálnom vydaní](https://github.com/PinKiePieSK/BP-VANET-LEO-simulator/releases/latest).

Projekt udržiava jeden aktuálny release. Staršie značky Git zostávajú záznamom zdrojových commitov; po odstránení ich závislostných archívov z nich nie je zaručená nová inštalácia. Uložené výsledky naďalej uvádzajú zdroj a vstupy použité pri svojom vzniku.
