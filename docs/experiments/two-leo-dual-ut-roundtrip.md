# Obojsmerná paketová cesta cez modelové LEO user, feeder a ISL

**22. 10. 2026, stav: prešlo v izolovanom diagnostickom teste.** Tento míľnik rozširuje [dvojterminálovú RSU politiku](two-leo-dual-ut-rsu-policy.md) o nový **24 B aplikačný echo záznam** od GW späť cez SNS-3 do RSU. Používa ns-3.38/SNS-3 3.38 a dva trvalo vytvorené UT pri jednej RSU; neimplementuje medzi družicový handover jedného terminálu ani Iridium Certus PHY/MAC. Archívne GP objekty 43253 a 43258 sú modelové pohyblivé LEO uzly, nie overený aktívny pár crosslinkov.

## Hypotéza a fyzikálna kontrola

Ak report RSU prejde UT0→SAT0→ISL→SAT1→hypotetická GW, dokáže sa odpoveď po zvolenej **jedinej kvalifikovanej feeder trase SAT1** vrátiť SAT1→ISL→SAT0→UT0→RSU? Druhá kontrola skúma priamy UT1/SAT1. Odstránenie jedinej modelovej ISL hrany musí zastaviť report UT0 aj jeho odpoveď, ale ponechať priamy UT1 tok. Potlačenie výskumného potvrdenia RSU trasy musí odstrániť druhý tok ešte pred LAN.

Pri prvom pokuse bez explicitnej spätnej trasy SNS-3 **doručilo** odpoveď na UT0 priamo z feeder PHY SAT0, teda bez spätného ISL. Nezávislá geometria v tom čase dala pre proxy GW→SAT0 iba približne **0,59°** elevácie, pod našou experimentálnou **10° maskou**. Tento beh zlyhal na kontrolnej podmienke `return ISL reply observation disagrees with topology`; nie je dôkazom vierohodného satelitného return path. Dôvod bol v sieťovom stave: SNS-3 pri stavbe beam topológie priradilo GW IP/ARP trasu k UT0 cez GW zariadenie SAT0, hoci report UT0 smeroval cez ISL ku GW pri SAT1. Viditeľnosť ani kvalifikácia feeder úseku nie je automatickým zákazom takého prenosu v generickom modeli.

Finálny diagnostický variant volá `SatUserHelper::UpdateGwRoutes` pre MAC UT0 z GW rozhrania SAT0 na GW rozhranie SAT1. UT0 **zostáva fyzicky priradené SAT0**. Paket odpovede musí teraz vstúpiť do modelu cez SAT1 feeder, potom byť smerovaný cez existujúcu ISL mapu do SAT0. Checker kontroluje GW `PacketTrace` `FWD` na SAT1, SAT1 sieťový príjem, celý IPv4/UDP paket na prijímacom ISL zariadení SAT0, SAT0 user PHY, UT0 sieťový príjem a 100 Mbit/s LAN do RSU. Výskumná 10° maska je preukázaná na **použitej** feeder/user ceste a vylučuje obídenú priamu SAT0 feeder cestu; SNS-3 sám masku neimplementuje ako všeobecné pravidlo služby.

## Algoritmus, vstupy a výstupy

[`two-leo-dual-ut-roundtrip.cc`](../../src/two-leo-dual-ut-roundtrip.cc) používa jeden RSU UDP socket na odoslanie dvoch rôznych 16 B skúšobných obsahov. UT pri LAN príjme vytvorí **nový** IPv4/UDP datagram cez vlastné statické SNS-3 rádio. GW na prijatý obsah odošle nový `GRA1` (24 B: ASCII `GRA1`, 32-bitové big-endian poradové číslo 1/2, celý pôvodný 16 B obsah). Nie je to ETSI ani operátorská správa. Odpoveď ide na UDP port **45911** príslušného UT user uzla; UT ju po overení zhodného obsahu a cesty odošle cez svoju LAN na RSU port **45912**. Pri čakaní 1,600–2,000 s RSU podľa explicitnej politiky zahodí tretiu ponuku bez frontu. Čas a potvrdenie sú skúšobné predpoklady, nie nameraný attach.

