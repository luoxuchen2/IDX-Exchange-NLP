
"""
Week 6: Listing Signal Extraction

Purpose:
    Convert real estate listing descriptions into structured,
    searchable property information.

This script contains two classes:

1. EntityExtractor (Week 3)
   Extracts bedrooms, bathrooms, prices, square footage,
   and basic amenity mentions.

2. SignalExtractor (Week 6)
   Reuses EntityExtractor and adds:
   - Expanded amenities
   - Property condition
   - Financing terms
   - Location features
   - Negation handling
   - Proximity detection

The final output is suitable for JSON export and filtering.

All extraction is rule-based using regular expressions.
"""


# ============================================================
# SECTION 1: IMPORT LIBRARIES
# ============================================================

# Regular expressions allow us to search property descriptions
# for patterns such as "3 bedrooms" or "near schools".
import re


# ============================================================
# SECTION 2: WEEK 3 ENTITY EXTRACTOR
# ============================================================

class EntityExtractor:
    """
    Extract numeric property information and basic amenity
    mentions from real estate listing descriptions.
    """

    # --------------------------------------------------------
    # 2.1 BASIC AMENITY PATTERNS
    # --------------------------------------------------------

    # These are the original Week 3 amenity categories.
    #
    # Each regular expression finds possible mentions
    # of a property feature.
    #
    # Negation is handled later by SignalExtractor.

    DEFAULT_AMENITIES = {
        "pool": [
            r"\b(?:swimming\s+|in[- ]ground\s+)?pools?\b"
        ],

        "garage": [
            r"\b(?:attached\s+|detached\s+)?garages?\b"
        ],

        "parking": [
            r"\b(?:parking|carport)\b"
        ],

        "fireplace": [
            r"\bfireplaces?\b"
        ],

        "patio": [
            r"\bpatios?\b"
        ],

        "deck": [
            r"\bdecks?\b"
        ],

        "balcony": [
            r"\bbalcon(?:y|ies)\b"
        ],

        "solar": [
            r"\bsolar(?:\s+panels?)?\b"
        ],

        "air_conditioning": [
            r"\b(?:central\s+air|central\s+a/?c|"
            r"air\s+conditioning|a/c|ac\s+units?)\b"
        ],

        "laundry": [
            r"\b(?:laundry|washer|dryer|w/d)\b"
        ],

        "updated_kitchen": [
            r"\b(?:updated|renovated|remodeled)\s+kitchen\b"
        ]
    }

    # --------------------------------------------------------
    # 2.2 WRITTEN NUMBERS
    # --------------------------------------------------------

    # Convert written numbers into numerical values.
    #
    # Example:
    # "three bedrooms" becomes 3.

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
        "ten": 10
    }

    # --------------------------------------------------------
    # 2.3 NUMERIC EXTRACTION PATTERNS
    # --------------------------------------------------------

    # These patterns find common real estate measurements.
    #
    # re.I means uppercase and lowercase are treated equally.
    # (?P<value>...) captures the number for conversion.

    PATTERNS = {

        # Examples:
        # "3 bedrooms", "4-bed", "3BR", "two bedrooms".
        "bedrooms": re.compile(
            r"\b(?P<value>\d{1,2}|one|two|three|four|five|"
            r"six|seven|eight|nine|ten)"
            r"\s*[-–—]?\s*"
            r"(?:bedrooms?|beds?|br|bd)\b",
            re.I
        ),

        # Examples:
        # "2 bathrooms", "2.5 baths", "2 1/2 baths",
        # "2½-bath", "1/2 bath", "½ bathroom".
        "bathrooms": re.compile(
            r"(?<!\w)(?P<value>"
            r"\d+\s+1/2|"
            r"\d+\s*½|"
            r"\d+/\d+|"
            r"½|"
            r"\d+(?:\.\d+)?|"
            r"one|two|three|four|five|"
            r"six|seven|eight|nine|ten"
            r")"
            r"\s*[-–—]?\s*"
            r"(?:(?:full|half)\s+)?"
            r"(?:bathrooms?|baths?|ba)\b",
            re.I
        ),

        # Examples:
        # "2,100 square feet", "576-square-foot",
        # "2,100 sq ft", "800sf".
        "sqft": re.compile(
            r"\b(?P<value>\d{1,3}(?:,\d{3})+|\d{2,6})"
            r"\s*[-–—]?\s*"
            r"(?:sq\.?\s*ft\.?|sqft|sf|"
            r"square[-\s]+feet|square[-\s]+foot)\b",
            re.I
        ),

        # Examples:
        # "$450,000", "$450K", "$1.5M".
        "price": re.compile(
            r"(?<!\w)\$\s*"
            r"(?P<value>\d{1,3}(?:,\d{3})+|\d+)"
            r"(?:\.(?P<decimal>\d+))?"
            r"(?P<suffix>\s*[kKmM])?"
            r"(?!\w)"
        )
    }

    # --------------------------------------------------------
    # 2.4 INITIALIZE THE EXTRACTOR
    # --------------------------------------------------------

    def __init__(self, amenities=None):
        """
        Prepare amenity patterns for repeated extraction.
        """

        # Use the default Week 3 amenities unless
        # a different taxonomy is provided.
        if amenities is None:
            amenities = self.DEFAULT_AMENITIES

        # Compile the patterns once to improve efficiency.
        self.amenity_patterns = {
            name: [
                re.compile(pattern, re.I)
                for pattern in patterns
            ]
            for name, patterns in amenities.items()
        }

    # --------------------------------------------------------
    # 2.5 NORMALIZE NUMERIC VALUES
    # --------------------------------------------------------

    @staticmethod
    def _numeric_value(kind, match):
        """
        Convert matched numeric text into standardized values.

        Examples:
        "three" -> 3
        "2 1/2" -> 2.5
        "½" -> 0.5
        "$1.5M" -> 1500000
        """

        # Get the number captured by the regular expression.
        raw_value = match.group("value").lower()

        # Remove commas.
        raw_value = raw_value.replace(",", "")

        # Convert Unicode fractions into a consistent format.
        #
        # "2½" becomes "2 1/2".
        # "½" becomes "1/2".
        raw_value = raw_value.replace("½", " 1/2").strip()

        # Handle written numbers.
        if raw_value in EntityExtractor.NUMBER_WORDS:

            value = float(
                EntityExtractor.NUMBER_WORDS[raw_value]
            )

        # Handle mixed fractions such as "2 1/2".
        elif " " in raw_value and "/" in raw_value:

            whole, fraction = raw_value.split()

            numerator, denominator = fraction.split("/")

            value = (
                float(whole)
                + float(numerator) / float(denominator)
            )

        # Handle fractions such as "1/2".
        elif "/" in raw_value:

            numerator, denominator = raw_value.split("/")

            value = float(numerator) / float(denominator)

        # Handle ordinary numbers and decimal values.
        else:

            # Include the decimal part of abbreviated prices.
            if kind == "price" and match.group("decimal"):
                raw_value += "." + match.group("decimal")

            value = float(raw_value)

        # Convert price abbreviations into full dollar amounts.
        if kind == "price":

            suffix = (
                match.group("suffix") or ""
            ).strip().lower()

            multiplier = {
                "k": 1_000,
                "m": 1_000_000
            }

            value *= multiplier.get(suffix, 1)

        # Return integers when there is no fractional part.
        return int(value) if value.is_integer() else value

    # --------------------------------------------------------
    # 2.6 DISTINGUISH LOT AREA FROM LIVING AREA
    # --------------------------------------------------------

    @staticmethod
    def _is_lot_sqft(text, start, end):
        """
        Identify square footage referring to land or lot area.

        Example:
        "8,300 square feet of land" should not be
        classified as indoor living area.
        """

        # Look at words immediately before and after the match.
        before = text[max(0, start - 50):start].lower()
        after = text[end:min(len(text), end + 45)].lower()

        # Detect land-related words after the measurement.
        if re.match(
            r"\s*[-–—]?\s*(?:of\s+)?"
            r"(?:(?:combined|usable|vacant|total)\s+)*"
            r"(?:lot|parcel|land|site)\b",
            after
        ):
            return True

        # Detect phrases such as "lot size of 8,300 square feet".
        if re.search(
            r"\b(?:lot|parcel|land|site)"
            r"(?:\s+\w+){0,4}\s*$",
            before
        ):
            return True

        # Detect phrases such as "6,201 sq ft lot".
        if re.match(
            r"\s*(?:on\s+)?"
            r"(?:a\s+|an\s+|the\s+|two\s+)?"
            r"(?:lot|parcels?|land)\b",
            after
        ):
            return True

        # Otherwise, allow the square-footage match.
        return False

    # --------------------------------------------------------
    # 2.7 HANDLE COMBINED BATHROOM COUNTS
    # --------------------------------------------------------

    def _extract_combined_bathrooms(self, text):
        """
        Identify full bathrooms and half bathrooms
        mentioned together.

        Example:
        "2 full bathrooms and 1/2 bath" -> 2.5
        """

        # Find a full-bathroom count followed by a half bath.
        pattern = re.compile(
            r"\b(?P<full>\d+)\s+full\s+bath(?:room)?s?"
            r"\s*(?:,|and|\+)\s*"
            r"(?:a\s+|one\s+)?"
            r"(?:1/2|½|half)"
            r"\s+bath(?:room)?s?\b",
            re.I
        )

        match = pattern.search(text)

        # If the pattern exists, combine the values.
        if match:
            return int(match.group("full")) + 0.5

        # None means this particular format was not found.
        return None

    # --------------------------------------------------------
    # 2.8 EXTRACT CHARACTER SPANS
    # --------------------------------------------------------

    def extract_spans(self, text):
        """
        Extract entities while retaining their exact text positions.

        A span contains:
        - start: starting character
        - end: ending character, exclusive
        - label: entity type
        - text: original matched text
        - value: normalized value
        """

        # Handle missing or invalid input.
        if not isinstance(text, str):
            text = "" if text is None else str(text)

        spans = []

        # Find numeric entities using Week 3 patterns.
        for label, pattern in self.PATTERNS.items():

            for match in pattern.finditer(text):

                # Ignore square footage identified as lot area.
                if label == "sqft" and self._is_lot_sqft(
                    text,
                    match.start(),
                    match.end()
                ):
                    continue

                # Store the numeric match.
                spans.append({
                    "start": match.start(),
                    "end": match.end(),
                    "label": label.upper(),
                    "text": match.group(),
                    "value": self._numeric_value(label, match)
                })

        # Find basic amenities.
        for name, patterns in self.amenity_patterns.items():

            for pattern in patterns:

                for match in pattern.finditer(text):

                    spans.append({
                        "start": match.start(),
                        "end": match.end(),
                        "label": "AMENITY",
                        "text": match.group(),
                        "value": name
                    })

        # Sort matches by their position in the description.
        spans.sort(
            key=lambda span: (
                span["start"],
                -(span["end"] - span["start"])
            )
        )

        # Remove overlapping matches.
        nonoverlapping = []

        for span in spans:

            if (
                not nonoverlapping
                or span["start"] >= nonoverlapping[-1]["end"]
            ):
                nonoverlapping.append(span)

        return nonoverlapping

    # --------------------------------------------------------
    # 2.9 EXTRACT ALL WEEK 3 ENTITIES
    # --------------------------------------------------------

    def extract_all(self, text):
        """
        Extract bedrooms, bathrooms, price, square footage,
        and basic amenity mentions.
        """

        # Prepare the output dictionary.
        result = {
            "bedrooms": None,
            "bathrooms": None,
            "price": None,
            "sqft": None,
            "amenities": []
        }

        # Make sure the input is text.
        if not isinstance(text, str):
            text = "" if text is None else str(text)

        # Extract numeric entities and amenities.
        for span in self.extract_spans(text):

            # Add basic amenities without duplicates.
            if span["label"] == "AMENITY":

                if span["value"] not in result["amenities"]:
                    result["amenities"].append(span["value"])

            else:

                # Convert labels such as BEDROOMS to bedrooms.
                key = span["label"].lower()

                # Use the first matched numeric value.
                if result[key] is None:
                    result[key] = span["value"]

        # Check for combined full and half bathroom counts.
        combined_bathrooms = self._extract_combined_bathrooms(text)

        if combined_bathrooms is not None:
            result["bathrooms"] = combined_bathrooms

        return result

    # --------------------------------------------------------
    # 2.10 INDIVIDUAL EXTRACTION METHODS
    # --------------------------------------------------------

    # These methods preserve the public interface
    # developed during Week 3.

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


