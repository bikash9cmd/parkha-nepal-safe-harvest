from datetime import date

from parkha import dates, lexicon, tools


def test_relative_and_numeric_dates(today):
    assert dates.parse_spray_date("I sprayed yesterday", today) == date(2026, 10, 20)
    assert dates.parse_spray_date("३ दिन अगाडि छरें", today) == date(2026, 10, 18)
    assert dates.parse_spray_date("hijo chhareko", today) == date(2026, 10, 20)
    assert dates.parse_spray_date("on 2026-10-15", today) == date(2026, 10, 15)
    assert dates.parse_spray_date("on 12 Oct", today) == date(2026, 10, 12)


def test_bs_date_without_year_is_the_most_recent_past_one(today):
    # Today is 4 Kartik 2083. "Asoj 28" is 2083's, "Kartik 10" has not happened yet so it is 2082's.
    assert dates.parse_spray_date("asoj 28 ma", today) == date(2026, 10, 14)
    assert dates.parse_spray_date("कात्तिक १० मा", today).year == 2025


def test_bs_with_year_and_formatting(today):
    assert dates.parse_spray_date("२०८३ असोज २५", today) == date(2026, 10, 11)
    assert dates.fmt_en(today) == "21 October 2026 (4 Kartik 2083 BS)"
    assert dates.fmt_ne(today) == "२०८३ कात्तिक ४ (२०२६-१०-२१)"


def test_vague_dates_give_none(today):
    assert dates.parse_spray_date("I sprayed last week", today) is None
    assert dates.parse_spray_date("I sprayed it", today) is None


def test_future_spray_date_is_an_error(book, today):
    assert tools.safe_harvest_date(book, "neem", "tomato", "2026-10-25", today)["error"] == "spray_date_in_future"


def test_names_in_three_scripts():
    assert lexicon.crops("गोलभेडामा") == ["tomato"]
    assert lexicon.crops("golbheda ma") == ["tomato"]
    assert lexicon.chemicals("Furadan and Coragen") == ["carbofuran", "chlorantraniliprole"]
    assert lexicon.pests("fauji kira") == ["fall armyworm"]
    assert lexicon.pests("brinjal shoot and fruit borer") == ["shoot and fruit borer"]


def test_devanagari_alias_must_start_a_word():
    # नीम (neem) is inside रोपनीमा ("per ropani"); bug #9.
    assert lexicon.chemicals("रोपनीमा २.५ मिलि") == []
    assert lexicon.chemicals("नीमको विषादी") == ["azadirachtin"]


def test_nepali_display_names_are_recognised():
    # Every name a template prints must be visible to the gate; bug #8.
    for chem in lexicon.CHEMICALS:
        name = lexicon.chem_ne(chem)
        assert chem in lexicon.chemicals(name), chem
