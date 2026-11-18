# Audit vstupných parametrov a fyzikálnych tvrdení — 4. 11. 2026

## Opravené

| Oblasť | Zmena | Overenie |
| --- | --- | --- |
| DENM poloha a kvalita | Elipsa neistoty je `unavailable` (ETSI kód 4095), orientácia neistoty je nedostupná a `informationQuality=0`. Súradnice udalosti sú stále zo SUMO, ale nepredstierame meranú 1 m presnosť. | Verifier číta kódy z raw ASN.1 bajtov v pozemnom aj spoločnom behu. |
| GeoNetworking | `PositionFix` používa hranicu PAI z MIB, takže bez modelu chyby GNSS nevydáva indikátor presnej polohy. | Verifier kontroluje PAI bit raw GN/BTP/CAM rámca. |
| Terén | Výšková matica sa skladá podľa uloženého počtu riadkov a stĺpcov, nie ako pevné 75 × 75. | Test s mriežkou 108 × 142, 5 testov lokálneho prostredia prešlo. |
| Výška RSU | Pozemná anténa a satelitný terminál tej istej RSU majú v oboch C++ enginoch `max(5 m, výška strechy + 2 m)` pri OSM budove. Vozidlo zostáva 1,5 m. | Oba natívne enginy sa zostavili a vykonali; výška je tá istá pri umiestnení Wi-Fi uzla i registrácii satelitného terminálu. |
| SUMO typ vozidla | Zrýchlenie, brzdenie, náhodnosť vodiča, dĺžka, šírka, minimálny odstup, faktor rýchlosti a maximálna rýchlosť typu pre ručnú mapu sú voliteľné parametre sveta. Rozmery sa zapisujú aj do CAM. | Skutočný SUMO súbor `vehicles.rou.xml` obsahuje 2,7/4,1/0,1/4,3/1,7/1,8/1,1; CAM waypoint má 43/17 dm. |
| ITS-G5 PHY | Scenár nastavuje 10 MHz kanál 172–184, sadzbu 3/6/12/24 Mb/s, výkon, šumové číslo, TX/RX zisk a voliteľné mestské tieňovanie. Frekvencia sa odvodí z kanála aj pre útlmový model. Friis s tieňovaním sa odmieta. | Kanál 178 → 5,890 GHz, 3 Mb/s, +2/−1 dBi a tieňovanie zapnuté prešli pozemným aj spoločným SNS-3 behom; verifier porovná natívny `OCB_CONFIG` log so scenárom. |
| Neznámy satelitný terminál | User-link gate už nevráti automaticky `true` pre neznámy mobility objekt; vyhodí chybu topológie. | Spoločný beh s troma RSU terminálmi a raw obojsmernou SNS-3 stopou prešiel. |

## Skutočné behy

- [Pozemný beh](../../results/simulations/audit-parameters-channel-ground-20261104): 5 áut, 3 RSU, 6 s; 98 CAM TX, 398 RX a 7 príjmov DENM. `bp_u9.py verify`: PASS.
- [Spoločný Iridium NEXT beh](../../results/simulations/audit-parameters-channel-iridium-final-20261104): ten istý typ vozidla a pozemné PHY, jedna vybraná družica v generickom SNS-3 DVB modeli; 98 CAM TX, DENM prijatá bránou a jedným vzdialeným autom. `bp_u9.py verify`: PASS. Ide o modelovú paketovú cestu, nie meranie služby Iridium.
- `PYTHONPATH=tools .venv/bin/python -m unittest discover -s tools -p test_u9_local_environment.py`: 5/5 PASS.
- Syntax troch upravených súborov JavaScriptu prešla kontrolou parserom Node. Študijná kópia všetkých 64 aktívnych zdrojov: `refresh_study_code.py --check` PASS.
- Negatívny preflight odmietol neplatný kanál 179, rýchlosť 5 Mb/s, text namiesto prepínača tieňovania a nulovú dĺžku auta.
- Po zabalení prešiel samostatný prenosný `run.sh run` a `run.sh verify` na predvolenom pozemnom scenári v pracovnom runtime; výsledok je mimo zdrojového ZIPu.

Staršie scenáre bez nových položiek používajú predvolené hodnoty: kanál 180, 6 Mb/s, 0 dBi, tieňovanie vypnuté a pôvodný SUMO typ. Testovací svet a scenár sú v `data/inputs/audit-parameters-20261104-world.json` a `config/audit-parameters-20261104.json`; satelitný variant je v `config/audit-parameters-iridium-20261104.json`. Tieto auditné vstupy nie sú súčasťou prenosného balíka.

## Zostávajúce hranice, ktoré sa nedajú pravdivo nahradiť číslom

- SNS-3 používa **diagnostickú konštantnú mapu zisku lúča**, nie publikované živé lúče a skutočné smerovanie Starlink, Iridium NEXT alebo Globalstar. Zisk je parameter citlivosti. Bez operátorskej mapy alebo merania sa nedá označiť za skutočné pokrytie služby.
- `SatChannel` aplikuje vlastnú výškovú masku na user aj feeder, no projektová kontrola montáže, Dopplera a miestnych budov je pripojená iba k **user linke RSU**. Hypotetická brána je mimo miestneho mapového výrezu; nemáme jej budovy ani anténny profil. Feeder preto nesmie byť interpretovaný ako plne fyzikálne overená brána. Návrat `true` pre neznámu user-link RSU bol odstránený.
- Automatický výber paketovej topológie stále potrebuje jednu družicu, ktorá drží všetky aktívne RSU a hypotetickú bránu nad maskou počas celého okna. Ak nie je, spustenie sa odmietne. Viacdružicový handover je overený v explicitných topológiách, nie ako neobmedzené automatické plánovanie celej konštelácie.
- RSU s vypnutým satelitným režimom má v aktuálnej natívnej topológii vytvorený UT/LAN uzol, ale aplikačné odosielanie a doručovanie sa filtruje politikou. Odstránenie takého terminálu vyžaduje rozdelenie pozemného zoznamu RSU od zoznamu SNS-3 terminálov v C++ sieťovej inštalácii a smerovaní; v tomto audite nebolo označené za hotové.
