# Obsah CAM a pôvod údajov

Tento záznam opisuje **aktuálne generované CAM osobných áut**. Ide o modelové údaje zo SUMO, zabalené knižnicou Vanetza do ETSI Release 2 ASN.1 UPER a prenášané v ns-3 cez ITS-G5. Nie sú to merania skutočných vozidiel. RSU CAM negenerujú; CAM prijímajú a podľa scenára môžu cez satelit šíriť aplikačnú výstrahu DENM.

| Pole CAM | Hodnota a pôvod |
| --- | --- |
| `protocolVersion`, `messageId` | Konštanty pripnutej schémy: 2 a 2 (CAM). |
| `stationId` | Jedinečné číslo 1001 + poradie rádiového uzla v pripravenom scenári. Identita auta je v manifeste a CSV, nie v tele CAM ako text. |
| `generationDeltaTime` | UTC okamih vzorky prevedený na čas ITS (TAI milisekundy od 1. 1. 2004), modulo 65 536. Nie čas doručenia. |
| `stationType` | `passengerCar`: všetky autá sú v aktuálnom SUMO dopyte typu osobné auto. |
| `latitude`, `longitude` | Poloha auta z FCD (`x`, `y`) prevedená cez referenčné súradnice scenára na WGS84; 1e−7 stupňa. |
| `altitudeValue` | Výška z geometrického prevodu vzhľadom na referenčnú výšku scenára; centimeter. Nie je to nadmorská výška meraná senzorom ani detailný terénny model. |
| `positionConfidenceEllipse`, `altitudeConfidence` | `unavailable`: simulátor nemodeluje presnosť GNSS ani výškomera. Predchádzajúce umelé tvrdenie o 1 m presnosti bolo odstránené. |
| `headingValue` | Smer zo SUMO FCD (`angle`), desatiny stupňa od severu. `headingConfidence = unavailable`. |
| `speedValue` | Okamžitá rýchlosť zo SUMO FCD (`speed`), centimetre za sekundu. `speedConfidence = unavailable`. |
| `driveDirection` | `forward`: scenár vozidiel používa jazdu vpred po trase SUMO. Cúvanie ako dopravné správanie zatiaľ nemodelujeme. |
| `vehicleLength`, `vehicleWidth` | 5,0 m a 1,8 m, explicitne zadaný typ osobného auta v SUMO dopyte. Je to modelový rozmer typu, nie nameraná veľkosť auta. Indikátor dĺžky označuje model bez prívesu. |
| `longitudinalAcceleration.value` | Okamžité zrýchlenie priamo z FCD pri zapnutom `--fcd-output.acceleration`; desatiny m/s², krajné hodnoty podľa ETSI kódu. Jeho presnosť je `unavailable`. |
| `yawRateValue` | Zmena smeru medzi dvoma 100 ms FCD vzorkami, s rozbalením uhla cez 0°; stotiny °/s. Kladné je proti smeru hodinových ručičiek podľa ETSI. Pri prvej vzorke je `unavailable`. Presnosť je `unavailable`. |
| `curvatureValue` | Uhlová rýchlosť v radiánoch za sekundu delená rýchlosťou v m/s, v jednotkách 1e−4/m. Pri rýchlosti pod 1 m/s alebo bez predchádzajúcej vzorky je `unavailable`; `curvatureCalculationMode` je potom tiež `unavailable`, inak `yawRateUsed`. Presnosť je `unavailable`. |
| `vehicleRole` | `default`: dopyt neobsahuje triedy zásahových ani špeciálnych áut. |
| `exteriorLights` | Z bitov SUMO FCD `signals`: predné svetlá → low beam, diaľkové → high beam, ľavý/pravý blinker, spätný chod, hmlové svetlá. Iné bity ostávajú 0, lebo im aktuálny model nepriradí zodpovedajúci stav. Brzdové svetlo nemá samostatný bit v tejto CAM položke. |
| `pathHistory` | V nízkofrekvenčnom kontajneri je po prvých 0,5 s jeden skutočný predchádzajúci bod z FCD: rozdiel voči aktuálnej polohe a `pathDeltaTime = 50` (50 × 10 ms). Ak sa delta nezmestí do ETSI rozsahu, bod sa vynechá. Na začiatku simulácie je história prázdna. |

Nízkofrekvenčný kontajner ide v prvom CAM a potom najskôr po 500 ms podľa skutočne odoslaných CAM; nie je v každom 100 ms pakete. Polia bez vstupu z modelu alebo senzora (napríklad uhol volantu, poloha v pruhu, stav pedálov, presnosť GNSS) sa zámerne neposielajú. Presnosť pohybových veličín je `unavailable`, pretože nulová chyba trajektórie SUMO nie je model presnosti palubných senzorov.

Správnosť obsahu sa kontroluje z raw UPER bajtov nezávislým dekóderom Vanetza, porovnaním s waypoint CSV a skutočným pozemným i spoločným ns-3/SNS-3 behom. Zmena veľkosti CAM v dôsledku `pathHistory` sa nepripúšťa obísť vypnutím kontroly surových bajtov.

Overenie 4. 11. 2026: `results/simulations/cam-data-ground-verified-20261104` (5 áut, 3 RSU, 92 odoslaných CAM a 233 pozemných príjmov) a `results/simulations/cam-data-iridium-final-20261104` (92 CAM, DENM cez natívny SNS-3 k vzdialeným autám) prešli príkazmi `run` aj `verify`. Dekódovaný CAM auta `car1` pri 0,602 s nesie rýchlosť 9,2 m/s, zrýchlenie 2 m/s², jeden bod histórie spred 0,5 s a kód 4095 pre nedostupnú presnosť polohy. Samostatný test adaptéra s FCD signálmi pre oba blinkre potvrdil masku `0x30` a so záporným zrýchlením potvrdil kód −25.

Podklady: [ETSI EN 302 637-2](https://www.etsi.org/deliver/etsi_en/302600_302699/30263702/01.04.01_60/en_30263702v010401p.pdf), [SUMO FCD](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html), [SUMO signal bits](https://sumo.dlr.de/docs/TraCI/Vehicle_Signalling.html).
