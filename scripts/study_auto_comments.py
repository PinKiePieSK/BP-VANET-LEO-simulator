"""Vkladá slovensky písané navigačné komentáre priamo medzi riadky študijného kódu.

Ručne napísané vysvetlenia v komentare.json majú prednosť. Tento modul dopĺňa
len vybrané funkcie, ktorých účel možno rozumne určiť z ich názvu.
Opisuje len veci, ktoré možno z daného kódu bezpečne vyčítať. Nepredstiera, že
statická analýza dokáže sama potvrdiť výsledok simulácie.
"""
from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path


VERBS = {
    "validate": "kontroluje platnosť vstupu a pri chybe zastaví ďalší postup",
    "verify": "nezávisle overuje uložený výsledok alebo vstup",
    "check": "vykonáva kontrolu podmienok",
    "preflight": "kontroluje scenár ešte pred spustením drahého behu",
    "run": "riadi vykonanie jedného kroku alebo celého behu",
    "load": "načíta dáta zo súboru alebo pamäte",
    "read": "číta vstupné dáta",
    "save": "ukladá pripravené dáta",
    "write": "zapisuje dáta do súboru",
    "fetch": "získava dáta z externého zdroja",
    "prepare": "pripravuje vstup pre ďalšiu vrstvu",
    "generate": "vytvára nové odvodené dáta",
    "make": "skladá nový objekt alebo správu zo vstupov",
    "build": "zostavuje výslednú štruktúru z častí",
    "compile": "zostavuje spustiteľný natívny program",
    "decode": "prekladá raw bajty na významové polia",
    "encode": "prekladá významové polia na bajty",
    "parse": "rozoberá textový alebo štruktúrovaný vstup",
    "render": "kreslí stav na obrazovku bez zmeny fyziky behu",
    "draw": "vykresľuje prvok rozhrania",
    "update": "aktualizuje existujúci stav",
    "sync": "zosúlaďuje dva pohľady na ten istý stav",
    "select": "vyberá použiteľnú možnosť podľa zadaných pravidiel",
    "sample": "vyberá alebo počíta časové vzorky",
    "analyze": "vyhodnocuje dôkazy alebo odvodené údaje",
    "audit": "kontroluje jednotlivé dôkazy a ich súlad",
    "export": "pripravuje výstup na ďalšiu kontrolu alebo čítanie",
    "traffic": "spracúva údaje o pohybe vozidiel",
    "orbit": "spracúva polohy alebo vstupy satelitov",
    "geometry": "pracuje s polohou, vzdialenosťou alebo uhlom",
    "position": "pracuje s polohou uzla",
    "route": "pracuje s trasou vozidla alebo sieťovou cestou",
    "packet": "pracuje s paketom a jeho bajtmi alebo stopami",
    "denm": "pracuje s výstrahou DENM",
    "cam": "pracuje so správou CAM",
}

