# Jediný RSU tok cez dve fyzické LEO terminálové cesty

**Stav 22. 10. 2026 UTC: tri párované kontroly prešli.** Tento izolovaný pokus nadväzuje na [dve statické UT PHY cesty](two-leo-static-dual-ut-phy.md). Namiesto dvoch aplikácií vysielajúcich priamo z dvoch UT vytvára **jediný UDP socket na RSU**. Ten podľa výskumného stavového automatu vyberá jednu z dvoch 100 Mbit/s LAN vetiev k dvom už vytvoreným a trvalo priradeným terminálom. Ide o **prepnutie toku medzi dvoma fyzickými rádiami**, nie o handover jedného terminálu, rádiový attach alebo postup siete Iridium.

## Hypotéza, reálny význam a kontrola

Hypotetická RSU má dve nezávislé satelitné terminálové jednotky. V jednej politike posiela pred zmenou správy cez UT0→SAT0→modelový ISL→SAT1→GW; po potvrdení výskumného výberu posiela cez UT1→SAT1→GW. Správa v čase prepínania sa pri politike `drop before LAN, no queue` zahodí. Takáto redundancia môže byť predmetom výskumného návrhu dopravnej infraštruktúry, ale nie je automatickou vlastnosťou Iridium Certus 100. Test odpovedá iba na otázku, či sieťová cesta, stav kontroléra a účtovanie strát naozaj súhlasia.

| Variant | SAT0–SAT1 ISL | Potvrdenie výskumnej trasy SAT1 | Očakávaná GW aplikácia | RSU zahodenia |
| --- | --- | --- | --- | --- |
| `positive` | Áno | Áno, v 2,000 s | správa 1 a 2 | správa X |
| `no_isl` | Nie | Áno, v 2,000 s | iba správa 2 | správa X |
| `no_confirm` | Áno | Nie, `attach_failed` | iba správa 1 | správy X a 2 |

Prvý a tretí beh používajú bitovo totožné konštelačné a anténne vstupy. Druhý odstraňuje iba modelovú ISL hranu. Všetky tri majú seed **314159**, run **1**, začiatok **2026-10-22 12:46:52 UTC**, dve archivované dráhy GP/OMM objektov **43253** a **43258**, RSU/UT pri **48,1486° N, 17,1077° E**, hypotetickú GW pri **37,8167° N, 22,6667° E**, generické SNS-3 DVB-S2/RCS2 user/feeder PHY a konštantnú všesmerovú diagnostickú mapu **17 dBi**. Dva objekty z katalógu nie sú dôkazom ich vzájomného operačného crosslinku. Modelová ISL má predvolený P2P strop **1 Gbit/s** a čas podľa vzdialenosti/c.

## Modul, algoritmus, vstupy a výstupy

[`two-leo-dual-ut-policy.cc`](../../src/two-leo-dual-ut-policy.cc) vytvorí pevne priradené `UT3→SAT0` a `UT5→SAT1`. Jediná RSU aplikácia používa jeden UDP socket a pri každom odoslaní vyhodnotí stav `Sat0`, `Switching` alebo `Sat1`. Pakety majú presne **16 B** a rôzne celé aplikačné bajty `LEOGEO1`, `LEOGEOX`, `LEOGEO2`; ide o diagnostické identifikátory, nie o CAM, ICB1 alebo operátorské rámce. RSU pošle správu 1 v **1,000 s** cez LAN0. V **1,500 s** kontrolér zapíše `candidate_observed` podľa pevného výskumného harmonogramu; geometria sama ho nevyvoláva. V **1,600 s** prejde do `Switching`, v **1,750 s** zahodí X pred LAN, v **2,000 s** buď potvrdí *router gate* pre SAT1, alebo zaznamená zlyhanie. Správu 2 ponúkne v **2,250 s**; pri nepotvrdenom stave ju zahodí pred LAN. Žiadny paket sa počas výpadku neukladá ani neopakuje. Tých **400 ms** je zvolená skúšobná doba, nie namerané trvanie attachu.

Obe LAN vetvy majú **100 Mbit/s** a nastavené jednosmerné šírenie **100 µs**. RSU posiela na UT adresu `10.91.0.2` alebo `10.92.0.2`, cieľový UDP port `45908`; oba pakety používajú ten istý RSU source socket/port. Príslušná UT až po skutočnom LAN prijatí vytvorí **nový** UDP/IP datagram pre GW port `45909`. Preto aplikácia zachová identitu informácie, ale hlavičky LAN a satelitnej IP cesty nie sú rovnaké. Vstupné voľby `--expectIsl` a `--confirmSwitch` určujú len výskumné kontroly. Výstupom sú časovo označené RSU/control/UT/GW udalosti v µs, LAN PPP PCAP, satelitný `PacketTrace.log`, celý IPv4/UDP paket na prijímacom ISL zariadení a diagnostické PHY štatistiky. `PacketTrace` neobsahuje proprietárne rádiové bajty.

[`run_two_leo_dual_ut_policy.py`](../../tools/run_two_leo_dual_ut_policy.py) vyžaduje presné ns-3/SNS-3 commity a presne zodpovedajúci [patch priradenia UT](../../patches/sns3-338-static-ut-sat-id.patch). Používa existujúci hashovaný OMM archív a pomocný generátor dvoch statických UT; vytvorí tri oddelené behy, surové logy, PCAP, anténne/scenárové vstupy a `manifest.json` so SHA-256. Geometriu SAT0→ISL→SAT1 v prvom pakete a SAT1 user/feeder trasu pri druhom odoslaní počíta z rovnakého GP. Výskumná maska je **10°**, nie publikovaný prah služby.

