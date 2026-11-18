# Brána pre spoločný OSM CAM → SNS-3 DVB LEO beh

Stav 22. 10. 2026 UTC. **Paketový beh s OSM CAM cez SNS-3 zatiaľ neexistuje.** Existujúci `src/vanet-sns3.cc` prenáša syntetický 300 B `SeqTsHeader` UDP payload nad starým syntetickým dopravným scenárom; nový OSM experiment vytvára 41 B ETSI Release 2 CAM, 85 B GN/BTP/CAM a 96 B RSU `ICB1` reporty pre päť časových polôh jedného auta. Tieto dve vetvy nemožno spojiť premenovaním toku. Táto brána presne oddeľuje dokázanú kompatibilitu knižníc od zatiaľ nedokázanej satelitnej paketovej trasy.

## Meraný problém so starým referenčným scenárom

`tools/audit_osm_sns3_reference_gate.py` číta nemenené `build/osm-ba-cam-waypoints.csv`, `data/scenarios/sns3-reference-geo/positions/{start_date,tles,ut_positions,gw_positions}.txt` a `standard/standard.txt`. Overuje päť UTC časov a CAM event ID, porovnáva dátum s epochami TLE a na sfére SNS-3 s polomerom 6 378 137 m spočíta veľkú kružnicu z hypotetickej OSM RSU na **každý** z referenčných UT. Pri nezlučiteľnosti uloží `results/osm_sns3_reference_gate/preflight.json` a zámerne vráti kód 2, aby ho žiadny runner nemohol ticho vyhlásiť za použiteľný vstup.

| Podmienka pre ten istý beh | OSM CAM a RSU | Historický SNS-3 DVB scenár | Výsledok |
| --- | --- | --- | --- |
| UTC počiatok | 2026-10-22 12:45:00Z; CAM t=5–9 s | 2014-09-29 12:15:48Z | rozdielny absolútny čas |
| Orbitálne elementy | dátovaná dráha blízka roku 2026 potrebná | dvojica ISS-like TLE s epochami 2014 | vek približne 4 405 dní pri OSM čase |
| Terminál pri OSM RSU | 48.1482681° N, 17.1085885° E | najbližší z piatich UT ≈ 8 573,466 km | žiadny lokálny UT |
| Satelitný štandard | požadovaný len ako **referenčný DVB** test | `standard/DVB` | zhoda typu referencie, nie operátorská služba |

Vstupný OSM waypoint SHA-256 je `1b89eaf70b81f5f8935307969169c498af7b5e6f3728792d4328fca0094e12e1`; preflight ukladá všetkých päť event ID a SHA-256 každého súboru referenčného scenára. Rovnaký UTC a tá istá pozícia RSU sú nevyhnutné pre žiadané párovanie. Pripustiť 8 573 km `RSU→UT` ako lokálny 1 Gb/s LAN a pustiť TLE 12 rokov mimo epochy by vytvorilo vykonateľný, ale nesprávne pomenovaný experiment. [Pôvodný geografický audit](../experiments/geografia-a-orbity.md) už ukázal, že starý SNS-3 môže doručiť paket aj pri vypočítanej feeder elevácii pod horizontom; preto je pri novej trase nezávislý audit **každého doručeného path** povinnou bránou, nie iba ilustračným grafom.

