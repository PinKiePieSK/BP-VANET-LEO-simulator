# F2 — časová fyzikálna dostupnosť LEO, 1. 11. 2026

## Výsledok

Časová fyzikálna vrstva teraz v každom behu s `dynamic_physical: true` prepočíta **celý vekovo kvalifikovaný pripnutý OMM katalóg**, nezávisle pre každé auto a RSU. Vzorkuje čas od logickej 0 po koniec simulácie po 0,5 s; interný 10 s nábeh sa nezobrazuje. Poloha terminálu pochádza zo surových WGS84 waypointov SUMO, dráha z hashovaného OMM/EOP. Pri každom uzle ukladá počet možných satelitov, vstupy/výstupy katalógových ID a ID s najvyššou eleváciou. Kandidátska vrstva preto nie je obmedzená na 2–3 satelity natívneho paketového podgrafu.

Výber natívnej trasy môže pripustiť aj satelit, ktorý fyzikálne vstúpi do obálky po logickom štarte. Samostatný audit prepočíta eleváciu **skutočne ponúknutých** RSU a priameho auto–satelit paketu pri jeho natívnom čase a z aktuálne pripojeného satelitu. Paket pod publikovanou terminálovou obálkou odmietne. Replay zobrazuje per-uzlový časový stav; úspešne sa otvoril v UI s osou 0–6 s a pri 0,5 s zobrazil zmenu počtu kandidátov.

## Integrovaný dôkaz

Všetky nové scenáre a surové výsledky sú v `~/Desktop/BP-Simulator-Workspace/runtime/`; dôkazy nie sú prepísaním starších behov.

| Scenár a konštelácia | Pozorovanie z raw stôp a opätovného `bp_u9 verify` |
| --- | --- |
| `f2-entering-starlink-20261101` | 5 áut, 3 RSU, 6 s. Verejné ID **68093** nebolo kandidátom primárnej RSU v čase 0, vstúpilo pri 0,5 s, natívny handover primárnej RSU na tento satelit nastal pri 1,2 s. Všetkých 8 terminálov má 13 časových vzoriek, ich vstupy sa líšia podľa polohy. 25 ponúknutých RSU a 13 priamych paketov prešlo nezávislou eleváciou; minimum 25,3429° pri požadovaných 25°. Natívny cross-RSU alert a priame CAM/ACK prešli. |
| `f2-dynamic-iridium-20261101` | 5 áut, 3 RSU, 6 s, 8 × 13 vzoriek, 25 RSU a 14 priamych paketov nad obálkou; minimum 8,3205° pri maske 0,5°. Natívny beh aj opätovná kontrola PASS. |
| `f2-dynamic-globalstar-20261101` | 5 áut, 3 RSU, 6 s, 8 × 13 vzoriek, 25 RSU a 13 priamych paketov nad obálkou; minimum 6,7042° pri maske 0,5°. Natívny beh aj opätovná kontrola PASS. |

Záporná kontrola zmenila priame spojenie auta na satelit pod obálkou; audit ju odmietol pri elevácii 15,636° pod 25° limitom Starlinku. `PYTHONPATH=tools .venv/bin/python -m unittest discover -s tools -p 'test_*.py'`: **130 testov OK**. Historické F1b a F1c behy zostali overiteľné cez zachované hashované zdroje. Pri Globalstare sa zároveň opravila chyba checkera: po handoveri auta kontroloval starú ISL cestu aj pre paket odoslaný cez nový serving satelit.

Aktualizovaný čistý prenosný priečinok `~/Desktop/BP-Simulator` má manifest overený na **11 403 súboroch a odkazoch**, bez testov a výsledkov. ZIP `~/Desktop/BP-Simulator.zip` prešiel kontrolou všetkých **12 245 položiek**; SHA-256 ZIP je `7c7cc5e83ed6fde86b386d08d4d7c7c12cd5c43c54fdb5ab6ff12ca8bb79d4f4`. Predošlý balík je uložený v `~/Desktop/BP-Simulator-Workspace/package-pre-f2-20261101`.

## Hranice tvrdenia

- Ide o **geometrickú a publikovanú terminálovú obálku**, nie o zapnutý lúč, registráciu terminálu, kapacitu, skutočný prah modemu ani komerčnú dostupnosť. Na ďalšie rozlíšenie slúžia F3–F5.
- Natívny SNS-3 paketový model stále inštanciuje vybraný malý podgraf a v tomto režime vykoná jeden naplánovaný handover primárneho a po jednom sekundárnych terminálov. **Nejde o opakované automatické prepojenie každého terminálu podľa najlepšieho kandidáta počas celého behu.** F2 dokončuje nezávislú fyzikálnu vrstvu a dokazuje pozitívny prípad neskôr vstupujúceho natívneho cieľa; nerozširuje paketový engine na celú konšteláciu.
- Globalstar natívny paketový hop v tomto teste je generický DVB/ISL experimentálny podgraf. Nie je to architektúra reálnej služby Globalstar bent-pipe. Z geometrického výsledku sa nesmie vyvodzovať operátorská cesta.
- 0,5 s mriežka je vzorkovaná dostupnosť; hranica vstupu medzi vzorkami má časovú neistotu najviac 0,5 s. Paketový audit používa presný natívny čas odoslania a pripnutú dráhu.
