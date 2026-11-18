# SNS-3 LEO DVB: viditeľná dvojica pozemných RF úsekov pri jednom pakete

**Míľnik 22. 10. 2026.** Malý referenčný test už zostaveného ns-3.48/SNS-3 3.48; **nie** profil Starlinku, Iridia ani Globalstaru. Hypotéza: v dodanom historickom LEO scenári existuje návratový paket, pri ktorom stopa SNS-3 potvrdí UT→SAT a SAT→GW PHY príjem a nezávislá propagácia vstupných TLE dá kladnú eleváciu na oboch pozemných koncoch. Kontrola pri chýbajúcej bránovej udalosti musí zlyhať.

## Scenár, zdroje a reálny význam

Použitý je dodaný `constellation-leo-2-satellites`, `standard/standard.txt = DVB`, štart **2014-09-29 12:15:48 UTC**. Súbor `tles.txt` obsahuje **dva umelo oddelené záznamy ISS/Zarya s rovnakým NORAD 25544**, nie skutočnú komerčnú dvojicu družíc. Počiatočné TLE, dva GW body, päť UT bodov, jeden modelový ISL `0 1` a presné bajty šiestich vstupných súborov sú skopírované do [raw výsledku](../../results/sns3_leo_dvb_geometry_gate/scenario/). Zdrojový ns-3 commit je `d2add90b452d600cfb4859baed8e9ea633519447`, SNS-3 satellite `2c0c6d4d7fd1628eda1b923a7e135749513769fa`, dátový gitlink `4200675fa10f3eb9ba3627bc664240a331be4ba9`, traffic `2710ed71c2cba9d92940bdf53ad85159504329d9` a stats `003f6a29ce74808d0b2579fd16a9718f793f5bfe`.

`sat-constellation-example` vytvára SGP4 LEO uzly, DVB user/feeder PHY/MAC, sieťovú regeneráciu a modelový 100 Mb/s bodový ISL. Spustená CBR aplikácia má zvolenú veľkosť **96 B** a interval **1 s**, ale `PacketTrace.log` nezachováva surových 96 B aplikačného obsahu. Preto kontrolujeme identitu modelového paketu a rádiové fázy, **nie bajtovú rovnosť jeho payloadu**. Scenár je užitočný pre overenie funkcie generického satelitného stacku, nie pre predpoveď pokrytia v roku 2026, operátorskej služby, lúča alebo terminálu.

## Presné vykonanie

Z koreňa repozitára; VM má pripnuté závislosti `.venv` podľa [reprodukcie](../reprodukcia.md). `--OutputPath` musí byť vopred existujúci adresár. Prvý starší auditný pokus bez `mkdir` skončil `NS_ASSERT IsValidDirectory`; v tomto míľniku bol adresár vytvorený a celý beh skončil **exit 0**. Uložený príkaz:

```bash
mkdir -p /tmp/sns3-leo-dvb-gate-output
cd vendor/ns-3.48
timeout 180s ./ns3 run 'sat-constellation-example --scenarioFolder=constellation-leo-2-satellites --packetSize=96 --interval=1s --OutputPath=/tmp/sns3-leo-dvb-gate-output' > /tmp/sns3-leo-dvb-gate-stdout.log 2>&1
```

Surové [`PacketTrace.log`](../../results/sns3_leo_dvb_geometry_gate/PacketTrace.log) a [`stdout.log`](../../results/sns3_leo_dvb_geometry_gate/stdout.log) sú uložené bez úpravy. Majú SHA-256 `d611969be30a46b409938da4855982d2e015bbf53de05010d32ebaef16164e52` (25 908 riadkov, 2 439 181 B) a `1b7c45dc3181cc1033baa41daf867384eb5b6ab73d4771bd51f5c849f0b0a1ce` (4 360 B). Ich počet riadkov neznamená počet aplikačných doručení. Kontrola výsledku:

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/check_sns3_leo_dvb_geometry_gate.py \
  --scenario results/sns3_leo_dvb_geometry_gate/scenario \
  --trace results/sns3_leo_dvb_geometry_gate/PacketTrace.log \
  --stdout results/sns3_leo_dvb_geometry_gate/stdout.log \
  --output results/sns3_leo_dvb_geometry_gate/verification.json
