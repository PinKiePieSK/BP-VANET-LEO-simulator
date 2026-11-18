# Rozbor jednej správy a jej paketovej cesty

**Stav 22. 10. 2026:** zmluva pre zjednotený inšpektor a budúce experimenty. Existujúci OSM párový replay má už päť event ID a presné raw bajty pre 13 fáz na správu a variant. Nové editovateľné scenáre zatiaľ nemajú sieťový beh; satelitná sonda sa implementuje oddelene. Zobrazenie nesmie vyplniť chýbajúce kroky imaginárnymi paketmi.

## Identita a čas

Každá **aplikačná informácia** dostane stabilné `event_id` pred prvým vyslaním. Jej pokusy o doručenie a všetky RX kópie nesú spolu toto ID; retransmisia môže mať ďalšie `attempt_id`. Ukladá sa absolútny UTC počiatok scenára, čas udalosti v celočíselných mikrosekundách simulačného času a zdroj časovej značky. Radenie krokov musí byť stabilné aj pri rovnakom čase. Pri párovom porovnaní sa `event_id`, obsah vstupnej správy, mobilita a seed nemenia.

| Položka raw kroku | Požiadavka |
| --- | --- |
| `event_id`, `attempt_id`, `flow_id` | naviazanie na jednu aplikačnú informáciu, pokus a plánovaný tok |
| `time_us`, `utc`, `node`, `stage`, `interface`, `peer` | kde a kedy bol krok pozorovaný; `peer` môže byť neznámy pri broadcast |
| `layer`, `wire_format`, `raw_hex`, `bytes` | skutočné bajty fázy alebo prázdne iba pri nepaketovej bráne; `bytes = len(raw_hex)/2` |
| `source_artifact`, `source_sha256`, `evidence_kind` | väzba na PCAP/CSV/PacketTrace a triedu `raw_packet`, `decoded_from_raw`, `model_gate`, `geometry_only` alebo `inferred` |
| `reason`, `profile_id`, `unmodelled_layers` | pri známej konfiguračnej bráne explicitný dôvod; inak `unknown`; nikdy neodvodzovať `PHY_ERROR` len z chýbajúceho prijatia |

Na jednom uzle môže vzniknúť **nová** správa. RSU v dnešnom pilote dekóduje prijatú CAM a vytvorí nový 96 B `ICB1` report. Inšpektor má zobraziť väzbu `derived_from=event_id`, hranicu konverzie a rovnosť vnútri vložených 41 B CAM, ale nemá volať report „tým istým paketom“. Podobne sa pri PPP/IP/UDP obale menia linkové bajty; porovnávať treba príslušnú vrstvu, nie celý rámec naprieč médiami.

## Obrazovky inšpektora

1. **Výber správy:** flow, pôvodné vozidlo, príjemca, event ID, čas a výsledok. Pri broadcast je viditeľná množina oprávnených prijímačov v danom čase.
2. **Cesta v čase:** chronologické riadky uzol→rozhranie→uzol, TX/RX, delta od predchádzajúceho pozorovaného kroku a delta od vytvorenia. Chýbajúca udalosť ostáva chýbajúca; na mape sa nesmie nakresliť dôkaz prenosu bez raw kroku.
3. **Rozklad bajtov:** raw hex, dĺžka, dekódované polia iba podľa skutočného kódovania (CAM UPER, GN/BTP, 802.11, IPv4/UDP, `ICB1`, PPP). Pri prechode cez RSU sa vyznačí pôvodná CAM a nová hlavička/report. Kontrolný súčet alebo hash sa kontroluje skriptom, nie iba farbou v UI.
4. **Rozklad času:** vytvorenie, lokálne rádio, spracovanie RSU, LAN, vzdialený user/feeder/ISL/gateway úsek **iba ak je implementovaný**, server. Každý krok má jednotku a uvedenú hranicu časovej presnosti.
5. **Vernostná stopa:** odznak `skutočné bajty v ns-3/PCAP`, `štandardovo dekódované`, `modelová abstrakcia`, `iba geometria`; pri každom profile sa zobrazí, ktoré RF/MAC, terminál, beam, handover alebo operátorské routing vrstvy chýbajú.

## Akceptačné kontroly

- Inšpektor načíta iba výsledok, ktorého zdrojové súbory a replay prešli kontrolou SHA-256.
- Pre každé ID presne spojí TX/RX fázy a nezamení päť časových polôh jedného auta za päť áut.
- Bajty každého raw kroku sú identické s príslušným CSV alebo PCAP; detekcia zmeneného bajtu vyvolá zlyhanie.
- Záporná kontrola má zachovaný TX a explicitne zvolený drop/gate dôvod, ak ho model pozná; chýbajúci RX sa nepremenuje na zistenú príčinu.
- Satelitné kroky sa ukážu iba pri scenári s reálnym satelitným uzlom v paketovom modeli a s časovo/geograficky zosúladeným vstupom. Generický ns-3 P2P frame sa nikdy neoznačí ako proprietárny satelitný PHY.

Inšpektor má podporiť obhajobu meraní tým, že každý súhrnný graf možno rozkliknúť po správu a po skutočný zdrojový bajt. Jeho vizualizácia je odvodená z dôkazov, nie ich náhrada.
