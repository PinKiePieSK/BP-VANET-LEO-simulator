# Model pilotu: účel, rozhrania a hranice platnosti

## Architektúra

`car0 -> car1` je lokálne V2V. `car0 -> RSU -> vzdialený server` je V2I plus abstraktný satelitný backhaul. Vozidlo v tomto pilote nemá satelitný terminál. Vzdialený server je koncový bod IP siete, nie uzol umiestnený na obežnej dráhe. Satelitný segment je reprezentovaný jednou kapacitne obmedzenou bodovou linkou s oneskorením a voliteľným výpadkom. Tento model umožňuje skúmať účinok backhaulu na doručenie paketov, ale **nereprezentuje konšteláciu, orbitálny pohyb, prepínanie satelitov, spektrum, antény, Dopplerov jav ani skutočnú dostupnosť služby**.

## Moduly a dátový tok

| Modul | Algoritmus a vstup | Výstup a jednotky | Predpoklad a obmedzenie |
| --- | --- | --- | --- |
| `scenarios/pilot/*.xml` | Jeden rovný jednopruhový úsek dlhý 2000 m; dve vozidlá v čase 0 a 2 s; `netconvert`, SUMO 1.18.0, krok 0.5 s, seed 42. | `road.net.xml`, FCD XML, sumár SUMO. FCD `x,y` v m, `speed` v m/s, čas v s. | Syntetická cesta bez križovatiek a premávkovej neistoty. Nevydávať za reálnu mapu ani validovaný dopravný model. |
| `tools/fcd_to_waypoints.py` | Streamuje FCD XML; vyberá `car0`, `car1`; kontroluje konečné čísla, kladnú rýchlosť a rastúci čas. | CSV `time_s,vehicle_id,x_m,y_m,speed_mps`. | Polohy sa nemenia projekciou. SUMO `x,y` označujú prednú časť vozidla; pri pilote sa používajú priamo ako poloha rádia. |
| `src/pilot-network.cc` | Interpoluje SUMO polohy cez `WaypointMobilityModel`; vytvára 802.11p V2V/V2I Wi-Fi, UDP pakety po 1 s a abstraktnú 5 Mb/s linku RSU–server. | CSV `flow,seq,event,time_s`, jednotka času s. | Nastavenia rádia a backhaulu nižšie sú scenárové predpoklady, nie merania. Ns-3 seed 42, run 1. |
| `tools/analyze_events.py` | Páruje vyslané a prijaté pakety podľa toku a poradového čísla. | JSON a CSV: PDR = RX/TX, priemerné jednosmerné oneskorenie v ms, priemerná absolútna zmena oneskorenia susedných doručených paketov v ms, dostupnosť = podiel 5 s okien s aspoň jedným doručením. | Nedodaný paket nemá oneskorenie ani jitter. Dostupnosť je aplikáciou pozorovaná v testovaných oknách; nie orbitálna viditeľnosť. Jeden beh nie je štatistický odhad. |

## Parametre

| Parameter | Hodnota | Pôvod a odôvodnenie |
| --- | --- | --- |
| Dopravný krok | 0.5 s | Voľba pilotu; SUMO umožňuje nastaviť krok a upozorňuje na dôsledky zmeny. [SUMO – Basic Definition](https://sumo.dlr.de/docs/Simulation/Basic_Definition.html) |
| Polohy vozidiel | SUMO FCD každých 0.5 s | [SUMO – FCD Output](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html) uvádza význam súradníc a rýchlosti. |
| Pozemné rádio | `WIFI_STANDARD_80211p` (10 MHz, 6 Mb/s) s `AdhocWifiMac` | Ubuntu balík ns-3.41 obsahuje profil 802.11p, ale nie WAVE modul a `Wifi80211pHelper`. Implementácia preto nepoužíva OCB/WAVE MAC ani ITS-G5 stack; je to zjednodušený ad-hoc Wi-Fi model s 802.11p PHY nastaveniami. [ns-3 Wi-Fi model](https://www.nsnam.org/docs/models/html/wifi-user.html). |
| Výkon rádia | 20 dBm | Pracovný predpoklad na overenie pipeline; pred odbornou interpretáciou treba kalibráciu voči zvolenému nasadeniu a právnemu rámcu. |
| Pozemný útlm | Log-distance exponent 2.7, strata pri 1 m 47.86 dB | Exponent je pracovný predpoklad prostredia. Referenčná strata je výpočet voľného priestoru `20 log10(4π f/c)` pri `f=5.9 GHz`; neobsahuje tienenie vozidlami, zástavbu ani fading. |
| RSU | `(600, -1.6, 0)` m | Scenárový bod pri ceste; bez optimalizácie umiestnenia. |
| LEO výška na dolnú hranicu šírenia | 550 km | Ilustračná hodnota v rozsahu LEO uvedenom v [ITU satelitnej príručke](https://www.itu.int/dms_pub/itu-r/opb/hdb/R-HDB-42-2002-PDF-E.pdf). Nepriraďuje sa konkrétnemu prevádzkovateľovi. |
| Backhaul jednosmerné oneskorenie | `2 × 550000 / 299792458 + 0.010 ≈ 0.013669 s` | Dva zvislé úseky (uplink + downlink) sú **optimistická dolná hranica geometrickej dráhy**; 10 ms spracovanie je výslovný scenárový predpoklad. Bez elevácie, routingu a front v skutočnej sieti. |
| Backhaul kapacita | 5 Mb/s | Scenárový predpoklad, nie špecifikácia satelitnej služby. |
| Výpadok | interval `[32,37)` s, iba variant `outage` | Umelo vložená kontrolovaná porucha na prijímači backhaulu. Nie je odvodená z TLE ani z orbitálnej predikcie. |
| Prevádzka | 300 B UDP raz za sekundu; V2V v 5–54 s, V2I/backhaul v 27–51 s (V2I o 100 ms neskôr) | Jednoduché diagnostické zaťaženie, nie skutočný profil bezpečnostných správ. Posun začiatku V2I/backhaulu bráni štartu pred dosahom RSU, ktorý v prvom neúspešnom behu zabránil ARP nadviazaniu. |

## Overovanie vierohodnosti

Pilot musí spĺňať: SUMO bez kolízií a teleportov, rýchlosť vozidiel pod 20 m/s, logické monotónne polohy, RX bez záporného oneskorenia, referenčný 802.11p tok s kladným doručením a menšie doručenie backhaulu vo variante `outage` ako v kontrolnom variante `nominal`. Pri ďalšom míľniku treba doplniť kalibrovaný rádiový model, viac scenárov a viac semien; výsledky pilotu nepoužiť ako všeobecné tvrdenie o VANET alebo LEO.

## Satelitné moduly

Lokálny Hypatia checkout je na commite z roku 2022 a obsahuje ns-3.31. Je cenný ako odborná referencia, ale jeho priame napojenie na zvolený ns-3.41 by vyžadovalo kompatibilitnú prácu. [SNS-3](https://github.com/sns3/sns3-satellite) sa udržiava a verzie modulov sa viažu na konkrétne ns-3 tagy; súčasný hlavný zdroj uvádza kompatibilitu s ns-3.48. Pre tento pilot, ktorý zámerne abstrahuje backhaul, satelitný modul netreba. Ak sa neskôr stanoví otázka na PHY, orbitálnu viditeľnosť alebo handover, zvoliť zodpovedajúci, spoločne otestovaný stack a preukázať jeho inštaláciu malým príkladom.
