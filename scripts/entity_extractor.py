
"""Rule-based entity extraction for real estate listing remarks.

Extract bedrooms, bathrooms, prices, living area, and amenities.

Spans use half-open Python character offsets [start, end).
Numeric values are normalized, while spans preserve original text.
"""

import re


class EntityExtractor:

    # Amenity taxonomy
    DEFAULT_AMENITIES = {
        "pool": [r"\b(?:swimming\s+)?pools?\b"],
        "garage": [
            r"\b(?:attached\s+|detached\s+)?garages?\b"
        ],
        "parking": [r"\b(?:parking|carport)\b"],
        "fireplace": [r"\bfireplaces?\b"],
        "patio": [r"\bpatios?\b"],
        "deck": [r"\bdecks?\b"],
        "balcony": [r"\bbalcon(?:y|ies)\b"],
        "solar": [r"\bsolar(?:\s+panels?)?\b"],
        "air_conditioning": [
            r"\b(?:central\s+air|air\s+conditioning|a/c|ac\s+unit)\b"
        ],
        "laundry": [
            r"\b(?:laundry|washer|dryer|w/d)\b"
        ],
        "updated_kitchen": [
            r"\b(?:updated|renovated|remodeled)\s+kitchen\b"
        ],
    }

    NUMBER_WORDS = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }

    # Regex patterns for numeric entities
    PATTERNS = {
        "bedrooms": re.compile(
            r"\b(?P<value>\d{1,2}|one|two|three|four|five|"
            r"six|seven|eight|nine|ten)"
            r"\s*[-–—]?\s*"
            r"(?:bedrooms?|beds?|br|bd)\b",
            re.I,
        ),

        "bathrooms": re.compile(
            r"\b(?P<value>\d+(?:\.\d+)?|one|two|three|"
            r"four|five|six|seven|eight|nine|ten)"
            r"\s*[-–—]?\s*"
            r"(?:(?:full|half)\s+)?"
            r"(?:bathrooms?|baths?|ba)\b",
            re.I,
        ),

        "sqft": re.compile(
            r"\b(?P<value>\d{1,3}(?:,\d{3})+|\d{2,6})"
            r"\s*[-–—]?\s*"
            r"(?:sq\.?\s*ft\.?|sqft|square\s+feet|"
            r"square\s+foot|sq\s*ft)\b",
            re.I,
        ),

        "price": re.compile(
            r"(?<!\w)\$\s*"
            r"(?P<value>(?:\d{1,3}(?:,\d{3})+|\d+)"
            r"(?:\.\d+)?)"
            r"(?P<suffix>\s*[kKmM])?\b"
        ),
    }

    def __init__(self, amenities=None):
        """Initialize extractor with optional Week 1 amenity taxonomy."""

        if amenities is None:
            amenities = self.DEFAULT_AMENITIES

        self.amenity_patterns = {
            name: [
                re.compile(pattern, re.I)
                for pattern in patterns
            ]
            for name, patterns in amenities.items()
        }

    @staticmethod
    def _numeric_value(kind, match):
        """Convert extracted text into a normalized numeric value."""

        raw_value = match.group("value").lower().replace(",", "")

        if raw_value in EntityExtractor.NUMBER_WORDS:
            value = float(EntityExtractor.NUMBER_WORDS[raw_value])
        else:
            value = float(raw_value)

        if kind == "price":
            suffix = (match.group("suffix") or "").strip().lower()

            multiplier = {
                "k": 1_000,
                "m": 1_000_000,
            }

            value *= multiplier.get(suffix, 1)

        return int(value) if value.is_integer() else value

    @staticmethod
    def _is_lot_sqft(text, start, end):
        """Identify square footage referring to land instead of living area."""

        before = text[max(0, start - 35):start].lower()
        after = text[end:min(len(text), end + 35)].lower()

        # Examples: "7,919 square foot lot"
        if re.match(
            r"\s*\.?\s*(?:lot|parcel|land|site)\b",
            after
        ):
            return True

        # Examples: "lot size of 7,919 square feet"
        if re.search(
            r"\b(?:lot|parcel|land|site)"
            r"(?:\s+\w+){0,4}\s*$",
            before
        ):
            return True

        # Examples: "7,919-square-foot lot"
        if re.match(
            r"\s*[-–—]?\s*(?:lot|parcel|land)\b",
            after
        ):
            return True

        return False

    def extract_spans(self, text):
        """Extract entities with exact character positions."""

        if not isinstance(text, str):
            text = "" if text is None else str(text)

        spans = []

        # Numeric entities
        for label, pattern in self.PATTERNS.items():

            for match in pattern.finditer(text):

                # Exclude land/lot square footage
                if label == "sqft" and self._is_lot_sqft(
                    text,
                    match.start(),
                    match.end()
                ):
                    continue

                spans.append({
                    "start": match.start(),
                    "end": match.end(),
                    "label": label.upper(),
                    "text": match.group(),
                    "value": self._numeric_value(label, match),
                })

        # Amenity entities
        for name, patterns in self.amenity_patterns.items():

            for pattern in patterns:

                for match in pattern.finditer(text):
                    spans.append({
                        "start": match.start(),
                        "end": match.end(),
                        "label": "AMENITY",
                        "text": match.group(),
                        "value": name,
                    })

        # Sort by text position
        spans.sort(
            key=lambda s: (
                s["start"],
                -(s["end"] - s["start"])
            )
        )

        # Remove overlapping matches
        nonoverlapping = []

        for span in spans:
            if (
                not nonoverlapping
                or span["start"] >= nonoverlapping[-1]["end"]
            ):
                nonoverlapping.append(span)

        return nonoverlapping

    def extract_all(self, text):
        """Return structured property information."""

        result = {
            "bedrooms": None,
            "bathrooms": None,
            "price": None,
            "sqft": None,
            "amenities": [],
        }

        for span in self.extract_spans(text):

            if span["label"] == "AMENITY":

                if span["value"] not in result["amenities"]:
                    result["amenities"].append(span["value"])

            else:
                key = span["label"].lower()

                if result[key] is None:
                    result[key] = span["value"]

        return result

    def extract_bedrooms(self, text):
        return self.extract_all(text)["bedrooms"]

    def extract_bathrooms(self, text):
        return self.extract_all(text)["bathrooms"]

    def extract_price(self, text):
        return self.extract_all(text)["price"]

    def extract_sqft(self, text):
        return self.extract_all(text)["sqft"]

    def extract_amenities(self, text):
        return self.extract_all(text)["amenities"]
