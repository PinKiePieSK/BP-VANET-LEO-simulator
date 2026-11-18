# Pevný používateľský lúč: viditeľnosť, zisk a prenos reportu

## Výskumná otázka a hypotéza

Predchádzajúci editorový LEO pilot pri každom posune RSU **nanovo namieril** user lúč na jej terminál. Tento experiment drží polohu lúča pevne nad archivovanou bratislavskou RSU a presunie celý rovnaký dopravný scenár geografickou kotvou k približne **52° N, 28° E**. Hypotéza: pri geometricky viditeľnej družici môže byť kvalita pevného lúča nedostatočná na vytvorenie a udržanie paketovej cesty. Doplňujúci kontrolovaný útlm user mapy `0/5/10 dB` iba skúma citlivosť **nášho** SNS-3 modelu; nie je nameranou stratou ani parametrom Starlinku, Iridia či Globalstaru.

V každom variante sú rovnaké JSON cesty, SUMO FCD, 24 waypointov, šesť CAM časov 20–22,5 s, seed `314159`, objekt GP 37741, proxy GW, feeder mapa a C++ paketový algoritmus. Mení sa výlučne anténna mapa user lúča. Steered kontrola v každom behu mieri na nový UT; pevný lúč mieri na starú RSU. C++ zdroj pevnej vetvy sa od integračnej vetvy líši **iba koncovou kontrolou počtu úspechov** (`== offered` → `<= offered`), aby paketová strata neskončila diagnostickou výnimkou. Presný instrumentovaný zdroj, pôvodný zdroj, mapy, stopy, PCAP a hashe sú v každom výstupe.

## Parametre, výpočet a jednotky

Používateľská mapa je archivovaná z [integrovaného editorového behu](editor-sns3-leo-reference.md), kde bol výskumne zvolený HPBW **22°** a vrchol približne **17,465 dBi**. Pôvod anténneho približného vzorca a explicitná 3D adaptácia sú uvedené v [denníku smerového lúča](sns3-338-leo-directional-reference-37741.md). Boresight zostal pri prvom čase `t=20 s` v smere družica→pôvodný UT. Nový UT je približne **14,506°** mimo osi; zisk pevnej mapy bol v prvom vzorkovaní **12,248 dBi** oproti približne **17,465 dBi** pri preladenej kontrole. Dodatočný útlm je odpočítaný rovnomerne z každého bodu pevnej user mapy; feeder mapa sa nemení. Žiadna z týchto antén alebo brán nie je identifikovaná ako prevádzkový profil operátora. GP vstup bol archivovaný po modelovanom UTC, takže orbitálna časť je retrospektívna, nie živá predikcia prevádzky.

`tools/run_leo_fixed_beam_sensitivity.py` overuje pripnutý checkout, hash rovnakého scenára, steered runner, pôvodný zdroj a surové vstupy; kontroluje, že v testovacom bode má user mapa väčší zisk než feeder mapa, aby SNS-3 nepriradil terminál nesprávnemu lúču. Pred každým RF porovnaním sa šesť ziskov z logu znovu porovná s priamym 3D uhlovým výpočtom do 0,5 dB a testuje sa elevácia nad 10°. `tools/check_leo_fixed_beam_sensitivity.py` nezávisle kontroluje hashe, presný vzťah všetkých bodov anténnej mapy k `0/5/10 dB`, originálne OCB/LAN PCAP, rovnaké pozemné a UT aplikačné bajty aj časy a `PacketTrace` fázy. `tools/analyze_leo_fixed_beam_sensitivity.py` vypočíta podiel prijatých šiestich reportov a per-event CAM→GW čas v **µs**. Uvedený „jitter“ je priemer absolútnych rozdielov susedných úspešných aplikačných oneskorení; pri nule prijatých paketov je `null`.

## Pozorovania

| Dodatočný user útlm | Zisk pevného lúča pri prvom CAM | Doručenie za GW | UT FWD PHY zahodenia za 25 s | UT RTN PHY rámce | Priemer CAM→GW |
|---:|---:|---:|---:|---:|---:|
| 0 dB | 12,248 dBi | 6/6 | 0 | 36 | 113 220 µs |
| 5 dB | 7,248 dBi | 6/6 | 83 | 29 | 113 223 µs |
| 10 dB | 2,248 dBi | 0/6 | 249 | 0 | nedefinovaný |

