# Návrh kontraktu servisného paketového backendu U9

**Dôvod:** [F2b](../experiments/f2b-servisne-trasy-2026-11-01.md) ukázalo, že natívny SNS-3 3.38 v súčasnom U9 vytvára statické feederové rozhranie a malý ISL strom. Globalstar bez ISL sa dá preniesť iba vtedy, keď je UT aj proxy brána na tom istom satelite. Pre ľubovoľne sa meniace terminály a brány treba nový dátový smerovací mechanizmus; premenovanie existujúceho DVB behu by zakrylo chybu.

## Nemenné pravidlá

1. Jeden spoločný čas udalostí ns-3 pre ITS-G5 CAM, RSU reporty, priamy auto–satelit, bránu, odpoveď a výstrahu z druhej RSU. Interný 10 s nábeh zostáva mimo zobrazovaných 0–T; každý aplikačný paket má pôvodné ID a bajty.
2. Orbitálny plán je dôsledok pripnutého OMM/EOP snapshotu a konkrétneho WGS84 terminálu. Pri odpojení sa paket nesmie tajne presmerovať cez iný satelit; pri zmene sa loguje starý/nový serving, dôvod a čas.
3. Iridium: IP profil Certus 100/9770, užívateľské L-band, publikované 22/88 kb/s ako **maximá**, štyri možné crosslinky na satelit. Skutočná topológia a scheduler sú neznáme; experimentálny proxy graf musí byť oddelený od fyzikálnej kvalifikácie.
4. Globalstar: RM200M je **MO/MT správa**, nie transparentný IP. MO 9–144 B, MT 9–128 B, half-duplex. Cesta vyžaduje ten istý satelit nad terminálom a aktívnou bránou; keď brána nie je potvrdená, použije sa výslovne označená proxy brána. ISL nesmie existovať ani ako záložná cesta. Veľká CAM výstraha sa musí explicitne serializovať do vhodnej MO správy alebo odmietnuť.
5. Starlink: IP profil konkrétne pomenovaného terminálu, Ku užívateľská vetva a jeho 140° FoV; priamy satelit–brána je základný variant. Optický ISL je voliteľný proxy predpoklad, kým nie je doložená dostupnosť pre príslušný satelit a okamih. Aktívny beam ani prevádzkový výkon sa neodvodzujú z OMM.
6. Reálne pokrytie má stavy `geometry`, `terminal_envelope`, `clear_view`, `link_margin_known`, `model_route`, `packet_result`; neznámy prah alebo beam nie je PASS. Produkčné výsledky nesmú zamieňať modelovú možnosť s komerčnou dostupnosťou.

## Výstupy a prijímacia brána

Každý paket nesie `event_id`, pôvodný zdroj a bajty, čas vzniku, servisný profil, serving a trasu v každom hope, bránu, veľkosť a dôvod odmietnutia. Checker rekonštruuje cez archivované vstupy, že hop existoval v čase vyslania aj prijatia a že bol dovolený službou. Po handoveri sa overí opakované doručenie aj zámerný výpadok, nie iba prepis stavu. Replay ukazuje tie isté uzly, časy a bajty ako trace.

Pozitívne a negatívne kontroly: tri služby × RSU→brána→RSU, priame auto→satelit, strata výhľadu, opakovaný handover, neexistujúca brána; osobitne Globalstar bez ISL a nadlimitná MO/MT správa, Iridium prekročený stupeň crosslinkov a Starlink vypnutý optický predpoklad. Výsledok musí byť stabilný pri 200 autách, viacerých RSU a 120 s bez pevného počtu satelitov. Historické generické DVB výsledky zostanú samostatne verifikovateľné.

## Schválená metodická voľba a implementácia

Používateľ 1. 11. 2026 schválil nový ns-3 udalostný backend. `src/u9-service-native.cc` zachováva pozemné ITS-G5/Vanetza a v tom istom `Simulator` čase vyvoláva servisné udalosti priamo z TX auta a RX RSU. `tools/u9_service_native.py` pripína orbitálny plán, rýchlosti, prístupový čas a bajty, zapisuje hashovaný manifest a nezávisle porovnáva reporty so skutočnými natívnymi CAM stopami. `bp_u9.py` ho spúšťa ako primárnu servisnú paketovú vetvu pre nové scenáre s `dynamic_physical` bez závislosti od pevného SNS-3 feederového grafu. Staré generické SNS-3 výsledky zostávajú samostatne overiteľné. Replay zobrazuje servisný trace.

Iridium používa horné produktové rýchlosti 22/88 kb/s; pri Globalstar a Starlink sú predvolené dátové rýchlosti a relay rate **výslovné experimentálne predpoklady**. Nulový prístupový čas je optimistická dolná hranica, nie známa latencia služby. Parametre možno meniť v CLI servisného runnera; ani pri defaultoch sa nepredikuje komerčná dostupnosť. Orbitálny plán dovoľuje najviac jeden ISL proxy; skutočná smerovacia topológia, aktívne lúče, modem/MAC, gateway a prevádzkové výpadky zostávajú neznáme.
