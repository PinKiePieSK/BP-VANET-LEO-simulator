# Jediný UT medzi družicami: audit stavu a prijímací kontrakt

**22. 10. 2026; zdrojový audit, nie úspešný paketový test.** Platí pre ns-3.38 `392e36833ce3c7e0ecde4188043f76345402d5a7` a SNS-3 3.38 `739a10dbe1db02fd2c4064501e4a48994e0b79f3` v `/tmp/ns3-sns3-338-feasibility`. Lokálny verzovaný patch `patches/sns3-338-static-ut-sat-id.patch` nastavuje ID družice **iba pri vytvorení** scenára z `ut_sat_ids.txt`. Tento audit rozširuje [skoršie zistenie o beam handoveri](sns3-338-handover-scope.md) a určuje, čo musí splniť prípadná dynamická implementácia. Doterajší [spoločný CAM/ICB1 beh](../experiments/two-leo-icb1-rsu-policy.md) používa dva trvalo pripojené UT.

## Zistený tok a chýbajúci stav

| Vrstva | Overiteľné miesto v pripnutom zdroji | Stav pri pokuse o SAT0→SAT1 |
| --- | --- | --- |
| Riadiaca správa | `model/satellite-request-manager.cc:865`, `model/satellite-control-message.cc:789`, `model/satellite-gw-mac.cc:561` | Odporúčanie nesie iba nové `beamId`; prijímací GW callback používa pôvodné `satId` z prijatého rámca. Neexistuje v tejto správe cieľové `satId`. |
| Riadenie kapacity | `model/satellite-ncc.cc:381-424` | `MoveUtBetweenBeams` nájde zdrojový aj cieľový scheduler s **rovnakým** `satId`. Samostatné `AddUt`/`RemoveUt` existujú, ale nepredstavujú atómový medzi družicový presun s potvrdením, frontom a smerovaním. |
| UT MAC | `model/satellite-ut-mac.cc:1114-1123,1802-1865` | TIM-U a `DoFrameStart` aktualizujú lúč/GW a volajú PHY callback len s `beamId`; `m_satId` zostáva konštrukčnou hodnotou. MAC podľa neho vyhľadáva scheduler a kontroluje beam. |
| UT PHY a kanál | `model/satellite-ut-phy.cc:192-220`, `model/satellite-phy.cc:417-431` | `PerformHandover(beamId)` odpojí staré Rx/Tx kanály a po reconfiguračnom čase vyžiada nové cez dvojicu **(m_satId, m_beamId)**. Samotné `SatPhy::SetSatId(1)` mení ID v PHY/Rx/Tx, ale *neodpája ani neprepája* kanály a neaktualizuje MAC. Preto nie je handoverom. |
| Smerovanie družíc | `model/satellite-geo-net-device.cc:791-806`, `helper/satellite-helper.cc:839-856` | `ConnectUt` eviduje MAC v `m_utConnected` a `SatIdMapper` na konkrétnej družici. Pri zmene treba najprv vyriešiť presun tej istej MAC, vplyv na in-flight pakety a obojsmerné ISL trasy. V existujúcom scenári sa spojenie vytvára len pri stavbe topológie. |
| IP a časovanie | `helper/satellite-user-helper.cc:631-705`, `model/satellite-mobility-observer.cc:112-122,260-274,305-335` | Callbacky `UpdateUtRoutes`/`UpdateGwRoutes` a ARP sú previazané s GW. `SatMobilityObserver` drží referenciu na pôvodnú družicu `m_geoSatMobility`; počíta z nej eleváciu a timing advance. Zmena iba UT PHY by ponechala zastarané pozorovanie. |

Záver zo zdrojového kódu je úzky: **verzia nemá hotové medzi družicové odovzdanie jedného UT**. Nie je to dôkaz, že ho nemožno doprogramovať. Dvojica už zapnutých UT a prepínač jedného RSU UDP socketu je platný **dvojterminálový** návrhový scenár, ale udalosti `attach_confirmed` v ňom potvrdzujú iba výskumnú smerovaciu politiku.

## Rozhranie budúceho rozšírenia

Jedno externé rozhodnutie `request(target_sat_id, target_beam_id, target_gw_id, packet_policy)` musí mať stav `connected_old → pending → confirmed_new` alebo `failed_old`. `pending` musí definovať, či sa nový prenos zahodí, drží vo fronte s maximálnou dĺžkou/časom, alebo zostáva na starej ceste. Pre prvý test voľme **no-queue drop**, ako v súčasnom dvojterminálovom pilote; jeho 800 ms je ľubovoľná citlivostná hodnota, nie nameraný attach.

Potvrdenie je dovolené až po všetkých kontrolách:

1. cieľ má existujúci user aj feeder beam, GW a prípustnú trasu cez modelovú ISL; samotná elevácia nestačí;
2. NCC presunul UT MAC zo zdrojového na cieľový scheduler a pridelil zdroje; cieľové riadiace správy a spätný link sa prijímajú;
3. jeden UT PHY odpojil starý Tx/Rx kanál a pripojil kanály cieľovej dvojice `(satId, beamId)`; MAC, PHY a rámcové tagy sa zhodujú;
4. `SatGeoNetDevice`/`SatIdMapper`, IP/ARP/GW trasy a `SatMobilityObserver` ukazujú cieľový satelit; stav starého satelitu už nesmie označovať UT ako lokálne pripojený;
5. záznam obsahuje per-packet pôvod, stav pri prijatí do frontu, prípadný drop dôvod a skutočné UT/SAT/GW PHY/sieťové udalosti. Vydané `attach_confirmed` bez týchto dôkazov je chyba modelu.

Výber kandidáta, signalizačný obsah a časovanie nad rámec verejnej špecifikácie zostanú označené ako **výskumné predpoklady**. Použité DVB-S2/RCS2 PHY/MAC nedokazuje kompatibilitu s Iridium Certus, Starlink ani Globalstar terminálom.

## Minimálny prijímací experiment

Použiť jeden fyzický `SatNetDevice`/UT a jeden RSU zdroj ICB1, pôvodné CAM vstupy, dve archivované dráhy a pevný seed. Spustiť párované varianty: `stay_sat0`, `switch_sat1`, `no_target_channel`, `no_target_gateway_or_isl`, `attach_failed`. V `switch_sat1` musí ten **istý UT MAC a IP** doručiť pred prechodom paket cez SAT0 a po potvrdení ďalší cez SAT1; počas `pending` podľa no-queue politiky žiadny. Ostatné kontroly nesmú pripustiť post-switch paket ako doručený cez SAT1. Checker má porovnať plné CAM/ICB1 bajty, IP/UDP checksum, PacketTrace ID na user i feeder, príslušnosť UT MAC v oboch satelitoch, scheduler, aktualizovaný timing advance a časové poradie. Kým neprejde, výsledky sú iba dvojterminálové alebo abstraktné, **nie single-radio handover**.

## Opakovanie auditu

```bash
cd /tmp/ns3-sns3-338-feasibility/contrib/satellite
rg -n 'CheckForHandoverRecommendation|SendHandoverRecommendation|MoveUtBetweenBeams|PerformHandover|ConnectUt|DisconnectUt|ObserveTimingAdvance' model helper
```

Zdrojový audit je kontrola dostupného API a toku stavu; neprodukuje PDR ani čas handoveru. Funkčný predchodca s dvoma UT sa overí príkazmi v [jeho experimente](../experiments/two-leo-icb1-rsu-policy.md).