# ============================================================
# SECTION 3: WEEK 6 SIGNAL TAXONOMY
# ============================================================

# A taxonomy groups different phrases under standard labels.
#
# Example:
# "in-ground pool" and "swimming pool" both become "pool".

SIGNAL_TAXONOMY = {

    # --------------------------------------------------------
    # 3.1 AMENITIES
    # --------------------------------------------------------

    "amenities": {

        "pool": [
            "pool", "pools", "swimming pool",
            "inground pool", "in-ground pool", "private pool"
        ],

        "garage": [
            "garage", "garages",
            "attached garage", "detached garage"
        ],

        "parking": [
            "parking", "carport", "covered parking"
        ],

        "fireplace": [
            "fireplace", "fireplaces",
            "gas fireplace", "wood-burning fireplace"
        ],

        "patio": [
            "patio", "patios", "covered patio"
        ],

        "deck": [
            "deck", "decks", "wooden deck"
        ],

        "balcony": [
            "balcony", "balconies"
        ],

        "solar": [
            "solar panels", "solar panel",
            "solar energy", "owned solar"
        ],

        "air_conditioning": [
            "central air",
            "central ac",
            "central a/c",
            "air conditioning",
            "a/c",
            "ac unit",
            "ac units",
            "central cooling",
            "cooling system"
        ],

        "laundry": [
            "laundry", "washer", "dryer", "washer and dryer"
        ],

        "updated_kitchen": [
            "updated kitchen",
            "renovated kitchen",
            "remodeled kitchen"
        ],

        "basement": [
            "basement", "finished basement",
            "walkout basement", "walk-out basement"
        ]
    },

    # --------------------------------------------------------
    # 3.2 PROPERTY CONDITION
    # --------------------------------------------------------

    "condition": {

        "renovated": [
            "renovated", "remodeled",
            "fully renovated", "recently renovated"
        ],

        "updated": [
            "updated", "recently updated", "upgraded"
        ],

        "new_construction": [
            "new construction", "newly built",
            "brand new home", "new build"
        ],

        "move_in_ready": [
            "move-in ready", "move in ready", "turnkey"
        ],

        "fixer_upper": [
            "fixer upper", "fixer-upper",
            "needs renovation", "needs repairs",
            "needs tlc", "handyman special"
        ]
    },

    # --------------------------------------------------------
    # 3.3 FINANCING
    # --------------------------------------------------------

    "financing": {

        "seller_financing": [
            "seller financing", "owner financing",
            "seller will finance", "owner will finance",
            "seller may finance", "owner may finance",
            "seller carry", "seller carryback", "owner carry"
        ],

        "assumable_mortgage": [
            "assumable mortgage", "assumable loan"
        ],

        "cash_only": [
            "cash only", "cash buyers only",
            "cash offers only"
        ],

        "lease_to_own": [
            "lease to own", "rent to own",
            "lease-to-own", "rent-to-own"
        ]
    },

    # --------------------------------------------------------
    # 3.4 LOCATION
    # --------------------------------------------------------

    "location": {

        "waterfront": [
            "waterfront", "lakefront", "riverfront",
            "water front", "lake front",
            "oceanfront", "beachfront"
        ],

        "cul_de_sac": [
            "cul-de-sac", "cul de sac", "culdesac"
        ],

        "near_schools": [
            "near schools", "near school",
            "close to schools", "close to school",
            "walking distance to school",
            "minutes from schools", "nearby schools"
        ],

        "near_parks": [
            "near parks", "near park",
            "close to parks", "close to park",
            "walking distance to park",
            "minutes from parks", "nearby parks"
        ],

        "corner_lot": [
            "corner lot"
        ],

        "gated_community": [
            "gated community", "gated neighborhood",
            "gated development"
        ],

        "near_shopping": [
            "near shopping", "close to shopping",
            "walking distance to shops",
            "near shops", "close to shops",
            "near boutiques", "close to boutiques",
            "near retail", "close to retail",
            "near shopping centers", "minutes from shopping"
        ]
    }
}


