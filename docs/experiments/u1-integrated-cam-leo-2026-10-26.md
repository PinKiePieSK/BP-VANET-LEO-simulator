# U1 — viacvysielačový CAM/DCC a natívny LEO roundtrip v jednom ns-3 behu

**Uzavreté:** 26. 10. 2026. **Runtime:** projektový ns-3.38/SNS-3 3.38; Vanetza a SUMO. **Tvrdenie:** výlučne generický výskumný DVB model, nie predikcia služby operátora.

## Reprodukovateľné dôkazy

- Konfigurácia: `config/u1-integrated-pilot.json`, `config/u1-ground-pilot.json` (tri syntetické LOS dopyty; 100 ms FCD, 30 vzoriek, seed 314159/run 1).
- Izolovaný V5 baseline: `results/u1_ground_baseline_20261026b/`, manifest SHA-256 `4395d309ad5ffa9148da71e98e0fc1044a2f07aae20cce500bb243b289357819`; `tools/check_v5_ground.py` **PASS**.
- Prijatý spoločný beh: `results/u1_integrated_20261026final/`, manifest SHA-256 `36361f2134c7350a395163ef4eec49b7942e3ccc369010a00546515f30ad62ee`; `tools/check_u1_integrated.py` **PASS**. Každý z deviatich prípadov má `waypoints.csv`, SUMO/FCD, `cam.csv`, `dcc_decisions.csv`, `phy_state.csv`, `rx.csv`, `identity.csv`, `trace.csv`, OCB/LAN PCAP, `PacketTrace.log` a `run.log`.
- Päť mutácií reálnych raw stôp (`ICB1` bajt, príjemca `I2V1`, CAM ID, merané CBR a bajt ISL IPv4/UDP) checker **odmietol** cez `tools/test_u1_integrated_mutation.py`.

```bash
.venv/bin/python tools/check_v5_ground.py results/u1_ground_baseline_20261026b
.venv/bin/python tools/check_u1_integrated.py results/u1_integrated_20261026final
.venv/bin/python tools/test_u1_integrated_mutation.py results/u1_integrated_20261026final

# Nový beh iba do nového adresára; runner odmieta prepis výsledku.
.venv/bin/python tools/run_u1_integrated.py \
  --baseline results/u1_ground_baseline_20261026b \
  --output results/u1_integrated_NEW_ID
```

## Výsledok prijímacej matice

| Dopyt, vetva | CAM TX | V2X/V2I RX | ICB1 z RSU | Brána prijala | I2V1 v aute | Rôzne autá s návratom |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 autá, positive | 35 | 105 | 35 | 35 | 35 | 3 |
| 3 autá, blocked / no_isl | 35 | 105 | 35 | 0 | 0 | 0 |
| 24 áut, DCC off, positive | 256 | 6 144 | 256 | 249 | 249 | 24 |
| 24 áut, DCC off, blocked / no_isl | 256 | 6 144 | 256 | 0 | 0 | 0 |
| 24 áut, DCC on, positive | 144 | 3 456 | 144 | 137 | 137 | 24 |
| 24 áut, DCC on, blocked / no_isl | 170 | 4 080 | 170 | 0 | 0 | 0 |

Pri zablokovanom satelite a chýbajúcej ISL sa **presné CAM bajty, ich vysielacie časy a všetky lokálne počty** rovnajú izolovanému V5: 35, 256 a 170 CAM. Pozitívna vetva bez DCC má rovnaké lokálne počty. Pozitívna vetva s DCC má skutočnú rádiovú spätnú väzbu: I2V1 obsadí OCB kanál, priemerné namerané CBR stúpne z 0,01915 na 0,02726 a dynamická CAM ponuka klesne zo 170 na 144. To je účinok spoločného času a rádia, nie dodatočná korekcia V5 výsledku. `249/256` a `137/144` sú prijatia v **generickej modelovej** bráne pri tejto záťaži; sedem strát v každej hustej kladnej vetve nemá operátorskú interpretáciu.

Checker prepočíta stabilné 64-bitové ID z U0, rodičovský vzťah CAM→report→odpoveď, presné 41/43 B CAM, 96/98 B ICB1 vrátane SHA-256, GRA1, I2V1 a správne auto. V5 kontrola nezávisle overí FCD, DCC/CBR z PHY stavov a každý OCB PCAP. U1 kontrola navyše páruje LAN PCAP a oba smery ISL IPv4/UDP s obsahom konkrétnych reportov a odmieta čas idúci dozadu. Negatívne vetvy vytvoria reporty v RSU bez doručenia bráne a bez odpovede; lokálne CAM pritom pokračujú.

Prvý pokus s 20–23 s oknom zlyhal, pretože vozidlá medzitým odchádzali zo SUMO mapy; jeho neúplný adresár nie je dôkaz. Prechodný spoločný beh `results/u1_integrated_20261026a` slúžil na ladenie checkera; prijatým behom je výlučne `...final` s aktuálnym hashom checkera v manifeste. Žiadny starší výsledok sa neprepisoval.

**Zostávajúce hranice U1:** iba jeden aktívny RSU/pevný UT, pripnutá dvojica LEO a epoch, syntetická premávka, nekalibrovaný LOS rádiový kanál a výskumná podmnožina DCC. Výber/deduplikácia RSU a fronty patria do U2; dynamické pripojenie a handover do U3; fyzika a kapacity do U4. [Presný kontrakt enginu](../decisions/u1-integrated-engine-contract.md) uvádza, čo vykonávajú jednotlivé moduly a ktoré tvrdenia sú mimo rozsahu.
