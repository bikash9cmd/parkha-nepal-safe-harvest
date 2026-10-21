from parkha import tools
from parkha.labels import per_unit_area


def test_ban_list_beats_the_indian_label(book):
    # Carbofuran, carbosulfan and chlorpyrifos have label rows and are banned in Nepal.
    for crop in ("brinjal", "cabbage", "maize", "tomato"):
        assert not [o for o in book.options(crop, None) if book.ban(o.chemical)]
    opts = tools.pesticide_options(book, "brinjal", "shoot and fruit borer")
    assert {"carbosulfan", "chlorpyrifos"} <= set(opts["banned_in_nepal_but_on_indian_label"])


def test_waiting_period_is_the_longest_row_for_the_crop(book):
    # Neem on tomato: 3 days for the 1% EC, 5 days for the 5% extract. The farmer rarely knows which.
    assert book.crop_waiting_days("azadirachtin", "tomato") == 5
    assert book.crop_waiting_days("chlorantraniliprole", "brinjal") == 22
    assert book.crop_waiting_days("chlorantraniliprole", "tomato") == 3


def test_blank_waiting_period_is_unknown_not_zero(book):
    assert book.crop_waiting_days("chlorpyrifos", "cabbage") is None
    assert book.crop_waiting_days("spinosad", "tomato") is None


def test_options_need_the_pest_on_the_label(book):
    # The tomato "leaf miner" label row is Liriomyza, not Tuta absoluta.
    assert book.options("tomato", "tuta absoluta") == []
    assert [o.chemical for o in book.options("tomato", "liriomyza leaf miner")] == ["broflanilide"]


def test_rates_in_ropani_and_kattha():
    area = per_unit_area((150.0, 150.0))
    assert area["ropani"] == (7.6, 7.6)
    assert area["kattha"] == (5.1, 5.1)


def test_options_shortest_waiting_first(book):
    days = [o["waiting_days"] for o in tools.pesticide_options(book, "cabbage", "diamondback moth")["options"]]
    assert days == sorted(days) and days[0] == 1
