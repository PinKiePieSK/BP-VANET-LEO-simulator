# Spoločná časová os CAM → RSU → ICB1 → LEO DVB referencia

**Stav:** kontrolovaný integrovaný pilot z 22. 10. 2026. Ide o **hypotetickú** LEO satelitnú anténu, hypotetickú GW proxy a referenčný DVB-S2/RCS2 model SNS-3 3.38; výsledok nie je simuláciou produktu Starlink, Iridium ani Globalstar. Účel je overiť celú trasu jedného obsahu vo **svojom jednom ns-3 kalendári udalostí** vrátane skutočného 802.11p OCB príjmu a skutočných satelitných PHY/MAC udalostí. Samostatný [16 B LEO packet probe](sns3-338-leo-separate-user-feeder-37741.md) overil dve smerové anténne mapy pred týmto pokusom.

## Hypotéza a kontrola

Hypotéza: počas šiestich párovaných časových vzoriek 20,0–22,5 s môže `car0` vyslať CAM cez ITS-G5/OCB; RSU má po vlastnom prijatí vytvoriť obsahovo korelovaný 96 B report `ICB1`; pevný terminál UT ho prenesie cez jeden archivovaný LEO GP objekt 37741 a oddelený user/feeder lúč do aplikácie pri bráne. Kontrolný variant `block_satellite=1` zastaví iba ponuku reportov z UT do satelitnej služby. Vyžadujeme bajtovo identické pozemné PCAP/obsahy a nezmenený dopravný i orbitálny vstup. Nulový serverový príjem v kontrole izoluje závislosť od satelitnej cesty; nie je to prirodzený výpadok služby.

## Vstupy, model, jednotky

Runner `tools/run_editable_v2_ocb_sns3_leo_reference.py` načíta **jeden** editovateľný dopravný podscenár `data/inputs/editable-road-v2/packet-subset.json`, spustí SUMO a pripraví šesť WGS84 waypointov pre `car0`, `car1`, `car3`, `rsu0`. Pozemné uzly používajú Vanetza CAM/GN/BTP nad ns-3 `OcbWifiMac`, 10 MHz kanál 180 pri 5,9 GHz a predchádzajúcim experimentom definované Friis prostredie. To je experimentálny otvorený kanál, nie kalibrovaná mestská propagácia. RSU vzniknutý 96 B ICB1 nesie pôvodný 41 B CAM, korelačné ID, čas príjmu a SHA-256. LAN RSU→UT je 100 Mb/s P2P s 100 µs nastaveným propagation delay. Čas simulácie 25 s, RNG seed **314159**, run **1**.

Satelitný vstup tvorí rovnaký archivovaný OMM/GP záznam a odvodené TLE ako v izolovanom referenčnom teste. SNS-3 SGP4 štartuje v `2026-10-22T12:45:00Z`; prvý CAM vznikne v UTC `12:45:20Z`. Je to retrospektívny GP archív získaný po simulovanom čase. UT je pevne pri RSU (`48,1480603° N, 17,1035340° E`), v C++ anténnom výpočte s 0 m výškou; RSU waypoint má 1 cm nad kotvou. GW (`37,8167° N, 22,6667° E`) je iba mestská proxy v Grécku. Lúč 30 je nasmerovaný na UT, lúč 43 na túto proxy pri UTC `12:45:20Z`, oba majú **výskumnú** šírku 22° a maximálny zisk 17,465 dBi. Mapy sa pohybujú podľa implementácie SNS-3; stav brány alebo skutočný beam operátora sa z nich nedá vyvodiť. Priamo auditovaných je šesť polôh, elevácií a ziskov. SNS-3 počíta pozemné `GeoCoordinate` na guli polomeru 6 378 137 m, nie na WGS84 elipsoide.

Satelit má zapnuté pôvodné forward/user a return/feeder `EM_AVI` chybové modely, sieťovú regeneráciu a generické SNS-3 DVB-S2/RCS2 plánovanie. Nepoužívame `EM_NONE`. Nie je tu operátorský modem, autorizácia ani overený servisný beam. V [hlbokej analýze](../hlbkova-analyza-komunikacie.md) sú tieto hranice kritériom, prečo sa úspech vlastnej DVB referencie nesmie zamieňať za presnosť Starlinku, Iridia či Globalstaru.

## Pozorovanie a testy

Kladný a blokovaný variant vyslali po **šesť** CAM z `car0`; `car1`, `car3` a `rsu0` ich dekódovali po šesť, spolu **18** príjmov. RSU vytvorila 6/6 ICB1 reportov výlučne z dekódovaných bajtov a UT prijal 6/6 cez LAN. V kladnom variante šesť reportov dorazilo po SNS-3 PHY/MAC do aplikácie GW, v blokovanom **0/6**. Overovač porovnal každý 41 B CAM, 85 B GN/BTP/CAM, všetkých šesť 96 B reportov na RSU/UT/GW, SHA-256 obsahu, časové poradie udalostí, OCB a LAN PCAP, šesť korelovaných interných satelitných PacketTrace ID a pri každom trasu UT ND/PHY → SAT PHY → GW PHY/ND. Pozemné PCAP oboch variantov sú binárne totožné. Paketové ID v `PacketTrace` je korelácia z kontrolovaného časovania toku; stopa neuchováva satelitné RF bajty.

