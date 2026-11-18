# V3: časový LEO kontrakt a hranica natívneho modelu

**26. 10. 2026.** Vstup `config/v3_leo_*.json` má schému
`v3-leo-topology-1`. Je to verzovaný topologický doplnok k scenárovej
generácii V3; nemení manifesty dokončených V1/V2 behov. `tools/v3_leo_topology.py`
vracia `v3-leo-topology-result-1` a jeho `packet_status` je jeden z
`supported_reference`, `geometry_only`, `unsupported`. Kladný geometrický
výsledok sám osebe neznamená existujúcu službu operátora.

## Vstup a rozhodovanie

- Snapshot GP/OMM je projektová cesta s pripnutým SHA-256 manifestu; overujú
  sa aj gzip a raw bajty každej použitej skupiny. Duplicity NORAD ID, chýbajúce
  vybrané ID, budúca epocha prvkov voči začiatku behu, prekročenie
  `max_age_h`, chyba SGP4 a chýbajúce EOP odmietnu kvalifikáciu.
- `utc_origin`, `duration_s`, `sample_s`, WGS84 polohy UT a proxy GW,
  `mask_deg`, dvojica `pair` alebo `auto`, diagnostický `beam` a modelová
  `isl` sú samostatné parametre s jednotkami v názve. V každej vzorke sa
  počíta TEME→ITRS, elevácia oboch koncov a výška najbližšieho bodu
  priamky ISL nad zemskou guľou. Výstup uchováva ID viditeľné z UT aj GW,
  zvolenú dvojicu, elevácie, clearance a dôvod kvalifikácie.
- `auto` hľadá SAT0 viditeľný z UT aj proxy GW a SAT1 viditeľný z UT,
  bez priamej GW; obe družice musia mať viditeľnosť a nezakrytú ISL po
  **celé** aplikačné okno 20–22,5 s. Voľba maximalizuje minimálnu eleváciu,
  pri zhode rozhodujú katalógové čísla. Iná geografia alebo UTC preto
  môže zvoliť inú dvojicu alebo vrátiť `unsupported`.
- Vybrané elevácie pri okrajoch okna sa nezávisle prepočítajú Skyfield;
  rozdiel nad 0,05° je chyba. EOP tabuľka je hashovaná. Kód 2 v
  `verification.json` znamená predikované UT1/polárny pohyb, teda
  výpočtovú, nie terénnu validáciu polohy.

## Päť oddelených udalostí

`check_v3_leo_native.py` ukladá do `verification.json/events` samostatné
záznamy `geometry_candidate`, `beam_selected`, `ut_attach`,
`gateway_route` a `application_delivery`. Prvý pochádza iba z OMM/EOP
preflightu, druhý z natívnej beam/scheduler kvalifikácie, tretí z toho
istého UT MAC/IP a výsledku obojsmernej sondy, štvrtý z GW/ISL stavu a
paketovej trasy, piaty z presného ICB1 prijatia v GW. Cieľ SAT1 a pôvodná
SAT0 trasa majú odlišný `scope`; nevyžiadaný cieľ má hodnotu
`not_requested`, nie falošný výpadok. Dôvody zahŕňajú
`no_candidate`, `no_beam`, `no_attach`, `no_route`, `phy_drop` a
`pending_no_queue`.

## Natívna podporovaná podmnožina

`tools/run_v3_leo_native.py` preberá analyzovanú konfiguráciu a vytvorí
SNS-3 3.38 topológiu so zvolenými **dvoma** 5-cifernými objektmi,
konfigurovaným lúčom/GW, jedným SatNetDevice UT a modelovou ISL.
Konverzia OMM→TLE sa pri oboch objektoch porovnáva v štyroch časoch;
maximálna chyba musí byť pod 2 m. Šesťciferné objekty sa do tohto TLE
adaptéra nikdy nekonvertujú. Jedno rádio pri handoveri prenesie scheduler,
PHY/MAC kanály, UT mapu, IP/ARP a timing advance; potvrdenie vyžaduje
sondu UT→SAT1→ISL→SAT0→GW a odpoveď späť.

Súčasný natívny adaptér podporuje generický DVB model s archivovanou
skupinou Iridium NEXT, 25 s oknom a najviac 0,5 s geometrickým krokom,
šiestimi CAM z overenej P3 cestnej fixture, modelovou ISL 1 Gbit/s,
diagnostickým všesmerovým beamom a sekundovým UTC začiatkom. UT polohu
možno premiestniť; cestné body sa vtedy **synteticky preložia** z
Bratislavy, takže nejde o OSM premávku iného mesta. Táto hranica je
kontrolovaná stavom `unsupported`; nie je to operátorský outage.
Čas handover žiadosti→retune 300 ms, timeout 750 ms, zisk 17 dBi v
uvedených prípadoch, proxy GW a ISL nie sú kalibrovanými údajmi služby.
Iný ISL bitrate je odmietnutý, kým ho fáza V4 nenapojí na skutočný SNS-3
atribút.

Kontroly `no_target_channel` a `no_target_route` sú injekcie zamietnutia
cieľovej kvalifikácie. `no_target_gateway_or_isl` odstraňuje modelovú ISL
fyzicky. `attach_failed` zadrží odpoveď sondy a testuje návrat na SAT0.
`phy_drop` používa natívny `PHY RTN DRP`. Checker odlíši ich príčiny,
nezamieňa neúspech cieľa s výpadkom stále funkčnej SAT0 trasy.

Starlink/Globalstar tu poskytujú len kandidátnu archivovanú geometriu.
Prítomnosť reálneho beamu, podporovaný terminál, skutočná poloha GW,
ISL politika ani komerčná PDR/latencia z tohto kontraktu nevyplývajú.
