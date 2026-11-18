# Rozhodovacia skúška cestného ITS stacku

**Stav 22. 10. 2026:** rozhodovacia skúška začala aplikačným ASN.1 kódovaním. Neskoršie samostatné testy už úspešne preniesli CAM cez Vanetza GN/BTP po ns-3 CSMA aj 802.11p a dekódovali ho na prijímači; ich presné hranice sú v [GN/BTP sonde](gn-btp-ns3-probe.md) a [rádiovej sonde](gn-btp-ns3-wifi11p-probe.md). Tento dokument zachováva postupné rozhodnutia a nadväzuje na [hlbokú analýzu](../hlbkova-analyza-komunikacie.md), oddiely 3–5 a 7.1. Starší pilot `src/vanet-sns3.cc` naďalej odosiela syntetický 300 B UDP payload cez `WIFI_STANDARD_80211p` a `AdhocWifiMac`; nie je to ETSI CAM/DENM ani plný ITS-G5 prenos.

## Rozhodnutie a overené verzie

| Vrstva/nástroj | Zistenie | Rozhodnutie |
| --- | --- | --- |
| Dopravná mobilita | Projekt má SUMO 1.18 a FCD import do ns-3. | Ponechať spoločný pohyb ako vstup pre jedno experimentálne časové okno. |
| Aktuálny ns-3/SNS-3 | Projekt má `ns-3.48`; miestny zdroj **nemá** `src/wave`, `OcbWifiMac` ani `Wifi80211pHelper`. Použitý `AdhocWifiMac` nie je OCB. | Pilot ďalej používať na diagnostiku paketovej trasy, bez tvrdenia o ETSI ITS-G5 zhode. |
| [Vanetza](https://github.com/riebl/vanetza/releases/tag/v26.06) | Tag `v26.06`, commit `fb6c551030dcc12b924299bf401e35e5fe814713` sa lokálne zostavil pre ciele `asn1` a `asn1_its_r2`. Obsahuje GN, BTP, DCC, bezpečnostnú vrstvu a ASN.1. Jeho aktuálny `CMakeLists.txt` ešte uvádza interné `project(Vanetza VERSION 26.02)`; preto identitu určuje **Git commit**, nie tento reťazec. | Primárny kandidát na C-ITS vrstvy v jednom procese ns-3. Zostavenie codecov ešte nepotvrdzuje integráciu routera ani rádia. |
| ASN.1 | Súbory v pripnutom commite sú `TS103900v231-CAM.asn`, `TS103831v231-DENM.asn` a `TS102894-2v241-CDD.asn`; wrapper treba výslovne vybrať ako `vanetza::asn1::r2::Cam/Denm`, lebo skrátené aliasy `Cam/Denm` odkazujú na Release 1. | Tento prototyp používa ETSI [CAM TS 103 900 V2.3.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf), [DENM TS 103 831 V2.3.1](https://www.etsi.org/deliver/etsi_ts/103800_103899/103831/02.03.01_60/ts_103831v020301p.pdf). Pred zmenou hlavného experimentu treba zosúladiť hlbokú analýzu, ktorá zatiaľ cituje v2.2.1. |
| BTP a GeoNetworking | [ETSI BTP register V2.4.1](https://www.etsi.org/deliver/etsi_ts/103200_103299/103248/02.04.01_60/ts_103248v020401p.pdf) určuje port CAM `2001`, DENM `2002`; [GeoNetworking EN 302 636-4-1 V1.3.1](https://www.etsi.org/deliver/etsi_en/302600_302699/3026360401/01.03.01_60/en_3026360401v010301p.pdf) rieši geografické adresovanie a hlavičky. Jedna konkrétna 41 B CAM prešla cez Vanetza BTP-B/SHB a ns-3.48 prijímač. | Funkčná interoperabilita konkrétnej fixture je overená; normatívna zhoda celého GN/BTP stacku, DCC a DENM ešte nie. BTP port nie je UDP port. |
| [Artery](https://github.com/riebl/artery/blob/master/docs/architecture.md) + Vanetza | Artery integruje SUMO/TraCI, Vanetza GN/BTP a rádio z INET/Veins v OMNeT++. Dokumentácia uvádza, že Artery samo rádio nemodeluje. V tejto VM nie je `opp_run`/OMNeT++ a miestny Artery build nie je overený. | Technická alternatíva pre cestný segment, ak spoločná integrácia Vanetza ↔ ns-3/OCB neprejde rozhodovacou skúškou. Dva izolované behy nie sú jeden end-to-end experiment. |

Závislosti dostupné bez inštalácie systémových balíkov: GCC 13.3, CMake 3.28.3, Boost 1.83. Pre túto izolovanú skúšku bolo vypnuté GeographicLib, Crypto++ a OpenSSL. CMake preto upozorňuje, že **neexistuje použiteľný bezpečnostný backend**. Pred tvrdením o podpísaných CAM/DENM treba tento stav odstrániť a urobiť vlastný pozitívny aj negatívny test podpisu/autorizácie.

## Reprodukovateľný malý test

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
tools/run_its_codec_probe.sh
```

Skript bez `sudo` stiahne pripnutý commit iba do ignorovaného `build/`, zostaví dva ciele s najviac dvoma úlohami a preloží `tools/its_codec_probe.cpp`. Lokálne vykonaný výsledok:

```text
CAM_UPER_BYTES=41
CAM_UPER_HEX=0202000003e93039005a4af9b60eaf87f100c80c80003a981e00384fc2b77e02c08a8333ffe1fffa00
DENM_UPER_BYTES=43
DENM_UPER_HEX=0201000003e980000001f4800380000030d40000000c3825257cdb0757c3f880640640001d4c0f05040400
VALIDATION=pass
NEGATIVE_TESTS=pass
```

**Obsah fixture, vstupy a jednotky:** CAM: stanica `1001`, `generationDeltaTime=12345 ms`, poloha `48.1486000° N, 17.1077000° E` v jednotkách `10⁻⁷°`, rýchlosť `13.90 m/s` v `0.01 m/s`, smer `90.0°` v `0.1°`, dĺžka `4.5 m` a šírka `1.8 m` v `0.1 m`. DENM: tá istá stanica, `actionId=(1001,7)`, `detectionTime=100000 ms`, `referenceTime=100100 ms`, tá istá poloha a situačný kód `accident2` so všeobecným podtypom `0`. Časy DENM sú **syntetické**, podľa CDD sú to plynúce milisekundy od ITS epochy 1. 1. 2004 so zohľadnením prestupných sekúnd; nepatria k dátumu nášho orbitálneho behu. Niektoré neistoty sú nastavené na hodnotu `unavailable`; nejde o kalibrované meranie GNSS. Správa nemá voliteľné doplňujúce kontajnery, podpis ani RSU prevod.

**Algoritmus a výstup:** vyplniť typované ASN.1 polia → skontrolovať obmedzenia schémy → zakódovať UPER → porovnať presné bajty s referenciou pre daný commit → dekódovať z bajtov → skontrolovať obmedzenia a rovnosť polí. Negatívne skúšky odmietnu zemepisnú šírku mimo schémy, DENM sequence mimo rozsahu a skrátený DENM. Veľkosť 41/43 B je len konkrétna fixture; celá on-air dĺžka by pridala BTP (4 B), premenlivú GeoNetworking hlavičku, prípadný bezpečnostný obal a MAC/PHY overhead. Nie je správne vložiť tieto bajty do UDP a výsledok nazvať kompletným ETSI ITS-G5.

## Podmienka ďalšej integrácie do ns-3

1. Každá ITS stanica (auto/RSU) dostane vlastný Vanetza `Router`, BTP dispatcher, DCC stav, aplikačné CAM/DENM služby a polohu zo SUMO. Simulačný adaptér implementuje Vanetza `Runtime` pomocou `ns3::Simulator::Schedule`; absolútny začiatok simulácie sa preloží na ITS epochu a musí mať správny UTC/TAI rozdiel. `Runtime` výslovne vyžaduje volania z toho istého vlákna. Nepoužívať stenu hodín počítača na plánovanie packet eventov.
2. Adaptér rádiového prístupu preloží `dcc::RequestInterface`/`access::Interface` na ns-3 `NetDevice` a prijatý surový GeoNetworking rámec so skutočnou MAC adresou zavolá do `Router::indicate`. `Router` podporuje SHB/GBC; v jeho rozhraní sú GUC, GAC a TSB označené ako nepodporované. Pred implementáciou scenára treba zvoliť podporovaný geografický profil. **Aktuálny ns-3.48 nemá OCB**: bez portu/validácie OCB MAC alebo iného vierohodného rádia integrácia nesplní cieľ cestnej vrstvy.
3. Pri V2V a V2I sa CAM/DENM prenáša ako `ASN.1 UPER → BTP → GeoNetworking → ITS-G5`, bez skrytej IPv4/UDP obálky. Príjemca dekóduje a zaznamená identitu stanice, `actionId`, čas, obsah a príčinu zahodenia. RSU ako aplikačný proxy vytvorí **nový** IP report pre satelitný backhaul so zachovanou väzbou na udalosť; musí sa odlíšiť od pôvodného DENM paketu.
4. Zaznamenať skutočný čas a identitu správy na každom hop-e. Test musí prejsť pre pohybujúce sa dve autá + RSU, korektne doručiť CAM/DENM, odmietnuť neplatnú/expirujúcu DENM, preukázať kolíziu a DCC reakciu pri hustote, potom previazať jeden unikátny report so satelitným paketom. Samostatne overiť podpisový profil, ak má byť súčasťou záverov.

**Priebežný záver:** Vanetza je zostaviteľný kandidát na aplikačné a GN/BTP vrstvy; pevná Release 2 CAM už prešla jedným ns-3 simulačným časom a 802.11p profilom s dekódovaním na prijímači. `AdhocWifiMac` stále nie je OCB a jeden úspešný rámec nevaliduje DCC, DENM, zabezpečenie ani výkon rádiového kanála. Rozhodnutie o cieľovom cestnom stacku preto zostáva podmienené presnejšou MAC/radio validáciou a viacnásobnými scenármi.
