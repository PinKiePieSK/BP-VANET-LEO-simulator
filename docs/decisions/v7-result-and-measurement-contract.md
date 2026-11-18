# V7 — kontrakt výsledku, neistoty a terénneho merania

Stav: vykonateľný výsledkový kontrakt pre overené P5 natívne a V6 servisné raw stopy. Kalibrácia a nezávislá validácia sú `null`, pretože projekt nemá porovnateľné terénne merania rovnakého payloadu, koncového bodu, zariadenia, plánu, miesta a času. V7 nepripisuje historickým produktovým údajom status nameraného výkonu.

## Autoritatívne vstupy a metrika

Vopred uložený protokol je [`config/v7_result_protocol.json`](../../config/v7_result_protocol.json). Primárny menovateľ je počet unikátnych ICB1 vytvorených RSU v danej jednotke a vetve. Čitateľ je počet unikátnych rovnakých ICB1 doručených vzdialenej aplikácii do **60 s od RSU vytvorenia**. V P5 je koncový bod `GATEWAY_ACCEPT`; vo V6 `REMOTE_APP_RX`. Sekundárne sa vykazuje návrat do auta (P5 `CAR0_I2V1_RX`) alebo lokálne aplikačné potvrdenie RSU (V6 `RSU_RECEIPT_RX`). Oneskorenie sa počíta iba pre včas doručené správy; pri nulovom doručení je `null`, nie nula. Deadline je výskumný prah, nie komerčná SLA.

[`events.jsonl`](../../results/v7_result_api_20261026/events.jsonl) má jeden záznam pre každú aplikáciu a vetvu. Kľúč zahŕňa rodinu, seed/UTC/skupinu/vetvu alebo službu/prípad a ID správy. Záznam má `execution`, `fidelity`, odkaz a SHA-256 raw CSV, presné číslo každého raw riadku, čas, veľkosť a hash payloadu, štyri vrstvy (`ground`, `access`, `satellite_or_service`, `return`) so stavom a dôvodom. V6 navyše odkazuje na pôvodné natívne CAM a RSU riadky; servisný čas preto nemožno zameniť za natívne SNS-3 udalosti. `not_observed` sa neprekladá na konkrétnu fyzickú príčinu bez raw dôkazu.

[`results.json`](../../results/v7_result_api_20261026/results.json) poskytuje strojovo čitateľné metriky po vetvách. Každý číselný výsledok obsahuje hodnotu, jednotku, `model_only` alebo `sensitivity`, rozsah platnosti a presné `event_keys`; frakcie majú čitateľ a menovateľ. `externally_validated` je povolená budúca hodnota schémy, ale aktuálny checker ju pri chýbajúcich meraniach výslovne odmieta. Manifest pinuje všetky zdroje, kód, výsledky a graf pomocou SHA-256. `figure-data.csv` prepája každý bod grafu s ID metriky a cez ňu s raw eventmi; checker graf znovu vykreslí a porovná bajtovo.

## Štatistická jednotka a identifikovateľnosť

P5 má šesť RNG seed klastrov. Dve UTC epochy sú vzdialené iba **92 s** a zostávajú v tom istom klastri pri 10 000 deterministických bootstrap výberoch. Tento interval je iba podmienená neistota daného modelu, umelého dopytu, archivovaných orbitálnych vstupov a šiestich seedov. Neodhaduje rozdiel dní, lokalít ani operátorskú prevádzku. Nulová šírka pri 100 %/0 % úspechu neznamená nulovú prevádzkovú neistotu.

V6 má jednu šesťsprávovú deterministickú dávku na vetvu; jej citlivosti **nie sú replikácie**. Interval `conditional_remote_fraction_min/max` je iba min–max z troch uvedených scenárov pri predpokladanej dostupnej službe. Keďže pravdepodobnosť dostupnosti nie je meraná, bezpodmienečný identifikovateľný rozsah je 0–1. Globalstar môže mať vo vzorke podmienene 1–1, no bezpodmienečný rozsah ostáva 0–1. Z tohto výsledku sa nedá odvodiť pravdepodobnosť výpadku ani reálne poradie služieb.

Percentily p95 a p99 latencie sú `null`. Šesť seed klastrov a jediná V6 dávka nemajú rozlíšenie pre nezávislý chvostový odhad, zvlášť pri stratách a cenzorovaní. Projektová budúca brána požaduje najmenej 100 nezávislých jednotiek beh–deň–miesto pre p95 a 1 000 pre p99 plus pozorované chvostové udalosti; tieto prahy sú konzervatívne rozhodnutie projektu, nie záruka štatistickej presnosti.

## Oddelené brány kvality

1. **Implementácia:** V7 checker kontroluje raw riadky, aplikáciu, čas, vrstvy, menovatele, metriky, hashe a regeneráciu grafu. Preberá aj read-only V6/P4 audit. Historický P5 natívny checker overil PCAP a stage stopy; V7 znovu páruje jeho raw trace s per-event metrikami.
2. **Zhoda s normou/modelom:** V5 má len vybraný CAM/DCC audit; V4 je generická DVB referencia; V6 má publikované hranice payloadu a product maxima. Tieto dôkazy nie sú operator RF/MAC konformita.
3. **Kalibrácia:** `null`. Bez porovnateľného externého súboru sa žiadna latencia, strata ani dostupnosť nedolaďuje na „realitu“.
4. **Nezávislá validácia:** `null`. P5 seed bootstrap a V6 citlivosti nie sú held-out terénne dáta.

## Kontrakt budúcich meraní

[`tools/validate_v7_measurements.py`](../../tools/validate_v7_measurements.py) akceptuje CSV s presným `FIELDS`: profil, site ID a súradnice, UTC deň, run ID, SKU, anténa, plán, ID a SHA-256 ICB1, UTC vznik/vzdialené doručenie/návrat, koncový bod `REMOTE_APP_RX_ICB1`, cestu a hash pôvodného logu. Vyžaduje všetkých šesť reportov na beh, chronológiu a aspoň dve nezávislé skupiny **na každý profil**. Skupina je UTC deň × miesto × SKU × anténa × plán; všetky jej behy zostávajú spolu. Zoradené skupiny sa striedavo priradia do kalibračnej a held-out validačnej množiny. To zabraňuje úniku rovnakého dňa medzi sady, ale samotné rozdelenie ešte nedokazuje reprezentatívnosť.

Brána vracia iba `candidate_external_dataset_only`. Ak sa miesto líši od simulovaného RSU, žiada nový beh. Ak je SKU, anténa alebo plán v profile predpoklad D alebo nesúhlasí s meraním, vypíše blokátor. SHA-256 preukazuje integritu súboru, nie autenticitu prístroja; obsah logu a pôvod zariadenia musí samostatne preveriť človek. Až po tomto audite možno zafixovať kalibračnú a nezávislú validačnú sadu, porovnať identické koncové body, reportovať chybu na held-out skupinách a zvážiť štítok `externally_validated` s úzkym rozsahom platnosti. Syntetická testovacia CSV existuje iba dočasne počas testu a nie je terénnym dôkazom.
