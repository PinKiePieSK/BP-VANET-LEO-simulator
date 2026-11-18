# Kandidátska zmena Iridium: konzervatívna geometrická brána

**Stav:** 22. 10. 2026 UTC. **Kód:** [`tools/build_iridium_candidate_schedule.py`](../../tools/build_iridium_candidate_schedule.py), [`tools/check_iridium_candidate_schedule.py`](../../tools/check_iridium_candidate_schedule.py) a malá spätne kompatibilná úprava parsera [`src/certus100-e2e.cc`](../../src/certus100-e2e.cc). **Výstup:** [`iridium-candidate-switch-bratislava-20261022.ns3-schedule.csv`](../../data/derived/multi-constellation/iridium-candidate-switch-bratislava-20261022.ns3-schedule.csv) a [metadáta](../../data/derived/multi-constellation/iridium-candidate-switch-bratislava-20261022.ns3-schedule.metadata.json). Nejde o model prevádzkového Iridia, jeho handoveru alebo dostupnosti Certus 100.

## Pravidlo, vstupy a pôvod

Vstupom je [13 vzoriek troch skupín](../../data/derived/multi-constellation/bratislava-20261022T124500Z.csv), ich [metadáta](../../data/derived/multi-constellation/bratislava-20261022T124500Z.metadata.json) a archivovaný [GP manifest](../../data/orbits/20261022T124815Z-retlector/manifest.json). Použijú sa iba riadky `iridium-NEXT` pre pevnú WGS84 polohu `48,1486° N, 17,1077° E, 0 m`. Začiatok je 2026-10-22 12:45 UTC, krok 30 s, dĺžka 360 s a **testovací geometrický prah 10°**. Pred tvorbou plánu sa overí SHA-256 zdrojového CSV, jeho generátora, manifestu, gzip/surových OMM dát a lokálneho EOP súboru. Každé vybrané ID má zodpovedajúci hash skutočného archivovaného OMM záznamu; `source_record_set_sha256` je SHA-256 kanonicky zoradeného zoznamu **všetkých 80 archivovaných** párov `{catalog_id, omm_record_sha256}`. Zdrojový viacobjektový výpočet predtým uplatnil vekový limit 48 h do konca okna a zamietol jeden starý element Iridium.

Polootvorený interval `[t_i,t_{i+1})` je zapnutý **iba keď je na oboch vzorkovaných koncoch vybrané rovnaké katalógové ID nad 10°**. Pri rozdielnom ID alebo chýbajúcom kandidátovi je vypnutý celý interval. Nepredpokladá sa ani neinterpoluje okamih zmeny. Pri zapnutí má `Delay` maximum z dvoch koncových `r/c`, zaokrúhlené na celé nanosekundy. Je to len jednosmerný vákuový čas **UT→vybraný objekt**; neobsahuje feeder, gateway, ISL, fronty mimo skúšobného serializeru ani RTT. Mimo 360 s okna je brána vypnutá. CSV nesie obe koncové ID, ich počty kandidátov, elevácie/vzdialenosti, výsledné ID, dôvod vypnutia a príslušný OMM hash. Metadáta nesú hashe všetkých vstupov a výstupu.

Pre toto archivované okno je 11 z 12 intervalov zapnutých. Jediný `[90,120)` je vypnutý, pretože výber sa mení z **43253** na **43258**. **Tridsaťsekundové vypnutie je svojvoľná konzervatívna politika vzorkovania, nie zmerané trvanie handoveru Iridia.** Po 120 s tento model znovu povoľuje geometrického kandidáta **bez modelovaného času attachu**; samotný attach, lúč ani oprávnenie terminálu neoveruje. Výber najvyššej elevácie je analytické pravidlo, nie algoritmus operátora.

