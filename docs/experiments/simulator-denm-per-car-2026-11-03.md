# DENM plánované pre jednotlivé autá — 3. 11. 2026

## Kontrakt

V editore má každé auto vlastný zoznam udalostí DENM. Jedna udalosť určuje zdrojové auto, čas od začiatku simulácie s rozlíšením 1 ms, číslo výstrahy, operáciu `new`/`update`/`cancel`, platnosť, polomer a opakovanie. Môže vzniknúť viac udalostí od viacerých áut alebo žiadna. Uložený scenár určuje vznik výstrahy; model zatiaľ sám nedetekuje zápchu. Identita výstrahy pozostáva zo zdrojového auta a čísla výstrahy, preto rovnaké číslo smú použiť dve autá.

Vanetza zakóduje DENM ako ASN.1 UPER a GN/BTP geografický broadcast. Pozemný prenos uskutočňuje ns-3 WAVE/OCB. Ak vybraná zdrojová RSU paket prijme, môže ho poslať cez generický SNS-3 DVB kanál do brány a vybranej vzdialenej RSU; tá vytvorí odvodený DENM so svojou identitou stanice a vyšle ho autám cez GN/BTP. Nie každé prijatie automaticky zaručuje satelitné doručenie. Pre daný beh je v scenári určená jedna zdrojová a jedna cieľová RSU.

## Skutočné behy

Každý riadok prešiel samostatným `run` aj následným `verify` proti surovým stopám a manifestu. Po poslednej zmene kontrolného kódu boli behy vytvorené znova, aby hash zdrojov súhlasil.

| Výsledok v `results/simulations/` | Dôkaz |
| --- | --- |
| `denm-per-car-final-ground-20261103` | 5 áut, 3 RSU, 4 udalosti od 3 áut, 17 pozemných prijatí; PASS. |
| `denm-per-car-final-iridium-20261103` | Iridium NEXT, 4 udalosti, 4 prijatia v bráne a 6 prijatí vzdialenými autami; PASS. |
| `denm-per-car-final-starlink-20261103` | Starlink, 4 udalosti, 4 prijatia v bráne a 7 prijatí vzdialenými autami; PASS. |
| `denm-per-car-final-globalstar-20261103` | Globalstar, 4 udalosti, 4 prijatia v bráne a 7 prijatí vzdialenými autami; PASS. |
| `denm-per-car-final-none-20261103` | Pozemný beh bez DENM; 92 CAM TX a 0 DENM; PASS. |
| `denm-per-car-final-iridium-none-20261103` | Natívny SNS-3 beh bez DENM; 92 CAM TX a 0 DENM; PASS. |
| `denm-ui-final-20261103` | Scenár uložený priamo z editora: 3 autá, 3 DENM TX a 78 CAM TX; PASS. Náhodné autá boli mimo dosahu, preto 0 DENM RX je správne pozorovaný výsledok. |

Samostatná čistá inštalácia finálneho prenosného balíka na Ubuntu prešla kompiláciou Vanetza a ns-3/SNS-3, jeho pozemný `portable-smoke-20261103180616` prešiel následným `verify`. Z tohto nového runtime sa spustil aj `portable-denm-per-car-iridium-20261103`: štyri udalosti od troch áut, štyri prijatia pri bráne a šesť prijatí vzdialenými autami, nezávislý `verify` PASS. Kontrola manifestu balíka a integrity ZIP: PASS. Skratka na ploche v skúške otvorila server a po skončení okna ho ukončila.

Druhý zdroj v multi-auto pokuse vyslal novú výstrahu v `t = 1,234 s`. Verifier vyžaduje zhodu zdrojovej stanice, času a dekódovaných DENM polí, poradia aktualizácií a surových bajtov. Kontroluje aj paketovú cestu cez zdrojovú RSU, bránu, cieľovú RSU a obnovený pozemný broadcast. Prípad bez udalostí potvrdzuje, že systém nevytvára DENM implicitne.

## Hranice

Pomenované konštelácie určujú orbitálne vstupy a fyzikálne profily, nie skutočný modem operátora; paketový model je pri všetkých troch generický DVB v SNS-3. Výstrahy v týchto testoch boli plánované scenárom a nevyvolali zmenu jazdy vozidiel. Výsledky nepreukazujú pravdepodobnosť doručenia komerčnej služby.
