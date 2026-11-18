# CAM z auta, report z RSU a bajty na dvojdružicovom modelovom ISL

**Stav 22. 10. 2026 UTC.** Tento experiment spája už overený SUMO→Vanetza→802.11p OCB→RSU tok s dvoma pohyblivými LEO objektmi a sieťovým medzisatelitným hopom v **jednej** udalostnej osi ns-3.38/SNS-3 3.38. Je to paketový referenčný model, **nie simulácia prevádzkovej služby Iridium**. [Iridium oficiálne opisuje LEO sieť s L-band user spojom a crosslinkmi](https://www.iridium.com/network); použitý generický DVB user/feeder PHY, all-direction anténa, manuálna ISL hrana a hypotetická brána tieto operátorské vlastnosti nereprodukujú.

## Hypotéza a kontrolné varianty

Hypotéza: šesť `ICB1` reportov vytvorených z *RSU prijatých* CAM možno preniesť cez modelovú trasu `auto → RSU → LAN → UT → SAT0 → ISL → SAT1 → proxy GW`, pričom na ISL zostanú overiteľné celé IPv4/UDP aj aplikačné bajty. Porovnávajú sa tri varianty:

| Variant | UT odosiela | Hrana SAT0–SAT1 | Očakávaný príjem GW |
| --- | ---: | ---: | ---: |
| `positive` | 6 ICB1 | Áno | 6 |
| `no_isl` | 6 ICB1 | Nie | 0 |
| `blocked` | 0 ICB1 | Áno | 0 |

Rovnaký SUMO pohyb, CAM obsah, RSU reporty, archivované dráhy, UTC štart, seed **314159** a run **1** sa zachovali. `no_isl` odstraňuje iba hranu v `isls.txt`; `blocked` ponecháva hranu, ale vypína odoslanie z UT. Negatívne varianty sú zásahmi do **modelu**, nie reálnymi výpadkami služby.

## Presný model a implementácia

- [`run_two_leo_isl_icb1.py`](../../tools/run_two_leo_isl_icb1.py) vezme existujúci kreslený cestný návrh, zmení jeho UTC počiatok na **2026-10-22 12:46:32Z**, znovu spustí SUMO a pripraví šesť časovo označených WGS84 waypointov pri t=20,0–22,5 s. Tým CAM a oba družicové modely používajú rovnaký UTC okamih. Z polohy `rsu0` priamo vytvorí bod pevného UT. Pôvodný návrh cesty je hashovaný a nemení sa.
- Archivované [CelesTrak GP/OMM](https://celestrak.org/NORAD/documentation/gp-data-formats.php) objekty **43253** a **43258**, ich SHA-256, pripnutá EOP tabuľka a presné Git commity ns-3/SNS-3 sú vstupmi. OMM→TLE konverzia sa kontroluje proti pôvodným OMM do 2 m. GP elementy sú údaje pre SGP4 dráhu, nie záznam o funkčnej službe, beamoch či skutočných crosslinkoch.
- [`editable-v2-ocb-sns3-dvb-gate.cc`](../../src/editable-v2-ocb-sns3-dvb-gate.cc) má experimentálny mód `two_sat_isl`. Auto vyšle 41 B UPER CAM v 85 B GN/BTP rámci cez 802.11p OCB. `car1`, `car3` a `rsu0` ho dekódujú. RSU z vlastného prijatého CAM zostaví **96 B ICB1**: 4 B označenie, 1 B verzia, 8 B ID udalosti, 8 B čas príjmu v µs, 2 B označenie a dĺžka, 32 B SHA-256 CAM, 41 B pôvodný CAM. Cez 100 Mbit/s modelovú LAN odíde do UT a následne do generickej SNS-3 DVB return-link cesty.
- User a feeder anténna mapa má všesmerový **konštantný 17 dBi zisk**; ide o čisto diagnostický predpoklad. Generický SNS-3 PHY/MAC error model ostáva zapnutý. Jeden `PointToPointIslNetDevice` hop medzi oboma družicami je predvolene **1 Gbit/s** a jeho geometrický čas je približne vzdialenosť/c. Skutočný Iridium ISL rádiový prenos, smerovanie, handover, lúče ani prístupový protokol tu nie sú implementované. Bod **37,8167° N, 22,6667° E** je proxy pri Nemei, **nie Iridium brána**.
- Pasívny callback na prijímacom ISL zariadení SAT1 ukladá celý **124 B IPv4/UDP paket** po odstránení PPP. [`check_two_leo_isl_icb1.py`](../../tools/check_two_leo_isl_icb1.py) preverí dĺžky, IP/UDP checksumy, adresy, porty, 96 B `ICB1` proti reportu vytvorenému RSU, jeho CAM a SHA-256, časové poradie aj jednoznačné ID v `PacketTrace`. Kontroluje aj bitovú zhodu TLE/UT/GW vstupov, presne jediný rozdiel v `isls.txt`, polohu UT odvodenú z RSU a konštantnú 17 dBi mapu. Jednobajtová mutácia obsahu musí zlyhať na UDP checksume. Rovnako overí zemský zákryt a obe pozemné elevácie v čase **každého** ISL paketu.

Všetky vzdialenosti sú v km, pozície WGS84 v stupňoch a metroch, čas logov v µs od UTC počiatku. Geometria počíta konzervatívnu guľu Zeme s polomerom **6 378,137 km** a výskumnú **10°** elevančnú masku. Skyfield aj Astropy v súvisiacich kontrolách používajú tie isté GP elementy a SGP4; nie sú externou presnou efemeridou.

## Surové výsledky a interpretácia

V `positive` behu prešlo **6 CAM TX**, **18 pozemných dekódovaní**, **6 RSU ICB1**, **6 UT odoslaní**, **6 celých ISL IPv4/UDP paketov** a **6 prijatí na GW**. `no_isl` zachoval 6 UT odoslaní, ale na SAT1 ani GW nedoručil skúšobné reporty; `blocked` zachoval RSU aj LAN, no nemal UT satelitné odoslanie. Kontrola potvrdila presných 96 B každého reportu od RSU po ISL a GW. Jeden zachytený ISL paket má IPv4 zdroj `250.1.0.2`, cieľ `10.2.0.2`, UDP cieľový port `45000`, dĺžku IPv4 **124 B**, UDP **104 B** a obsah **96 B ICB1**. Nie je to surový proprietárny rádiový rámec.

ISL prijímač videl reporty pri t = **20,115899; 20,617907; 21,115921; 21,615931; 22,115942; 22,615953 s**. Šesť výpočtov z archivovaného GP dalo rozsah elevácie RSU UT→SAT0 **13,606–13,861°**, SAT1→proxy GW **36,465–36,970°**, vzdialenosť družíc približne **4 034,319 km**, rezervu spojnice nad konzervatívnou Zemou **482,122–482,144 km** a vákuový ISL čas približne **13,457 ms**. `PacketTrace` po zaokrúhlení súhlasí s týmto modelovým časom do 0,1 ms. Tieto veličiny dokazujú iba konzistenciu zvolenej geometrie a idealizovaného hopu.

Pri presných UTC okamihoch UT odoslania mala z dvojice najvyššiu eleváciu družica **43253** pre prvé štyri reporty (12:46:52,000330 až 12:46:53,500327) a **43258** pre posledné dva (12:46:54,000326 a 12:46:54,500325). Vložená user linka však v celom behu zostala **pevne na 43253**, ktorej elevácia aj pri poslednom reporte bola ešte približne **13,617°**. Všetkých šesť úspechov preto **neoveruje handover**; režim iba transparentne ukazuje, že zmena geometricky najvyššieho kandidáta automaticky nemení obsluhujúcu družicu. Identita reálne pridelenej družice v službe Iridium nie je z OMM zistiteľná.

Šesť úspešných modelových časov CAM TX→GW aplikácia bolo **129 117; 122 102; 120 114; 120 116; 120 119; 120 122 µs**; priemer **121 948,3 µs**. Priemer absolútnych rozdielov susedných úspešných časov bol **1 802,2 µs**. Sú to výsledky jedného krátkeho nezaťaženého referenčného behu, nie odhad PDR, jitteru alebo latencie reálnej služby. Z týchto čísel nemožno zoradiť Iridium, Starlink a Globalstar.

Pri `no_isl` sa zmenila topológia SNS-3 a tým pridelená MAC adresa v hlavičke GN; v prvom GN/BTP rámci sa odlišoval bajt na offsete **19**. Preto celé pozemné OCB PCAP nie sú bitovo zhodné s kladným variantom. **Samotný 41 B CAM, jeho RSU príjem, všetkých šesť 96 B reportov a LAN PCAP sú zhodné.** `positive` a `blocked` majú zhodné aj celé OCB PCAP. Bez ISL sa v `PacketTrace` vyskytli opakované UT PHY vyslania pred sieťovým príjmom na SAT0, ale žiadny dátový príjem SAT1/GW; checker preto dovolí PHY retransmisie, vyžaduje jeden sieťový príjem a nulové doručenie za chýbajúcou hranou.

## Reprodukcia a neúspešné pokusy

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_two_leo_isl_icb1.py \
  /tmp/ns3-sns3-338-feasibility results/two_leo_isl_icb1_repeat
.venv/bin/python tools/check_two_leo_isl_icb1.py results/two_leo_isl_icb1_repeat
```

Výstupný priečinok musí byť nový alebo prázdny. Runner ukladá scenár, SUMO FCD, waypointy, presné satelitné vstupy, tri raw stopy `trace.csv`, `PacketTrace.log`, PCAP, build log, kontrolu pozemnej časti, hashovaný manifest a zdrojové commity. Checker vytvorí `isl-verification.json`; pre pôvodný beh vrátil `status=PASS`, šesť ISL paketov a doručenie **6/0** s hranou/bez hrany.

Prvý integračný pokus zlyhal, pretože SNS-3 parser rozdelil argument UTC s medzerou a C++ odmietol neplatný počiatok. Druhý opakoval tú istú chybu, aby sa zachoval presný text zlyhania; finálna verzia prijíma ISO argument `2026-10-22T12:46:32` a interne ho normalizuje. Prvý nezávislý checker chybne vyžadoval bitovo zhodnú GN hlavičku aj po zmene topológie, potom iba jedno UT PHY vyslanie a neokrúhlené časové poradie pred SAT1 PHY. Surové stopy ukázali odlišnú GN MAC adresu, viacero PHY retransmisií a zaokrúhlenie `PacketTrace`; checker bol spresnený na **identický CAM/report**, explicitné retransmisie a časovú toleranciu **0,1 ms**. Žiadna z týchto úprav nemení výsledok simulácie.

## Hranice a ďalší overovací krok

Tento integrovaný míľnik už obsahuje dve pohyblivé LEO pozície, modelový ISL hop a presné sieťové bajty ICB1. Stále neoveruje, či objekty **43253–43258** boli v danom čase aktívnymi susedmi, či terminál mal kompatibilnú službu, skutočnú bránu, pokrytie lúča alebo dostupnú kapacitu. Všesmerový zisk **17 dBi** a **1 Gbit/s** P2P ISL by ako operátorský profil boli nepodložené. Nasleduje kalibrovaný terminál/lúč/brána a dynamický výber družice s handoverom; až potom možno zostaviť porovnateľné scenáre služieb. UI zatiaľ tento nový dvojdružicový mód nevystavuje ako voľbu kresleného scenára; spúšťa sa uvedeným reprodukovateľným príkazom.