Všetky tri steered kontroly prijali **6/6** pri identickom scenári. V pevných vetvách zostali pozemné OCB a LAN PCAP a aplikačné reporty pred satelitným úsekom identické. Pri 10 dB UT aplikácia úspešne zavolala `SendTo` pre šesť reportov, ale `PacketTrace` neobsahuje žiadne návratové UT PHY vyslanie ani príjem na GW. Dopredné kontrolné rámce boli zahadzované na UT PHY, takže príčina modelového výpadku leží už v riadiacej doprednej ceste. Záznam `UT_SAT_REPORT_TX` preto znamená **ponuku aplikácie**, nie dôkaz rádiového vyslania. Pri 5 dB časť dopredných rámcov zlyhala, ale zvyšná riadiaca komunikácia umožnila doručenie všetkých šiestich reportov; nejde o tvrdenie o reálnej redundancii operátora.

Pre 0 a 5 dB vyšlo definované susedné absolútne kolísanie oneskorenia **1 609,8 µs**; pri 10 dB je nedefinované. Výsledok určuje iba interval prechodového správania tohto krátkeho nezáťaženého behu: medzi **5 a 10 dB pridaného výskumného útlmu**. Nie je to odhad link margin, dostupnosti alebo PDR akejkoľvek komerčnej služby. Potrebujeme viac semien, dlhší čas, kapacitnú záťaž a nezávisle doložený terminálový profil pred porovnaním operátorov.

## Neúspešné pokusy a oprava vstupného kontraktu

Pri prvom kandidátovi **40° N, 25° E** bola družica viditeľná, ale pôvodná pevná user mapa mala v bode UT menší zisk než feeder mapa. C++ kontrola skončila `LEO user beam not 30` ešte pred vysielaním CAM. Surový diagnostický log a scenár sú hashované v `results/leo_fixed_beam_invalid_inputs/`; tento pokus sa nepoužíva ako úspešný paketový výsledok. Runner následne dostal explicitnú kontrolu preferencie user lúča.

Kandidát **53° N, 29° E** prerušil aj steered kontrolu. Uchovaný diagnostický log v `results/leo_fixed_beam_invalid_inputs/` obsahuje `GetBestBeamId - Beam 30 returned a NAN antenna gain value` v `t=0`. Zdroj SNS-3 posúva anténnu mriežku podľa aktuálnej polohy družice; mapu ukotvenú v `t=20 s` sa pokúša čítať už pri inicializácii v `t=0`, keď sa bod posunul mimo geografickej mriežky. Prvé pokusy s 54° N a 53° N neuchovali všetky dočasné súbory; preto sa z nich neodvodzuje žiadna paketová metrika. `tools/scenario_server.py` teraz pred spustením vypočíta **51 posunov mapy po 0,5 s v celom 25 s intervale** a odmietne RSU, ktorá opustí bezpečnú bilineárnu bunku. Bod 52° N, 28° E touto kontrolou prešiel.

## Reprodukcia

Z koreňa projektu na pripravenom pripnutom checkoute a s archívnym základným behom:

```bash
.venv/bin/python tools/run_editable_v2_ocb_sns3_leo_reference.py \
  /tmp/ns3-sns3-338-feasibility /tmp/leo-steered-opakovanie \
  --scenario results/leo_fixed_beam_52n28e_loss0_v2/scenario.json
.venv/bin/python tools/run_leo_fixed_beam_sensitivity.py \
  /tmp/ns3-sns3-338-feasibility \
  results/leo_fixed_beam_52n28e_loss0_v2/scenario.json \
  /tmp/leo-steered-opakovanie /tmp/leo-fixed-loss10-opakovanie \
  --extra-user-loss-db 10
.venv/bin/python tools/check_leo_fixed_beam_sensitivity.py \
  /tmp/leo-fixed-loss10-opakovanie
```

Pre porovnávaciu trojicu zmeň `--extra-user-loss-db` na `0` a `5`, vždy použi nový výstupný adresár, a potom spusti `tools/analyze_leo_fixed_beam_sensitivity.py` s tromi adresármi v poradí 0/5/10 a `--output`. Uložené originály sú `results/leo_fixed_beam_52n28e_loss{0,5,10}_v2/`; súhrn je `results/leo_fixed_beam_sensitivity_52n28e_summary.json`.
