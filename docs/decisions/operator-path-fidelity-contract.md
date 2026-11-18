# Brána tvrdení pre satelitnú paketovú cestu

**Audit 22. 10. 2026 UTC.** Tento kontrakt pripúšťa práve jeden reprodukovateľný výrok: päť reportov RSU prešlo **otvoreným diagnostickým ns-3 modelom** s geometriou archívneho objektu Globalstar 37741. Kontrakt výslovne odmieta výrok, že ide o meranie alebo predikciu služby Globalstar. Konkrétna konfigurácia je [`globalstar-open-geometry-packet.json`](../../data/inputs/operator-path-contracts/globalstar-open-geometry-packet.json); spustiteľný audit je [`audit_operator_path_contract.py`](../../tools/audit_operator_path_contract.py).

## Reprodukcia

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
.venv/bin/python tools/test_operator_path_contract.py -v
.venv/bin/python tools/audit_operator_path_contract.py \
  --config data/inputs/operator-path-contracts/globalstar-open-geometry-packet.json \
  --output results/operator_path_contract/globalstar-open-audit.json
sha256sum results/operator_path_contract/globalstar-open-audit.json
```

Testy: **10/10**. Audit: `status=pass`, `claim=open_packet_model`, päť vzoriek. SHA-256 výstupného JSON: `cb14ba6f1f2bfe011637bb06649695e594323ab8031e71830b712e034816a04f`; skript ukladá aj SHA-256 konfigurácie, vlastného kódu, manifestu, paketového plánu a trace do výstupu. Pri neúspešnom behu odstráni starý výstup na tej istej ceste, aby po zmene vstupu nezostal zdanlivý `pass`. Nevyžaduje sieťové spojenie ani novú kompiláciu.

Vstupný geometrický CSV má SHA-256 `f7c2a1280c4f1a005971cc9ab5ab2c20e053422b4083dca3c0a84fd09edc59c3`; manifest archívu `d28ad3618304780d3cd118e83e8e8a2e88c14d015fa022c3082ba7b2f624d826`; paketový plán `f3a40a58c72f7720d29185d9c6d5e97b4bf72f3dfce44061152277099ceb1b15`; manifest paketového behu `b9646816bee57713826d89cfdb245172eebc5e12bce970c1abdb8ae36478c47b`; verifikačný záznam `fff2e47e977d5b3c7d3f8fdde706f0d7c8a0aad440f6a05aeae2b7c8cec3ad66`; raw paketový trace `c8bc5dfe8641bd726a7604b0abbd565ac7b1c77d90019d59548b2c457e1744ca`. Audit preveruje tieto bajty, zhodu plánu s vypočítanými časmi a predchádzajúci úspešný paketový checker. Podrobnosti 96 B `ICB1` reportu a štyroch ideálnych P2P hrán sú v [paketovej sonde](../experiments/osm-leo-hop-probe.md).

## Čo sa počíta

[CelesTrak vysvetľuje](https://celestrak.org/NORAD/documentation/gp-data-formats.php), že GP/OMM sú priemerné orbitálne elementy určené pre SGP4; OMM odstraňuje obmedzenie päťmiestneho katalógového čísla TLE. Lokálny `20261022T124815Z-retlector` archív obsahuje OMM záznam 37741 s epochou **21. 10. 2026 06:54:00,067392 UTC** a kanonickým SHA-256 `64a1f3de50a39556c1d94d33d7369589ee0b6ea3a3624af70c80796c661311aa`. Snímka bola získaná **22. 10. 2026 12:49:43,719531 UTC**, zatiaľ čo prehrávanie začína 12:45:00 UTC. Je to retrospektívna rekonštrukcia, nie predpoveď, ktorú mohol mať terminál na začiatku behu. Vek elementu pri piatich udalostiach je **29,8514–29,8525 h**, pod experimentálnym stropom 48 h; tento strop negarantuje presnosť dráhy.

Pevný bod RSU `48,1482681° N, 17,1085885° E, 0 m` zastupuje hypotetický používateľský terminál. Koncový bod `37,8167° N, 22,6667° E, 0 m` je **centrum mesta Nemea**, nie poloha antény. [Globalstar 21. 9. 2026 oznámil](https://investors.globalstar.com/news-releases/news-release-details/globalstar-completes-expansion-greece-ground-station-marking-key) rozšírenie stanice v Nemea, no súčasne uviedol, že uvedenie novej infraštruktúry do prevádzky ešte prebiehalo. Oznámenie nedokazuje prevádzkový stav ani priradenie konkrétneho staršieho objektu, služby a antény pri našej udalosti. [Opis siete Globalstar](https://www.globalstar.com/en-us/about/our-technology) podporuje dvojkoncovú transparentnú cestu používateľ–satelit–pozemná brána; preto na oboch koncoch testujeme **ten istý katalógový objekt**. Maska 10° je experimentálny vstup, nie limit výrobcu.

Audit znovu načíta hashovaný OMM a vypočíta SGP4 polohu, WGS84 topocentrickú eleváciu a šikmú vzdialenosť pomocou Skyfield 1.55 / python-sgp4 2.27. Porovnáva ich s uloženým výpočtom Astropy TEME→ITRS. **SGP4 jadro je spoločné**: ide o druhú implementáciu transformácie a topocentrie, nie nezávislé potvrdenie skutočnej dráhy. Skyfield používa zabudovaný časový podklad; odvodené Astropy CSV použilo pripnuté IERS EOP. Rozdiely z toho môžu pochádzať. Tolerancie 0,01° elevácie, 0,1 km vzdialenosti a 0,001 ms dvojvetvového `r/c` sú *kontrola konzistencie*, nie empirická chyba orbity.

| UTC 22. 10. 2026 | Elevácia RSU / Nemea | Dosah RSU / Nemea | `(r₁+r₂)/c` | Negatívna kontrola toho istého objektu |
| --- | --- | --- | --- | --- |
| 12:45:05 | 21,3603° / 22,7879° | 2727,0424 / 2648,5024 km | 17,9309 ms | bod 37,8167° N, 100° W: −39,7191° |
| 12:45:09 | 21,1099° / 22,4123° | 2741,1806 / 2668,6271 km | 18,0452 ms | −39,7129° |

Medzi nimi sú vzorky v sekundách 06, 07 a 08; všetkých päť je nad 10° na **oboch** kladných koncoch. Záporný západný bod je len geometrický kontrolný prijímač pre **rovnaké ID 37741**, nie tvrdenie, že tam nie je viditeľný nijaký iný satelit. Maximálny rozdiel oproti uloženému Astropy CSV bol približne 0,00062°, 0,03285 km a 0,000214 ms. `c=299792,458 km/s`; vypočítaný súčet dvoch vákuových oneskorení je fyzikálna dolná hranica, pretože neobsahuje serializáciu, RF/MAC, fronty, spracovanie, opakovanie ani pozemný core. Packet probe pridáva štyri **idealizované 1 Gbit/s** PPP/IP/UDP P2P hrany; jeho približne 17,935–18,049 ms nie je meraním Globalstar.

## Fail-closed kontrakt

`requested_claim=open_packet_model` prejde len pre presne pripnutý Globalstar profil: rovnaké UTC 12:45:05–09, OMM objekt 37741, WGS84 RSU a výslovne označenú **mestskú proxy** Nemea, 10° experimentálnu masku, archívny SHA, geometriu, pozitívny paketový plán a overený raw trace. Schéma odmietne chýbajúcu/neznámu bránu, premenu proxy na „overenú anténu“, ISL v Globalstar bent-pipe ceste, označenie diagnostického IPv4/UDP za natívne RM200M IP, zmenené časy a zdroje. Rovnaký profil nevie implicitne schváliť Starlink ani Iridium.

`requested_claim=operator_service` je zatiaľ **vždy odmietnuté**. Neexistuje revidovaný register dôkazov o termináli, autorizovanej službe, skutočnej anténe a priradení lúča, trase a nezávislom meraní. [Produktový list RM200M](https://www.globalstar.com/getmedia/932da082-c545-4ed1-b7fc-67ff34967651/rm200m-sales-sheet.pdf) uvádza natívne MO správy 9–144 B a MT 9–128 B a vyžaduje certifikáciu riešenia; nepublikuje priehľadné IP/UDP rozhranie ani jeho presné RF rámce. Našich 96 B sa nominálne zmestí do veľkostného limitu MO, no bez aktuálneho API a certifikačnej skúšky nevieme potvrdiť nezmenený 96 B používateľský payload ani prípustnosť piatich správ po jednej sekunde. Packet probe preto nie je RM200M simulácia.

Pre povýšenie profilu treba: (1) presný model, firmware, anténu, montáž, aktiváciu a servisný plán terminálu; (2) overenú polohu/prevádzku vhodnej brány, beam a skutočne dostupný satelit alebo doloženú prevádzkovú trasu; (3) rozhranie a limity správy, rýchlosť, fronty, ACK/retry a prechod do servera; (4) RF/MAC parametre s nezávislou validáciou na **rovnakom** produkte, lokalite a časovom období, alebo poctivo označený meraním kalibrovaný servisný obal. Pre Starlink treba navyše rozhodnúť, či konkrétna trasa použila optické ISL; pre Iridium sú síce [crosslinky súčasťou architektúry](https://www.iridium.com/network), ale GP/OMM neurčuje ich aktuálnu trasu. Proprietárny RF, plánovač a obsah satelitných rámcov pre všetkých troch operátorov zostáva z týchto dát neprístupný. Preto zatiaľ nemožno vytvoriť fyzicky a bitovo presný model komerčnej služby ani poradie operátorov.
