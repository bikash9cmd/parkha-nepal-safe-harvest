from datetime import date

from parkha import assistant, dates, lexicon, tools


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


def test_ad_month_names_and_abbreviations(today):
    assert dates.parse_spray_date("Oct 12", today) == date(2026, 10, 12)
    assert dates.parse_spray_date("on 3 March", today) == date(2026, 3, 3)
    assert dates.parse_spray_date("Sept 5", today) == date(2026, 9, 5)
    assert dates.parse_spray_date("on 5 Sept. 2026", today) == date(2026, 9, 5)
    assert dates.parse_spray_date("on 2 may", today) == date(2026, 5, 2)


def test_words_that_start_like_a_month_are_not_dates(today):
    # "market 2" was 2 March and "maybe 2" was 2 May, overriding "yesterday".
    yesterday = date(2026, 10, 20)
    assert dates.parse_spray_date("sprayed yesterday, can I sell at market 2 days later?", today) == yesterday
    assert dates.parse_spray_date("sprayed yesterday, maybe 2 times", today) == yesterday
    assert dates.parse_spray_date("hijo chhareko, 1 marchha?", today) == yesterday
    for word in ("junk", "decide", "novel", "octane", "septic", "marketing"):
        assert dates.parse_spray_date(f"I sprayed it, {word} 3", today) is None, word


def test_market_in_a_harvest_question_keeps_the_real_spray_date(today):
    r = assistant.ask(
        "I sprayed chlorantraniliprole on my brinjal yesterday. Can I take it to market 2 days later?", today=today
    )
    assert "20 October 2026" in r.answer and "11 November 2026" in r.answer
    assert "harvest now" not in r.answer
