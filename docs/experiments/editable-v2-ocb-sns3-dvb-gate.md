# Jeden simulačný čas: CAM → RSU → terminál → referenčný DVB satelit → brána

**Stav:** integračná brána, 22. 10. 2026. Presný výsledok je v `results/editable_v2_ocb_sns3_dvb_gate/verification.json`; všetky čísla nižšie platia len pre tento malý deterministický experiment. Ide o statický referenčný GEO model `SatHelper::SIMPLE` v SNS-3 3.38. **Nie je to model siete Starlink, Iridium ani Globalstar a nejde o LEO experiment.**

## Výskumná otázka a hypotéza

Otázka: Dá sa v jednej simulácii zachovať identita a bajtový obsah udalosti od ETSI CAM vyslaného pohybujúcim sa autom, cez fyzické OCB rádio a RSU, až po DVB satelitný návratový spoj a aplikáciu za bránou? Pozitívna hypotéza: všetkých šesť ICB1 správ vytvorených *až po prijatí CAM na RSU* prejde cez UT a referenčný DVB return link. Kontrolný variant vypne výlučne `UT → satellite SendTo`; pozemné CAM aj RSU→UT zostanú bajtovo identické a brána neprijme žiadnu ICB1.

## Logika skutočnej služby a modelu

Auto `car0` vysiela kooperatívnu informáciu o polohe/rýchlosti (CAM), ktorú lokálne prijímajú `car1`, `car3` a `rsu0`. RSU môže takúto informáciu zaslať do vzdialeného centra cez samostatný satelitný terminál. Auto nepotrebuje satelitnú anténu; miestna správa medzi vozidlami satelitom neprechádza. V tomto pilote má RSU experimentálnu aplikáciu, ktorá z prijatého CAM vytvorí 96-bajtový formát ICB1. ICB1 je **náš experimentálny report**, nie paketový formát ktoréhokoľvek operátora. Terminál `UT` ho dostane cez 100 Mb/s LAN s nastaveným 100 µs kanálovým oneskorením a odošle cez modelovaný DVB user/feeder spoj SNS-3 do `GW user`.

SUMO poskytne šesť vzoriek v časoch 20,0–22,5 s pri kroku 0,5 s. `prepare_editable_v2_cam.py` zapisuje WGS84 aj lokálne polohy z kontrolovaného podscenára `data/inputs/editable-road-v2/packet-subset.json`. Vanetza Release 2 vytvorí 41 B UPER CAM, 4 B BTP-B a GeoNetworking SHB; ns-3.38 OCB odosiela 85 B GN/BTP/CAM cez 802.11p pri 5,9 GHz, 10 MHz, 6 Mb/s, 20 dBm a Friisovom voľnom priestore. Tieto hodnoty sú **konfigurácia skúšobného rádia**, nie kalibrácia mestskej prevádzky. Tri prijímače dekódujú CAM cez Vanetza a validujú polohu, rýchlosť, smer i generationDeltaTime. RSU vloží presné prijaté CAM bajty do ICB1 spolu s ID, časom príjmu a SHA-256.