`SatPhyRxCarrier` log pri kladnom behu obsahuje **249 dopredných** a **31 návratových** `EM_AVI` rozhodnutí, všetky bez zaznamenanej chyby. V blokovanom behu zostalo 249 dopredných a 22 návratových rozhodnutí bez chyby; rozdiel vyplýva z chýbajúcich šiestich dátových reportov a súvisiaceho modelového prenosu. Tieto počty nie sú pokusmi aplikácie o vyslanie CAM ani odhadom PDR.

Šesť úspešných modelových časov `CAM_TX→GATEWAY_REPORT_RX` je **119 626, 113 630, 111 662, 111 684, 111 675, 111 697 µs**; priemer **113 329 µs**. Priemer absolútnych zmien medzi susednými úspešnými časmi je **1 603,4 µs**. Ide o definíciu pozorovanej premenlivosti šiestich paketov pri jednom semene; nie o servisný jitter alebo jeho štatistický odhad. Modelová aplikačná úspešnosť v tomto behu je 6/6, kontrola 0/6. Pri jednom semene a nezaťaženom satelitnom prístupe z toho nemožno odhadnúť prevádzkovú PDR či dostupnosť. Prvý report prešiel cez satelitné interné ID 258, ostatné 279, 293, 308, 323, 338. Presné časy, geometria, manifest a obmedzenia sú v `results/editable_v2_ocb_sns3_leo_reference/verification.json`.

Pri všetkých šiestich orbitálnych vzorkách v **oboch** variantoch mala guľová elevácia oboch pozemných koncov najmenej **20,041°**. Najväčší rozdiel interpolovaného anténneho zisku od priameho 3D výpočtu bol **0,00208 dB**. Kladný a blokovaný variant mali rovnaké vzorky s výnimkou stopy v indexe 2: rozdiel modelovej výšky bol **3,443 cm** a rozdiely vypísaných ziskov boli pod **0,000004 dB**. Kontrola ich preto posudzuje fyzikálnou toleranciou 100 m / 0,5 dB a každý variant osobitne voči nezávislej efemeride. Prvý pokus o audit vyžadoval **doslovne identické textové riadky** a na tejto malej odchýlke skončil, hoci bajtový paketový checker prešiel. Neúspech je evidovaný; oprava testuje merané veličiny a ich odchýlku. Rozdiel nie je empirická chyba orbity ani dôkaz prevádzkového handoveru.

## Reprodukcia a výstupy

Použi pripnutý ns-3/SNS-3 checkout, lokálne zostavenú Vanetza v manifeste a projektové Python prostredie. Výstupný priečinok musí byť prázdny:

```bash
.venv/bin/python tools/run_editable_v2_ocb_sns3_leo_reference.py \
  /tmp/ns3-sns3-338-feasibility /tmp/novy-ocb-sns3-leo-beh
```

Runner overí Git commity, hashované scenárové a anténne vstupy, skompiluje integráciu, vykoná kladný i blokovaný variant, spustí bajtový overovač a nezávisle porovná šesť SNS-3 výšok/ziskov s SGP4/3D výpočtom. Výstup obsahuje `waypoints.csv`, vstupný SUMO FCD, `positive/` a `blocked/` raw CSV/PCAP/PacketTrace/logy, `check.log`, `verification.json`, `run-manifest.json`. Uložený manifest viaže zdrojový kód, binárku, vstupy a výsledok SHA-256.

Po pridaní voliteľného LEO režimu znovu prešiel aj pôvodný GEO runner `tools/run_editable_v2_ocb_sns3_dvb_gate.py` s 6/6 kladnými a 0/6 blokovanými reportmi. Opakovaný LEO beh zachoval oba `PacketTrace.log` bajtovo identické s predchádzajúcim auditovaným behom; textový `run.log` zahŕňa adresy objektov závislé od procesu a nie je binárne deterministický. Aj predchádzajúca izolovaná jednolúčová kontrola znovu potvrdila 0/1 aplikačné doručenie pri zisku približne 13,32/13,30 dBi. Sú to cielené regresné skúšky, nie nezávislé validačné merania siete.

## Hranice interpretácie a ďalšia fáza

Pilot preukazuje spoločné fungovanie lokálneho VANET toku a LEO referenčného DVB rádia. Nepreukazuje presnú kapacitu, rámce alebo latenciu žiadneho z troch komerčných operátorov. Chýba pozorované operátorské priradenie brány, beam, terminálový link budget, viacdružicový handover, ISL, dopravné tienenie a zaťažený satelitný scheduler. Report končí na GW aplikácii; odpoveď k autu sa v tomto LEO DVB behu netestuje. Pri väčšom scenári treba vopred určiť viac orbitálnych epoch/geografií a párované semená, počítať intervaly neistoty a validovať anténne/servisné parametre na nezávislých dátach príslušnej služby. Kým tie dáta nie sú, ide o **integráciu a citlivostnú referenciu**, nie rozhodnutie, ktorý operátor je efektívnejší.