[`run_two_leo_dual_ut_roundtrip.py`](../../tools/run_two_leo_dual_ut_roundtrip.py) overí presné commity, archívne OMM/EOP, patch statického priradenia dvoch UT, zostaví program a vykoná tri párované behy s ns-3 semenom **314159/run 1**, UTC počiatkom **2026-10-22 12:46:52Z**, pevným bodom UT **48,1486° N, 17,1077° E** a proxy GW **37,8167° N, 22,6667° E**. Ukladá všetky vstupy, binárny súbor, `PacketTrace.log`, obojsmerné PPP PCAP, behové logy, orbitálnu geometriu v čase oboch ISL smerov a SHA-256 manifest. Diagnostická anténna mapa má **17 dBi vo všetkých smeroch**; vložená P2P ISL má modelovú kapacitu **1 Gbit/s**. Sú to výskumné voľby, nie parametre služby.

[`check_two_leo_dual_ut_roundtrip.py`](../../tools/check_two_leo_dual_ut_roundtrip.py) kontroluje manifest a surové stopy, úplný `GRA1` obsah na GW/UT/RSU, časové poradie, oba LAN PCAP v oboch smeroch, dĺžky/adresy/porty a IPv4/UDP checksumy modelovej spätnej ISL (52 B IPv4 paket), príslušné `PacketTrace` ID, zákaz priameho GW0 feeder pre toto ID a negatívnu jednobajtovú mutáciu checksumu. Orbitálny prepočet v Skyfield používa tie isté GP elementy ako pôvodný SGP4 výpočet, takže nekvalifikuje operátorskú orbitu nezávislým meraním.

## Párované výsledky

| Variant | RSU reporty prijaté GW | Odpovede prijaté RSU | Spätný ISL obsah | RSU odoslanie→RSU odpoveď |
| --- | ---: | ---: | ---: | --- |
| `positive` | 2/3 ponúk | **2** | 1× `GRA1` pre UT0 | UT0 **171 172 µs**; UT1 **71 041 µs** |
| `no_isl` | 1/3 | **1** (UT1) | 0 | UT1 **92 067 µs** |
| `no_confirm` | 1/3 | **1** (UT0) | 1× `GRA1` | UT0 **171 172 µs** |

V kladnom behu GW odoslala prvý `GRA1` pri **1 126 182 µs**, SAT0 prijala celý spätne smerovaný IPv4/UDP paket na ISL pri **1 158 011 µs** a RSU prijala rovnaký 24 B obsah pri **1 171 172 µs**. Tomuto obsahu patrí SNS-3 `PacketTrace` **ID 37** na GW/SAT1/SAT0/UT0; druhému priamemu obsahu patrí ID **83**. Kontrola bez ISL zachovala UT1 report aj odpoveď, ale UT0 report sa nedostal na GW, takže nemohla vzniknúť jeho odpoveď. Rozdiel modelového času UT1 medzi topológiami s/bez ISL **nie je čas ISL na UT1 trase**; krátke deterministické behy majú odlišný stav generického plánovača. Toto nie je vzorka komerčnej RTT, PDR či jitteru.

## Reprodukcia a hranice

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_two_leo_dual_ut_roundtrip.py \
  /tmp/ns3-sns3-338-feasibility results/two_leo_dual_ut_roundtrip_repeat
.venv/bin/python tools/check_two_leo_dual_ut_roundtrip.py \
  results/two_leo_dual_ut_roundtrip_repeat
```

Overené surové dáta sú v ignorovanom `results/two_leo_dual_ut_roundtrip_verified_v2/`; kontrola vypísala `PASS`, odpovede **2/1/1**. Časy sú µs od UTC počiatku, geodetické súradnice stupne/metre. Model neobsahuje prevádzkové prideľovanie beamov, skutočnú GW, servisný modem/PHY/MAC, queue/retransmission pravidlá ani handover jediného rádia. Spätné potvrdenie je zatiaľ pri **izolovaných 16 B obsahoch**, nie pri spoločnom SUMO CAM/96 B ICB1 toku; ten je ďalším integračným krokom. Prijatie IP bajtov na ISL a v aplikáciách nedokazuje znalosť proprietárnych RF rámcov.
