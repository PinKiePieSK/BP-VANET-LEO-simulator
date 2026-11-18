# U9: individuálne komunikačné voľby uzlov (30. 10. 2026)

## Rozsah

V technickom profile `combined_advanced` má scenár schémy 3 položku `node_policy`. Každé auto má vlastné `ground` (`all`, `cars`, `off`) a `direct_satellite` (bool). Každá RSU má vlastné `ground` a `satellite_backhaul` (bool). Editor vyberá uzol kliknutím alebo podľa ID v paneli vedľa mapy. Zmeny ukladajú celý presný slovník ID a preflight odmieta chýbajúci alebo nadbytočný uzol. Existujúce scenáre schémy 2 zostávajú spustiteľné.

`all` vysiela ITS-G5 CAM pre autá aj RSU. `cars` vysiela rovnaký broadcast, ale RSU ho zahodí v aplikačnej vrstve pred reportom; nie je to izolácia fyzického RF príjmu. `off` nevysiela GN/BTP CAM a uzol neprijíma pozemné rámce, no aplikačný CAM môže nezávisle obslúžiť priamy satelitný terminál. Vypnutá RSU neprijíma pozemné správy. RSU bez satelitného backhaulu prijíma pozemné CAM, ale označí ich `ignored` a nevytvorí report ani handover. Dormantné OCB/UT inštancie môžu byť v engine stále alokované; nejde o simuláciu ich fyzickej absencie.

Validátor vyžaduje aspoň dve pozemné autá, zdrojové auto v `all`, primárnu a cieľovú RSU s oboma vetvami, aspoň jeden priamy terminál auta a presnú zhodu `direct_cars` s príslušnými voľbami uzlov. Ide o obmedzenie tohto spoločného výskumného profilu. Staršie technické profily nemajú individuálnu politiku. Satelitný úsek je generický DVB model, nie kalibrovaná sieť Starlink.

## Prijímací dôkaz v prenosnom runtime na ploche

- `results/u9_runs/per-node-smoke-2-20261030`: **PASS** úplný scenár, natívny pozemný a satelitný beh, raw paketový audit a manifest. 4 autá, 3 RSU, 4 aktívne satelity. `bg01` s vypnutým ITS-G5 má 7 aplikačných CAM, 0 GN TX a 0 pozemných RX; spolu s `bg00` má priamy satelit 6/6 odpovedí. `bg02` s `cars` nemá RSU príjem. `rsu2` s vypnutým satelitným backhaulom má `ignored` rozhodnutia a 0 reportov. Medzi RSU a cez satelit prešla výstraha k 2 autám pri cieľovej RSU. Checker PASS.
- `results/u9_runs/per-node-rsu-off-20261030`: **PASS** úplný beh s `rsu2` úplne vypnutou. Pozemné aj spoločné natívne RX obsahujú 0 riadkov tejto RSU; `selection.csv` tiež 0. Ostatné vetvy vrátane výstrahy fungovali.
- Starší `results/u9_runs/constellation-starlink-smoke-20261030` v prenosnom runtime a `results/u9_runs/u9_advanced_cli_20261028` v zdrojovom projekte: opätovné overenie **PASS** cez presne hashované historické snapshoty. Nové behy používajú nové zdroje.
- Negatívny preflight odmietol vypnuté pozemné rádio zdrojového auta, vypnutú primárnu RSU a rozpor medzi `direct_cars` a politikou.
- Lokálny prehliadač: výber auta/RSU podľa ID, zmena ich nastavenia, preflight 24 áut/31 RSU a uloženie scenára `per-node-ui-copy` boli úspešné.

Prvý skúšobný beh `per-node-smoke-20261030` zlyhal na starom invariantnom počítaní všetkých vytvorených CAM ako pozemných vysielaní. Kontrola bola opravená, zlyhaný výstup sa nepoužíva ako výsledok.
