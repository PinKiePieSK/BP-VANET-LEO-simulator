# Rozsah vstavaného handoveru SNS-3 3.38 v dvojdružicovom pilote

**Audit zdrojového kódu 22. 10. 2026.** Kontrolovaný checkout je `/tmp/ns3-sns3-338-feasibility`, ns-3 commit `392e36833ce3c7e0ecde4188043f76345402d5a7`, SNS-3 commit `739a10dbe1db02fd2c4064501e4a48994e0b79f3`. Tento dokument opisuje **túto pripnutú verziu**, nie každé vydanie SNS-3.

## Zistenie

V pripnutom SNS-3 súbore `contrib/satellite/model/satellite-ut-handover-module.cc` funkcia `CheckForHandoverRecommendation(satId, beamId)` pri neplatnej súčasnej polohe volá `GetBestBeamId(satId, coords, false)`: pri hľadaní ponechá **rovnaké `satId`** a mení iba `beamId`. `SatNcc::MoveUtBetweenBeams` v `satellite-ncc.cc` používa ten istý `satId` pre zdrojový aj cieľový scheduler. `SatUtPhy::PerformHandover` v `satellite-ut-phy.cc` prijíma iba nový `beamId`. Ide teda o mechanizmus **beam handoveru na jednej družici**, nie o automatické prepnutie UT z katalogizovaného objektu 43253 na 43258.

V [integrovanom dvojdružicovom pokuse](../experiments/two-leo-isl-icb1-e2e.md) bola UT user cesta vytvorená na SAT0/43253 a zostala tam počas všetkých šiestich reportov. Pri posledných dvoch mala geometricky vyššiu eleváciu SAT1/43258, ale samotné poradie elevácie službu neprepína. Preto log úspešných paketov v tomto pilote **nie je testom inter-satellite handoveru**.

## Dôsledok pre implementáciu

Inter-satellite handover potrebuje vlastný, explicitne definovaný kontrolér priradenia s udalosťami `candidate_observed`, `attach_requested`, `attach_confirmed`/`attach_failed`, zmenou fyzického kanála a beam/satellite identity, aktualizáciou smerovania a politikou paketu vo fronte a v lete. Samotné SGP4 poradie elevácií nemôže vyvolať `attach_confirmed`. Pred výsledkom pre operátora sa musia získať dôkazy o jeho termináli, servise, prahoch a skutočnej politike výberu; inak bude kontrolér označený ako **výskumná politika** s citlivostnými variantmi. Súčasný 1 s [geometrický gate](../experiments/iridium-one-second-candidate-guard.md) už blokuje neznámy interval a kontroluje identitu paketu, ale pracuje v abstraktnom IP proxy, nie v SNS-3 rádiovej ceste.

**Cielený prijímací test budúcej implementácie:** pri rovnakom CAM/ICB1 v troch kontrolách potvrdiť (a) statická SAT0 cesta pokračuje, kým má fyzikálne použiteľný link, (b) výskumná politika prepne až po explicitnom `attach_confirmed` a naopak počas nastaveného výpadku/dĺžky frontu nedoručí falošné pakety, (c) nová SAT1 trasa má vlastné UT PHY, prípadnú ISL/GW cestu a per-packet identitu; kontrolný variant bez druhej linky ju nedoručí. Čas výpadku ani parametre politiky sa nesmú vydávať za meranie Iridia.
