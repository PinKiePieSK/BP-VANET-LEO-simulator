# Natívne satelitné kroky v prehrávači — 4. 11. 2026

Beh `results/simulations/satellite-trace-20261104` používa uložený scenár
`realna-d1-satelit` (60 s, 6 áut, 2 RSU, Iridium NEXT ako orbitálny vstup,
jeden aktívny satelit). `bp_u9.py run` a samostatný `bp_u9.py verify` vrátili PASS.
Výsledok je generický paketový DVB model SNS-3, nie model modemu Iridium.

`satellite-ip-trace.csv` zaznamenáva pri odoslaní na `SatNetDevice` ns-3 packet
UID, DENM ID, smer a kompletný IP/UDP datagram. Uplink DENM
`d319516eb46351c4` mal UID 977; downlink z brány UID 1029. Rovnaké UID sú v
natívnom `PacketTrace.log` na UT, satelite a bráne. Verifier porovnáva UDP
payload s aplikačnou DENM stopou a vyžaduje natívny prijímací krok, ak
aplikácia zaznamenala príjem. Riadiace rámce SNS-3 bez takejto väzby sa k
DENM nepriraďujú.

Prehrávač pridáva `SNS3_{ND,LLC,MAC,PHY}_{SND,RCV,DRP,ENQ}_{RTN,FWD}` do
rovnakého časovaného zoznamu a detailu DENM. Pri vstupe do SNS-3 možno
rozkliknúť skutočné IPv4, UDP a dekódovaný ETSI DENM. Ostatné vrstvové
riadky poskytujú metadata SNS-3, nie surové bajty celého DVB rámca. Údaj
`82 B IP` je dĺžka priradeného IP datagramu, nie dĺžka rádiového rámca.

Overenie API: 16 968 časovaných udalostí, 28 natívnych krokov tohto DENM,
v detaile celkom 52 krokov. V prehliadači pri 5,16 s vidno satelitný PHY
príjem aj následný príjem v UT; rozkliknutý `SNS3_ND_SND_FWD` ukázal
IPv4 (0–19), UDP (20–27) a Vanetzou dekódovaný DENM (28–81).

Staršie zapečatené behy bez `satellite-ip-trace.csv` sa nedajú spätne
jednoznačne prepojiť s natívnym UID, preto ostávajú v pôvodnom rozsahu.
