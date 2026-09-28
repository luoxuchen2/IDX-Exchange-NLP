import pandas as pd
import nltk
import re

from collections import Counter
from nltk.corpus import stopwords
from nltk.util import ngrams


# Download NLTK resources
nltk.download("punkt")
nltk.download("stopwords")


# Load the listing sample created in data_loading.py
df = pd.read_csv("data/processed/listing_sample.csv")


# Combine all listing remarks into one lowercase string
all_text = " ".join(
    df["remarks"]
    .dropna()
    .astype(str)
    .str.lower()
)


# Tokenize the remarks
tokens = nltk.word_tokenize(all_text)


# Remove common English stopwords and punctuation
stop_words = set(stopwords.words("english"))

clean_tokens = [
    token
    for token in tokens
    if re.fullmatch(r"[a-zA-Z-]+", token)
    and token not in stop_words
    and len(token) > 2
]


# -----------------------------
# BIGRAM EXTRACTION
# 
# -----------------------------

bigrams = list(ngrams(clean_tokens, 2))

bigram_freq = Counter(bigrams)

print("\nTop 200 Bigrams:\n")

for bigram, count in bigram_freq.most_common(200):
    print(f"{' '.join(bigram)}: {count}")


# -----------------------------
# OPTIONAL TRIGRAM EXTRACTION
# Added to find more detailed real-estate phrases
# -----------------------------

trigrams = list(ngrams(clean_tokens, 3))

trigram_freq = Counter(trigrams)


# -----------------------------
# SAVE TAXONOMY CANDIDATES
# -----------------------------

results = []

# Save top 300 bigrams
for phrase, count in bigram_freq.most_common(300):
    results.append({
        "term": " ".join(phrase),
        "frequency": count,
        "type": "bigram"
    })

# Save top 200 trigrams
for phrase, count in trigram_freq.most_common(200):
    results.append({
        "term": " ".join(phrase),
        "frequency": count,
        "type": "trigram"
    })


results_df = pd.DataFrame(results)

results_df.to_csv(
    "data/processed/taxonomy_candidates.csv",
    index=False
)


print(
    f"\nSaved {len(results_df)} taxonomy candidates "
    "to data/processed/taxonomy_candidates.csv"
)