# Pohyblivé CAM a konzervatívna brána kandidátskej geometrie Iridium

**Stav:** overený integračný test, 22. 10. 2026. Tento samostatný variant rozširuje [pohyblivý CAM experiment](moving-cam-backhaul.md); jeho pôvodný runner a výsledky nemení.

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
bash tools/run_moving_cam_iridium_gate.sh
```

Runner kompiluje s jednou úlohou a uloží `results/moving_cam_iridium_gate/{ungated,geometry_positive,geometry_block}.csv`, šesť rámcov na každom Wi-Fi PCAPe príslušného prípadu, dekódované polia CAM, stopy brány, `verification.json`, `manifest.json` a vstup zámerne poškodeného plánu s chybovým výstupom. Nepotrebuje `sudo`.

## Účel a presný mechanizmus

Hypotéza: pohyblivé auto z predchádzajúceho testu odovzdá CAM RSU bez ohľadu na stav vzdialeného servisného segmentu; pri povolenej kandidátskej geometrii má RSU report pokračovať cez UT proxy na server, pri blokovaní sa musí zastaviť. Celý sled udalostí beží v **jednom ns-3.48 čase** s UTC počiatkom `2026-10-22T12:45:00Z`. Vanetza v26.06 používa ten istý simulovaný čas. SUMO je archivovaný beh v bodoch 0,5 s; nesynchronizuje sa živým procesom. Pozemná vetva je skutočný ASN.1 Release 2 CAM → BTP-B → GN → ns-3 802.11p `AdhocWifiMac` → RSU príjem. RSU vytvorí nový UDP/IPv4 report s presnými CAM bajtmi a SHA-256, ktorý ide 1 Gbit/s LAN do UT. Podrobné polia, jednotky, predpoklady a limity pozemnej vetvy uvádza [pôvodný experiment](moving-cam-backhaul.md).

`src/moving-cam-iridium-gate.cc` má voliteľný argument `--geometry`. Bez neho je 22 kbit/s point-to-point servisný segment otvorený a jeho dodatočný kanálový delay je 0. S ním číta **pripnutý** [kandidátsky Iridium plán](../../data/derived/multi-constellation/iridium-candidate-switch-bratislava-20261022.ns3-schedule.csv). SHA-256 musí byť `c1653be357e49dfd9ae654a3a3c57c556c19ac5100a8ced8a9952c7a3f5f0ca3`; C++ ho prepočíta a odmietne iný súbor pred spustením siete. Runner ho kontroluje tiež a verifier znovu porovnáva s metadátami. Parser ďalej požaduje 12 spojitých 30 s intervalov, pôvod 12:45 UTC, koniec 12:51 UTC, 64 znakov pôvodových hashov a vybrané katalógové ID/OMM hash pri zapnutom intervale. Mimo okna zlyhá uzavretým stavom. [Pôvod plánu a jeho úplné pravidlo](../experiments/iridium-candidate-switch-gate.md) sú zaznamenané osobitne.

Plán hodnotí pevné miesto RSU/UT `(48,1486° N,17,1077° E,0 m)`. Polootvorený interval `[t_i,t_{i+1})` povoľuje prenos, len keď majú oba vzorkované konce rovnaké vybrané katalógové ID nad testovacím prahom elevácie 10°. V prvých dvoch intervaloch `[0,30)` a `[30,60)` je kandidát `43253`; `one_way_vacuum_delay_ns` je postupne **5 222 076 ns** a **5 832 199 ns**. Plán vypne skutočný interval `[90,120)` pre zmenu katalógového ID, ale náš šesťbodový CAM úsek končí v 31,5 s, takže tento prirodzene vypnutý interval **nie je jeho negatívnym testom**.

Pri zmene stavu v ns-3 sa `PointToPointChannel.Delay` nastaví na plánovaný jednosmerný vákuový `r/c` (maximum dvoch koncových vzoriek) a `PointToPointNetDevice.ReceiveErrorModel` na prijímači na packet rate 0 alebo 1. Pred udalosťou t=0 je príjem blokovaný. UT navyše kontroluje stav pri odoslaní reportu. Preto správu pri vypnutom stave vôbec neodošle do servisného segmentu, kým rámec odoslaný v povolenom stave a prichádzajúci po vypnutí môže padnúť na prijímači. ns-3 dokumentuje použitie [RateErrorModel a PhyRxDrop pre NetDevice](https://www.nsnam.org/docs/models/html/error-model.html). Toto je **umelá geometrická brána** na abstraktnom P2P linku, nie simulovaný satelitný RF fade ani protokol operátora.

Na test hranice runner pridá explicitný **syntetický override** `[30,520 s,31,020 s)`, teda `--block_start_us=30520000 --block_end_us=31020000`. Plán CSV zostáva nedotknutý a v tomto čase je sám povolený. Override má prednosť pred plánom a je v stopách označený `test_override`. Používa sa výhradne na kontrolu správania paketov pri vypnutí uprostred letu; **nepredstavuje odhadovaný výpadok ani handover Iridia**. Pri opätovnom zapnutí sa použije pôvodný plánovaný delay.

## Výsledky a bajtová kontrola

| Prípad | CAM auto→RSU | Reporty na serveri | Pozorovanie |
|---|---:|---:|---|
| `ungated` | 6/6 | 6/6 | Kontrolný 22 kbit/s serializer bez geometrie a bez dodatočného delay. |
| `geometry_positive` | 6/6 | 6/6 | Kandidát 43253 je v celom úseku povolený. |
| `geometry_block` | 6/6 | 4/6 | Report t=30,5 s spadol už po TX počas letu; report t=31,0 s zastavil UT pred service TX. |

Pri pozitívnom geometrickom behu začali reporty na `SERVICE_PHY_TX` t=29,000267 a 30,000267 s. Prvý došiel o **51 040 µs**, druhý o **51 650 µs**: v oboch prípadoch 126 B PPP/IPv4/UDP rámec pri 22 kbit/s potrebuje približne 45 818 µs serializácie, ku ktorej sa pripočíta príslušný vzorkovaný jednosmerný `r/c`. Od pôvodného vyslania CAM po server je to 51 307, respektíve 51 917 µs. Tieto čísla nie sú oneskorením reálnej Iridium služby.

V negatívnom behu odišiel report pre CAM t=30,5 s na servisný segment v **30 500 267 µs**. Brána sa vypla v **30 520 000 µs**; prijímač v **30 551 917 µs** emitoval `SERVICE_GATE_RX_DROP` s presnými 126 B pôvodného rámca. Server ho nikdy neprevzal. Report pre CAM t=31,0 s dosiahol UT v **31 000 267 µs** a je zapísaný ako `UT_GATE_BLOCK_TX`, bez servisného rámca. Report t=31,5 s po opätovnom zapnutí prešiel. Tento výsledok priamo dokazuje, že testované ns-3 ReceiveErrorModel pravidlo vyhodnotí aj príchod už odoslaného rámca pri hranici.

`tools/check_moving_cam_iridium_gate.py` nezávisle kontroluje všetkých šesť CAM oproti uloženým WGS84/SUMO bodom, presné 41 B CAM, 85 B GN/BTP/CAM a 96 B reportov, dva raw 802.11 PCAPy, SHA-256 CAM, PPP/IPv4/UDP dĺžky a checksumy na každom príslušnom hope. Kontroluje servisné TX/RX/drop rámce, výpadok jediného packetu počas letu, absenciu servisného TX pri UT bloku a čas `126×8/22000 + r/c` s toleranciou 2 µs. Osobitný test zmení jednu kópiu CSV: C++ ju pred vytvorením siete odmietne hláškou `Iridium candidate schedule SHA-256 mismatch`; originálny plán sa nemení. Prvé spustenie počas vývoja už prenieslo pakety, no runner ukončil chýbajúcim verifier skriptom; po doplnení verifieru kompletný runner končí kódom 0. Konfigurácie, neúspešný zámerný beh, surové výsledky a hashe sú zachované v `results/moving_cam_iridium_gate/`.

## Čo model nedokazuje

Plán vychádza z retrospektívnej polohy katalógových objektov pri **pevnom mieste** RSU/UT, nie z aktívneho operátorského výberu satelitu. Medzi 30 s koncovými vzorkami nezaručuje neprerušenú viditeľnosť. Objekt `43253` je štítok geometrického kandidáta; v ns-3 sa nevytvára satelitný uzol. P2P link od UT priamo k serveru pridáva **iba jednu** dobu šírenia UT→kandidátsky objekt a serialization limit 22 kbit/s. Chýba cesta satelit→gateway→server, reálny beam, antény, RF/MAC, rušenie, error-rate a retransmisie operátora, attach, handover, inter-satellite link aj servisné oprávnenie. Všetky tieto chýbajúce časti by museli byť modelované alebo merané pred tvrdením o reálnej dostupnosti, RTT alebo presnom paketovom správaní Iridium. Výsledok je obhájiteľný **ako integrácia CAM paketovej cesty s konzervatívnou geometriou a reprodukovateľným kontrolným výpadkom**, nie ako validovaný operátorský satelitný simulátor.
