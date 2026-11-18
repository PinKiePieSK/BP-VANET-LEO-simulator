# V4 — fyzikálna a frontová vernosť generickej SNS-3 referencie

**Stav:** uzavretá natívna referenčná podmnožina, 26. 10. 2026. **Zdroj pravdy:** [`config/v4_leo_reference.json`](../../config/v4_leo_reference.json), [`src/v4-leo-reference.cc`](../../src/v4-leo-reference.cc), [`tools/run_v4_leo_reference.py`](../../tools/run_v4_leo_reference.py), [`tools/check_v4_leo_reference.py`](../../tools/check_v4_leo_reference.py), [`results/v4_leo_reference_complete_20261026`](../../results/v4_leo_reference_complete_20261026). [Kontrakt a hranice](../decisions/v4-generic-dvb-contract.md) rozlišujú skutočný mechanizmus SNS-3 od neznámych parametrov operátora.

## Vykonanie a pozorovanie

Reprodukcia do **novej neexistujúcej** cesty:

```bash
.venv/bin/python tools/run_v4_leo_reference.py vendor/ns-3.38-ocb-eval results/v4_leo_reference_NOVY_ID config/v4_leo_reference.json
.venv/bin/python tools/test_v4_reference_mutation.py results/v4_leo_reference_NOVY_ID
```

Všetky prípady používajú tie isté archivované OMM, UTC, trasu auta, šesť CAM→ICB1 identít, seed a P3 attach. Počas riadiaceho attach ostávajú ISL smery na 1 Gbit/s; o 19 s sa nastaví uvedený návratový dátový smer a výkon UT. `burst` znamená presun *skutočných* šiestich reportov z aplikačnej fronty UT naraz o 23 s.

| Prípad | Zmena oproti základnej ceste | Zahodené ICB1 / iné ISL pakety | Prijaté v GW / 6 | Medián UT→GW po SAT TX |
| --- | --- | ---: | ---: | ---: |
| `baseline` | 17 dBi, 4 dBW, ISL 1 Gbit/s, fronta 100, bežné časy | 0 / 0 | 6 | 117,775 ms |
| `beam_low` | iba zisk diagnostického lúča 7 dBi | 0 / 0 | 6 | 117,962 ms |
| `ut_power_low` | iba UT Tx −50 dBW po attach | 0 / 0 | 6 | 772,088 ms |
| `burst_fast` | rovnakých 6 reportov naraz, ISL 1 Gbit/s, fronta 1 paket | 2 / 0 | 4 | 118,388 ms |
| `isl_congested` | tá istá dávka/fronta, SAT1→SAT0 10 kbit/s | 5 / 57 | 1 | 853,789 ms |

Pri `burst_fast` sa dva pakety stratia aj pri 1 Gbit/s, pretože jediná pozícia v P2P fronte nestačí pri takmer súčasnom príchode paketov. Rozdiel `burst_fast`→`isl_congested` drží ponuku a veľkosť fronty konštantné: o 3 viac skutočných ICB1 sa zahodí a o 3 menej dôjde do GW. Každý drop má ID konkrétneho CAM odvodeného reportu; nie je vloženým syntetickým `Packet(16)` z P2 testu.

Tá istá SAT1→SAT0 fronta nesie aj **ne-ICB1** pakety modelu. V základnom prípade mala 261 vstupov a 261 výstupov bez dropu; pri 10 kbit/s 201 vstupov, 200 výstupov a 57 dropov do konca 25 s. Jeden paket zostal vo fronte. Preto čakanie prvého ICB1 približne 726 ms a výslednú stratu nemožno pripísať výlučne šiestim dátovým reportom. Raw stopa identifikuje tieto ďalšie rámce ako `OTHER`, nie ako overený obsah konkrétneho riadiaceho protokolu operátora.

`ut_power_low` má v return-user raw `rx_power_output_trace` pokles maxima hustoty prijatého výkonu o **54,014 dB** pri príkaze −54 dB; medián UT→GW rastie o **654,313 ms** a všetkých šesť správ sa prijme. `beam_low` dáva **−10,000 dB** v tom istom fyzikálnom signáli, ale v tomto okne nevzniká zlyhanie. Tieto čísla potvrdzujú citlivosť konkrétneho výskumného DVB PHY/schedulera, neodhadujú prah komerčného terminálu. `PacketTrace.log` v týchto pároch neobsahuje return PHY drop; zmena sa prejavuje v kontinuálnom Rx výkone a pri nízkom UT výkone v aplikačnej latencii.

## Nezávislé analytické kontroly

- Obidva smery P3 sondy potvrdili attach pred dátami; čas od `P3_PROBE_TX` po potvrdenie bol približne 723 ms. Táto riadiaca latencia sa **nepripočítava** k metrike jednotlivých ICB1.
- SGP4/TLE + okamžitá poloha SAT1/SAT0 dávajú pri dátach približne 4 034 km. `d/c ≈ 13,457 ms`. Pri 126-bajtovom ISL rámci a 10 kbit/s je serializácia 100,800 ms; raw rozdiel od výstupu frontu po prijatie je 114,257 ms. Najväčšia absolútna odchýlka analytického súčtu v kontrolovaných udalostiach je približne 1,1 µs.
- Nezávislé FSPL pre UT→SAT1 pri 20 s a generickej návratovej user frekvencii 29,5 GHz je **188,293 dB**. Checker overuje fyzikálne jednotky, zmenu raw výkonu pri zisku/výkone a dolnú hranicu UT→SAT1→SAT0→GW `distance/c` pre každý prijatý report. Absolútne C/N a MODCOD konkrétneho výrobku nie sú kalibrované.
- Šesť identít sa musí zachovať cez `RSU_REPORT_CREATED`, `UT_SAT_REPORT_TX`, skutočné `Enqueue/Dequeue/DropBeforeEnqueue`, `ISL_NATIVE_REPORT_RX` a `GATEWAY_ACCEPT`. Manifest kontroluje hash zdroja, runnera, checkera, configu a všetkých raw súborov.

## Negatívne a regresné brány

[`tools/test_v4_reference_mutation.py`](../../tools/test_v4_reference_mutation.py) na **dočasných kópiách** odmietol (1) zmenu raw stopy bez zmeny manifestu, (2) sfalšované ID zahodeného ICB1 pri aktualizovanom hashi a (3) posun odoslania z ISL frontu o 10 ms pri aktualizovanom hashi. Štyri zlé konfigurácie sa odmietli už v preflighte: duplicitné ID, NaN pri šume, neprípustná ISL rýchlosť a neznáme pole. Read-only [`tools/check_v3_leo_native.py`](../../tools/check_v3_leo_native.py) nad historickým V3 výsledkom prešiel po vytvorení V4. Historické vstupy a výsledky sa nemenili.

## Vernosť a zostávajúce hranice

Status **A** majú iba vykonané paketové/frontové/časové javy generickej SNS-3 referencie. Hodnoty lúča, proxy gateway, veľkosť ISL, dávka ponuky a nízky UT výkon sú **D** citlivosti. Pásma, ACM a plánovač sú pravdivo odhalené nastavenia DVB referencie, bez externej validácie Starlink/Iridium/Globalstar hardvéru alebo služby. Jediná archivovaná dvojica, miesto, 25 s a jeden seed neposkytujú operačné PDR, outage distribúciu ani interval spoľahlivosti. User/feeder kapacita a retransmisie sú nastavené z SNS-3, nie samostatne kalibrované; citlivosť v tejto V4 podmnožine sleduje UT výkon, beam a návratovú ISL. Ďalšia fáza V5 sa týka dopravy/CAM/ITS-G5/mestského rádia.
