# U9: handover všetkých RSU a fyzikálne podmienky natívneho satelitného kanála

**2. 11. 2026.** Aktívny runtime: ns-3.38/SNS-3 3.38. Paketový prenos zostáva v jednom procese s pozemným OCB/Vanetza tokom. Žiadny servisný prenos ani aplikačné dopĺňanie doručených paketov sa nepoužíva.

## Implementácia

- `src/u9-full-integration-per-rsu.cc`: každá RSU má vlastný handover stav, vlastné presunutie UT MAC/PHY/NCC členstva a vlastný skúšobný UDP paket s návratom. Súčasné RSU sa prepínajú s odstupom 200 ms, aby nedošlo k súbežnému prepisu schedulerov. Potvrdenie patrí konkrétnej RSU; počas jej `pending` stavu sa zahadzujú len jej nové reporty. Aktívny scenár s explicitným cieľom prepne všetky tri RSU terminály; tretia RSU má aplikačný satelitný backhaul vypnutý, preto po prepnutí nevytvára reporty, ale jej probe a potvrdenie sa overia.
- `SatChannel::ScheduleRx` v SNS-3 teraz volá deklarovanú podmienku používateľského spoja pred `StartRx`. `src/u9-native-satellite-condition.h` vyhodnocuje montáž a zorné pole Starlink FHP, rýchlosť elektronického smerovania, relatívnu ECEF radiálnu rýchlosť a zvyškový Doppler, ako aj priechod lúča cez lokálny OSM polygón s výškou. Zamietnutý signál nevstúpi do natívneho prijímača. Feeder spoj brány si naďalej zachováva výškovú masku; miestny súbor budov okolo RSU nie je automaticky údajom o okolí brány.
- `tools/u9_native_editor.py` prenáša každému RSU terminálu explicitné RF parametre z existujúcej konfigurácie scenára. Pri Iridium NEXT a Globalstar nie je verejne doložená smerová krivka namontovaného terminálu, preto ich smerový cutoff ostáva vypnutý; Doppler a lokálne budovy sa vyhodnocujú aj pre ne. `tools/u9_check_native_editor.py` kontroluje RF rozhodnutia voči zadaným hodnotám a pri novom viacdružicovom behu vyžaduje presun, probe, potvrdenie a následný doručený aplikačný paket každej aktívnej RSU.
- `tools/u9_physical_report.py` a panel replay rozlišujú RF signály zamietnuté pre budovu, montáž, Doppler alebo smerovanie od straty aplikačného paketu.

Kumulatívny patch pre kanál je `patches/sns3-338-native-channel-conditions.patch`. Predchádzajúce zdroje a knižnica sú uložené v `archive/u9-native-editor-pre-rf-20261102`, aby historické manifesty zostali nezávisle overiteľné.

## Skutočné behy a samostatný verifier

Nasledujúca tabuľka zachováva prvú overenú etapu pred zjednotením nosnej frekvencie. Pri jej Dopplerovom riadku používala citlivostná podmienka scenárovú frekvenciu, zatiaľ čo generický SNS-3 kanál ešte vlastnú predvolenú frekvenciu. **Konečný stav je v ďalšej tabuľke**: Doppler aj natívny prijímač používajú tú istú skutočnú nosnú. Tieto staršie behy slúžia len ako reprodukovateľný historický kontrolný bod.

Všetky prijaté riadky majú `bp_u9.py run` **PASS** a následné samostatné `bp_u9.py verify` **PASS**. Checker číta PCAP, PacketTrace, celé CAM/ICB1/GRA1/I2V1 bajty, identitu, poradie, pripojenie terminálov a SHA-256 surových vstupov/stôp. Počty `RF drop` sú počty signálov v SNS-3 kanáli, nie počty stratených aplikačných správ.

| Beh v `results/u9_runs/` | Kontrola | Natívna brána / návrat do auta | RF signály |
| --- | --- | ---: | --- |
| `native-rf-handover-starlink-20261102` | 2 Starlink družice, ISL, presun všetkých 3 RSU UT | 74 / 74 | 3 presuny, 3 probe RX, 3 potvrdenia; všetky aktívne RSU doručili aj po prepnutí |
| `native-rf-iridium-20261102` | Iridium NEXT orbitálny vstup, generické DVB | 91 / 91 | prijaté |
| `native-rf-globalstar-20261102` | Globalstar orbitálny vstup, 1 družica bez ISL | 91 / 91 | prijaté |
| `native-rf-mount-control-20261102` | RSU0 panel otočený nadol | 38 / 38 | RSU0: 185 `mount_fov`; RSU1 ďalej prijíma |
| `native-rf-building-control-20261102` | deklarovaná 100 m budova 3–8 m od RSU0 v smere satelitu | 38 / 38 | RSU0: 185 `building`; RSU1 ďalej prijíma |
| `native-rf-doppler-control-20261102` | scenárových 29,5 GHz, kompenzácia 98 %, tolerancia 5 kHz | 58 / 58 | 90 `doppler` zamietnutí, ostatné signály prijaté |
| `native-rf-steering-control-20261102` | 1,5°/s smerovanie, 1° úzky prijímací lúč | 93 / 93 | 423 skorých `pointing` zamietnutí; v aplikačnom okne sa anténa dosmerovala |

Párový historický výsledok bez lokálnej prekážky a s voľnou montážou `native-rf-baseline-final-20261102` dosiahol 91/91 a 744 prijatých RF signálov. Úmyselne blokovaná RSU0 dala v dvoch oddelených prípadoch 0 reportov na bráne; 38 reportov RSU1 zostalo doručených. V budovovom prípade bol pozemný model budovy súčasne zapnutý, takže porovnanie počtu vytvorených CAM/RSU reportov treba čítať zo surového pozemného záznamu, nie pripisovať celý rozdiel výlučne satelitnému kanálu.

