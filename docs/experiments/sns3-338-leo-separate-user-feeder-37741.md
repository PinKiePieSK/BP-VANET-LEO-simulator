# Oddelené používateľské a feeder lúče nad jedným LEO objektom

**Stav:** úspešný, ale výlučne hypotetický referenčný paketový pokus (22. 10. 2026). Nesimuluje produkt Globalstar, Starlink ani Iridium. Účel je preveriť, či SNS-3 3.38 vie na časovo platnej LEO dráhe uskutočniť PHY/MAC prenos UT→družica→GW, keď má používateľský a feeder spoj vlastný smerový anténny vzor a oba prijímače zachovajú pôvodný `EM_AVI` model chýb.

## Hypotéza a kontrolný variant

Predošlý [jeden spoločný lúč](sns3-338-leo-directional-reference-37741.md) prepustil dopredné riadiace rámce, ale zahodil návratový dátový rámec na GW PHY. Jeho feeder zisk bol 13,298 dBi. Hypotéza tohto pokusu: pri **rovnakej vopred určenej šírke 22° a maximálnom zisku 17,465 dBi** umožnia dva samostatne nasmerované lúče aj návratový priechod. Mení sa počet vzorov a ich smerovanie; nie výkon, `EM_AVI`, GP objekt, konce, čas, seed, UDP obsah či DVB tabuľky. Je to citlivostná skúška modelovej antény, nie empirická kalibrácia.

## Mechanizmus v SNS-3

Vo verzii SNS-3 3.38 `SatBeamHelper::Install` priradí používateľskému PHY vzor podľa ID jeho lúča; pre feeder PHY spočíta `GetBestBeamId(satId, gwPos, true)` a odovzdá **iný** vzor do `SatGeoHelper::AttachChannels`. Tento helper odovzdá `userAgp` a `feederAgp` samostatne do `AttachChannelsUser` a `AttachChannelsFeeder`. Dokladajú to lokálne zdrojové súbory `contrib/satellite/helper/satellite-beam-helper.cc:499–508` a `satellite-geo-helper.cc:276–298` pri pripnutom commite v manifeste. Nie je preto potrebné obísť satelitný PHY/MAC alebo zasahovať do upstream knižnice.

`tools/run_sns3_338_leo_separate_beams.py` číta rovnaký hashovo overený archivovaný OMM objekt číslo 37741, pôvodné UT/GW body a čas `2026-10-22T12:45:20Z`. UT je pevný bod pri RSU v Bratislave (`48,1480603° N`, `17,1035340° E`); GW (`37,8167° N`, `22,6667° E`) je **hypotetická mestská proxy** v Grécku. Jej polohu nemáme doloženú ako prevádzkovú bránu. GP archív vznikol po simulovanom čase, takže výsledok je retrospektívny.

