# U9 — jeden pás trasy a presný kliknutý cieľ, 31. 10. 2026

Pri plánovaní trasy na reálnej mape sa predtým kreslil samostatný zvýraznený objekt pre každý cestný úsek. Cieľ bol celý vybraný úsek, takže vozidlo mohlo prejsť za kliknutý bod.

`viewer/u9-route-planner.js` teraz zostaví jednu súvislú geometriu z orientovaných úsekov, oreže jej začiatok na polohu auta a koniec na kliknutý bod. Tú istú geometriu používajú SVG pracovnej mapy aj MapLibre na glóbuse. `viewer/u9-simulator.js` kreslí len dva polylines (obrys a farebný pás) bez ohľadu na počet úsekov; `viewer/u9-earth-map.js` posiela jednu GeoJSON LineString s oblými spojmi.

Plánovač ukladá voliteľné `arrival_pos_m` na poslednom orientovanom úseku. SUMO ho dostáva ako `arrivalPos`, ktoré podľa [oficiálnej dokumentácie SUMO](https://sumo.dlr.de/docs/Definition_of_Vehicles%2C_Vehicle_Types%2C_and_Routes.html#arrivalpos) určuje miesto opustenia siete. Náhodná trasa toto pole odstráni a správa sa ako predtým. Validátor odmieta cieľ za dĺžkou poslednej cesty a cieľ pred štartom na tom istom úseku. Reálny mapový objekt si cieľ zachová pri synchronizácii aktívneho výrezu.

Skúška v editore: Bratislavská reálna predloha, auto `car0`, cieľ kliknutý na inú cestu. Výsledok 11 navzájom spojených úsekov, približne 568 m, na SVG len 2 polyline vrstvy, preflight 4 autá / 0 RSU / 0 satelitov. Negatívny validator odmietol cieľ pred autom na tom istom úseku. Izolovaný SUMO beh s tromi úsekmi pre `car0` a `arrival_pos_m=41,5` m na poslednom úseku prešiel; `vehicles.rou.xml` obsahuje `arrivalPos="41.5"`, 4/4 autá boli vložené, 0 kolízií a teleportov. Posledný FCD bod `car0` bol 2,16 m od geometrického cieľa na predchádzajúcom 0,5 s kroku; auto potom dosiahlo cieľ a odišlo zo siete. Vstup aj raw výsledok sú mimo prenosného balíka v `/home/samuel-petrik/Desktop/BP-Simulator-Workspace/route-band-test-20261031`.

Po nasadení na porte 8765 bol rovnaký klikací postup zopakovaný: 11 úsekov, dva SVG polylines a úspešný preflight. Snímka `route-band.png` je v uvedenom testovacom adresári.

Naďalej platí, že cestná sieť je zložená z jednotlivých OSM úsekov a nie je kalibrovaná na všetky dopravné pravidlá. Zmena sa týka trasy auta a polohy jej konca; nepretvára celú sieť na jeden fyzický cestný objekt.
