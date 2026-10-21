"""Template answers in English and Nepali, built only from tool results.

These are the offline backend's answers and the fallback whenever the model's answer fails the
gate. They are plain on purpose: a farmer reading one on a phone at the field edge needs the
waiting period and the date, not a paragraph.
"""

from __future__ import annotations

from . import config, dates, lexicon

AKC_EN = "Confirm with your Agriculture Knowledge Centre or municipality agriculture section that the product you buy is registered in Nepal."
AKC_NE = "किन्ने विषादी नेपालमा दर्ता भएको हो कि होइन, कृषि ज्ञान केन्द्र वा पालिकाको कृषि शाखामा पुष्टि गर्नुहोस्।"


def _days(n: int) -> str:
    return "1 day" if n == 1 else f"{n} days"


def _rate_ne(rate: str) -> str:
    return dates.ne_digits(rate.replace(" ml", " मिलि").replace(" g", " ग्राम"))


def _list_en(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _list_ne(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " र " + items[-1]


def crisis(lang: str) -> str:
    if lang == "ne":
        return (
            "तपाईं धेरै गाह्रो समयबाट गुज्रिरहनुभएको जस्तो लाग्छ। तपाईं एक्लो हुनुहुन्न। कृपया अहिले नै राष्ट्रिय आत्महत्या "
            f"रोकथाम हेल्पलाइन {config.CRISIS_LINE} मा फोन गर्नुहोस्, वा नजिकको मान्छे वा अस्पतालसँग कुरा गर्नुहोस्। "
            "घरमा विषादी छ भने अरू कसैलाई ताल्चा लगाएर राख्न दिनुहोस्।"
        )
    return (
        "It sounds like you are going through something very hard, and you don't have to face it alone. Please call "
        f"Nepal's suicide prevention helpline {config.CRISIS_LINE} now, or talk to someone near you or go to the nearest "
        "hospital. If there are pesticides at home, ask someone else to lock them away."
    )


def refusal(kind: str, lang: str) -> str:
    en = {
        "harm": "I can't help with using pesticides on people, animals or fish. Poisoning rivers kills far more than fish "
        "and is a crime. I can help with protecting your crops.",
        "cosmetic": "I can't help with spraying to make vegetables look fresh before market. It is the main reason "
        "vegetables fail the residue test at Kalimati and are destroyed. Harvest only after the label waiting period; "
        "for freshness, pick in the cool morning and keep produce in shade.",
        "injection": "I can only answer questions about crop pests, pesticide waiting periods and safe use.",
        "too_long": "Please ask one short question about your crop, the pest or the product you used.",
    }
    ne = {
        "harm": "मान्छे, जनावर वा माछामा विषादी प्रयोग गर्न म सहयोग गर्न सक्दिनँ। खोलामा विष हाल्नु अपराध हो र यसले माछा मात्र "
        "होइन धेरैलाई मार्छ। बाली जोगाउन भने म सहयोग गर्न सक्छु।",
        "cosmetic": "बजार लैजानुअघि तरकारी ताजा देखाउन विषादी छर्ने कुरामा म सहयोग गर्न सक्दिनँ। कालीमाटीमा तरकारी अवशेष "
        "परीक्षणमा फेल भएर नष्ट हुने मुख्य कारण यही हो। लेबलको पर्खने अवधि पूरा भएपछि मात्र टिप्नुहोस्; ताजा राख्न बिहान "
        "चिसोमा टिपेर छहारीमा राख्नुहोस्।",
        "injection": "म बालीका कीरा, विषादीको पर्खने अवधि र सुरक्षित प्रयोगबारे मात्र जवाफ दिन्छु।",
        "too_long": "कृपया बाली, कीरा वा प्रयोग गरेको विषादीबारे छोटो प्रश्न सोध्नुहोस्।",
    }
    return (ne if lang == "ne" else en)[kind]


def harvest(h: dict, lang: str) -> str:
    chem, crop = h["chemical"], h["crop"]
    ban = h.get("banned_in_nepal")
    sd = dates.date.fromisoformat(h["spray_date"])
    if lang == "ne":
        name, crop_n = lexicon.chem_ne(chem), lexicon.crop_ne(crop)
        # The ban goes first, and later sentences say "यसको" ("its"): the gate checks each sentence
        # that names a banned product for a ban word (bug #7).
        ban_line = (
            f"{name} {dates.ne_digits(h['banned_year'])} देखि नेपालमा प्रतिबन्धित छ; फेरि प्रयोग नगर्नुहोस्। " if ban else ""
        )
        subject = "यसको" if ban else f"{name}को"
        if h["status"] == "no_verified_waiting_period":
            return (
                f"{ban_line}{crop_n}मा {subject} पर्खने अवधि मसँग पुष्टि भएको छैन, त्यसैले सुरक्षित टिप्ने मिति भन्न सक्दिनँ। "
                "लेबलमा लेखिएको पर्खने अवधि हेर्नुहोस् वा कृषि ज्ञान केन्द्रमा सोध्नुहोस्; त्यसअघि नटिप्नुहोस्।"
            )
        when = (
            f"अझै {dates.ne_digits(h['days_left'])} दिन पर्खनुहोस्।"
            if h["status"] == "wait"
            else "त्यो दिन बितिसकेको छ, अब टिप्न सकिन्छ।"
        )
        return (
            f"{ban_line}{crop_n}मा {subject} पर्खने अवधि {dates.ne_digits(h['waiting_days'])} दिन हो। तपाईंले {dates.fmt_ne(sd)} मा "
            f"छर्नुभयो, त्यसैले सबैभन्दा चाँडो सुरक्षित टिप्ने दिन {h['earliest_harvest_ne']} हो। {when} पर्खने अवधि अन्तिम "
            "पटक छरेको दिनदेखि गन्नुहोस्।"
        )
    ban_line = (
        f"{chem.capitalize()} has been banned in Nepal since {h['banned_year']}; do not use it again. " if ban else ""
    )
    subject = "it" if ban else chem
    if h["status"] == "no_verified_waiting_period":
        return (
            f"{ban_line}I don't have a verified waiting period for {subject} on {crop}, so I can't give you a safe harvest "
            "date. Read the waiting period on the label or ask your Agriculture Knowledge Centre, and don't harvest before then."
        )
    when = (
        f"That is {_days(h['days_left'])} from today."
        if h["status"] == "wait"
        else "That day has passed, so you can harvest now."
    )
    return (
        f"{ban_line}The label waiting period for {subject} on {crop} is {_days(h['waiting_days'])}. You sprayed on "
        f"{dates.fmt_en(sd)}, so the earliest safe harvest is {h['earliest_harvest_en']}. {when} Count from the last spray, "
        "not the first."
    )


def need_date(status: dict, crop: str, lang: str) -> str:
    chem = status["chemical"]
    days = (status.get("waiting_days_by_crop") or {}).get(crop)
    if lang == "ne":
        base = (
            f"{lexicon.crop_ne(crop)}मा {lexicon.chem_ne(chem)}को पर्खने अवधि {dates.ne_digits(days)} दिन हो।"
            if days
            else (f"{lexicon.crop_ne(crop)}मा {lexicon.chem_ne(chem)}को पर्खने अवधि मसँग पुष्टि भएको छैन।")
        )
        return base + " अन्तिम पटक कुन दिन छर्नुभयो (जस्तै हिजो, अस्ति, वा गते) भन्नुभयो भने सुरक्षित टिप्ने मिति निकालिदिन्छु।"
    base = (
        f"The label waiting period for {chem} on {crop} is {_days(days)}."
        if days
        else (f"I don't have a verified waiting period for {chem} on {crop}.")
    )
    return (
        base
        + " Tell me the day you last sprayed (yesterday, a few days ago, or the date in BS or AD) and I'll give you the safe harvest date."
    )


def status(s: dict, lang: str) -> str:
    chem = s["chemical"]
    by_crop = {c: d for c, d in (s.get("waiting_days_by_crop") or {}).items() if d is not None}
    if lang == "ne":
        name = lexicon.chem_ne(chem)
        if s.get("banned_in_nepal"):
            stock = (
                " पुरानो मौज्दात पसलमा दुई वर्षसम्म बिक्न सक्छ, तर पसलमा पाइनु कानुनी हुनुको प्रमाण होइन।"
                if s["banned_year"] >= 2024
                else ""
            )
            return (
                f"{name} {dates.ne_digits(s['banned_year'])} देखि नेपालमा प्रतिबन्धित छ। नकिन्नुहोस्, प्रयोग नगर्नुहोस्।{stock} "
                "आफ्नो बाली र कीराको नाम भन्नुभयो भने प्रतिबन्ध नलागेका विकल्प र तिनको पर्खने अवधि बताउँछु।"
            )
        if by_crop:
            parts = [f"{lexicon.crop_ne(c)} {dates.ne_digits(d)} दिन" for c, d in sorted(by_crop.items())]
            return f"{name} नेपालको प्रतिबन्धित सूचीमा छैन। लेबलअनुसार पर्खने अवधि: {_list_ne(parts)}। {AKC_NE}"
        return f"{name} नेपालको प्रतिबन्धित सूचीमा छैन, तर मसँग यसको पुष्टि भएको पर्खने अवधि छैन। लेबल हेर्नुहोस्। {AKC_NE}"
    if s.get("banned_in_nepal"):
        stock = (
            " Shops may still sell old stock for up to two years, but being on a shelf does not make it legal to recommend."
            if s["banned_year"] >= 2024
            else ""
        )
        return (
            f"{chem.capitalize()} has been banned in Nepal since {s['banned_year']}. Do not buy or use it.{stock} Tell me "
            "your crop and the pest and I'll give you options that are not banned, with their waiting periods."
        )
    if by_crop:
        parts = [f"{c} {_days(d)}" for c, d in sorted(by_crop.items())]
        return f"{chem.capitalize()} is not on Nepal's banned list. Label waiting periods: {_list_en(parts)}. {AKC_EN}"
    return f"{chem.capitalize()} is not on Nepal's banned list, but I have no verified waiting period for it. Read the label. {AKC_EN}"


def advice(notes: list[dict], opts: dict | None, crop: str | None, pest: str | None, lang: str) -> str:
    note = notes[0] if notes else None
    steps = []
    if note:
        steps = list(note["steps_ne"] if lang == "ne" else note["steps"])[:3]
    lines = []
    if lang == "ne":
        head = " ".join(
            x for x in [lexicon.crop_ne(crop) + "मा" if crop else "", lexicon.pest_ne(pest) if pest else ""] if x
        )
        if steps:
            lines.append((f"{head}: " if head else "") + "पहिले यी गर्नुहोस्: " + " ".join(steps))
        if opts and opts["options"]:
            parts = []
            for o in opts["options"][:3]:
                rate = f", रोपनीमा {_rate_ne(o['per_ropani'])}" if o.get("per_ropani") else ""
                op = ", अर्गानोफस्फेट: कालीमाटी परीक्षणले यही समात्छ" if o.get("residue_test_target") else ""
                parts.append(
                    f"{lexicon.chem_ne(o['chemical'])} (टिप्नुअघि {dates.ne_digits(o['waiting_days'])} दिन पर्खनुहोस्{rate}{op})"
                )
            lines.append(
                "छर्नैपरे, यी विषादी यो बाली र कीराका लागि आधिकारिक लेबलमा छन् र नेपालमा प्रतिबन्धित छैनन्: "
                + _list_ne(parts)
                + "।"
            )
        elif crop:
            lines.append("यो बाली र कीराका लागि मसँग पुष्टि भएको विषादी र पर्खने अवधि छैन, त्यसैले मात्रा भन्दिनँ।")
        if opts and opts["banned_in_nepal_but_on_indian_label"]:
            names = [lexicon.chem_ne(c) for c in opts["banned_in_nepal_but_on_indian_label"]]
            lines.append(f"{_list_ne(names)} नेपालमा प्रतिबन्धित छ; प्रयोग नगर्नुहोस्।")
        lines.append(AKC_NE)
        return " ".join(lines)
    head = " on ".join(x for x in [pest, crop] if x)
    if steps:
        lines.append((f"For {head}, start with this: " if head else "Start with this: ") + " ".join(steps))
    if opts and opts["options"]:
        parts = []
        for o in opts["options"][:3]:
            rate = f", {o['per_ropani']} per ropani" if o.get("per_ropani") else ""
            op = "; an organophosphate, the kind the Kalimati test detects" if o.get("residue_test_target") else ""
            parts.append(f"{o['chemical']} (wait {_days(o['waiting_days'])} before harvest{rate}{op})")
        lines.append(
            f"If you must spray, these are on an official label for this crop and pest and are not banned in Nepal: {_list_en(parts)}."
        )
    elif crop:
        lines.append("I have no verified product and waiting period for this crop and pest, so I won't give a dose.")
    if opts and opts["banned_in_nepal_but_on_indian_label"]:
        lines.append(f"Do not use {_list_en(opts['banned_in_nepal_but_on_indian_label'])}: banned in Nepal.")
    lines.append(AKC_EN)
    return " ".join(lines)
