# Oficiálne zadanie bakalárskej práce a usmernenie vedúceho

Text zadania a odporúčaní poskytol autor práce 22. 10. 2026. Tento súbor uchováva pôvodné znenie ako referenciu pre rozsah práce; technická interpretácia je v [analýze komunikácie](hlbkova-analyza-komunikacie.md).

## Zadanie

> Riadenie inteligentnej a bezpečnej dopravy je v poslednom období predmetom mnohých výskumov. Komunikácia medzi vozidlami v cestnej premávke navzájom a medzi vozidlami a infraštruktúrou až Internetom prináša mnohé nové funkcionality na zefektívnenie cestnej premávky a taktiež zvyšuje spoľahlivosť a bezpečnosť dopravy. Vzhľadom na mobilitu vozidiel je potrebná bezdrôtová komunikácia. V súčasnosti zažíva druhý veľký rozmach aj budovanie nových satelitných systémov na nízkych obežných dráhach, ktoré poskytujú oneskorenie prenosu porovnateľné s pozemnými sieťami. Popri existujúcich satelitných systémoch (Iridium, Globalstar) sú budované ďalšie komplexnejšie systémy (napr. Starlink). Preto motiváciou tohto zadania je vyhodnotiť správanie sa sietí VANET, ak komunikácia bude prebiehať prostredníctvom takýchto satelitných sietí.
>
> Analyzujte základné princípy činnosti sietí VANET a inteligentnej dopravy ako aj spôsoby komunikácie v nich. Rovnako sa sústreďte na koncepciu satelitných sietí využívajúcich konšteláciu satelitov na nízkych obežných dráhach. Charakterizujte stručne aj relevantné nástroje, ktoré umožňujú skúmať správanie sa rôznych dopravných scenárov. Navrhnite infraštruktúru pre siete VANET s integrovanou komunikáciou cez satelitné siete. Navrhnite sadu scenárov pre otestovanie výkonnosti danej infraštruktúry. Navrhnutú infraštruktúru a scenáre implementujte vo vybranom simulačnom nástroji. Vykonajte experimenty prostredníctvom navrhnutých scenárov a zhodnoťte výsledky.

## Odporúčanie vedúceho

Vedúci odporučil porovnať štyri možnosti rozšírenia ns-3 o LEO: [ns-3-leo](https://gitlab.ibr.cs.tu-bs.de/tschuber/ns-3-leo), [SNS-3](https://github.com/sns3/sns3-satellite), [Hypatia](https://github.com/snkas/hypatia) a [Anysam Starlink ns-3](https://github.com/anysam/starlink_ns3). Pri každej možnosti sa má posúdiť podpora GEO/LEO/MEO, potrebná verzia ns-3, dostupné príklady a dokumentácia. Výstupom má byť rozhodnutie, ktorú verziu použiť. Odporúčanie nie je záväzné pre všetky ďalšie technické voľby; konkrétne porovnanie je v [dokumente výberu modelu](vyber-satelitneho-modelu.md).