`SatHelper::SIMPLE` používa statický GEO satelit pri 33°E a výške 35 786 km podľa [dokumentácie SNS-3](https://www.sns3.org/doc/satellite-design.html). Jeho DVB-S2/RCS2 návratový model obsahuje satelitný MAC/PHY, rámcovanie a bránu. **Poloha UT/GW v tejto jednoduchej satelitnej scéne nie je geodeticky zosúladená s editorovou mapou auta a RSU.** Tento experiment preto dokazuje paketovú integráciu, nie pokrytie daného miesta, fyzikálny rozpočet spojenia alebo výkonnosť LEO. `PacketTrace.log` sleduje interné ID cez UT PHY → SAT PHY → GW PHY/ND, ale neobsahuje úplné PHY bajty. Rovnakosť dát dokazujú aplikačné záznamy a LAN/OCB PCAP; spojenie aplikačného ID s interným satelitným ID je pri jednom kontrolovanom toku korelácia podľa času, nie kryptografický dôkaz payloadu v rádiovom rámci.

## Vstupy, výstupy a reprodukcia

- Vstup: podscenár editoru JSON, SUMO FCD, deterministické waypoint CSV, seed `314159`, run `1`.
- Pripnuté: ns-3.38 `392e368`, SNS-3 satellite `739a10d`, traffic `c68daaf`, magister-stats `c613ba7`, SNS data `faf7d76`, Vanetza `fb6c551`; úplné SHA sú v `run-manifest.json`.
- Kód: `src/editable-v2-ocb-sns3-dvb-gate.cc`; spúšťač `tools/run_editable_v2_ocb_sns3_dvb_gate.py`; nezávislá kontrola `tools/check_editable_v2_ocb_sns3_dvb_gate.py`.
- Výstupy: `waypoints.csv`, SUMO FCD, `positive/` a `blocked/` so šiestimi PCAP na variant, `trace.csv` s presnými bajtmi a časom v µs, `PacketTrace.log`, `delivery.csv`, `verification.json`, log zostavenia, manifest s hashmi. Satelitný `PacketTrace` zapisuje čas v sekundách s obmedzenou desatinnou presnosťou.

Spustenie z koreňa projektu, keď je izolovaný checkout pripravený podľa `docs/experiments/sns3-338-ocb-dvb-packet-gate.md`:

```bash
.venv/bin/python tools/run_editable_v2_ocb_sns3_dvb_gate.py \
  /tmp/ns3-sns3-338-feasibility /tmp/novy-ocb-sns3-cam-beh
.venv/bin/python tools/check_editable_v2_ocb_sns3_dvb_gate.py \
  /tmp/novy-ocb-sns3-cam-beh
```

Výstupný adresár musí byť prázdny alebo neexistovať. Build je `-O0 -g0` a využíva rovnakú sadu ns-3.38 knižníc pre OCB aj satelit. Spúšťač používa dočasné cesty bez medzier pre argumenty `ns3::CommandLine` a archivuje výsledok do zvoleného adresára.

## Kontrola a výsledok

Kontrola vyžaduje 6 vyslaných CAM, 18 dekódovaní, 6 RSU ICB1 a 6 doručení do UT v oboch variantoch. OCB aj LAN PCAP musia byť medzi variantmi *binárne identické*. Pri každej udalosti kontrola porovnáva vyslané CAM a všetky prijaté CAM bajty, GeoNetworking/BTP payload v OCB rámci, UPER polia s waypointom, SHA-256 a obsah 96 B ICB1, UDP kontrolný súčet na LAN a identické ICB1 na bráne. Pozitívny variant musí mať pre každú správu súvislú ID stopu `UT ND → UT PHY → SAT PHY → GW PHY → GW ND`. V blokovanom variante nesmie existovať aplikačné odoslanie UT ani príjem brány; satelitná riadiaca prevádzka môže v pozadí pokračovať.

| Meranie | Pozitívny | Blokovaný satelitný send |
|---|---:|---:|
| CAM vyslané autom | 6 | 6 |
| CAM prijaté a dekódované troma susedmi | 18 | 18 |
| ICB1 vytvorené na RSU / prijaté UT | 6 / 6 | 6 / 6 |
| ICB1 prijaté bránou | 6 / 6 | 0 / 6 |

Koncové oneskorenia auto→brána boli **309 015, 302 674, 302 015, 302 015, 302 015 a 302 015 µs**. Priemer je 303 291,5 µs. Aritmetický priemer absolútnych rozdielov susedných oneskorení je 1 400 µs; toto je tu označené ako jednoduchý jitter, nie presná implementácia RFC 3550. Prvá správa zahŕňa rozbeh plánovania spojenia. Šesť úspechov nedáva spoľahlivý odhad PDR pri záťaži či v teréne. Nie sú modelované rušenie mesta, tienenie, beam/handover, reálny operátorský terminál ani jeho prístupové pravidlá.

Čerstvý druhý beh v samostatnom adresári mal totožné SHA-256 pre waypoint CSV, verifikáciu, oba aplikačné trace CSV, oba satelitné `PacketTrace.log` aj porovnané OCB/LAN PCAP. Hash znovuzostaveného binárneho súboru sa medzi dočasnými build adresármi líšil, preto sa za kritérium opakovateľnosti považujú pripnuté zdroje a identické raw výsledky, nie samotná bitová zhoda ELF súboru. Zámerná jednobajtová zmena v kópii pozitívneho ICB1 trace bola auditom odmietnutá.

## Neúspešné pokusy a opravy

1. Pri kompilácii spoločného zdroja sa globálne makro `pi` zo SNS-3 SGP4 hlavičky dostalo pred Boost hlavičky Vanetza. Kompilátor odmietol ich parameter. Satelitná hlavička je v zdroji zaradená po ostatných includoch; tým sa odstránil konflikt bez úpravy knižníc.
2. `ns3::CommandLine` rozdelil absolútnu cestu s medzerou v názve projektu. Priamy test skončil chybou „v2 waypoint CSV absent“. Spúšťač používa dočasné cesty bez medzier a výsledky potom bezpečne skopíruje.
3. Prvá verzia auditu požadovala, aby textový `GW ND RCV` čas neprekročil presný čas aplikácie. `PacketTrace` vytlačil 20.8027 s pre paket, ktorý aplikácia prijala v 20.802674 s. Povolená tolerancia 100 µs zodpovedá textovému zaokrúhleniu; aplikačné časy ostávajú v celočíselných µs.

Ďalšia brána: v tej istej verzii SNS-3 použiť **geograficky a časovo konzistentnú LEO orbitu** s UT a GW na miestach zo scenára, nezávisle prepočítať eleváciu/vzdialenosť a preveriť satelitný výber, beam a handover. Až potom možno začať seriózne porovnávanie satelitných trás.
