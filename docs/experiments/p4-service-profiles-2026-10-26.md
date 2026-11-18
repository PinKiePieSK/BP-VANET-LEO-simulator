# P4 — tri servisné profily, 26. 10. 2026

## Rozsah a reprodukcia

P4 vykonáva **servisnú hranicu**, nie operátorský RF/MAC protokol. Všetky profily prijímajú tých istých šesť 96 B ICB1 reportov, ktoré RSU naozaj vytvorila z dekódovaných CAM v čerstvom jednoclockovom behu ns-3.38/SNS-3 3.38. Natívny zdroj `results/p4_certus_native_20261026` prešiel: 6/6 kladná cesta CAM→RSU→IP/GRA1→I2V1 a 0/6 pri blokovanom UT. P4 následne prehráva **identické aplikačné bajty a čas vytvorenia** cez tri rozdielne servisné obaly; pozemný WAN je hypotetická párovaná kontrola. Nejde o ďalší natívny satelitný PHY/MAC beh.

```bash
native_out=results/p4_certus_native_REPLACE_WITH_UNUSED_ID
service_out=results/p4_service_profiles_REPLACE_WITH_UNUSED_ID
.venv/bin/python tools/run_editable_v2_ocb_certus100_i2v_e2e.py --output "$native_out"
.venv/bin/python tools/run_p4_service_profiles.py --native-base "$native_out" --output "$service_out"
.venv/bin/python tools/check_p4_service_profiles.py "$service_out"
.venv/bin/python -m unittest tools.test_p4_service_profiles
```

Pre opakovanie zvoľte nepoužité ID, aby zostali zachované staré výsledky; P4 runner odmietne prepísať existujúci adresár. Všetky hodnoty, jednotky, zdroje a neistoty sú v `config/p4_service_profiles.json`; každý raw CSV má hash v `results/p4_service_profiles_20261026_v6/manifest.json`. Konečný manifest má SHA-256 `3f710567fca4bd6459cbec899789f15885869c7706cde64ae4dadccd236f8c2b`. V tomto kroku vznikli aj staršie prieskumné P4 adresáre bez finálneho rozsahu auditu; **autoritatívny dôkaz je iba `_v6`**.

## Zdrojovaný profil a fyzikálna hranica

