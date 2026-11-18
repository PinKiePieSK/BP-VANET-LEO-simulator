# Geometrický kandidátsky timeline v návrhovom editore

**22. 10. 2026 UTC.** Tento panel sprístupňuje už vypočítaný [60-sekundový audit RSU](editable-globalstar-candidate-timeline.md) v návrhovom editore. Je to samostatný, iba čítací výstup; načítanie nespúšťa ns-3, nemení návrh, paketový E2E beh ani jeho výsledky. Zobrazuje vzorky pre presný referenčný scenár `data/inputs/editable-road-v2/packet-subset.json`, nie pre aktuálne rozkreslený alebo posunutý návrh.

## Kontrakt a overenie

`GET /api/editor/globalstar-candidate-timeline` vracia iba kurátorované geometrické polia: `scope=archived_globalstar_two_endpoint_geometry_candidates_only`, 121 vzoriek po 0,5 s, UTC, katalógové ID, počet spoločných kandidátov, eleváciu pri RSU a pri proxy brány v stupňoch a súčet dvoch vákuových `r/c` časov v ms. Prechod je interval medzi dvoma vzorkami, nie udalosť v satelitnom termináli. Endpoint nemá parameter scenára ani ID paketového behu a nič neukladá.

Pred odpoveďou [`read_editable_globalstar_timeline.py`](../../tools/read_editable_globalstar_timeline.py) kontroluje nezávislý pripnutý SHA-256 celého `.metadata.json` (`68bcba1c…`), hash CSV zaznamenaný v metadátach (`9806aa75…`), hash referenčného JSON, manifestu archívu, komprimovaného aj rozbaleného Globalstar OMM, hash generátora, časové zarovnanie, 121 riadkov, výberové ID, oba uhly nad pokusnou maskou 10° a `r/c` zo vzdialeností. Zmenený scenár alebo archív spôsobí HTTP 409. Endpoint nevracia neupravené metadáta, aby sa jeho odpoveď nedala zameniť za výsledok operátorskej služby. Odpoveď nesie hashe pôvodu a informáciu, že archív bol získaný až po začiatku modelovaného intervalu.

Panel v [`draft-editor.html`](../../viewer/draft-editor.html) ukazuje obidve elevácie v dvoch krivkách časového priebehu, ovládač 0–60 s s krokom 0,5 s a čísla pre vybranú vzorku. Pruh medzi 21,5–22,0 s označuje zmenu geometrického poradia 37741 → 37190. V oboch okolitých vzorkách existujú dva spoločné kandidáty. Text vysvetľuje, že zmena poradia nedokazuje prepnutie ani dostupnosť spojenia. Nemea je centrum mesta, nie overená poloha gateway antény; OMM objekty nie sú overený zoznam aktívnych satelitov. Výstup neobsahuje beam, RF rozpočet, PHY/MAC, terminálovú registráciu, straty ani latenciu služby.

## Reprodukcia a cielené kontroly

```bash
cd '/home/ubuntu/Documents/ChatGPT/Bakalarska praca'
python3 -m unittest discover -s tools -p 'test_editor_globalstar_timeline_api.py' -v
python3 tools/scenario_server.py --port 8765
# editor: http://127.0.0.1:8765/draft-editor.html
```

Tri testy pokrývajú HTTP 200 pre referenčný súbor a HTTP 409 pre poškodenú kópiu CSV, poškodenú kópiu metadát, zmenený scenár a zmenený orbitálny archív. HTTP smoke test na izolovanom porte 8782 vrátil 200 pre HTML/JS/CSS a pre endpoint 121 vzoriek; syntax `draft-editor.js` prešla kontrolou Node.js. CUA prehliadač v podúlohe nebol dostupný, preto vizuálnu interakciu panelu ešte treba overiť v hlavnom vlákne. Tento limit nezmení overený backendový kontrakt.
