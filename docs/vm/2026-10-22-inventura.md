# Inventúra a zmeny VM (2026-10-22 UTC)

## Východiskový stav

- Ubuntu 24.04.4 LTS, jadro `6.17.0-20-generic`; 4 vCPU; RAM 7.8 GiB; swap 0.
- `/dev/sda`: 100 GiB (107374182400 B), GPT, model VBOX HARDDISK, ID `FFF13496-A1D2-40CD-81F2-C1ADDEEE16B6`. BIOS boot `/dev/sda1` (1 MiB) a systémový `/dev/sda2` (ext4, UUID `3e2da5cd-cacd-43fe-9ee9-509dbf42c310`, pôvodne 25 GiB). `df -h /`: 25G celkom, 23G použité, 801M voľné, 97 %.
- `/dev/sdb`: 111.02 GiB (119207231488 B), bez rozpoznanej tabuľky oddielov a bez signatúr `wipefs -n`; `file -s` hlási `data`. Disk nebol zmenený. Nulové signatúry samy osebe nedokazujú, že na ňom nie sú dáta.
- `dpkg --audit` nevypísal poškodené ani nedokončené balíky. Pred obnovením indexov APT bolo zobrazených 331 aktualizovateľných balíkov; po `apt-get update` simulácia `apt-get -s upgrade` ukázala 349 aktualizácií a 5 podržaných balíkov.
- Pri prvom meraní load average 4.44/2.51/1.48. `vmstat` ukázal krátkodobé I/O čakanie 1–2 %. Kernel log neukázal chyby ext4 ani I/O.
- Guest Additions 7.1.2r164945; hostiteľ podľa guest property 7.1.2. Moduly `vboxguest`, `vboxsf`, `vboxvideo` sú načítané, `vboxadd-service` beží. `vboxadd.service` zlyhal pri kompilácii modulu pre jadro 6.17: chýbajú hlavičky `internal/iprt.h`, `the-linux-kernel.h`, `iprt/string.h`. `VBoxControl guestproperty enumerate` funguje ako root; bežný používateľ nemá prístup k `/dev/vboxguest`. Ide o čiastočnú funkčnosť.
- Používateľ uviedol, že pôvodný systémový VDI je na hostiteľskom C: ako návratová kópia. Prítomnosť a konzistenciu tejto hostiteľskej kópie nemožno z hosťovskej VM nezávisle overiť.

## Vykonané zmeny

| Zmena | Dôvod | Overenie |
| --- | --- | --- |
| `growpart /dev/sda 2` a `resize2fs /dev/sda2` | Oddiel bol 25 GiB na 100 GiB systémovom disku a `/` bol zaplnený na 97 %. | `df -h /` ukázal 99G celkom, 23G použité, 72G voľné, 24 %. Porovnanie `sda-before.sfdisk` a `sda-after.sfdisk`: zachovaný začiatok oddielu, jeho UUID a typ. |
| `/swapfile` 4 GiB, režim 0600, záznam vo `/etc/fstab` | Pri 8 GiB RAM nebol žiadny swap; `systemd-oomd` hlásil zhoršené vyhodnocovanie tlaku na pamäť. | `swapon --show` a `free -h`: 4 GiB aktívneho swapu. Pôvodný `/etc/fstab` uložený ako `/etc/fstab.bak-2026-10-22`. |
| `apt-get update` a `apt-get upgrade` | 349 čakajúcich aktualizácií Ubuntu. | `apt-get upgrade` skončil s exit 0; záznam `apt-upgrade-2026-10-22.log.gz`; `dpkg --audit` je prázdny. |
| Inštalácia `libns3-dev` a `ns3` vo verzii `3.41-1.1build1` | Chýbajúci overiteľný sieťový simulátor pre nový projekt. | Balíky nainštalované (exit 0), verzia potvrdená `dpkg-query`; pilotný C++ ns-3 program sa skompiloval a prešiel kontrolou. Záznam `apt-ns3-2026-10-22.log.gz`. |