`src/vanet-sns3.cc` načíta scenár `sns3-reference-geo`, nastaví lúče `{43,30}`, vyberie prvý UT user a spája RSU s ním P2P. V zdroji SNS-3 `vendor/ns-3.48/contrib/satellite/helper/satellite-helper.cc`, `LoadConstellationScenario`, sa pozícia UT mapuje cez `GetClosestSat` a `GetBestBeamId`; pri žiadnom lúči sa UT preskočí. Samotná zmena `ut_positions.txt` na Bratislavu preto tiež nezaručuje attach alebo DVB spoj. Beam a gateway musia byť validované spoločne s konkrétnou dráhou. [Oficiálny SNS-3 zdroj](https://github.com/sns3/sns3-satellite) opisuje modelované LEO a DVB mechanizmy; ich použitie by stále **nebolo** protokolom Starlink, Iridium alebo Globalstar.

## Dva vykonané diagnostické testy

```bash
python3 tools/test_osm_sns3_reference_gate.py
bash tools/test_osm_sns3_abi.sh
```

Prvý test vyžaduje presne tri detegované prekážky (`REFERENCE_START_UTC_DIFFERS_FROM_OSM_CAM`, `REFERENCE_TLE_EPOCH_OUTSIDE_SEVEN_DAYS`, `NO_REFERENCE_UT_WITHIN_100M_OF_OSM_RSU`), návratový kód 2 diagnostiky, správne event ID, waypoint hash a geodetickú symetriu. Výsledok testu je `PASS historical SNS-3 reference blocked...`, **nie** doručenie satelitného paketu. Raw JSON má `status=blocked_reference_reuse`, `reference_suitable=false` a `scope=preflight only; no SNS-3 packet experiment run`.

Druhý test kompiluje malý `src/osm-sns3-vanetza-link-probe.cc` v jednom procese proti pripnutému ns-3.48 `satellite` a Vanetza v26.06 Release 2 CAM, potom ho spustí z koreňa ns-3. Výsledok `PASS co-linked ns-3.48 satellite and Vanetza Release 2 CAM types` ukazuje, že **ABI/linkovanie nie je súčasný blokér**. Ukladá `results/osm_sns3_reference_gate/abi.json` s hashmi zdroja, runnera a binárky a výslovným `packet_path_tested=false`. Prvý ručný pokus spustiť binárku z koreňa práce skončil `SatEnvVariables::LocateDirectory ... contrib/satellite/data` a exit 134: SNS-3 hľadá dáta relatívne k pracovnímu adresáru. Testovací runner to opravuje `cd vendor/ns-3.48` pred spustením. Tento neúspech je konfiguračný, nie chyba ASN.1 ani DVB.

## Presný ďalší implementačný postup

1. **Datovaný georeferencovaný vstup.** Z pripnutej orbitálnej snímky alebo primárnych [CelesTrak GP elementov](https://celestrak.org/NORAD/elements/) vybrať dráhu s epochou blízkou `2026-10-22T12:45Z`, uložiť pôvodné bajty, URL, čas získania a hash. Existujúca `data/orbits/20261022T124815Z-retlector/` je OMM snímka pre geometriu, nie bez ďalšieho parserovo kompatibilný SNS-3 `tles.txt`; podľa [CelesTrak pravidiel prístupu](https://celestrak.org/usage-policy.php) sa po HTTP 403 nesmie obchádzať server opakovanými masovými požiadavkami. Ak sa použije syntetická referencia, musí mať explicitne syntetické TLE a nesmie niesť meno operátora. Pre každú variantu vybrať konkrétne UT, gateway, lúč a interval t=5–9 s, potom nezávisle skontrolovať UT–SAT a SAT–GW eleváciu a prípadnú ISL priechodnosť v tom istom UTC. Vybraná servisná minimálna elevácia musí byť označeným predpokladom, nie odvodená iba z geometrického horizontu 0°.
2. **SNS-3 scenár bez zmeny starého referenčného vstupu.** Vytvoriť nový názov scenára s `start_date=2026-10-22 12:45:00`, UT geodeticky pri OSM RSU, doloženou/označenou GW, zladenými TLE a beam mapou. Overiť, že SNS-3 naozaj vytvorí zvolený UT user, satelitný uzol a GW user, a že `GetBestBeamId` vracia zamýšľaný lúč. Archívny `sns3-reference-geo` neprepisovať.
3. **Jeden spoločný event clock.** Z `src/osm-ba-paired-backhaul.cc` prevziať Vanetza→ns-3 CAM/GN/BTP rádio a presný 96 B RSU report. SNS-3 `SimulationHelper` inicializovať v tom istom ns-3 procese a časový počiatok Vanetza `SimulatorRuntime` zhodovať s `start_date`. RSU report poslať cez meranú lokálnu LAN do SNS-3 `terminalUser`, potom jeho **úplne rovnaké aplikačné bajty** cez UDP `GetUserAddress(gatewayUser)` a fyzické SNS-3 user/satellite/feeder uzly do `gatewayUser`; až potom do samostatného servera, ak je požadovaný. Proxy vytvorí nové IP/UDP hlavičky, takže sa má overovať identita 96 B reportu a korelácia paketovej PHY stopy, nie tvrdiť identitu RF bitov medzi linkami.
4. **Vykonateľné brány.** Pozitívny beh musí mať päť rovnakých event ID, source CAM byte hash a rádiové časy ako pozemný párový beh; každý prijatý report musí mať nezmenené celé bajty, validný SHA-256 CAM a sekvenciu UT PHY SND→SAT RCV/SND→GW PHY RCV z `PacketTrace.log`. Nezávislý audit skontroluje geometriu v presných časoch týchto udalostí a potvrdí súlad identít fyzických uzlov s UT/GW geodetickými súradnicami. Samostatná záporná kontrola odstráni dostupnosť lúča alebo nastaví explicitne neviditeľný interval; ak SNS-3 napriek tomu doručí paket, experiment má **zlyhať geometriu/servis**, nie vykázať „úspech pri nedostupnosti“. Uložiť PCAP, surové aplikačné bajty, PHY packet trace, per-hop časy, checksumy dostupných IPv4/UDP rámcov, drop/attach dôvody, konfiguráciu a všetky neúspešné pokusy.

Tieto kroky sú nové implementačné brány, nie hotové výsledky. Dopravný vstup zostáva deterministický `randomTrips` na reálnej OSM geometrii, nie meraná premávka. Ani budúci DVB paketový úspech automaticky nevaliduje Starlink/Iridium/Globalstar rádio, rámce, plánovač alebo dostupnosť služby.