| Profil | Produktový údaj | Modelová časť a hranica |
| --- | --- | --- |
| Iridium SkyLink 5100 / Certus 9770 / Certus 100 IP | [Iridium 9770](https://www.iridium.com/products/iridium-certus-9770): najviac 22 kbit/s UL, 88 kbit/s DL, L-band 1616–1626,5 MHz; [sieť](https://www.iridium.com/network) má RF crosslink architektúru. | Oddelené UL/DL fronty a vlastné časovanie serializácie, servisná strata/oneskorenie 150–750 ms na smer ako **citlivosť**. Archivované Iridium NEXT OMM povoľuje iba UT geometrického kandidáta. Pridáva sa len známy UT→družica vákuový čas, neznáma brána/mesh sa nevymýšľa. Existujúci natívny C++ IP obal má nulový service delay; nové časovanie a straty sú explicitná deterministická vrstva P4. Žiadna 17 dBi DVB mapa ani 1 Gbit/s ISL nie sú vydávané za Iridium. |
| Globalstar RM200M | [RM200M sheet](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet1.pdf): MO 9–144 B, MT 9–128 B; [sieť](https://www.globalstar.com/en-us/about/our-technology) je bent-pipe k pozemnej bráne bez ISL. | ICB1 96 B sa posiela ako natívna MO, GRA1 46 B ako natívna MT. Tá istá archivovaná družica musí byť nad 10° na RSU aj na proxy brány v Nemei v každej vzorke; poloha Nemea je centrum mesta, nie overená anténa. Model pridáva dva vypočítané vákuové úseky a hypotetických 0,5–5 s na smer; retry 0–2 sa skúša iba ako citlivosť MO. 300 B lokálny aplikačný payload sa rozdelí do troch správ a reassembľuje; toto nie je tvrdenie o podpore segmentácie modemom. |
| Starlink Performance **Gen3 + Local Priority 50GB** | [Performance spec](https://starlink.com/public-files/specification_sheet_performance.pdf): 140° FoV; [pohyb a plán](https://starlink.com/sz/support/article/50e933eb-54f5-1a77-cc85-c6c8325564cf), [Priority plány](https://starlink.com/support/article/1124df77-fdec-91e7-bed9-ba489cffda25): podmienky pre mobilné použitie. Pilot používa pevnú RSU vo vnútrozemí SR. | Model IP/UDP, experimentálne UL 5–20 Mbit/s, DL 25–100 Mbit/s, delay 15–100 ms/smer a strata 0–10 %. Tieto čísla sú **predpoklady**, nie SLA. Archivované Starlink OMM vyberá jednu družicu nad 10° súčasne z RSU a hypotetickej viedenskej mestskej proxy; obe elevácie a vákuový čas checker nezávisle prepočítava. Ide o priamu fyzikálne možnú trasu bez použitia ISL. Proxy nie je známa prevádzková brána, lúč/scheduler/pridelenie nie sú modelované. |

OMM snapshot je z 22. 10. 2026, modelový čas je 22. 10. 2026 12:45:20–22,5 UTC. Prvky majú epochu pred dejom a najviac 48 h; snapshot bol stiahnutý **po** modelovom deji, teda ide o retrospektívnu geometriu. Manifest pinuje gzip/raw hash, Starlink record hash a lokálnu EOP tabuľku. Vzorky nepreukazujú spojité pokrytie ani aktívny komerčný beam. Autobahn RTT dáta inej generácie terminálu a koncového bodu zostávajú iba [externý kontext](../decisions/empiricka-kalibracia-konkretnych-sluzieb.md), nie kalibrácia.

## Výsledky servisného pilotu

Menovateľ je vždy šesť jedinečných RSU reportov. `remote` znamená rovnaký event ID a presné ICB1 bajty na vzdialenej aplikácii; `return` znamená správny GRA1 hash pri RSU. Priemer sa počíta len z doručených správ. Šesť správ nie je vzorka na p95/p99 alebo reálnu PDR služby.

| Profil | Kontrola | Remote | Return | Priemer RSU→server |
| --- | --- | ---: | ---: | ---: |
| Pozemný WAN, hypotetický 10 Mbit/s a 10 ms/smer | kladná | 6/6 | 6/6 | 10,100 ms |
| Iridium | kladná / blokovaná UT | 6/6 / 0/6 | 6/6 / 0/6 | 300,140 ms / — |
| Iridium | citlivosť nízka / vysoká | 6/6 / 3/6 | 6/6 / 3/6 | 200,140 / 845,216 ms |
| Globalstar | kladná / blokovaná brána | 6/6 / 0/6 | 6/6 / 0/6 | 1018,401 ms / — |
| Globalstar | citlivosť nízka / vysoká | 6/6 / 6/6 | 6/6 / 6/6 | 518,401 / 11685,068 ms |
| Starlink | kladná / zakázaná trasa | 6/6 / 0/6 | 6/6 / 0/6 | 33,405 ms / — |
| Starlink | citlivosť nízka / vysoká | 6/6 / 5/6 | 6/6 / 2/6 | 18,355 / 103,504 ms |

Čísla nie sú poradie skutočných operátorov: každý servis používa neznáme parametre s rôznym hypotetickým rozsahom. Pozemný WAN takisto nie je meranie. Deadline 60 s je výskumný prah kontraktu P0, nie garancia služby. P4 vysoké varianty používajú deterministickú SHA stratu pre reprodukovateľnú kontrolu vetiev, nie kalibrovanú stochastickú distribúciu.

## Brány a negatívne dôkazy

1. **Iridium PASS:** čerstvý natívny ns-3.38 IP/UDP packet path a dve nezávislé fronty; P4 kladná 6/6, blokovaná geometria UT 0/6, účinné rate/delay/loss rozsahy. Publikované rýchlosti sú maximá a všetky varianty ich dodržia. Chýba matching raw SkyLink 5100/Certus 100 meranie, preto `scenario/sensitivity`.
2. **Globalstar PASS:** MO 96 B a MT 46 B pod publikovanými limitmi, tá istá družica viditeľná na oboch koncoch v kladnej vzorke; negatívny gateway CSV má eleváciu −1° a 0/6. Lokálne 300 B → 3 natívne limitované segmenty, spätná montáž, duplicitná správa a 145 B MO/129 B MT odmietnuté. Chýba overená brána, servisný API/ACK a raw RM200M meranie; `scenario/sensitivity`.
3. **Starlink PASS:** Gen3/plán pripnuté; IP/UDP checksumy, priamy obojstranne viditeľný kandidát bez tvrdenia o ISL; kladná 6/6, explicitná blokácia trasy 0/6, nízky/vysoký interval. Chýba overený aktívny plán, reálna brána, beam/scheduler a matching raw meranie; `scenario/sensitivity`.

Checker verifikuje vstupné a výstupné SHA-256, bajty ICB1/GRA1 a IP/UDP checksum, smerové limity MO/MT, rovnaké event ID, dve elevácie a orbitálnu polohu vybranej Starlink družice, menovatele i oneskorenia. Umelo poškodený ICB1 na serveri odmietol **aj po prepísaní hashu CSV v manifeste**. Päť cielených unit testov pokrýva nezávislé fronty, checksum, veľkostné limity, segment count/hash a deterministickú stratu.

**Otvorené mimo P4:** porovnateľné nezávislé merania presných terminálov/plánov, reálne GW/beam/scheduler/handover a finálna viac-epochová experimentálna matica patria do P5. Tieto neznáme položky nesmú byť v texte BP interpretované ako validovaná operačná dostupnosť ani PDR.