Východiskový konzervatívny limit bol 2 build úlohy. Pri konkrétnom debug builde SNS-3/ns-3.48 bolo postupne otestovaných 2, 3 a 4 úlohy: pri 4 mal `free -h` stále približne 3,2–3,7 GiB dostupnej pamäte, `vmstat` len jednotky KiB/s swap-in a žiadny trvalý I/O wait; disk mal vyše 60 GiB voľných. Preto sa tento build vykonáva s `ninja -j 4`. Pri inom profile alebo súbežnej veľkej úlohe sa limit musí znovu zmerať, prípadne znížiť na 2. Počas aktualizácie sa swap využil približne do 440 MiB a pri tvorbe `initramfs` vzrástol tlak na diskové I/O. Po skončení práce meranie `iostat` ukázalo pri nečinnosti systémového disku približne 0 % využitia a `vmstat` 0 % I/O čakania. Nezistili sa chyby ext4/I/O v kernel logu. Nie je dôvod meniť schedulery či nastavenia cache.

Stav po zásahoch: `df -h /` = 99G celkom, 29G použité, 66G voľné (31 %); RAM 7.8 GiB, aktívny swap 4 GiB. `findmnt --verify` má 0 chýb a očakávané upozornenie, že zdroj swap mountu je súbor. `/var/run/reboot-required` požaduje reštart kvôli balíkom `apparmor` a `gnome-shell`.

Neskoršia pracovná zmena: staré bakalárske adresáre a súbory sa po overení obnoviteľného 210 MiB lokálneho archívu odstránili; presný zoznam, dôvod a kontrola sú v [docs/legacy.md](../legacy.md) a vykonávacom skripte `scripts/cleanup_legacy.py`. Nový izolovaný SNS-3 checkout s dátovým submodulom a buildom dočasne zaberá približne 6–7 GiB. Počas buildu bolo `df -h /` približne 99G celkom, 34G použité, 61G voľné. Nie je to zmena oddielu ani druhého disku.

## Otvorené body

- Päť balíkov zostalo po bezpečnom `apt-get upgrade` podržaných: `fwupd`, `linux-firmware` a tri HWE metabalíky, ktoré by zmenili jadro z 6.17 na 7.0. Simulácia samostatnej aktualizácie `fwupd`/`linux-firmware` pridáva 19 balíkov firmvéru bez zistenej potreby vo VM; zatiaľ bez zásahu. Kernel upgrade odložiť, kým sa zosúladia Guest Additions.
- Guest Additions: zlyhávajúca kompilácia 7.1.2 pre jadro 6.17. [Oracle uvádza podporu jadra 6.17 až v rade 7.1.14](https://download.virtualbox.org/virtualbox/7.1.14/UserManual.pdf) a [odporúča zhodnú verziu hostiteľského VirtualBoxu a Guest Additions](https://docs.oracle.com/en/virtualization/virtualbox/7.1/user/EN-VBOX-7-1-USER.pdf). Preto nebola naslepo nainštalovaná novšia guest verzia proti hostiteľovi 7.1.2. Konkrétny postup: na hostiteľovi preveriť obnoviteľnú kópiu/snapshot, aktualizovať VirtualBox na kompatibilné vydanie 7.1 s podporou jadra 6.17, vložiť zodpovedajúce Guest Additions ISO, nainštalovať v hosťovi, reštartovať a overiť `systemctl --failed`, `VBoxControl --version`, dynamické rozlíšenie a prípadné zdieľané priečinky.
- Systémový reštart po aktualizácii je potrebný, ale v tejto relácii by odpojil aplikáciu, v ktorej práca beží. Po reštarte overiť `df -h /`, `swapon --show`, `dpkg --audit`, `systemctl --failed` a opakovať pilot.
- Pri `/dev/sdb` nebol vykonaný žiadny zápis. Pred rozhodnutím o použití treba potvrdiť pôvod alebo urobiť bitovú zálohu, ak by na ňom mohli byť dáta bez signatúry.

## Kontrola po kompiláciách a nových experimentoch

Opakované meranie 22. 10. 2026: `/` má 99G, z toho 37G použitých a 58G voľných. Z 7,8 GiB RAM bolo 3,0 GiB dostupných; 4 GiB swap sú aktívne a 1,8 GiB obsahovalo staršie odložené stránky. Štyri jednosekundové následné vzorky `vmstat 1 5` ukázali swap-out 0 KiB/s, swap-in len jednorazovo 12 KiB/s a I/O wait 0–1 %. Táto obsadenosť sama osebe nepreukazuje aktívny tlak; nastavenie swapu ani I/O scheduler sa nemenili. `dpkg --audit` zostal prázdny, `.venv/bin/pip check` nenašiel chyby. `vboxadd.service` je naďalej jediná zlyhaná služba, s už vyššie zdokumentovanou nekompatibilitou Guest Additions/jadra. Kompilácia integračných sond používa jednu úlohu.
