from datetime import date

import pytest

from parkha.corpus import default_corpus
from parkha.labels import default_book

TODAY = date(2026, 10, 21)


@pytest.fixture
def book():
    return default_book()


@pytest.fixture
def corpus():
    return default_corpus()


@pytest.fixture
def today():
    return TODAY
