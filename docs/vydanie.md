# Proces vydania

Zdrojový kód aplikácie je v Git repozitári. GitHub Release obsahuje archív závislostí, ktorý inštalátor sťahuje podľa pevného názvu vydania, názvu súboru a SHA-256 v `scripts/setup_single_folder.py`. Archív nie je alternatívnym zdrojovým stromom aplikácie.

## Príprava závislostí

1. Overiť piny zdrojov ns-3.38/SNS-3, Vanetza, Python wheels a mapových dát v pracovnom projekte.
2. Zostaviť archív príkazom `python3 scripts/build_dependency_archive.py /cesta/BP-VANET-LEO-dependencies.zip`.
3. Overiť výsledok pomocou `sha256sum` a `unzip -tq`. Hodnotu SHA-256 a názov súboru zapísať do `scripts/setup_single_folder.py`.
4. V čistom Git klone vykonať `scripts/setup_single_folder.py`, štart servera, nový skúšobný beh a `simulator_cli.py verify`. Pri lokálnej skúške možno použiť `BP_SIM_DEPENDENCY_ZIP` na presný ešte nezverejnený archív.

## Zverejnenie

Po úspešnej kontrole odoslať zdrojový commit na `main`, vytvoriť značku a GitHub Release na tomto commite a priložiť presne pomenovaný archív. Popis vydania uvádza podporovanú platformu, obsah archívu, SHA-256, inštalačné príkazy, vykonané overenie a hranice modelu. Po zverejnení zopakovať stiahnutie archívu cez GitHub CLI a skontrolovať SHA-256. Následne vykonať čistú inštaláciu z publikovaného klonu.

Vydanie, na ktoré odkazuje podporovaný inštalátor, musí zostať dostupné. Odstránenie takého vydania preruší nové inštalácie aj vtedy, keď Git commit a značka stále existujú. Staršie commity môžu odkazovať na staršie vydania; pri rozhodnutí o ich odstránení treba výslovne uviesť, že už nepodporujú reprodukovateľnú inštaláciu.