JS_HINTS = {
    "svg": "vytvorí SVG prvok pre kreslenie mapy",
    "fmt": "naformátuje číslo pre čitateľný slovenský výpis",
    "error": "zobrazí chybu používateľovi",
    "status": "zobrazí priebežný stav používateľovi",
    "api": "odošle HTTP požiadavku serveru a prečíta JSON odpoveď",
    "post": "odošle JSON cez HTTP POST serveru",
    "svgPoint": "prevedie polohu myši z obrazovky do súradníc SVG mapy",
    "worldPoint": "prevedie kliknutie na metrovú polohu pracovného sveta",
    "unitsPerPixel": "zistí, koľko metrov mapy pripadá na jeden pixel obrazovky",
    "sy": "obráti os Y medzi metrovým svetom a kreslením SVG",
    "viewRatio": "vypočíta pomer šírky a výšky viditeľnej mapy",
    "fullView": "vypočíta výrez, do ktorého sa zmestí celá pracovná plocha",
    "clampView": "obmedzí výrez mapy na povolené hranice a mierku",
    "setView": "nastaví SVG viewBox, mierku a mapový podklad podľa aktuálneho výrezu",
    "zoom": "zmení mierku mapy okolo kurzora alebo stredu",
    "fit": "zarámuje objekty na mape",
    "renderGrid": "nakreslí pomocnú metrovú mriežku",
    "nearestRoad": "nájde najbližší cestný úsek k bodu",
    "entityAt": "určí auto, RSU alebo cestu pod kurzorom",
    "replayCar": "interpoluje polohu auta medzi uloženými časovými vzorkami replay",
    "linkVisualKind": "priradí spojeniu typ farby podľa dvojice uzlov a vrstvy",
    "linkKey": "vytvorí jednoznačný kľúč spojenia medzi dvoma uzlami",
    "activePacketLinks": "vyberie paketové spojenia v okolí aktuálneho času replay",
    "groundPosition": "vráti aktuálnu polohu auta alebo pevnú polohu RSU",
    "graph": "zostaví graf ciest pre hľadanie trás",
    "tree": "vypočíta najkratšie cesty v cestnom grafe",
    "pathTo": "zrekonštruuje trasu z predchodcov grafu",
    "legal": "skontroluje povolené nadväzovanie cestných úsekov",
    "travelSpeed": "odhadne rýchlosť auta podľa cesty a nastaveného limitu",
    "estimatedSeconds": "odhadne trvanie naplánovanej jazdy",
    "durationNotice": "upozorní, ak auto nemusí stihnúť cieľ počas pokusu",
    "cam": "rozpozná CAM a zostaví jeho čitateľné polia z raw bajtov",
    "denm": "rozpozná DENM a zostaví jeho čitateľné polia z raw bajtov",
    "groups": "rozdelí paket na protokolové vrstvy pre inspektor",
    "hexdump": "zobrazí raw bajty v riadkoch s offsetom a ASCII",
    "globeBasis": "vypočíta osi otočeného glóbusu",
    "globeSize": "zistí skutočnú veľkosť kresliaceho plátna a mierku",
    "globeUnit": "prevedie zemepisnú polohu na jednotkový priestorový vektor",
    "siteEcef": "prevedie miesto pokusu na súradnice so začiatkom v strede Zeme",
    "motionFrame": "vyberie časové vzorky satelitnej animácie",
    "replaySatelliteXyz": "nájde polohu satelitu z overeného replay",
    "localToGeo": "prevedie lokálne metre na zemepisné súradnice",
    "geoToLocal": "prevedie zemepisné súradnice na lokálne metre",
}

