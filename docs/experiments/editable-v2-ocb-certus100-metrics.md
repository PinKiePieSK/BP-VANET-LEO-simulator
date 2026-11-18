# Metriky jedného OCB→Certus IP modelového behu

## Hypotéza a jednotka porovnania

Kladný a synteticky blokovaný variant [jediného ns-3.38 experimentu](editable-v2-ocb-certus100-e2e.md) majú rovnakých šesť pôvodných CAM a šesť RSU reportov `ICB1`. Počet správ prijatých serverom sa preto dá porovnať **voči vytvoreným RSU reportom**. Hypotéza kontroly: kladný kandidátsky gate zachová 6/6 pri malej ponuke, synteticky vypnutý 0/6, pričom lokálna CAM vetva zostane identická. Nejde o hypotézu, že skutočná služba Iridium bude mať takú istú dostupnosť.

## Reprodukcia a algoritmus

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/run_editable_v2_ocb_certus100_e2e.py
.venv/bin/python tools/analyze_editable_v2_ocb_certus100_metrics.py
```

Druhý príkaz iba číta `run-manifest.json`, `verification.json`, dva raw `trace.csv` a geometrické plány; pred výpočtom kontroluje ich SHA-256 a počty/ID overené paketovým checkerom. Výsledok uloží do `results/editable_v2_ocb_certus100_e2e/metrics.json` s hashom vstupnej verifikácie a per-event časmi. Jednotkou je jeden unikátny `event_id` reportu pripraveného na RSU, nie jeden 802.11 rámec či pokus modemu.

Definície:

- `cam_pdr_at_rsu = prijaté CAM na rsu0 / 6` a `server_delivery_fraction_of_created = unikátne serverové ICB1 / 6`. Druhá hodnota pri blokovaní zahŕňa **predservisné scenárové rozhodnutie** a nie je samotnou servisnou PDR.
- `service_delivery_fraction_of_offered = serverové ICB1 / odoslané zo RSU do servisnej vetvy`; pri 0 ponúknutých správach je `null`, nie 0 ani 100 %.
- Jednosmerný čas na aplikačnej hranici je `SERVER_ACCEPT - RSU_REPORT_TX` v µs; návratový `RSU_ACK_RX - RSU_REPORT_TX` v µs. Počítajú sa len doručené ID. Neobsahujú Iridium RF/propagation, preto nejde o operátorskú latenciu alebo RTT.
- Opisná zmena oneskorenia je priemer absolútnych rozdielov jednosmerných časov **susedných pôvodných doručených ID**. V kladnom behu je päť párov, pri úplnom bloku nula a hodnota `null`. Chýbajúcim paketom sa nepriraďuje nulové oneskorenie.
- `candidate_gate_open_fraction` je podiel šiestich vzoriek, v ktorých **experimentálny** geometrický prepínač dovolil odoslanie. Nie je to dostupnosť siete, lúča ani produktu.

## Overený výsledok a interpretácia

| Variant | CAM na RSU | RSU ICB1 vytvorené | Ponúknuté servisu | Server | GRA1 na RSU | Priemer RSU→server | Priemer RSU→RSU ACK | Zmena oneskorenia |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kladný kandidát | 6/6 | 6 | 6 | 6 | 6 | 45 928 µs | 52 943 µs | 0 µs; 5 párov |
| Umelý blok kandidáta | 6/6 | 6 | 0 | 0 | 0 | `null` | `null` | `null`; 0 párov |

Priemerný čas CAM→RSU bol v oboch variantoch 217,5 µs. Kladná `service_delivery_fraction_of_offered` je 1,0 v tomto **šesťsprávovom nezaťaženom modeli**; blokovaná je nedefinovaná. Oddelený [záťažový obal](certus100-icb1-ip-envelope-38.md) používa syntetické opakovania a vlastný front, nie hustú CAM premávku. Rozdiel kladného/blokovaného variantu nie je meraním Iridium outage. Vypočítané 0 µs variation pochádza z konštantného serializátora a nie je dôkazom nulového jitteru služby. Pre porovnávanie reálnych operátorov ešte treba ich konkrétne terminály, služby, kalibrované RF/servisné dáta a rovnaký aplikačný workload.
