import re
import html
import unicodedata
from collections import Counter

import pandas as pd


class TextCleaner:
    def __init__(self):
        self.abbrev_map = {
            "br": "bedroom",
            "bdr": "bedroom",
            "bdrm": "bedroom",
            "bd": "bedroom",
            "ba": "bathroom",
            "bath": "bathroom",
            "bth": "bathroom",
            "sqft": "square feet",
            "sf": "square feet",
            "sq ft": "square feet",
            "w/": "with",
            "w/o": "without",
            "mbr": "master bedroom",
            "mbdr": "master bedroom",
            "lr": "living room",
            "dr": "dining room",
            "fr": "family room",
            "kit": "kitchen",
            "gar": "garage",
            "gar.": "garage",
            "ac": "air conditioning",
            "a/c": "air conditioning",
            "hw": "hardwood",
            "hdwd": "hardwood",
            "bsmt": "basement",
            "bsmnt": "basement",
            "apt": "apartment",
            "condo": "condominium",
            "pkg": "parking",
            "prkg": "parking",
            "lau": "laundry",
            "lndry": "laundry",
            "flr": "floor",
            "lvl": "level",
            "yr": "year",
            "yrs": "years",
            "mo": "month",
            "mins": "minutes",
            "min": "minute",
            "approx": "approximately",
            "incl": "included",
            "excl": "excluded",
            "renov": "renovated",
            "utils": "utilities",
            "elec": "electric",
            "rec": "recreation"
        }

    def clean_text(self, text):
        """Run the complete cleaning pipeline."""

        if pd.isna(text):
            return ""

        text = str(text)

        text = self.normalize_unicode(text)
        text = self.remove_html(text)
        text = self.normalize_prices(text)
        text = self.normalize_measurements(text)
        text = self.expand_abbreviations(text)
        text = self.normalize_punctuation(text)
        text = self.normalize_whitespace(text)

        return text.strip()

    def normalize_unicode(self, text):
        """
        Normalize unicode characters such as curly quotes,
        em dashes, and non-breaking spaces.
        """

        text = html.unescape(text)
        text = unicodedata.normalize("NFKC", text)

        replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u00a0": " "
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def remove_html(self, text):
        """Remove HTML tags and decode HTML entities."""

        text = html.unescape(text)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        return text

    def normalize_prices(self, text):
        """
        Convert shortened price notation:
        450k -> 450000
        $450K -> $450000
        1.2m -> 1200000
        """

        # Millions first
        def replace_million(match):
            value = float(match.group(1))
            return str(int(value * 1_000_000))

        text = re.sub(
            r"(?<!\w)(\d+(?:\.\d+)?)\s*[mM]\b",
            replace_million,
            text
        )

        # Thousands
        def replace_thousand(match):
            value = float(match.group(1))
            return str(int(value * 1_000))

        text = re.sub(
            r"(?<!\w)(\d+(?:\.\d+)?)\s*[kK]\b",
            replace_thousand,
            text
        )

        return text

    def normalize_measurements(self, text):
        """
        Normalize common real estate measurements.

        2,000 sqft -> 2000 square feet
        1500 sq ft -> 1500 square feet
        0.5 acre -> 0.5 acres
        """

        # Square feet
        text = re.sub(
            r"(\d[\d,]*(?:\.\d+)?)\s*(?:sq\.?\s*ft\.?|sqft|sf)\b",
            lambda m: f"{m.group(1).replace(',', '')} square feet",
            text,
            flags=re.IGNORECASE
        )

        # Acres
        text = re.sub(
            r"(\d+(?:\.\d+)?)\s*(?:acre|acres|ac)\b",
            lambda m: f"{m.group(1)} acres",
            text,
            flags=re.IGNORECASE
        )

        return text

    def expand_abbreviations(self, text):
        """Expand common MLS and real estate abbreviations."""

        # Longest keys first so "sq ft" is processed before "sf"
        abbreviations = sorted(
            self.abbrev_map.items(),
            key=lambda item: len(item[0]),
            reverse=True
        )

        for abbreviation, replacement in abbreviations:

            # Special handling for abbreviations containing /
            if "/" in abbreviation:
                pattern = re.escape(abbreviation)
            else:
                pattern = r"(?<!\w)" + re.escape(abbreviation) + r"(?!\w)"

            text = re.sub(
                pattern,
                replacement,
                text,
                flags=re.IGNORECASE
            )

        return text

    def normalize_punctuation(self, text):
        """Standardize repeated and unusual punctuation."""

        # Repeated exclamation marks
        text = re.sub(r"!{2,}", "!", text)

        # Repeated question marks
        text = re.sub(r"\?{2,}", "?", text)

        # Three or more periods become one period
        text = re.sub(r"\.{3,}", ".", text)

        # Add one space after punctuation when needed
        text = re.sub(r"([,.!?;:])(?=[A-Za-z])", r"\1 ", text)

        return text

    def normalize_whitespace(self, text):
        """Remove extra spaces, tabs, and line breaks."""

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def profile_column(self, df, column_name):
        """Analyze cleaning issues in a text column."""

        series = df[column_name]

        non_null = series.dropna().astype(str)

        return {
            "null_rate": series.isnull().mean(),
            "null_count": series.isnull().sum(),
            "avg_length": non_null.str.len().mean(),
            "median_length": non_null.str.len().median(),
            "price_mentions": non_null.str.contains(
                r"\$\s*\d",
                regex=True,
                case=False
            ).sum(),
            "has_html": non_null.str.contains(
                r"<[^>]+>",
                regex=True
            ).sum(),
            "unicode_issues": non_null.str.contains(
                r"[^\x00-\x7F]",
                regex=True
            ).sum(),
            "common_terms": self._extract_top_ngrams(non_null),
            "common_abbreviations": self._detect_abbreviations(non_null)
        }

    def _extract_top_ngrams(self, series, n=1, top_n=15):
        """Return the most common words or n-grams."""

        counter = Counter()

        for text in series:
            words = re.findall(r"\b[a-zA-Z]+\b", text.lower())

            if len(words) < n:
                continue

            grams = [
                " ".join(words[i:i+n])
                for i in range(len(words) - n + 1)
            ]

            counter.update(grams)

        return counter.most_common(top_n)

    def _detect_abbreviations(self, series):
        """Count known MLS abbreviations in the dataset."""

        counts = Counter()

        for text in series:
            text_lower = text.lower()

            for abbreviation in self.abbrev_map:

                if "/" in abbreviation:
                    pattern = re.escape(abbreviation)
                else:
                    pattern = (
                        r"(?<!\w)"
                        + re.escape(abbreviation)
                        + r"(?!\w)"
                    )

                matches = re.findall(
                    pattern,
                    text_lower,
                    flags=re.IGNORECASE
                )

                if matches:
                    counts[abbreviation] += len(matches)

        return counts.most_common()