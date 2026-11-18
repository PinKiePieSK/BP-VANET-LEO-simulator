# V4: kontrakt fyzikálnej a frontovej citlivosti generickej SNS-3 referencie

**Jediný runtime:** projektový ns-3.38/SNS-3 3.38. V3 a historické P0–P6 zdroje/výsledky sa nemenia. V4 má vlastný `src/v4-leo-reference.cc`, JSON, runner, checker a nový menný priestor výsledku.

## Čo V4 vykonáva

V3 kvalifikuje dve archivované obežné dráhy, jedno UT, syntetický všesmerový user/feeder lúč a proxy gateway. V4 zachová túto výslovne výskumnú geometriu. Handover SAT0→SAT1 a obojsmerná sonda prebehnú pred 19 s. O 19 s sa nastaví fyzikálna citlivosť; šesť ICB1 reportov vznikne až z dekódovaných CAM medzi 20 a 22,5 s. Pri `burst=true` sa **tie isté skutočné reporty** podržia vo frontovej aplikačnej vrstve a o 23 s pošlú ako dávka. Na SAT1→SAT0 sa pre ICB1 meria skutočný `DropTailQueue<Packet>` cez `Enqueue`, `Dequeue`, `DropBeforeEnqueue`. Opačný smer ISL ostáva 1 Gbit/s/100 paketov kvôli časovaniu riadiacich správ SNS-3. Čas sondy, fáza aplikácie, fyzikálny príjem a obidva smery ISL sú oddelené v raw stope.

Na SAT1→SAT0 sa zároveň zapisujú `Enqueue/Dequeue/DropBeforeEnqueue` pre všetky **ne-ICB1** rámce ako `OTHER`. To umožňuje odlíšiť aplikačné straty od ďalšej prevádzky na zdieľanej fronte; neznáme bajty automaticky nepomenúvame ako protokol konkrétneho operátora.

Zmena rýchlosti oboch smerov na 1 alebo 10 kbit/s spôsobila ešte pred testom dát interné `NS_FATAL` na príchode riadiacej správy/TBTP po jej termíne. V4 túto situáciu **nepočíta ako výpadok používateľských dát**. Parametrizácia jedného návratového smeru začína až po potvrdení attach. Toto je hranica vykonateľnosti aktuálneho modelu, nie dôkaz o riadení reálnej siete.

## Parametre, pôvod a stav

`config/v4_leo_reference.json` je jediný V4 vstup. `sns3_reference` nastavuje bežné hodnoty po vytvorení `SimulationHelper`, keďže jeho konštruktor volá `SetDefaultValues` a skoršie globálne predvolené hodnoty by prepísal. `cases` mení anténny zisk, UT výkon, návratovú ISL rýchlosť/frontu a vzor ponuky. Runner prijíma iba explicitné polia a medze; výsledok nesie konfiguráciu, hash, zdrojový hash a každý raw súbor.

| Oblasť | Aktuálne referenčné nastavenie | Pôvod / hranica tvrdenia |
| --- | --- | --- |
| Anténna mapa | 17 dBi všesmerový diagnostický user/feeder beam; 7 dBi citlivosť | Generuje `tools/run_v3_leo_native.py::model_files`; fyzikálne nejde o reálnu anténu (D). |
| UT výkon a šum | 4 dBW, Rx 24,6 dBK | `simulation-helper.cc::ConfigureLinkBudget`, skutočná hodnota výkonu na UT PHY; zmenený výkon vyžaduje znovu `SatPhy::Initialize`, lebo EIRP sa tam ukladá do cache. Stav A pre mechanizmus, D pre zariadenie. |
| Satelitný user RX a GW RX | 28,4/24,62 dBK | `simulation-helper.cc::ConfigureLinkBudget`; obe hodnoty sú nastaviteľné, bez kalibrácie terminálu (D). |
| Generické RF pásma | Forward feeder 27,5 GHz/2 GHz, forward user 19,7 GHz/0,5 GHz; return feeder 17,7 GHz/2 GHz, return user 29,5 GHz/0,5 GHz | `simulation-helper.cc::ConfigureFrequencyBands`; návratové base frekvencie sú v V4 konfigurovateľné, forward zostáva v tomto kontrakte pripnutý. Sú to DVB referenčné pásma, nie RF troch operátorov (A pre nastavenie, D pre interpretáciu). |
| DVB link/MODCOD | `EM_AVI`, `IF_PER_PACKET`, ACM v oboch smeroch, default forward `QPSK_1_TO_2`, return default waveform ID 3 | `SimulationHelper::SetDefaultValues` a `EnableAcm`; V4 sprístupňuje ACM a forward MODCOD. Žiadne tvrdenie o proprietárnom MODCOD operátora. |
| Scheduler a fronta SNS-3 | 100 ms superframe/request evaluation/control slot; VBDC RC3; `SatQueue::MaxPackets=10000`; návratový ARQ predvolene vypnutý | `SimulationHelper::SetDefaultValues`, `EnableOnlyVbdc`, `SatLlc` predvolené false. V4 sprístupňuje kontrolný interval, limit `SatQueue` a ARQ switch. Pri zapnutí ARQ má SNS-3 vlastné mechanizmy; V4 ich ešte nevaliduje ako protokol služby. |
| Modelová ISL | 1 Gbit/s, `DropTailQueue` 100 paketov, `c=299792458 m/s`; citlivosť 10 kbit/s/1 paket v SAT1→SAT0 | `satellite-point-to-point-isl-helper.cc`, `satellite-point-to-point-isl-channel.cc`, `SatConstVariables`. Skutočné optické ISL operátorov nie sú týmto modelované (D). |

Pre každú výstupnú metriku platí: implementačný dej dokázaný raw stopou je **A**; použitie aktuálnych čísel na Iridium, Starlink alebo Globalstar je **D**. Tu nie je žiadny status C, lebo chýba porovnateľná nezávislá kalibrácia terminálovej zostavy, lúča, gateway, plánovača a prevádzky. Širší [register reálne dohľadateľných údajov](resers-realne-parametre-a-medzery-2026-10-26.md) určuje, čo možno neskôr nahradiť produktovým údajom a čo vyžaduje meranie alebo kontakt s kompetentnými ľuďmi.

## Analytické brány a výstup

Checker viaže každé ICB1 ID od RSU cez UT, natívnu ISL frontu, príjem SAT0 a gateway; `DropBeforeEnqueue` musí vysvetliť rozdiel počtov. Nezávisle z TLE/SGP4 vypočíta okamžitú SAT1–SAT0 vzdialenosť a kontroluje `t_príchod - t_dequeue ≈ L·8/R + d/c` v tolerancii 2,5 ms (výpis raw časov má 1 µs). Tri úseky UT→SAT1→SAT0→GW dávajú dolnú medzu latencie aplikácie. Pre return user kanál sa overí zmena surovej hustoty prijatého výkonu v dB pri zmene UT výkonu/zisku a explicitne sa spočíta FSPL pri 29,5 GHz. Čas obojsmernej sondy sa uvádza oddelene od dátovej latencie.

**Nezamieňať:** 17 dBi mapa je diagnostická a nekryje tvar/pointing skutočného lúča; `SatQueue` nie je ISL P2P fronta; modelové `EM_AVI` a ACM nie sú RF stack konkrétneho operátora; dávka o 23 s je citlivostná záťaž, nie nameraný dopyt; `Gateway_ACCEPT=1/6` v preťaženom referenčnom prípade neodhaduje PDR žiadnej komerčnej služby.
