import json
import pandas as pd

df = pd.read_csv("data/processed/listing_sample.csv")

with open("data/processed/taxonomy.json", encoding="utf-8") as f:
    taxonomy = json.load(f)

terms = [
    item["term"].lower()
    for item in taxonomy["terms"]
]

def contains_taxonomy_term(text):
    text = str(text).lower()
    return any(term in text for term in terms)

matches = df["remarks"].apply(contains_taxonomy_term)

coverage = matches.mean()

print(f"Listings checked: {len(df)}")
print(f"Listings containing taxonomy terms: {matches.sum()}")
print(f"Taxonomy coverage: {coverage:.2%}")

if coverage >= 0.30:
    print("PASS: Taxonomy coverage is at least 30%")
else:
    print("FAIL: Taxonomy coverage is below 30%")