# Izolovaná sonda mestského V2V LOS/NLOS rádia

**Dátum:** 22. 10. 2026. **Verzia:** lokálne zostavené `vendor/ns-3.48` (ns-3.48); nové izolované [C++](../../src/v2v-urban-radio-probe.cc), [runner](../../tools/run_v2v_urban_radio_probe.sh), [kontrola](../../tools/check_v2v_urban_radio_probe.py). Tento experiment realizuje úzky krok z [rozhodnutia o ďalšej vernosti rádia](../decisions/radio-fidelity-next.md). Neimplementuje OCB, DCC, CAM, mapu Bratislavy ani kalibráciu reálnych jednotiek.

## Hypotéza a scenár

Pri rovnakej vzdialenosti, anténach a ponúkanom UDP toku bude podľa **vybraného 3GPP TR 37.885 urban V2V modelu** budovou blokovaná spojka klasifikovaná ako NLOS a bude mať vyšší vypočítaný útlm než kontrolná LOS spojka. Dvojica fiktívnych áut stojí 60 m od seba; uprostred je v jednom variante jednoduchá budova. Je to laboratórna citlivostná skúška významu geometrie, nie predpoveď PDR konkrétnej križovatky. [3GPP TR 37.885](https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3209), [implementácia ns-3.48](https://gitlab.com/nsnam/ns-3-dev/-/blob/ns-3.48/src/propagation/model/three-gpp-v2v-propagation-loss-model.cc), [nezávislé 5,9 GHz križovatkové merania](https://www.dsn.kastel.kit.edu/download/bmw/nlos_model/index.html).

## Algoritmus a jednotky

| Prvok | Nastavenie, dôvod a obmedzenie |
| --- | --- |
| Geometria | TX `(0,0,1.5)` m, RX `(60,0,1.5)` m. Pri `building` je syntetická budova `x=[25,35]`, `y=[−5,5]`, `z=[0,10]` m. Výšky a šírky sú **testovacie predpoklady**, nie lokálne merania. Obe autá sú vonku. |
| Tri režimy | `forced_los`: `AlwaysLosChannelConditionModel`; `forced_nlos`: `NeverLosChannelConditionModel`; `building`: `ThreeGppV2vUrbanChannelConditionModel` nad explicitným ns-3 `Building`. Prvé dva kontrolujú rovnice a packet path; tretí kontroluje geometrickú klasifikáciu budovy. NLOSv sa v tejto sonde nenúti ani neštatisticky nevyhodnocuje. |
| Útlm | `ThreeGppV2vUrbanPropagationLossModel`, `Frequency=5.9e9` Hz, `ShadowingEnabled=false`, penetrácia budovy vypnutá. LOS = `38.77 + 16.7 log10(d/m) + 18.2 log10(f/GHz)` dB; NLOS = `36.85 + 30 log10(d/m) + 18.9 log10(f/GHz)` dB. Vypnutie shadowingu izoluje analytický výpočet; nepredstavuje reálny kanál. [ns-3.48 zdroj](https://gitlab.com/nsnam/ns-3-dev/-/blob/ns-3.48/src/propagation/model/three-gpp-v2v-propagation-loss-model.cc). |
| Rádiová cesta | `WIFI_STANDARD_80211p`, `YansWifiPhy`, 10 MHz kanál 180 / 5900 MHz, `OfdmRate6MbpsBW10MHz`, 20 dBm TX, zisk antén 0 dB, RX noise figure 7 dB. Frekvencia/šírka/rýchlosť sú z [ETSI EN 302 663 V1.3.1](https://www.etsi.org/deliver/etsi_en/302600_302699/302663/01.03.01_60/en_302663v010301p.pdf); 20 dBm a 7 dB sú **testovacie nastavenia bez kalibrácie terminálu**. `AdhocWifiMac` je len OCB podobný. Unicast môže retransmitovať podľa predvoleného Wi-Fi MAC; PCAP zachováva tieto pokusy. |
| Obsah a zaťaženie | Štyri syntetické **UDP/IPv4** datagramy po 32 B aplikačného obsahu, seq 1–4 vo veľkom endian na prvých 4 B, potom presné bajty `04..1f`. Interval 200 ms od 1,2 s. Nie sú to CAM ani ETSI správy. Trvalá ARP položka v TX zaisťuje, že NLOS zlyhanie nezamieňame za nedoriešenú IP→MAC adresu. |
| Náhodnosť | ns-3 `RngSeedManager::SetSeed(314159)`, run 1, priradené RNG streamy 5 (condition) a 10 (loss). Pri pevných podmienkach a vypnutom shadowingu sú výsledky deterministické. |
| Výstupy | `MODEL` loguje zvolený `condition`, analytický path loss a `CalcRxPower` RSS v dBm. `UDP_TX`/`UDP_RX` logujú simulačný čas v ns a celé payload bajty v hex. `SUMMARY` rozlišuje modelový RSS od **skutočného PHY signal/noise trace**; pri nulovom príjme je tento trace `NA`. `DLT_IEEE802_11` PCAP ukladá celé vyslané/prijaté rámce s IP/UDP. |

## Príkaz a výsledky

```bash
bash tools/run_v2v_urban_radio_probe.sh
```

Runner kompiluje len jeden C++ súbor proti už zostavenému ns-3.48; žiadne `sudo`, inštalácia ani paralelný build. Surové logy a PCAP sú v `results/v2v_urban_radio/` (ignorované Gitom); kontrolný skript číta tieto artefakty.

| Režim | Condition | Analytický útlm | Modelový RSS | UDP prijaté | PHY signal trace |
| --- | --- | ---: | ---: | ---: | ---: |
| `forced_los` | LOS | 82,494632 dB | −62,494632 dBm | 4/4 | −62,494632 dBm pri poslednom úspešnom príjme |
| `forced_nlos` | NLOS | 104,763641 dB | −84,763641 dBm | 0/4 | N/A |
| `building` | NLOS | 104,763641 dB | −84,763641 dBm | 0/4 | N/A |

**Interpretácia:** pri týchto testovacích voľbách model dáva rozdiel útlmu **22,269009 dB**; zvolený ns-3 PHY/MAC preto prijal štyri LOS UDP datagramy a žiadny NLOS. Táto PDR z **iba štyroch** správ nie je odhad reálnej spoľahlivosti. NLOS modelový RSS je hodnota výpočtu `CalcRxPower`, nie nameraná sila prijatého rámca; pri NLOS nebol ani jeden úspešný PHY RX. Zdrojové PCAP obsahujú každý z odoslaných payloadov aj pri NLOS; viacero kópií tam vzniká z Wi-Fi retransmisií. Pri LOS kontrola našla rovnaké bajty v prijímacom PCAP a aplikačnom logu.

## Kontroly a záznam neúspešného pokusu

- Kontrolný skript prepočítal obe rovnice nezávisle od C++, overil stav NLOS pri budove, štyri seq/payloady, súlad TX/RX bajtov, prítomnosť bajtov v TX a RX PCAP a zhodu LOS PHY signal s modelovým RSS do 0,001 dB. Tri režimy prešli.
- Opakovaný beh `--scenario=forced_los --separationM=60 --seed=314159` dal bajtovo rovnaký log (`cmp`). Pozmenenie `condition=LOS` v kópii logu na NLOS spôsobilo očakávané zlyhanie checkera.
- **Neúspešný prvý pokus:** bez trvalého ARP záznamu sa pri NLOS neodoslali IP/UDP rámce, pretože ARP odpoveď nedošla. Rovnaký výsledok 0/4 by nesprávne prisudzoval rádiu. Po pridaní statického ARP záznamu zdrojový PCAP dokazuje skutočné odoslanie každého UDP payloadu. Tento zásah je diagnostické odstránenie ARP konfúzie, nie realistický mechanizmus objavovania susedov.

## Hranice tvrdenia a ďalší krok

Sonda **neobsahuje** 3GPP rýchle úniky, kalibrované materiály budov, skutočné vozidlové tienenie, anténne diagramy, Doppler, meraný hluk, OCB/EDCA profil ITS-G5, DCC, dynamické generovanie CAM ani V2I/RSU propagáciu. Budova je umelá; 3GPP V2V model bol pôvodne určený pre LTE/NR V2X hodnotenie, hoci útlm pri rovnakej frekvencii možno testovať ako oddelený fyzikálny vstup 802.11p. Nie je preto dôkazom zhody s Bratislavou alebo konkrétnymi komerčnými jednotkami. [ns-3 WAVE/OCB dokumentácia 3.38](https://www.nsnam.org/docs/release/3.38/models/html/wave.html), [ETSI CAM frekvencia/DCC V2.3.1](https://www.etsi.org/deliver/etsi_ts/103900_103999/103900/02.03.01_60/ts_103900v020301p.pdf).

Ďalší krok: nahradiť fiktívnu geometriu auditovanými budovami a výškami pre jednu trasu, merať sériu vzdialeností/semená a oddelene porovnať RSS/PDR s **nezávislou** 5,9 GHz LOS/NLOS kampaňou pri podobnej geometrii; až potom skúmať prenesenie do spoločného CAM/backhaul behu. Pre RSU s vyššie umiestnenou anténou je potrebný samostatný model alebo validácia.