```

Checker používa `sgp4 2.27` a `astropy 7.1.1` offline (`IERS` automatické sťahovanie vypnuté). Vstupné zemepisné šírky/dĺžky sú stupne, výšky metre, vzdialenosť km, čas UTC a simulačný čas sekundy. Zo vstupných TLE zostaví TEME polohu na čase udalosti, prevedie ju do ITRS a cez WGS84 `EarthLocation`/`AltAz` vypočíta topocentrickú eleváciu. Identitu oboch TLE skontroluje oproti počiatočným polohám družíc vytlačeným SNS-3; rozdiely sú povolené do 0,2° a 3 km kvôli rozdielnemu Earth orientation/SGP4 prevodu. Súradnice `UT10` a `GW2` musí potvrdiť vstupný súbor aj SNS-3 topológia.

## Konkrétny paket a výpočet

`PacketTrace` označuje modelový návratový paket ako **ID 62**. Počiatočný čas je 2014-09-29 12:15:48 UTC. `UT10` je vstupný bod **18° N, 115° E**, `GW2` prvá brána **17,69° N, 101,62° E**. Pozorované fázy a nezávislý výsledok [verification.json](../../results/sns3_leo_dvb_geometry_gate/verification.json):

| Fáza | Čas simulácie | TLE družica | Elevácia pozemného konca | Vzdialenosť |
| --- | ---: | --- | ---: | ---: |
| `UT10 PHY SND` → SAT1 | 2,09620 s | SAT1 | **16,493593°** | 1 146,264 km |
| `SAT1 PHY RCV` od UT10 | 2,10204 s | SAT1 | **16,493075°** | 1 146,286 km |
| `SAT1 ND RCV` | 2,10204 s | SAT1 | – | – |
| `SAT0 PHY SND` → GW2 | 2,10888 s | SAT0 | **2,472288°** | 2 077,192 km |
| `GW2 PHY RCV` od SAT0 | 2,11597 s | SAT0 | **2,472400°** | 2 077,181 km |
| `GW2 ND RCV` | 2,11597 s | SAT0 | – | – |

Z časov a identického ID vyplýva úspešný modelový PHY a sieťový príjem na oboch koncoch. Prechod medzi družicami vidno **nepriamo** ako `SAT1 ND RCV` a následné `SAT0 PHY SND` s tým istým ID; medzi nimi nie je v `PacketTrace.log` samostatná PHY udalosť ISL. Modelový ISL 0↔1 je v scenári a vo vytlačenej topológii, no jeho paketovo špecifické surové bajty stopa neposkytuje. Preto konkrétny vnútorný rámec ani jeho payload nemožno auditovať. Pozitívna geometrická elevácia je **iba test nad horizontom**: na GW je ~2,47° a neoverili sme minimálnu prevádzkovú eleváciu, dostupnosť lúča ani link margin. Bez týchto podmienok nemožno tvrdiť platnú komerčnú službu. Čas od UT PHY TX po GW PHY RX je **19,77 ms modelu**, nie meranie reálneho operátora ani end-to-end aplikačná latencia.

## Overenie a obmedzenia

Checker prešiel na uložených raw dátach. Z kontrolnej kópie stopy sa odstránil iba riadok `GW2 ND RCV` pre ID 62; checker ju odmietol s `gw_network_rx: expected one trace row, found 0` (exit 1). Táto kontrola chráni pred odvodzovaním doručenia zo samotnej plánovanej topológie alebo PHY TX. Výsledok neoveruje celý ISL payload, priradenie beam, rušenie, shadowing ani operátorský PHY/MAC. Nesmie sa spájať s oddeleným ns-3.38 OCB behom do jedného časového merania.
