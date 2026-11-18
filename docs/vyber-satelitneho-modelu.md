# Výber satelitného modelu (stav 22. 10. 2026)

## Otázka a kritériá

Zadanie žiada vyhodnotiť VANET s komunikáciou cez LEO. Porovnávame skutočný prenos IP paketov cez vozidlo–RSU, používateľský satelitný spoj, satelitný uzol, feeder spoj a prípadné medzisatelitné spoje. Pre satelitný model sú rozhodujúce pohyb/viditeľnosť, kanál a PHY/MAC, routovanie, príklady, kompatibilita s ns-3 a reprodukovateľnosť. **Názov konštelácie v dátach ešte neznamená implementáciu protokolu daného operátora.**

| Možnosť | Verzia a údržba overená zo zdroja | Orbity, linky, príklady | Vhodnosť pre túto prácu |
| --- | --- | --- | --- |
| [SNS-3](https://github.com/sns3/sns3-satellite) | Spoločne označené tagy `ns-3.48`/`3.48` pre `satellite`, `traffic`, `magister-stats`; modul má príklady a testy. Lokálne pripnuté commity sú v `docs/reprodukcia.md`. | Dokumentovaný LEO aj GEO príklad, SGP4, UT/GW, DVB satelitný prístupový kanál, rôzne režimy regenerácie, ISL a mobilné UT/handover príklady. MEO scenár nebol potvrdený. | Najlepšia verejne dostupná sada na **štandardizovaný satelitný PHY/MAC** v spoločnej ns-3 simulácii s Wi-Fi. Súbor `constellation-starlink-1584-sats` má však `standard/DVB`, takže ním nemožno tvrdiť verné Starlink MAC/PHY. |
| [Hypatia](https://github.com/snkas/hypatia) | Lokálny upstream commit `0ac531c` používa ns-3.31; upstream má otvorený neprevzatý návrh portu na 3.45. | LEO TLE/SGP4, dynamický stav GSL/ISL a routovania, paketové ns-3 experimenty. Kanál `GSLChannel` počíta oneskorenie zo vzdialenosti, `GSLNetDevice` rýchlosť/front a voliteľný všeobecný error model; to nie je overený operátorský rádiový PHY/MAC. | Referencia pre orbitálnu topológiu a routovanie, nie základ na presný rádiový profil troch operátorov. |
| [ns-3-leo](https://gitlab.ibr.cs.tu-bs.de/tschuber/ns-3-leo) | [Autorský článok](https://d-nb.info/1253136572/34) uvádza implementáciu pre ns-3.30. Priamy GitLab pri kontrole vracal HTTP 429, preto ďalší stav/tagy nepotvrdzujeme. | LEO orbitálny model, zem–satelit/ISL, príklady s paketmi. Autori výslovne opisujú sieťové zariadenie ako tenký obal fronty s error modelom, prahom prijatého výkonu a maximálnou rýchlosťou. | Užitočné pre LEO protokoly; nižšia istota build kompatibility a rádiovej fidelity. |
| [Anysam Starlink ns-3](https://github.com/anysam/starlink_ns3) | Repo obsahuje `ns-allinone-3.30.1`, bez publikovaného release. | Príklad UDP echo a FlowMonitor. Lokálne prečítaný zdroj `leo-satellite-config.cc` vytvára GSL cez `CsmaHelper` a ISL cez `CsmaHelper`/`PointToPointHelper` s pevnou sadzbou 5.36 Gb/s a oneskorením podľa vzdialenosti. | Názov Starlink nie je dôkazom Starlink rádiového protokolu; pre požadovanú PHY/MAC vernosť nevhodné. |

Ďalšia možnosť: samotný [ns-3.48 mobility model](https://www.nsnam.org/docs/models/html/mobility.html) obsahuje kruhovú LEO orbitu, ale neobsahuje tým automaticky satelitný prístupový protokol.

## Konkrétni operátori a hranica overiteľnosti

Používateľ požaduje rovnocenné porovnanie Starlink, Iridium a Globalstar. Musia to byť **tri konfiguračné profily**, s rovnakým dopravným scenárom a meracími bodmi, nie tvrdenie, že jeden DVB model je presnou implementáciou všetkých troch systémov.

- [Starlink](https://starlink.com/technology) zverejňuje LEO architektúru, Ku/Ka antény a optické ISL. [FCC dokument](https://docs.fcc.gov/public/attachments/DOC-391957A1.pdf) uvádza príklad pásma terminálu 14,0–14,5 GHz uplink a 10,7–12,7 GHz downlink. Presné rozvrhovanie, rámce a handover konkrétnej prevádzky z týchto zdrojov nezískame. Aktuálne orbitálne vrstvy sa menia; výšku treba viazať na dátum a zvolenú generáciu, nie automaticky na 550 km.
- [Iridium](https://www.iridium.com/network) uvádza LEO asi 780 km, používateľský L-band a štyri rádiové crosslinky na satelit. [FCC povolenie](https://docs.fcc.gov/public/attachments/DA-16-875A1.pdf) uvádza príslušné frekvenčné pásma. Topológia je mesh, ale neznáme interné MAC/routing pravidlá budú označené ako predpoklad.
- [Globalstar](https://www.globalstar.com/en-ap/about/who) výslovne opisuje bent-pipe architektúru cez pozemné gateway bez vlastného medzisatelitného mesh. Preto profil Globalstar **nesmie** dostať ISL len kvôli zjednoteniu scenárov.

Štandardizovaný referenčný model SNS-3 je technická kalibrácia a možná základňa pre sieťovú integráciu. Jeho DVB-S2/RCS2 rámce sa nesmú označiť ako skutočné rámce Starlink/Iridium/Globalstar. Pri troch operátorských profiloch budú výsledky fyzického prenosu podmienené zverejnenými parametrami, explicitným link budgetom a zdokumentovanými predpokladmi. Ak konkrétne MAC/PHY parametre chýbajú, pravdivý výsledok je interval/senzitivita, nie „100 % presná“ replika.

## Rozhodnutie pre najbližší experiment

1. Otestovať SNS-3 `3.48` na malom GEO a LEO príklade a uchovať logy. Zvlášť overiť, že LEO príklad skutočne prijíma pakety.
2. Pripojiť pozemný SUMO V2V/V2I segment k satelitnému UT a vzdialenej GW v **jednom** ns-3 behu. Meracie body: aplikácia vozidla, 802.11p MAC/PHY, RSU/UT, satelitný user/feeder link, GW, server.
3. Výsledok SNS-3 pomenovať referenčným DVB variantom. Tri operátorské topológie zavádzať až so zdrojmi, samostatnými konfiguráciami a testami; pri proprietárnych detailoch vyhodnotiť citlivosť.

Neúspešné pokusy a limity zostávajú v denníku; pilot s pevnou bodovou linkou je len historická kontrola pipeline.
