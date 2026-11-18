# Izolovaný test servisného obalu Iridium Certus 100

**Stav:** 22. 10. 2026 UTC. **Kód:** [`src/iridium-certus100-envelope.cc`](../../src/iridium-certus100-envelope.cc), [`tools/run_iridium_envelope.py`](../../tools/run_iridium_envelope.py). **Rozhodnutie o službe:** [operátorské profily](../decisions/operator-services.md). Tento test nie je ešte satelitný experiment ani replika Iridium PHY/MAC. Overuje, že ďalšia integrácia dokáže rešpektovať publikované smerové **IP servisné stropy**, fronty, aplikačný deadline a účtovanie prenosu bez idealizovaného neobmedzeného linku.

## Hypotéza a reálny význam

Pri RSU s terminálom [SkyLink 5100](https://ifp.iridium.com/products/nal-research-skylink-5100-satellite-terminal/) môže vzdialený IP report odchádzať službou [Certus 100](https://www.iridium.com/services/iridium-certus-100). Terminál obsahuje [modul Certus 9770](https://www.iridium.com/products/iridium-certus-9770), pre ktorý výrobca uvádza najviac **22 kbit/s od terminálu** a **88 kbit/s k terminálu**. Nejde o garantované rýchlosti. Kontrolná hypotéza: ponúkané aplikačné zaťaženie pod príslušným stropom pri tomto nastavení frontu/deadline prejde, zaťaženie nad stropom spôsobí frontové straty alebo neskoré doručenie. Test nekalibruje komerčné oneskorenie.

Smer `up` v tomto teste znamená `UT → abstraktný výstup služby` (22 kbit/s); `down` znamená `abstraktný vstup služby → UT` (88 kbit/s). Každý smer sa spúšťa **v samostatnom ns-3 behu**; nejde o obojsmernú prevádzku ani fyzický satelit/gateway. Úsek `RSU → LAN → UT`, orbita, user link, ISL, feeder link a IP core sa doplnia v následnom integrovanom experimente. Tento test nemôže rozhodnúť, koľko reálnych ISL skokov alebo ktorú gateway používa Iridium.

## Algoritmus, vstupy a jednotky

1. ns-3.41 `PointToPointHelper` vytvorí dva IP uzly a jeden P2P serializer. `DataRate` je 22 alebo 88 **kbit/s**. `Delay=0 ms` znamená **vynechanú propagáciu**, nie fyzikálne nulové satelitné oneskorenie. P2P link je zámerne abstraktný service envelope; názvy `PhyTxBegin/PhyRxEnd` v API ns-3 tu opisujú P2P trace, nie satelitné rádio.
2. Aplikácia od `t=1 s` počas 10 s odosiela syntetické 300 B UDP reporty. Prvých 12 B je ns-3 `SeqTsHeader` s explicitne nastaveným `seq` a simulačným časom; zvyšok je bez sémantiky. Konštruktor `SeqTsHeader` nastaví čas na `Simulator::Now()`; kód pri odoslaní túto rovnosť kontroluje a prijímač odmietne čas z budúcnosti. Nie je to CAM, DENM ani natívny Iridium rámec. Ponúkaný **aplikačný** tok je `pps × 300 B × 8`, bez IP/UDP/PPP overheadu. P2P serializer účtuje aj tento overhead, teda výber jeho rýchlosti podľa *IP* maxima je konzervatívna testovacia aproximácia a nesmie sa zameniť za RF bitovú rýchlosť.
3. `DropTailQueue` zariadenia aj predvolený root queue-disc majú v teste `MaxSize=4p` **každý**. Sú to experimentálne hodnoty, nie publikovaná veľkosť interných front Iridia. Drop callback zaznamená skutočné zahodenie v príslušnej vrstve. Identifikátor konkrétneho zahodeného reportu v tomto trace nie je dekódovaný; kontrola preto účtuje počty, zatiaľ čo prijaté reporty sa identifikujú cez `SeqTsHeader`.
4. Prijímač považuje report za včasný, ak `t_rx_app − t_tx_app ≤ 500 ms`. **500 ms je testovací aplikačný deadline**, nie produktový limit ani predpoklad RTT. Neskorý report sa zaznamená `app_rx_expired`; fyzicky stále dorazil. Neprijatie sa nezamieňa s nameraným dlhým oneskorením.
5. CSV `event,direction,seq,time_s,bytes,detail` obsahuje `app_tx`, `p2p_tx`, `p2p_rx`, `queue_disc_drop`, `queue_drop`, `app_rx_on_time` alebo `app_rx_expired`. `seq=-1` znamená, že daná nižšia vrstva v tomto prototype nepreukázala ID reportu. Bajty v `app_*` sú aplikačné; bajty `p2p_*` zahŕňajú PPP/IP/UDP hlavičky. Beh sa zastaví najskôr 5 s po skončení zdroja; pri väčšom voliteľnom fronte vypočíta dlhší čas vyprázdnenia z dvoch front a smerovej rýchlosti.

**Verzie a pôvod:** Ubuntu `libns3-dev=3.41-1.1build1`; [Iridium Certus 9770](https://www.iridium.com/products/iridium-certus-9770) pre smerové produktové maximá a frekvenčné rozhranie; [SkyLink 5100](https://ifp.iridium.com/products/nal-research-skylink-5100-satellite-terminal/) pre pevné/mobilné použitie; ostatné parametre sú explicitné experimentálne voľby. `results/iridium_certus100_envelope/manifest.json` zapisuje SHA-256 kódu, verziu a nastavenia. Prípadné externé RTT meranie s **iným terminálom** nie je kalibračný parameter tohto testu.

## Reprodukcia a prijímací test

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 tools/run_iridium_envelope.py
```

Skript zostaví izolovaný C++ program systémovým ns-3, spustí štyri prípady a ukončí sa chybou, ak neplatí `app_tx = p2p_tx + drops`, `p2p_tx = p2p_rx = on_time + expired`, ak podlimitný beh stráca správy alebo ak nadlimitný beh nepreukáže zahodenie a nižší počet včasných správ. Kontroluje tiež sekvenčné unikátne ID odoslaných reportov, unikátne prijaté ID, úplnú rovnosť množín ID v podlimitnom behu a príslušnosť prijatých ID k odoslaným v preťaženom behu. ID zahodených reportov na queue-disc trace nie je dostupné, preto sa v preťažení nedá tvrdiť úplná per-packet identita dropu. Výstupy sú v `results/iridium_certus100_envelope/`; tento adresár je ignorovaný Gitom, ale reprodukovateľný príkaz a verzia sú tu.

| Prípad | Ponúkané aplikačné zaťaženie | Produktové maximum | TX / P2P TX / včas RX / neskoro / queue-disc drop | Výsledok |
| --- | ---: | ---: | ---: | --- |
| `up_under` | 12 kbit/s | 22 kbit/s od UT | 50 / 50 / 50 / 0 / 0 | Prešiel. |
| `up_over` | 72 kbit/s | 22 kbit/s od UT | 300 / 92 / 5 / 87 / 208 | **Negatívna kapacitná skúška prešla:** 208 zahodení a 87 neskorých prijatí. |
| `down_under` | 48 kbit/s | 88 kbit/s k UT | 200 / 200 / 200 / 0 / 0 | Prešiel. |
| `down_over` | 120 kbit/s | 88 kbit/s k UT | 500 / 341 / 341 / 0 / 159 | **Negatívna kapacitná skúška prešla:** 159 zahodení. |

**Neúspešné vývojové behy a kontrola kódu:** prvá verzia merala iba drop trace frontu zariadenia a pri preťažení hlásila nulu, hoci `app_tx > p2p_tx`: pakety zahadzoval predvolený ns-3 queue-disc. Pridal sa jeho drop trace aj explicitné `MaxSize`; účtovná rovnosť teraz platí. Ďalší problém: `ns-3 CommandLine` rozdelil absolútnu cestu obsahujúcu medzeru. Runner spúšťa binárku z výstupného adresára s relatívnym názvom CSV. Kontrola kódu potom odhalila, že pôvodný odosielací callback nevkladal `seq` do `SeqTsHeader`; opravil sa volaním `SetSeq(seq)` a runner teraz testuje množiny ID. Tieto chyby nie sú vlastnosťami satelitnej služby.

## Obmedzenia pre text práce

- Nižšia priepustnosť či výpadky v tomto teste **nie sú predikcia Iridia**. Sú dôsledkom publikovaných maximálnych IP smerových rýchlostí a našej dĺžky správy, tempa, deadline, dvoch 4-paketových front a zjednodušeného ns-3 P2P serializeru.
- Nie je implementovaný rádiový link budget, fading, doppler, attach, handover, crosslink, gateway, protokolový scheduler, FEC, retransmisie ani reálna IP kapacita po overhead. Nijaké komerčné RTT z testu nevyplýva.
- Presný aplikačný bajtový obsah možno zachovať cez budúcu RSU proxy, ale rámce a paketové ID na každej technológii sa menia. Neskoršia integrácia musí doplniť per-hop ID a dôvody zahodenia bez pripisovania nepozorovaného dropu konkrétnemu rádiovému hopu.