CPP_HINTS = {
    "ensure": "overí predpoklad a pri jeho porušení vyvolá výnimku",
    "need": "zastaví beh, ak povinná podmienka nie je splnená",
    "schedule": "preloží požiadavku Vanetza na plánovanú udalosť v hodinách ns-3",
    "cancel": "zruší ešte nevykonané časované udalosti",
    "now": "vráti aktuálny simulačný čas prevedený na čas Vanetza",
    "on_native_satellite_mask_drop": "zaznamená odmietnutie satelitného linku pre elevačnú masku",
    "id_hex": "naformátuje identitu udalosti v šestnástkovej sústave",
    "unique_id": "vytvorí stabilnú identitu z obsahu vstupu",
    "report_id": "odvodí identitu hlásenia od pôvodného CAM",
    "response_id": "odvodí identitu odpovede od prijatého hlásenia",
    "denm_id": "odvodí identitu konkrétnej verzie výstrahy DENM",
    "policy_ids": "načíta zoznam uzlov, na ktoré sa vzťahuje vybraná komunikačná politika",
    "address_of": "získa MAC adresu ns-3 sieťového zariadenia",
    "mac_of": "získa MAC adresu pozemného zariadenia",
    "hex_bytes": "prevedie raw bajty na čitateľný hexadecimálny text",
    "hex": "prevedie raw bajty na hexadecimálny text",
    "packet_bytes": "skopíruje bajty z objektu ns-3 Packet na ďalšiu kontrolu",
    "u4_packet_kind": "rozpozná diagnostický typ paketu podľa raw obsahu",
    "on_lan_drop": "zapíše stratu rámca na drôtovom prepojení RSU a terminálu",
    "on_wifi_phy_drop": "zapíše dôvod odmietnutia rámca fyzickou vrstvou ITS-G5",
    "append_u64": "zapíše 64-bitové číslo do výstupných bajtov",
    "read_u64": "prečíta 64-bitové číslo z raw bajtov",
    "sha256": "vypočíta kontrolný odtlačok obsahu pomocou SHA-256",
    "valid_report": "skontroluje štruktúru a pôvod experimentálneho hlásenia",
    "valid_ack": "skontroluje štruktúru a pôvod odpovede z brány",
    "valid_i2v1": "skontroluje rámec spätnej správy smerom k autu",
    "make_ack": "zostaví odpoveď brány na prijaté hlásenie",
    "make_i2v1": "zostaví spätnú správu určenú pre pozemnú vetvu",
    "bind_udp": "vytvorí a pripojí ns-3 UDP socket k uzlu a adrese",
    "server_receive": "spracuje paket skutočne prijatý bránovým socketom",
    "ut_ack_receive": "spracuje odpoveď prijatú používateľským satelitným terminálom",
    "rsu_ack_receive": "spracuje odpoveď doručenú z terminálu do RSU",
    "service_forward": "obslúži čakajúce hlásenia v smere RSU → brána",
    "enqueue_reverse": "vloží spätnú správu do ohraničeného frontu",
    "service_reverse": "obslúži čakajúce odpovede v smere brána → RSU",
    "cam_matches": "porovná dekódované polia CAM s polohovou vzorkou",
    "probe_mib": "pripraví parametre Vanetza GeoNetworking stanice",
    "on_state": "zaznamená čas vysielania, príjmu alebo obsadenosti rádia",
    "on_drop": "zaznamená dôvod straty prijímaného pozemného rámca",
    "send_denm": "odošle výstrahu DENM cez Vanetza a pozemné ns-3 rádio",
    "rebroadcast_denm": "znovu rozšíri relevantnú DENM v pozemnej oblasti",
    "request": "prijme požiadavku Vanetza na odoslanie rámca cez ns-3 zariadenie",
    "indicate": "prevezme z Vanetza dekódovanú prijatú ITS správu",
    "l2_tx": "vráti počítadlo odoslaných rámcov na linkovej vrstve",
    "l2_rx": "vráti počítadlo prijatých rámcov na linkovej vrstve",
    "cam_rx": "vráti počet prijatých CAM",
    "primary_cam_rx": "vráti počet CAM prijatých z primárneho zdroja",
    "gn_drops": "vráti počet odmietnutí vo vrstve GeoNetworking",
    "id": "vráti identitu aktuálnej stanice",
    "Register": "priradí fyzikálny profil ku konkrétnemu terminálu",
    "RegisterSatellite": "priradí katalógové poradie k mobilnému modelu družice",
    "SetServing": "aktualizuje satelit, ktorý práve obsluhuje terminál",
    "Accept": "rozhodne o fyzikálnej prípustnosti konkrétneho satelitného linku",
    "steer": "vypočíta obmedzený krok smerovania antény",
    "unit": "normalizuje vektor na jednotkovú dĺžku",
    "angle": "vypočíta uhol medzi priestorovými vektormi",
}

def short(value: str, limit: int = 105) -> str:
    """Skráti zdrojový výraz tak, aby komentár zostal čitateľný vedľa kódu."""
    value = " ".join(value.split())
    return value if len(value) <= limit else value[:limit - 1] + "…"