# ============================================================
# SECTION 4: WEEK 6 SIGNAL EXTRACTOR
# ============================================================

class SignalExtractor:
    """
    Combine Week 3 entities with Week 6 taxonomy signals.

    The Week 3 extractor handles entity recognition.

    This class handles:
    - Expanded keyword matching
    - Negation
    - Location proximity
    - Combining results into a single record
    """

    # --------------------------------------------------------
    # 4.1 INITIALIZE THE EXTRACTOR
    # --------------------------------------------------------

    def __init__(self, taxonomy, entity_extractor):

        # Store the signal taxonomy.
        self.taxonomy = taxonomy

        # Store the existing Week 3 extractor.
        #
        # We will call its extract_all() and extract_spans()
        # methods instead of duplicating their logic.
        self.extractor = entity_extractor

        # Compile all taxonomy phrases into regex patterns.
        #
        # Compiling once saves work when processing
        # thousands of listing descriptions.
        self.category_patterns = {

            category: {

                signal: [
                    re.compile(
                        r"(?<!\w)"
                        + re.escape(phrase)
                        + r"(?!\w)",
                        re.I
                    )
                    for phrase in phrases
                ]

                for signal, phrases in signals.items()
            }

            for category, signals in taxonomy.items()
        }

    # --------------------------------------------------------
    # 4.2 PREPARE LISTING TEXT
    # --------------------------------------------------------

    @staticmethod
    def _prepare_text(remarks):
        """
        Convert missing listing remarks into safe text.
        """

        # Handle None values.
        if remarks is None:
            return ""

        # Handle floating-point NaN values.
        if isinstance(remarks, float) and remarks != remarks:
            return ""

        return str(remarks)

    # --------------------------------------------------------
    # 4.3 IDENTIFY NEGATED FEATURES
    # --------------------------------------------------------

    @staticmethod
    def _is_negated(text, start, end):
        """
        Check whether a feature is described as absent.

        Examples:
        "No pool" -> negative
        "No swimming pool or garage" -> both negative
        "Without a patio or balcony" -> both negative
        "A pool is not included" -> negative

        This is a rule-based approximation, not a full
        grammatical understanding of negation.
        """

        # Examine the text before the feature.
        before = text[max(0, start - 120):start]

        # Examine the text after the feature.
        after = text[end:min(len(text), end + 45)]

        # A sentence may switch from a negative statement
        # to a positive statement using words like "but".
        #
        # Example:
        # "No pool, but a garage is available."
        #
        # We only inspect the part after the most recent
        # sentence boundary or contrast word.
        segments = re.split(
            r"[.!?;\n]|\b(?:but|however|although)\b",
            before,
            flags=re.I
        )

        current_segment = segments[-1].strip()

        # Detect direct negatives such as "no pool".
        direct_negative = re.search(
            r"\b(?:no|without|lacks|does not have|"
            r"doesn't have|not equipped with)"
            r"\s+(?:(?:a|an|any|private|shared|existing)\s+)*$",
            current_segment,
            re.I
        )

        # Detect negatives applying to multiple features.
        #
        # Examples:
        # "No swimming pool or garage"
        # "Without a patio or balcony"
        #
        # The negative must appear in the current clause.
        list_negative = re.search(
            r"\b(?:no|without)\s+"
            r"[^.!?;\n]{0,100}"
            r"(?:\s+or\s+|\s+and\s+|,\s*)"
            r"(?:(?:a|an|any)\s+)*$",
            current_segment,
            re.I
        )

        # Detect negative statements following the feature.
        #
        # Examples:
        # "Pool not included"
        # "Seller financing is not available"
        after_negative = re.match(
            r"\s+(?:is\s+|are\s+)?"
            r"(?:not\s+(?:included|available|permitted|offered)"
            r"|unavailable)\b",
            after,
            re.I
        )

        # Return True if any negative rule matches.
        return bool(
            direct_negative
            or list_negative
            or after_negative
        )

    # --------------------------------------------------------
    # 4.4 MATCH TAXONOMY SIGNALS
    # --------------------------------------------------------

    def _match_category(self, remarks, category):
        """
        Search for standardized signals in one category.

        Examples:
        "Swimming pool" -> pool
        "Recently renovated" -> renovated
        "Seller may finance" -> seller_financing
        """

        # Prepare the property description.
        text = self._prepare_text(remarks)

        # Store detected signals without duplicates.
        found = []

        # Retrieve patterns for the requested category.
        category_patterns = self.category_patterns.get(
            category, {}
        )

        # Examine each standardized signal.
        for signal, patterns in category_patterns.items():

            # Keep track of whether this signal has been found.
            signal_found = False

            # Examine each phrase associated with the signal.
            for pattern in patterns:

                # Search for every occurrence of this phrase.
                for match in pattern.finditer(text):

                    # Ignore mentions that are explicitly negative.
                    if self._is_negated(
                        text,
                        match.start(),
                        match.end()
                    ):
                        continue

                    # A positive mention was found.
                    signal_found = True

                    # No need to examine more occurrences.
                    break

                if signal_found:
                    break

            # Add the signal only when it has a positive match.
            if signal_found:
                found.append(signal)

        return found

    # --------------------------------------------------------
    # 4.5 EXTRACT MULTIPLE NEARBY LOCATION FEATURES
    # --------------------------------------------------------

    def _extract_proximity(self, remarks):
        """
        Recognize nearby places in natural-language lists.

        Examples:
        "Near shopping, schools, and parks"
        "Minutes from parks, schools, and shopping"
        "Close to boutiques and restaurants"

        One proximity phrase may apply to multiple features.
        """

        # Prepare the listing description.
        text = self._prepare_text(remarks)

        # Store location signals found through proximity rules.
        found = []

        # Recognize words and phrases indicating proximity.
        #
        # The match continues until a sentence boundary.
        # This helps detect multiple features within a list.
        proximity_pattern = re.compile(
            r"\b(?:near|nearby|close to|"
            r"minutes from|moments from|"
            r"walking distance to|"
            r"within walking distance of|"
            r"proximity to|short distance from|"
            r"conveniently located near)\b"
            r"\s+(?P<features>[^.!?;\n]+)",
            re.I
        )

        # These keywords represent nearby location categories.
        feature_keywords = {

            "near_schools": [
                "school",
                "schools",
                "elementary school",
                "high school",
                "school campus"
            ],

            "near_parks": [
                "park",
                "parks",
                "playground",
                "playgrounds",
                "recreation area"
            ],

            "near_shopping": [
                "shopping",
                "shops",
                "stores",
                "boutiques",
                "retail",
                "shopping center",
                "shopping mall"
            ]
        }

        # Find each proximity phrase in the description.
        for match in proximity_pattern.finditer(text):

            # Extract the nearby feature list.
            nearby_text = match.group("features")

            # Stop when the sentence shifts to a contrasting idea.
            #
            # Example:
            # "Near schools, but the home has no garage."
            nearby_text = re.split(
                r"\b(?:but|however|although)\b",
                nearby_text,
                maxsplit=1,
                flags=re.I
            )[0]

            # Identify every location category in the phrase.
            for signal, keywords in feature_keywords.items():

                for keyword in keywords:

                    # Match whole words instead of substrings.
                    keyword_pattern = (
                        r"(?<!\w)"
                        + re.escape(keyword)
                        + r"(?!\w)"
                    )

                    # Search for the nearby feature.
                    if re.search(
                        keyword_pattern,
                        nearby_text,
                        re.I
                    ):

                        # Add each standardized signal once.
                        if signal not in found:
                            found.append(signal)

                        break

        return found

    # --------------------------------------------------------
    # 4.6 EXTRACT AMENITIES
    # --------------------------------------------------------

    def _match_amenities(self, remarks):
        """
        Identify amenities through the Week 6 taxonomy.
        """

        return self._match_category(remarks, "amenities")

    # --------------------------------------------------------
    # 4.7 EXTRACT CONDITION
    # --------------------------------------------------------

    def _extract_condition(self, remarks):
        """
        Identify condition-related keywords.
        """

        return self._match_category(remarks, "condition")

    # --------------------------------------------------------
    # 4.8 EXTRACT FINANCING
    # --------------------------------------------------------

    def _extract_financing(self, remarks):
        """
        Identify financing-related keywords.
        """

        return self._match_category(remarks, "financing")

    # --------------------------------------------------------
    # 4.9 EXTRACT LOCATION
    # --------------------------------------------------------

    def _extract_location(self, remarks):
        """
        Combine location taxonomy matching with proximity rules.
        """

        # Identify explicitly mentioned location features.
        taxonomy_location = self._match_category(
            remarks,
            "location"
        )

        # Detect location features in shared proximity phrases.
        proximity_location = self._extract_proximity(remarks)

        # Combine both methods without duplicate labels.
        return list(dict.fromkeys(
            taxonomy_location + proximity_location
        ))

    # --------------------------------------------------------
    # 4.10 EXTRACT POSITIVE WEEK 3 AMENITIES
    # --------------------------------------------------------

    def _positive_week3_amenities(self, remarks):
        """
        Reuse Week 3 amenity spans, but remove negated mentions.

        Week 3 identifies the words and character positions.
        Week 6 determines whether the amenity is present.

        Example:
        "No swimming pool or garage" -> []
        """

        # Retrieve all Week 3 entity spans.
        spans = self.extractor.extract_spans(remarks)

        # Store positive amenities.
        amenities = []

        # Examine all extracted spans.
        for span in spans:

            # Only process amenity spans.
            if span["label"] != "AMENITY":
                continue

            # Check whether this particular mention is negative.
            if self._is_negated(
                remarks,
                span["start"],
                span["end"]
            ):
                continue

            # Add the amenity if it was not already recorded.
            if span["value"] not in amenities:
                amenities.append(span["value"])

        return amenities

    # --------------------------------------------------------
    # 4.11 EXTRACT ALL LISTING SIGNALS
    # --------------------------------------------------------

    def extract_signals(self, listing_record):
        """
        Process one listing record.

        Input:
            A dictionary containing L_ListingID and L_Remarks.

        Output:
            A JSON-compatible dictionary containing:
            - listing_id
            - entities
            - amenities
            - condition_keywords
            - financing_terms
            - location_features
        """

        # Get the unique property listing ID.
        listing_id = listing_record["L_ListingID"]

        # Retrieve and prepare the listing description.
        remarks = self._prepare_text(
            listing_record.get("L_Remarks", "")
        )

        # STEP 1: CALL THE WEEK 3 ENTITY EXTRACTOR.
        #
        # This is where we reuse the existing Week 3 class.
        #
        # It extracts bedrooms, bathrooms, price,
        # square footage, and basic amenity mentions.
        entities = self.extractor.extract_all(remarks)

        # STEP 2: GET POSITIVE WEEK 3 AMENITIES.
        #
        # Use the character positions extracted in Week 3
        # and exclude negatively described features.
        week3_amenities = self._positive_week3_amenities(
            remarks
        )

        # STEP 3: GET EXPANDED WEEK 6 AMENITIES.
        #
        # These patterns recognize additional expressions
        # such as "central AC" and "owned solar".
        week6_amenities = self._match_amenities(remarks)

        # STEP 4: COMBINE AMENITIES.
        #
        # Remove duplicates while preserving original order.
        amenities = list(dict.fromkeys(
            week3_amenities + week6_amenities
        ))

        # STEP 5: UPDATE THE AMENITIES INSIDE WEEK 3 ENTITIES.
        #
        # The original Week 3 method may detect negative mentions.
        # We replace those raw mentions with the cleaned list.
        #
        # This ensures entities["amenities"] and the top-level
        # amenities field contain the same standardized features.
        entities["amenities"] = amenities.copy()

        # STEP 6: EXTRACT ADDITIONAL WEEK 6 SIGNALS.
        condition = self._extract_condition(remarks)

        financing = self._extract_financing(remarks)

        location = self._extract_location(remarks)

        # STEP 7: CREATE THE FINAL STRUCTURED RECORD.
        result = {
            "listing_id": listing_id,
            "entities": entities,
            "amenities": amenities,
            "condition_keywords": condition,
            "financing_terms": financing,
            "location_features": location
        }

        # Return the complete result.
        return result