Skript preloží OMM pomocou SGP4 a TEME→ITRS do ECEF. Kvôli zhode s implementáciou SNS-3 vypočíta pozemné body na guli polomeru **6 378 137 m**. V t=0 nasmeruje lúč 30 na UT a lúč 43 na proxy GW. Uhlová separácia dvoch smerov je **25,947°**. V oboch použije vopred zvolený výskumný model `G_dBi(θ)=G_peak−min[12(θ/22°)^2,25 dB]`, `G_peak=10 log10(27000/22²)=17,465 dBi`. Vzťah zisku a šírky je približný model kruhovej apertúry z [ITU-R príručky](https://www.itu.int/dms_pub/itu-r/opb/hdb/R-HDB-42-2002-PDF-E.pdf); parabolický pokles je naša 3D adaptácia [otvoreného anténneho modelu ns-3](https://www.nsnam.org/docs/models/html/antenna.html). Šírka, cap, bod brány a používanie generického DVB-S2/RCS2 nie sú zverejnené technické parametre žiadnej z troch skúmaných služieb.

Generované súbory `BpLeoSeparated_30.txt`, `BpLeoSeparated_43.txt` vzorkujú zisk na mriežke `32–54° N`, `10–30° E` po 0,25°; `GeoPos.in` má polohu družice v t=0. Skript číta pôvodné scenárové `tles.txt`, `isls.txt`, `ut_positions.txt`, `gw_positions.txt` s kontrolou hashov. C++ sonda používa `SatHelper`, sieťovú regeneráciu, seed **314159**, run **1**, štyri sekundy a odošle v t=1 s jeden presný 16 B UDP payload (`LEOGEO1\0\0\0\0\1\x12\x34\x56\x78`). Prijímací callback porovná všetkých 16 bajtov. Tento obsah je experimentálna sonda; nie CAM ani ICB1.

## Overenie a raw výsledok

V t=0 SNS-3 vybral **user beam 30** a **feeder beam 43**. Pri pakete boli interpolované satelitné zisky **17,4630 dBi** pri UT a **17,4637 dBi** pri proxy GW; hypotetické lúče majú rôzne smery. Priamy 3D výpočet v t=1 s sa od posúvanej mapy líšil o **−0,00183 dB** a **−0,00123 dB**. Ide o kontrolu krátkeho okna, nie validáciu anténneho pohybu pri dlhom lete. Guľový SNS-3 model mal voči WGS84 slant range kratší o **5,70 km** pri UT a **13,41 km** pri GW; obe elevácie aj tak prekročili výskumnú 10° masku. SNS-3 a nezávislý SGP4 guľový výškový výpočet sa líšili o **0,310 m**.

Pri zapnutých modeloch `EM_AVI` bolo v `run.log` **39 dopredných a 4 návratové rozhodnutia bez PHY chyby**. `PacketTrace.log` má pre dátový paket ID 9 UT PHY TX **1,09074 s**, SAT PHY RX **1,10068 s** a **1,10135 s** (opakovaný burst), SAT PHY TX **1,10136 s**, GW PHY/ND RX **1,11074 s**. Prijímací callback dostal identický 16 B obsah v **1 118 741 µs**, teda **118 741 µs** po odoslaní z UT aplikácie. Je to jediné modelové doručenie **1/1**, nie PDR odhad. V predchádzajúcom jedinom lúči zostalo 0/1 a GW PHY drop; rozdiel podporuje citlivosť referenčného modelu na feeder smerovanie. Nehovorí nič o prevádzkovom výkone operátorov.

Overovač odmieta iný Git pin, zmenený OMM a vstupy, iný výber lúča, nezhodu 3D zisku >0,5 dB, nesúlad výšky >100 m, chýbajúce PHY hopy, PHY chyby pri úspechu alebo chýbajúce presné aplikačné prijatie. Výstupný priečinok `results/sns3_338_leo_separate_user_feeder_37741/` obsahuje vstupy, `build.log`, `run.log`, `PacketTrace.log`, SINR/RX power, `verification.json` a hashový `manifest.json`.

## Reprodukcia

Vyžaduje pripnutý checkout podľa manifestu a závislosti Python prostredia. Výstupný adresár musí byť prázdny:

```bash
.venv/bin/python tools/run_sns3_338_leo_separate_beams.py \
  /tmp/ns3-sns3-338-feasibility /tmp/novy-leo-oddeleny-beh
```

Úspešný kontrolný výstup je `SEPARATED_BEAMS packet_received=True UT_gain=17.46 dBi GW_gain=17.46 dBi`. Všetky výsledky treba interpretovať spolu s `verification.json` a surovým trace.

## Hranice a ďalší experiment

Táto referencia má len jeden satelit, jeden pevný UT, jednu hypotetickú GW, jeden krátky paket a žiadne meranie operátora. Neobsahuje lúčové/spektrálne plánovanie konštelácie, zrážky viacerých terminálov, servisný handover, autorizáciu, prevádzkový feeder, crosslinky ani priame auto→satelit. Vzor sa len translačne posúva po zemepisnej mape; nie je to úplné 3D natáčanie payloadu. Ďalší zmysluplný krok je vložiť **skutočný RSU report ICB1 z prijatého CAM** do tejto LEO cesty a po overení bajtov vykonať vopred definovanú citlivosť na zisk/šírku, masku a zaťaženie. Porovnávanie Starlink/Iridium/Globalstar má zmysel až s oddelenými službami, kompatibilnými terminálmi a validovanými parametrami.
