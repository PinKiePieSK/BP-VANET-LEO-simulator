# U9: reálna mapa pri štarte a cache slovenského výrezu

## Príčina a oprava

Nový editor sa po obnovení stránky otváral v prázdnom režime. Podklad reálnej mapy a načítanie ciest sa spustili až po ručnej voľbe „Nový z reálnej mapy“. Pri lokálnom slovenskom výreze sa navyše zakaždým opakoval rozbor XML ciest a budov z PBF, čo trvalo približne minútu. Stavové hlásenie pri ručnej voľbe prepísalo hlásenie o prebiehajúcom načítaní.

Editor sa teraz pri prvom otvorení prepne do reálneho režimu a okamžite zobrazí podklad. Režim prázdneho sveta zostáva dostupný tlačidlom aj voľbou mapy. Hlásenie počas načítania uvádza, že sa pripravujú jazdné cesty a budovy. Kompletný odvodený slovenský výrez sa ukladá do externého pracovného cache ako gzip JSON. Kľúč zahŕňa georeferenciu, rozmery, zapnutie prostredia, pripnutý SHA-256 PBF a obsah troch súvisiacich modulov; PBF sa pred prijatím cache overí.

## Overenie

- V prehliadači na porte 8766 sa po obnovení bez ďalšieho kliknutia vybral reálny režim a podklad Bratislavy bol viditeľný pred dokončením importu. Po dokončení sa zobrazilo 5 779 editovateľných úsekov a 12 977 budov.
- Pri priamom volaní `load()` nad 4 × 4 km bratislavským výrezom trvalo prvé spracovanie 56,02 s, opakované volanie z cache 0,17 s; výsledok mal 5 786 surových úsekov a 12 977 budov. Rozdiel 7 úsekov je filtrovanie krátkych/nevhodných segmentov pri projekcii do editora.
- `PYTHONPATH=tools .venv/bin/python -m unittest tools/test_u9_slovakia_local_pbf.py tools/test_u9_osm_rate_cache.py`: 4 testy OK.
- Prenosný balík na ploche: `verify.py` PASS pre 11 269 súborov a odkazov; ZIP bol vytvorený s SHA-256 `870cb9a85dfa6c1571c7efeef30f1a888d9d6c357229e78dfd24c9d9404be51d`. Aktívny runtime má totožné bajty zmenených súborov.
- Priamy import v aktualizovanom runtime po naplnení cache: 5 786 úsekov, 12 977 budov, celkový proces 0,68 s.

Cache zrýchľuje opakovaný rovnaký výrez. Prvé spracovanie nového výrezu zostáva nákladné; vzdialený mapový podklad OpenFreeMap stále potrebuje pripojenie a funkčné WebGL v prehliadači.
