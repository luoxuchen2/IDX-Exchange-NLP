import pandas as pd
import pytest

from scripts.text_cleaning import TextCleaner


@pytest.fixture
def cleaner():
    return TextCleaner()


# --------------------------------------------------
# PRICE TESTS
# --------------------------------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("priced at 450k", "450000"),
        ("priced at 450K", "450000"),
        ("$450k home", "$450000"),
        ("$1.2m home", "$1200000"),
        ("1.5M property", "1500000"),
        ("2m mansion", "2000000"),
        ("750K listing", "750000"),
        ("325k condo", "325000"),
    ]
)
def test_price_normalization(cleaner, input_text, expected):
    result = cleaner.normalize_prices(input_text)
    assert expected in result


# --------------------------------------------------
# MEASUREMENT TESTS
# --------------------------------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("2,000 sqft", "2000 square feet"),
        ("1500 sqft", "1500 square feet"),
        ("2000 sq ft", "2000 square feet"),
        ("950 SF", "950 square feet"),
        ("1,250 sq. ft.", "1250 square feet"),
        ("0.5 acre", "0.5 acres"),
        ("2 acres", "2 acres"),
        ("1 AC", "1 acres"),
    ]
)
def test_measurement_normalization(cleaner, input_text, expected):
    result = cleaner.normalize_measurements(input_text)
    assert expected.lower() in result.lower()


# --------------------------------------------------
# ABBREVIATION TESTS
# --------------------------------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("3 br home", "3 bedroom home"),
        ("2 ba", "2 bathroom"),
        ("large mbr", "large master bedroom"),
        ("finished bsmt", "finished basement"),
        ("w/ garage", "with garage"),
        ("w/o parking", "without parking"),
        ("large lr", "large living room"),
        ("formal dr", "formal dining room"),
        ("updated kit", "updated kitchen"),
        ("2 car gar", "2 car garage"),
        ("central ac", "central air conditioning"),
        ("hw floors", "hardwood floors"),
        ("lau room", "laundry room"),
        ("3rd flr", "3rd floor"),
        ("upper lvl", "upper level"),
    ]
)
def test_abbreviation_expansion(cleaner, input_text, expected):
    result = cleaner.expand_abbreviations(input_text)
    assert expected.lower() in result.lower()


# --------------------------------------------------
# HTML TESTS
# --------------------------------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("<p>Beautiful home</p>", "Beautiful home"),
        ("<b>New</b> kitchen", "New kitchen"),
        ("Home<br>Garage", "Home Garage"),
        ("&amp;", "&"),
        ("3 &lt; 4", "3 < 4"),
    ]
)
def test_html_removal(cleaner, input_text, expected):
    result = cleaner.remove_html(input_text)
    result = cleaner.normalize_whitespace(result)

    assert result == expected


# --------------------------------------------------
# WHITESPACE TESTS
# --------------------------------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("beautiful   home", "beautiful home"),
        ("home\nwith\npool", "home with pool"),
        ("home\twith\tgarage", "home with garage"),
        ("   large home   ", "large home"),
        ("home     garage", "home garage"),
    ]
)
def test_whitespace(cleaner, input_text, expected):
    assert cleaner.normalize_whitespace(input_text) == expected


# --------------------------------------------------
# PUNCTUATION TESTS
# --------------------------------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("Amazing!!!", "Amazing!"),
        ("Really???", "Really?"),
        ("Beautiful...home", "Beautiful. home"),
        ("Home.Garage", "Home. Garage"),
        ("Great!Must see", "Great! Must see"),
    ]
)
def test_punctuation(cleaner, input_text, expected):
    assert cleaner.normalize_punctuation(input_text) == expected


# --------------------------------------------------
# FULL PIPELINE TESTS
# --------------------------------------------------

def test_full_pipeline(cleaner):
    text = "<p>Beautiful 3 BR / 2 BA home w/ 2,000 sqft!!!</p>"

    result = cleaner.clean_text(text)

    assert "3 bedroom" in result
    assert "2 bathroom" in result
    assert "with" in result
    assert "2000 square feet" in result
    assert "<p>" not in result


def test_null_value(cleaner):
    assert cleaner.clean_text(None) == ""


def test_nan_value(cleaner):
    assert cleaner.clean_text(float("nan")) == ""


# --------------------------------------------------
# PROFILING TESTS
# --------------------------------------------------

def test_profiling_keys(cleaner):

    df = pd.DataFrame(
        {
            "remarks": [
                "Beautiful 3 br home",
                "<p>2 ba condo</p>",
                "$450k listing"
            ]
        }
    )

    profile = cleaner.profile_column(df, "remarks")

    assert "null_rate" in profile
    assert "avg_length" in profile
    assert "has_html" in profile
    assert "price_mentions" in profile
    assert "common_terms" in profile
    assert "common_abbreviations" in profile


def test_html_profile(cleaner):

    df = pd.DataFrame(
        {
            "remarks": [
                "<p>Home</p>",
                "Normal home"
            ]
        }
    )

    profile = cleaner.profile_column(df, "remarks")

    assert profile["has_html"] == 1


def test_null_profile(cleaner):

    df = pd.DataFrame(
        {
            "remarks": [
                "Home",
                None
            ]
        }
    )

    profile = cleaner.profile_column(df, "remarks")

    assert profile["null_rate"] == 0.5