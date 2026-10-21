"""Names of crops, pests and pesticides in English, Nepali and romanised Nepali.

Farmers ask about "Furadan", "गोलभेडा" or "fauji kira", and the tables are keyed on
"carbofuran", "tomato" and "fall armyworm". Every alias below was added because a test
question used it, or because it is the name printed on products sold in Nepal.

Devanagari aliases match at a word start and may run on, because Nepali postpositions attach
to the word (गोलभेडामा, "in tomato"). Latin aliases match at a word start and may take a suffix
(golbhedama), except brand names, which match whole words only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CROPS: dict[str, dict] = {
    "tomato": {"ne": "गोलभेडा", "aliases": ["tomato", "golbheda", "golbhenda", "गोलभेडा", "गोलभेंडा", "टमाटर"]},
    "cabbage": {"ne": "बन्दा", "aliases": ["cabbage", "banda kobi", "bandakobi", "बन्दा", "बन्दागोभी"]},
    "cauliflower": {"ne": "काउली", "aliases": ["cauliflower", "cauli", "kauli", "काउली", "फूलगोभी"]},
    "brinjal": {"ne": "भन्टा", "aliases": ["brinjal", "eggplant", "bhanta", "भन्टा", "भण्टा", "बैगन"]},
    "okra": {"ne": "भिण्डी", "aliases": ["okra", "lady finger", "ladyfinger", "bhindi", "भिण्डी", "भिन्डी"]},
    "chilli": {"ne": "खुर्सानी", "aliases": ["chilli", "chili", "khursani", "akabare", "खुर्सानी", "अकबरे"]},
    "cucumber": {"ne": "काँक्रो", "aliases": ["cucumber", "kakro", "kankro", "काँक्रो", "काक्रो"]},
    "bitter gourd": {"ne": "करेला", "aliases": ["bitter gourd", "karela", "करेला"]},
    "bean": {"ne": "सिमी", "aliases": ["bean", "beans", "simi", "सिमी", "बोडी"]},
    "maize": {"ne": "मकै", "aliases": ["maize", "corn", "makai", "मकै"]},
    "rice": {"ne": "धान", "aliases": ["rice", "paddy", "dhan", "धान"]},
}

PESTS: dict[str, dict] = {
    "fall armyworm": {
        "ne": "फौजी कीरा",
        "aliases": ["fall armyworm", "armyworm", "army worm", "faw", "fauji kira", "फौजी कीरा", "फौजी किरा"],
    },
    "tuta absoluta": {
        "ne": "टुटा (गोलभेडाको पात सुरुङ्गे कीरा)",
        "aliases": ["tuta", "tomato leaf miner", "pinworm", "टुटा", "पात सुरुङ्गे"],
    },
    "liriomyza leaf miner": {"ne": "पात सुरुङ्गे झिंगा", "aliases": ["liriomyza"]},
    "diamondback moth": {"ne": "हीरे पुतली", "aliases": ["diamondback", "diamond back", "dbm", "हीरे पुतली", "हिरे पुतली"]},
    "shoot and fruit borer": {
        "ne": "टुप्पो र फल छेड्ने कीरा",
        "aliases": ["shoot and fruit borer", "fruit and shoot borer", "shoot borer", "टुप्पो र फल छेड्ने", "टुप्पो छेड्ने"],
    },
    "fruit borer": {"ne": "फल छेड्ने कीरा", "aliases": ["fruit borer", "pod borer", "फल छेड्ने"]},
    "stem borer": {"ne": "गबारो", "aliases": ["stem borer", "dead heart", "gabaro", "गबारो"]},
    "leaf folder": {"ne": "पात बेर्ने कीरा", "aliases": ["leaf folder", "leaffolder", "पात बेर्ने"]},
    "planthopper": {"ne": "फड्के कीरा", "aliases": ["planthopper", "plant hopper", "bph", "फड्के"]},
    "aphid": {"ne": "लाही कीरा", "aliases": ["aphid", "aphids", "lahi", "लाही"]},
    "whitefly": {"ne": "सेतो झिंगा", "aliases": ["whitefly", "white fly", "seto jhinga", "सेतो झिंगा"]},
    "jassid": {"ne": "हरियो फड्के", "aliases": ["jassid", "jassids", "leafhopper", "leaf hopper", "हरियो फड्के"]},
    "thrips": {"ne": "थ्रिप्स", "aliases": ["thrips", "थ्रिप्स"]},
    "mite": {"ne": "सुलसुले", "aliases": ["mite", "mites", "sulsule", "सुलसुले"]},
    "fruit fly": {"ne": "फल कुहाउने झिंगा", "aliases": ["fruit fly", "fruitfly", "aunsa", "औंसा", "फल कुहाउने"]},
    "caterpillar": {"ne": "लार्भा", "aliases": ["caterpillar", "larva", "larvae", "लार्भा", "पात खाने कीरा"]},
}

# Generic name -> aliases. Brand names (match whole word only) are the ones printed on products sold
# in Nepal; farmers know "Furadan" far better than "carbofuran".
CHEMICALS: dict[str, dict] = {
    "acephate": {"ne": "एसिफेट", "aliases": ["acephate", "एसिफेट"], "brands": []},
    "acetamiprid": {"ne": "एसिटामिप्रिड", "aliases": ["acetamiprid", "एसिटामिप्रिड"], "brands": []},
    "afidopyropen": {"ne": "एफिडोपाइरोपेन", "aliases": ["afidopyropen"], "brands": []},
    "azadirachtin": {
        "ne": "नीम (एजाडिराक्टिन)",
        "aliases": ["azadirachtin", "neem", "नीम", "एजाडिराक्टिन"],
        "brands": [],
    },
    "bifenthrin": {"ne": "बाइफेन्थ्रिन", "aliases": ["bifenthrin"], "brands": []},
    "broflanilide": {"ne": "ब्रोफ्लानिलाइड", "aliases": ["broflanilide"], "brands": []},
    "buprofezin": {"ne": "बुप्रोफेजिन", "aliases": ["buprofezin"], "brands": []},
    "chlorantraniliprole": {
        "ne": "क्लोरान्ट्रानिलिप्रोल",
        "aliases": ["chlorantraniliprole", "chlorantraniliprol", "क्लोरान्ट्रानिलिप्रोल"],
        "brands": ["coragen"],
    },
    "chlorfenapyr": {"ne": "क्लोरफेनापायर", "aliases": ["chlorfenapyr"], "brands": []},
    "chlorfluazuron": {"ne": "क्लोरफ्लुआजुरोन", "aliases": ["chlorfluazuron"], "brands": []},
    "clothianidin": {"ne": "क्लोथियानिडिन", "aliases": ["clothianidin"], "brands": []},
    # Not in the label table: Parkha knows the name, so it can say it has no verified waiting period.
    "spinosad": {"ne": "स्पिनोसाड", "aliases": ["spinosad", "स्पिनोसाड"], "brands": []},
    "novaluron": {"ne": "नोभालुरोन", "aliases": ["novaluron"], "brands": []},
    "emamectin benzoate": {"ne": "इमामेक्टिन बेन्जोएट", "aliases": ["emamectin", "इमामेक्टिन"], "brands": []},
    "imidacloprid": {"ne": "इमिडाक्लोप्रिड", "aliases": ["imidacloprid", "इमिडाक्लोप्रिड"], "brands": ["confidor"]},
    "cypermethrin": {"ne": "साइपरमेथ्रिन", "aliases": ["cypermethrin", "cypermethrine", "साइपरमेथ्रिन"], "brands": []},
    "dimethoate": {"ne": "डाइमेथोएट", "aliases": ["dimethoate", "डाइमेथोएट"], "brands": ["rogor"]},
    "malathion": {"ne": "मालाथियन", "aliases": ["malathion", "मालाथियन"], "brands": []},
    "mancozeb": {"ne": "म्यान्कोजेब", "aliases": ["mancozeb", "म्यान्कोजेब"], "brands": ["dithane"]},
    # Banned in Nepal (data/nepal_banned.csv).
    "carbofuran": {"ne": "कार्बोफुरान", "aliases": ["carbofuran", "कार्बोफुरान"], "brands": ["furadan", "फुराडान"]},
    "carbosulfan": {"ne": "कार्बोसल्फान", "aliases": ["carbosulfan"], "brands": []},
    "chlorpyrifos": {
        "ne": "क्लोरपाइरिफस",
        "aliases": ["chlorpyrifos", "chlorpyriphos", "chlorpyrephos", "क्लोरपाइरिफस", "क्लोरोपाइरिफस"],
        "brands": ["dursban"],
    },
    "dichlorvos": {"ne": "डाइक्लोरभस", "aliases": ["dichlorvos", "ddvp", "डाइक्लोरभस"], "brands": ["nuvan", "नुभान"]},
    "endosulfan": {"ne": "इन्डोसल्फान", "aliases": ["endosulfan"], "brands": ["thiodan"]},
    "monocrotophos": {"ne": "मोनोक्रोटोफस", "aliases": ["monocrotophos"], "brands": []},
    "methyl parathion": {"ne": "मिथाइल प्याराथियन", "aliases": ["methyl parathion", "parathion"], "brands": ["metacid"]},
    "phorate": {"ne": "फोरेट", "aliases": ["phorate", "फोरेट"], "brands": ["thimet"]},
    "paraquat": {"ne": "प्याराक्वाट", "aliases": ["paraquat", "प्याराक्वाट"], "brands": ["gramoxone"]},
    "triazophos": {"ne": "ट्राइजोफस", "aliases": ["triazophos"], "brands": []},
    "carbaryl": {"ne": "कार्बारिल", "aliases": ["carbaryl"], "brands": ["sevin"]},
    "dicofol": {"ne": "डाइकोफल", "aliases": ["dicofol"], "brands": []},
    "benomyl": {"ne": "बेनोमिल", "aliases": ["benomyl"], "brands": []},
    "aluminium phosphide": {
        "ne": "एल्मुनियम फस्फाइड",
        "aliases": ["aluminium phosphide", "aluminum phosphide", "celphos", "सेल्फस"],
        "brands": [],
    },
    "ddt": {"ne": "डीडीटी", "aliases": ["ddt", "डीडीटी"], "brands": []},
    "lindane": {"ne": "लिन्डेन", "aliases": ["lindane"], "brands": []},
}

# The two groups the RBPR test at Kalimati detects (it measures cholinesterase inhibition).
ORGANOPHOSPHATE_OR_CARBAMATE = {
    "acephate", "dimethoate", "malathion", "chlorpyrifos", "dichlorvos", "monocrotophos", "methyl parathion",
    "phorate", "triazophos", "phosphamidon", "carbofuran", "carbosulfan", "carbaryl",
}  # fmt: skip

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
# A Devanagari alias may take a suffix (गोलभेडामा) but must start a word: नीम ("neem") sits inside
# रोपनीमा ("per ropani"), and the gate once flagged every Nepali dose line as naming neem (bug #9).
_NOT_AFTER_DEVANAGARI = r"(?<![\u0900-\u097F])"


@dataclass(frozen=True)
class Mention:
    canonical: str
    start: int
    end: int


def _patterns(table: dict[str, dict]) -> list[tuple[str, re.Pattern]]:
    out = []
    for canonical, entry in table.items():
        # The Nepali display name is an alias too: the gate must recognise every name the templates
        # print, or it cannot check them (bug #8: broflanilide was invisible in Nepali answers).
        display = re.sub(r"\s*\(.*?\)", "", entry.get("ne", "")).strip()
        inner = re.findall(r"\((.*?)\)", entry.get("ne", ""))
        for alias in entry["aliases"] + [canonical] + [a for a in [display, *inner] if a and a not in entry["aliases"]]:
            if _DEVANAGARI.search(alias):
                out.append((canonical, re.compile(_NOT_AFTER_DEVANAGARI + re.escape(alias))))
            else:
                out.append(
                    (canonical, re.compile(r"\b" + re.escape(alias).replace(r"\ ", r"[\s-]+") + r"\w{0,3}\b", re.I))
                )
        for brand in entry.get("brands", []):
            if _DEVANAGARI.search(brand):
                out.append((canonical, re.compile(_NOT_AFTER_DEVANAGARI + re.escape(brand))))
            else:
                out.append((canonical, re.compile(r"\b" + re.escape(brand) + r"\b", re.I)))
    # Longest alias first, so "shoot and fruit borer" wins over "fruit borer".
    out.sort(key=lambda p: -len(p[1].pattern))
    return out


_CROP_PATTERNS = _patterns(CROPS)
_PEST_PATTERNS = _patterns(PESTS)
_CHEM_PATTERNS = _patterns(CHEMICALS)


def _find(text: str, patterns) -> list[Mention]:
    taken: list[tuple[int, int]] = []
    found: list[Mention] = []
    for canonical, pat in patterns:
        for m in pat.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            found.append(Mention(canonical, m.start(), m.end()))
    return sorted(found, key=lambda m: m.start)


def crops(text: str) -> list[str]:
    return _unique(_find(text, _CROP_PATTERNS))


def pests(text: str) -> list[str]:
    return _unique(_find(text, _PEST_PATTERNS))


def chemicals(text: str) -> list[str]:
    return _unique(_find(text, _CHEM_PATTERNS))


def chemical_mentions(text: str) -> list[Mention]:
    return _find(text, _CHEM_PATTERNS)


def _unique(mentions: list[Mention]) -> list[str]:
    seen: list[str] = []
    for m in mentions:
        if m.canonical not in seen:
            seen.append(m.canonical)
    return seen


def crop_ne(crop: str) -> str:
    return CROPS.get(crop, {}).get("ne", crop)


def pest_ne(pest: str) -> str:
    return PESTS.get(pest, {}).get("ne", pest)


def chem_ne(chem: str) -> str:
    return CHEMICALS.get(chem, {}).get("ne", chem)