[`check_two_leo_dual_ut_policy.py`](../../tools/check_two_leo_dual_ut_policy.py) najprv kontroluje všetky hashe a párové topológie. Každý LAN PPP PCAP dekóduje na IPv4/UDP, overí dĺžky a oba checksumy, zachovanie 16 B obsahu, spoločný UDP zdrojový port aj prijatie po nastavenom LAN oneskorení. Záporná kontrola `no_confirm` musí mať na LAN1 iba PCAP hlavičku. Checker spáruje prvý paket s UT3/SAT0, druhý s UT5/SAT1 a konečné prijatia na GW podľa modelového `PacketTrace`; prvý ISL datagram dekóduje vrátane checksumov a jednobajtová mutácia ho musí zneplatniť. Nezávislý topocentrický výpočet Skyfield kontroluje SAT1 user/feeder polohu pri druhom vyslaní a ISL geometriu; používa tie isté archivované GP elementy, preto nie je nezávislým meraním orbity. Checker uloží `verification.json`.

## Pozorovaný výsledok

| Udalosť | `positive` | `no_isl` | `no_confirm` |
| --- | ---: | ---: | ---: |
| RSU→UT0 LAN a UT0 satelitná ponuka | 1 | 1 | 1 |
| RSU→UT1 LAN a UT1 satelitná ponuka | 1 | 1 | 0 |
| RSU správy zahodené politikou | 1 | 1 | 2 |
| Prijaté aplikačné správy na GW | **2** | **1** | **1** |
| GW prijatia / tri RSU ponuky | **2/3** | **1/3** | **1/3** |

Všetky kontroly prešli. LAN0 preniesla prvých **16 B** v čase RSU TX **1 000 000 µs** a UT RX **1 000 103 µs**; po konfigurácii 100 µs jednosmerného šírenia vzniká ďalšia modelová serializácia/obsluha. Modelová ISL doručila celý **44 B IPv4/UDP paket** do SAT1 v **1 114 815 µs**. GW prijala prvý obsah v **1 126 182 µs** pri ISL, a druhý v **2 306 457 µs** cez SAT1 user/feeder bez ISL. Pri `no_isl` prišiel len druhý v **2 313 471 µs**. Pri `no_confirm` zostala LAN1 bez aplikačného paketu; prvý prišiel cez ISL. `PacketTrace` priradil v kladnom behu správe 1 ID **21** na UT3/SAT0 a správe 2 ID **65** na UT5/SAT1. Rozdiel času druhého prijatia medzi kontrolami je výsledok konkrétneho generického DVB behu, nie účinok reálneho ISL na tento druhý paket.

Pri druhom RSU vyslaní mala podľa nezávislej transformácie rovnakých GP prvkov SAT1 z miesta UT eleváciu **13,780°** a vzdialenosť **2 068,464 km**; z hypotetickej GW eleváciu **36,895°** a vzdialenosť **1 194,012 km**. Obe sú nad výskumnou 10° maskou. Toto stále nepotvrdzuje existenciu správneho lúča, registráciu terminálu ani brány. `positive` a `no_isl` majú identické celé LAN PCAP na oboch vetvách; prvá LAN vetva je identická aj v `no_confirm`.

Prvý pokus o nezávislú PCAP kontrolu chybne požadoval identické *časové značky* vysielacieho a prijímacieho záznamu na LAN. Zaznamenaný rozdiel **103 µs** je očakávaný; checker teraz vyžaduje bitovo identické datagramy a kauzálny rozdiel 100–110 µs. Táto oprava nemenila C++ simuláciu ani surové výsledky. Starší neúspešný `NaN` pri SAT1 z nedostatočného rozsahu diagnostickej mapy bol odstránený už v predchádzajúcom statickom UT experimente a zostáva opísaný tam.

## Reprodukcia a hranice tvrdenia

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_two_leo_dual_ut_policy.py \
  /tmp/ns3-sns3-338-feasibility results/two_leo_dual_ut_policy_repeat
.venv/bin/python tools/check_two_leo_dual_ut_policy.py \
  results/two_leo_dual_ut_policy_repeat
```

Príkaz vyžaduje prázdny výstupný adresár a už aplikovaný presný patch v pripnutom SNS-3 checkoute. Overené surové stopy sú v ignorovanom `results/two_leo_dual_ut_policy_verified_v2/`; manifest obsahuje hashe zdroja, binárneho programu, orbitálneho archívu, vstupov a všetkých surových stôp. Tento pokus **neprepína PHY/MAC stav jediného rádia**: oba terminály sú pripojené k svojim modelovým družiciam od začiatku, `attach_confirmed` znamená výlučne potvrdenie našej RSU politiky a nie satelitnú registráciu. Neobsahuje obsluhujúci beam operátora, jeho handover signalizáciu, skutočné antény, MAC, crosslink ani gateway. Jediný pár diagnostických správ neurčuje prevádzkovú PDR, jitter alebo najefektívnejšiu konšteláciu. Ďalším krokom je preniesť do tohto dvojcestného modelu **96 B ICB1 vytvorené z RSU prijatého CAM**, zdokumentovať schopnosť dvoch terminálov a porovnať kontrolované výpadky pri väčšom toku; single-radio handover zostáva samostatná technická úloha.