def function_explanation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Krátko pomenuje účel rozsiahlejšej funkcie, ak ho prezrádza názov."""
    name = node.name
    token = name.strip("_").lower().split("_")[0]
    purpose = VERBS.get(token)
    if not purpose or node.end_lineno - node.lineno < 8:
        return ""
    return f"`{name}()` {purpose}."


def add(blocks: dict[int, list[str]], line: int, prose: str, manual: set[int]) -> None:
    if line not in manual and prose:
        blocks[line].append(prose)


class PythonComments(ast.NodeVisitor):
    """Nájde funkcie, pri ktorých má krátky komentár informačnú hodnotu."""

    def __init__(self, original: str, manual: set[int], notes: dict[str, dict]) -> None:
        self.manual = manual
        self.blocks: dict[int, list[str]] = defaultdict(list)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        first = min((d.lineno for d in node.decorator_list), default=node.lineno) - 1
        add(self.blocks, first, function_explanation(node), self.manual)
        self.generic_visit(node)

def python_comments(original: str, manual: set[int], notes: dict[str, dict]) -> dict[int, list[str]]:
    visitor = PythonComments(original, manual, notes)
    visitor.visit(ast.parse(original))
    return visitor.blocks


def js_comments(original: str, manual: set[int]) -> dict[int, list[str]]:
    """Doplní stručné komentáre iba pri dlhších pomenovaných JS funkciách."""
    blocks: dict[int, list[str]] = defaultdict(list)
    lines = original.splitlines()
    for line_number, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r"(?:async\s+)?function\s+([\w$]+)\s*\(([^)]*)", stripped)
        if match and len(stripped) > 180:
            name, args = match.groups()
            token = re.split(r"(?=[A-Z])|_", name)[0].lower()
            purpose = JS_HINTS.get(name, VERBS.get(token))
            if purpose:
                add(blocks, line_number, f"`{name}({args})` {purpose}.", manual)
    return blocks


def cpp_comments(original: str, manual: set[int]) -> dict[int, list[str]]:
    """Doplní význam niektorých natívnych funkcií a parametrov."""
    blocks: dict[int, list[str]] = defaultdict(list)
    for line_number, line in enumerate(original.splitlines()):
        stripped = line.strip()
        param = re.search(r'cmd\.AddValue\("([^"]+)",\s*"[^"]*",\s*([\w_]+)\)', stripped)
        if param:
            key, variable = param.groups()
            if any(word in key.lower() for word in ("handover", "mask", "doppler", "steering")):
                add(blocks, line_number, f"Voľba `--{key}` sa načíta do `{variable}` a ovplyvní natívny beh.", manual)
        definition = re.match(r"(?:static\s+|inline\s+|virtual\s+)?[\w:<>,*& ]+\s+([A-Za-z_][\w:]*)\s*\([^;]*\)\s*(?:(?:const|override|final|noexcept)\s*)*\{", stripped)
        if definition and not stripped.startswith(("return ", "if ", "for ", "while ", "switch ", "catch ")) and definition.group(1) not in {"if", "for", "while", "switch"}:
            name = definition.group(1)
            token = name.split("::")[-1].strip("_").split("_")[0].lower()
            purpose = CPP_HINTS.get(name, VERBS.get(token))
            if purpose:
                add(blocks, line_number, f"`{name}()` {purpose}.", manual)
    return blocks


def shell_comments(original: str, manual: set[int]) -> dict[int, list[str]]:
    blocks: dict[int, list[str]] = defaultdict(list)
    for line_number, line in enumerate(original.splitlines()):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        match = re.match(r"([A-Za-z_][\w]*)=(.+)", stripped)
        if match and match.group(1) in {"package", "workspace", "runtime", "package_id", "command"}:
            name, value = match.groups()
            add(blocks, line_number, f"`{name}` určuje cestu alebo režim spúšťača: `{short(value, 75)}`.", manual)
        elif stripped.startswith("case "):
            add(blocks, line_number, "`case` vyberá príkaz spúšťača; každá vetva volá inú operáciu.", manual)
    return blocks


def automatic_comments(path: str, original: str, manual: set[int], notes: dict[str, dict]) -> dict[int, list[str]]:
    suffix = Path(path).suffix
    if suffix == ".py":
        return python_comments(original, manual, notes)
    if suffix == ".js":
        return js_comments(original, manual)
    if suffix in {".cc", ".h"}:
        return cpp_comments(original, manual)
    if suffix == ".sh":
        return shell_comments(original, manual)
    return {}