Pôvodný jednoobjektový plán má nemenný `source_omm_record_sha256`. Nový viacobjektový plán používa konštantný `source_record_set_sha256` a v každom zapnutom intervale `source_selected_omm_record_sha256`. Parser C++ rozpozná oba formáty, kontroluje spojitosť, interný konštantný zdrojový hash a prítomnosť ID/hasha zapnutého intervalu. **C++ nepočíta SHA-256 vstupov**; externý Python checker počíta a porovnáva ich s archívom. Pri vypnutom intervale zmeny nie je jediné vybrané ID, preto sú výsledné ID a per-interval OMM hash prázdne; obidve koncové ID ostávajú zapísané. V novom formáte dostane každá povolená správa na UT proxy udalosť `geometric_candidate` s `seq/event_id/hash` a vybraným ID; toto ID je **iba geometrický štítok v stope**, simulátor nevytvára družicový uzol.

## Reprodukcia a testované výsledky

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/build_iridium_candidate_schedule.py \
  --geometry-csv data/derived/multi-constellation/bratislava-20261022T124500Z.csv \
  --geometry-metadata data/derived/multi-constellation/bratislava-20261022T124500Z.metadata.json \
  --snapshot data/orbits/20261022T124815Z-retlector \
  --output-csv data/derived/multi-constellation/iridium-candidate-switch-bratislava-20261022.ns3-schedule.csv
.venv/bin/python tools/check_iridium_candidate_schedule.py
```

Checker dvakrát v dočasných priečinkoch znovu zostaví plán a porovná CSV/metadata bajt po bajte. Vypočíta `source_record_set_sha256` nezávisle zo surového archivovaného JSON, overí každé koncové ID, hash vybraného OMM záznamu a pravidlo 12 intervalov. Poškodenie zdrojového CSV musí spôsobiť chybu SHA-256 bez výstupu. Potom spustí **všetkých šesť pôvodných** E2E regresných prípadov s jednoobjektovým plánom a porovná štyri dvojice krátkych behov s rovnakým syntetickým 300 B reportom cez ns-3.48. Surové udalosti, aplikačné hex bajty a [manifest](../../results/iridium_candidate_switch/manifest.json) sú v `results/iridium_candidate_switch/`, ignorovanom Gitom. SHA-256 plánu je `c1653be357e49dfd9ae654a3a3c57c556c19ac5100a8ced8a9952c7a3f5f0ca3`.

| Štart reportu | Jeden objekt 43253 | Kandidátsky plán | Vysvetlenie iba v rámci abstraktného gate |
| ---: | --- | --- | --- |
| 105 s | 1 doručený | 1 blokovaný pred SERVICE_UP | `[90,120)` blokuje rozdielne koncové ID. |
| 149 s | 1 doručený | 1 doručený | Obe brány sú v tomto čase zapnuté, ale vybrané ID sa líši. |
| 149,95 s | 1 `PhyRxDrop` po 150 s | 1 doručený | Jeden objekt po 150 s vypne príjem; kandidátsky plán ďalej vyberá 43258. |
| 150 s | 1 blokovaný pred SERVICE_UP | 1 doručený | Pôvodný objekt je mimo svojho 10° plánu; nový kandidát má oba koncové vzorkované body nad prahom. |

Každý beh vyvolal presne jeden RSU report a jeden UT LAN príjem. Checker overil nemenné `seq`, `event_id`, znovu vypočítaný FNV-1a hash tela, 300 B aplikačný paket na uložených hopoch, presné počty servisných TX/RX, blokovania, `PhyRxDrop` a doručenia. Pri novom povolenom pláne potvrdil aj presne jedno `geometric_candidate` s ID 43258; pri blokovaní a pri pôvodnom formáte žiadne.

**Interpretácia a obmedzenie:** Paketové rozdiely sú dôsledkom dvoch zvolených geometrických pravidiel a ns-3 abstraktného serializeru s produktovým maximom 22 kbit/s. **Nedokazujú skutočný Iridium handover, kapacitu v mieste, terminálový attach, vhodný beam, spoj cez gateway ani komerčnú dostupnosť služby.** Žiadny prijatý paket v teste neprešiel reálnym satelitným RF/MAC modelom. Pred prevádzkovým tvrdením treba konkrétny terminál/službu, aktuálny operátorský profil, gateway/beam údaje a merania rovnakej trasy.