## Konečná kontrola nosnej a RF podmienok

`SatChannel::ScheduleRx` odovzdáva RF podmienke frekvenciu vypočítanú tým istým `m_carrierFreqConverter`, ktorý používa `StartRx`. Doppler sa počíta z tejto nosnej a relatívnej radiálnej rýchlosti. Konfigurácia SNS-3 používa pre generický DVB user link scenárový uplink a verejne doložený downlink profil príslušnej služby; nejde o implementáciu operátorského modemu. Verifier z raw `satellite_rf.csv` nezávisle prepočítava Doppler a kontroluje rozsah uplinku aj downlinku. Pre Starlink sú v stope return user nosné 14,250625–14,288125 GHz a forward user 11,7625 GHz; pre Iridium NEXT 1,621875–1,659375 GHz a 1,68375 GHz; pre Globalstar 1,615625–1,653125 GHz a 2,55425 GHz. Rozdiel oproti báze je pridelenie nosiča v generickej SNS-3 konfigurácii, nie operátorské kanálové plánovanie.

Všetky riadky nižšie majú nový `bp_u9.py run` **PASS** a po ňom samostatný `bp_u9.py verify` **PASS**. Stopy a manifesty sú v uvedených priečinkoch pod `results/u9_runs/`.

| Beh `native-carrier-…-20261102` | Scenár | Brána / odpoveď do auta | RF rozhodnutia v SNS-3 |
| --- | --- | ---: | --- |
| `starlink` | voľná montáž, 1 družica | 91 / 91 | 744 prijatých |
| `starlink-handover` | 2 družice s ISL, presun všetkých 3 RSU UT | 74 / 74 | 712 prijatých, 8 `pointing`; 3 presuny, 3 probe RX a 3 potvrdenia |
| `iridium` | orbitálny vstup Iridium NEXT | 91 / 91 | 726 prijatých |
| `globalstar` | orbitálny vstup Globalstar, bez ISL | 91 / 91 | 727 prijatých |
| `mount-control` | RSU0 má anténu otočenú nadol | 38 / 38 | 185 `mount_fov`, 450 prijatých |
| `building-control` | 100 m vysoká lokálna budova v lúči RSU0 | 38 / 38 | 185 `building`, 450 prijatých |
| `doppler-control` | sprísnená zvyšková tolerancia na 2,3 kHz | 35 / 35 | 248 `doppler`, 586 prijatých |
| `steering-control` | 1,5°/s smerovanie a okamžitý lúč 1° | 93 / 93 | 423 `pointing`, 518 prijatých |

RF počty sú **signály**, nie aplikačné pakety. Handover test kontroluje aj raw návratový UDP paket pre každý RSU terminál a po presune prijaté aplikačné pakety aktívnych RSU. Smerovanie je scenárový model terminálu, nie verejne známy algoritmus operátora. Predchádzajúcu verziu so samostatnou scenárovou frekvenciou uchováva `archive/u9-native-editor-pre-carrier-20261102`; oba historické archívy zostávajú overiteľné.

Kontrola zdrojov `scripts/check_migration.py` prešla. Sedem zameraných unit testov pre fyzikálny audit, anténnu obálku a časovú viditeľnosť prešlo. Audit budovového výsledku bol exportovaný a samostatne overený v `results/u9_runs/native-carrier-building-control-20261102/physical-audit`. Finálny zdrojový balík na ploche `BP-Simulator.zip` prešiel kontrolou 11 450 súborov/odkazov, integritou ZIP a SHA-256. Po synchronizácii do pracovného runtime na ploche prešiel ešte nový Starlink beh `BP-Simulator-Workspace/runtime/results/u9_runs/native-carrier-runtime-starlink-20261102` a jeho samostatný verifier s 91/91 paketmi. Otvorené okno starého serverového procesu načíta nový Python backend až po jeho riadnom zatvorení a opätovnom spustení ikony; aktuálny proces nebol nútene ukončený kvôli rozpracovanému editoru.

## Presná hranica modelu

Tieto RF brány sú **deklarované citlivostné predpoklady v natívnom kanáli**, nie overená dostupnosť služieb. Pre Starlink sa používa verejne uvedené 140° zorné pole Flat High Performance terminálu; náklon, azimut, rýchlosť smerovania, šírka okamžitého lúča a Dopplerova kompenzácia sú vstupmi scenára. Pre Iridium NEXT a Globalstar sa nevymýšľa smerová hranica antény. Model budovy používa zadanú/odhadnutú výšku a tvrdý geometrický blok; nepočíta difrakciu, penetráciu ani presný zisk. Lokálny terén, budovy pri bráne, RF link budget a reálna aktivácia spot-beamov zatiaľ nie sú zapojené do tohto natívneho user linku.

Handover všetkých RSU je preukázaný v **explicitne kvalifikovanej spoločnej topológii** s jedným spoločným cieľovým satelitom. Automatický výber stále vyžaduje jedinú družicu nad všetkými aktívnymi RSU a bránou počas celého okna. Samostatný cieľ každého terminálu, opakované prepínanie počas dlhého behu a Globalstar handover bez ISL nie sú zatiaľ implementované; ide o hranice aktuálnej integrácie a konfigurácie feeder brány, nie o preukázanú nemožnosť SNS-3. Operátorské modemy a riadiaci systém zostávajú mimo generického DVB modelu.

Na reprodukciu použi nový výstupný názov, napríklad `PYTHONPATH=tools .venv/bin/python tools/bp_u9.py run config/u9-native-rf-building-control.json results/u9_runs/NOVY_BEH`, potom rovnaký príkaz s `verify` a cestou k novému výsledku.
