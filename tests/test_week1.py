import json
import pandas as pd


def test_taxonomy_loaded():
    with open("data/processed/taxonomy.json", encoding="utf-8") as f:
        tax = json.load(f)

    assert len(tax["terms"]) >= 200

    assert all(
        "id" in term
        and "term" in term
        and "category" in term
        for term in tax["terms"]
    )


def test_taxonomy_categories():
    with open("data/processed/taxonomy.json", encoding="utf-8") as f:
        tax = json.load(f)

    categories = {
        term["category"]
        for term in tax["terms"]
    }

    assert len(categories) == 8


def test_sample_data_quality():
    df = pd.read_csv(
        "data/processed/listing_sample.csv"
    )

    assert len(df) >= 500
    assert df["remarks"].str.len().min() > 50


def test_sample_queries():
    df = pd.read_csv(
        "data/processed/sample_queries.csv"
    )

    assert len(df) >= 50
    assert "query" in df.columns
    assert "intent" in df.columns


def test_taxonomy_coverage():
    df = pd.read_csv(
        "data/processed/listing_sample.csv"
    )

    with open(
        "data/processed/taxonomy.json",
        encoding="utf-8"
    ) as f:
        tax = json.load(f)

    terms = [
        item["term"].lower()
        for item in tax["terms"]
    ]

    matches = df["remarks"].apply(
        lambda text: any(
            term in str(text).lower()
            for term in terms
        )
    )

    assert matches.mean() >= 0.30