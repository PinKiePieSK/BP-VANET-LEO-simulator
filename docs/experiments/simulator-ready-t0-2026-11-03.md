# Spoločný štart v t = 0 — 3. 11. 2026

## Zistenie

Pôvodná schéma 6 vkladala pred experiment pevný 10 s interval. Nebolo doložené, že aktuálny generický SNS-3 3.38 model potrebuje desať sekúnd na prihlásenie terminálu. Pri vytvorení natívnej topológie už hlásil pripojené UT a bránu. Samotný počet uzlov však nie je dôkaz paketovej cesty, preto sa rozhodnutie opiera aj o nové skutočné behy a raw verifier.

## Aktuálny kontrakt

Schéma 7 používa `ready_at_t0_full_duration`. Zvolený UTC čas je priamo časom prvého kroku SUMO, orbitálneho výpočtu aj ns-3/SNS-3. Žiadny skrytý posun pred prvým CAM alebo DENM sa nepripočítava. SUMO dostane iba 0,3 s technickej rezervy za koncom experimentu na úplný zápis poslednej polohy; natívny paketový proces sa zastaví presne pri zvolenej dĺžke.

Orchestrátor dokončí SUMO a kontrolu všetkých áut vo FCD pred prípravou waypointov, potom zvolí orbitálny vstup, vytvorí SNS-3 scenár a spustí natívny proces. Ten pred `Simulator::Run()` vyžaduje prvú polohu každého uzla v t = 0, pozemné rádiá, každé vytvorené RSU UT, PHY/LLC/MAC, členstvo každého UT v jeho vlastnom satelitnom plánovači, feeder s bránou a aplikačné sockety. Kontrola používa veľkosť skutočnej topológie scenára, nie pevný počet RSU alebo družíc. Následne raw verifier vyžaduje riadok `READY_AT_T0` s počtom terminálov a družíc a kontroluje skutočné CAM/DENM bajty a cestu. Pri nepripravenosti beh zlyhá; rádiové tienenie alebo neskorší výpadok zostáva výsledkom pokusu.

Staršie uložené scenáre schémy 6 sa pri načítaní v editore prevedú na schému 7. K technickému `utc_origin` sa pripočíta pôvodných 10 s, takže používateľom zvolený fyzický okamih zostane rovnaký. Historické výsledky sa nemenia; nové výsledky majú nové manifesty.

## Overenie nového kódu

Každý z nasledujúcich výstupov prešiel skutočným `run` a samostatným `verify`. Prvá surová polohová vzorka je pri všetkých v `time_us = 0`.

| Výstup v `results/simulations/` | Topológia a raw výsledok |
| --- | --- |
| `ready-final-ground-20261103` | 5 áut, 3 RSU; 92 CAM TX a 3 prijatia DENM. |
| `ready-final-iridium-20261103` | 3 UT, 1 Iridium NEXT družica; 92 CAM TX, DENM do brány 1, vzdialené autá 2. |
| `ready-final-starlink-20261103` | 3 UT, 1 Starlink družica; rovnaká paketová pozitívna kontrola. |
| `ready-final-globalstar-20261103` | 3 UT, 1 Globalstar družica; rovnaká paketová pozitívna kontrola. |
| `ready-final-two-sat-20261103` | 3 UT, 2 Iridium NEXT družice, ISL a presun každého UT; DENM do brány 1, vzdialené autá 2. Log obsahuje tri `U3_MOVE_US` a tri `U3_ATTACH_CONFIRMED_US`. |
| `ready-final-denm-zero-20261103` | DENM vzniklo presne pri t = 0; brána prijala 1 a vzdialené autá 2. |
| `ready-final-car7-20261103` | Používateľský 25 s reálny výrez: 20 áut, 4 RSU a Starlink. FCD má všetkých 20 áut vrátane `car7` pri 0,00 s; 835 CAM TX. DENM v tomto konkrétnom výreze do brány nedorazilo, čo je priznaný výsledok, nie dôkaz úspešného satelitného spojenia. |

Pri používateľskom výreze bolo príčinou pôvodného zlyhania poradie vkladania vozidiel na tú istú cestu: `car7` čakalo do 12,10 s, hoci malo pri 10,00 s voľnú plánovanú polohu. Generátor teraz pri spoločnom čase odchodu zapíše predné auto pred zadným. Izolovaná SUMO kontrola aj celý 20-autový paketový beh potvrdili `car7` pri t = 0. Pri skutočne nedostatočnej kapacite cesty zostáva kontrola chýbajúceho vozidla aktívna.

Sada aktuálnych Python testov: 35 OK. Študijná komentovaná kópia: 63 aktívnych súborov, `refresh_study_code.py --check` PASS.

## Hranice tvrdenia

`READY_AT_T0` potvrdzuje vytvorenú paketovú infraštruktúru, nie zaručený RF dosah alebo dostupnosť operátorskej služby. Reálny logon Starlink/Iridium/Globalstar sa tým nemodeluje. Súčasný SNS-3 beh používa generický DVB; ak sa neskôr zapne samostatná procedúra logonu, pripravenosť musí zahŕňať aj jej potvrdenie pred aplikáciou. V tomto prípade sa zvolený UTC začiatok nesmie potichu posunúť: nepripravený model má skončiť vysvetlenou chybou.
