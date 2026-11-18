# Reálna mapa vo Firefoxe — 4. 11. 2026

Používateľ po otvorení simulátora ikonou videl v editore načítané cesty, ale nie reálny mapový podklad. Aktuálny server vracal HTML, MapLibre a cestnú sieť cez HTTP 200. Log samostatného snap Firefoxu obsahoval `glGetGraphicsResetStatus: 0x8253`, následné `WebGL::LoseContext` a opakované zlyhania `mImplicitMakeCurrent`. Príčina prázdneho podkladu je strata WebGL kontextu prehliadača; výpočet cestnej siete a simulačný backend sa pri tejto chybe nezmenili.

Spúšťač `scripts/portable_launch.py` teraz odovzdáva Firefoxu premenné `LIBGL_ALWAYS_SOFTWARE=1`, `MOZ_WEBRENDER_SOFTWARE=1` a `MOZ_X11_EGL=0`. Tým používa programové vykresľovanie WebGL bez závislosti od nestabilnej cesty cez ovládač GPU. Je to nastavenie iba pre prehliadač otvorený ikonou; môže znížiť rýchlosť vykresľovania veľkej mapy.

Overenie: nový samostatný Firefox s týmito premennými načítal režim `real`, glóbus aj cestný podklad. Snímka je v pracovnom prostredí `tests/map-software-gl-20261104.png`; vidno na nej reálne podkladové cesty pod zvýraznenou sieťou 5 779 úsekov. Skúška aktuálneho spúšťača potvrdila HTTP 200, odovzdanie všetkých troch premenných a ukončenie jeho servera po skončení skúšobného prehliadača. Prenosný manifest overil 10 226 súborov/odkazov, ZIP prešiel `testzip()` a starý a nový manifest sa líšia iba v `launch.py`. Pripravenému runtime bol preto aktualizovaný `PACKAGE-ID`; simulačné zdroje ani binárky sa nemenili. Študijná komentovaná kópia prešla `refresh_study_code.py --check`.

Už otvorený Firefox používa pôvodné grafické prostredie. Pre prejavenie opravy treba zavrieť jeho okno a spustiť ikonu znova; rozpracovaný neuložený scenár je potrebné predtým uložiť.
