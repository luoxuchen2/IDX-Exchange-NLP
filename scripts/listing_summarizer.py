import re

import nltk
import pandas as pd


class ListingSummarizer:
    @staticmethod
    def _sentences(remarks):
        """Split the original listing remarks into sentences."""
        if not isinstance(remarks, str) or not remarks.strip():
            return []
        return nltk.sent_tokenize(remarks.strip())

    @staticmethod
    def _features(entities):
        """Keep the first two distinct features from the listing data."""
        raw_features = entities.get("features")
        if not isinstance(raw_features, (list, tuple)):
            return []

        features = []
        seen = set()

        for raw_feature in raw_features:
            if not isinstance(raw_feature, str):
                continue

            feature = raw_feature.replace("_", " ").strip().rstrip(".")
            if feature.casefold() == "cul de sac":
                feature = "cul-de-sac"

            key = feature.casefold()
            if feature and key not in seen:
                features.append(feature)
                seen.add(key)

            if len(features) == 2:
                break

        return features

    @staticmethod
    def _mentions(sentence, feature):
        """Check whether a sentence contains the feature phrase."""
        return bool(
            re.search(
                rf"(?<!\w){re.escape(feature)}(?!\w)",
                sentence,
                flags=re.IGNORECASE,
            )
        )

    def _features_from_listing(self, remarks, entities):
        """Fill open feature slots with details found in the remarks."""
        features = self._features(entities)
        if len(features) == 2 or not isinstance(remarks, str):
            return features

        patterns = [
            (
                r"\bviews? of the city\b[^.!?]*\bcoastline\b",
                "city and coastline views",
            ),
            (r"\bwalk[- ]in closet\b", "walk-in closet"),
        ]

        seen = {feature.casefold() for feature in features}
        for pattern, label in patterns:
            if label.casefold() not in seen and re.search(
                pattern, remarks, flags=re.IGNORECASE
            ):
                features.append(label)
                seen.add(label.casefold())
            if len(features) == 2:
                break

        return features

    def extractive_summary(self, remarks, entities, num_sentences=2):
        """Select original remarks sentences and preserve their order."""
        sentences = self._sentences(remarks)
        features = self._features_from_listing(remarks, entities)

        def rank(index):
            matches = sum(
                self._mentions(sentences[index], feature)
                for feature in features
            )
            return -matches, index

        selected = sorted(range(len(sentences)), key=rank)[:num_sentences]
        return " ".join(sentences[index] for index in sorted(selected))

    def summarize(self, remarks, entities):
        """Combine available listing facts with up to two features."""
        facts = []

        for field, label in (("bedrooms", "bed"), ("bathrooms", "bath")):
            value = entities.get(field)
            if pd.notna(value) and str(value).strip():
                number = float(value)
                plural = "" if number == 1 else "s"
                facts.append(f"{number:g} {label}{plural}")

        location = entities.get("location")
        if pd.notna(location) and str(location).strip():
            facts.append(str(location).strip())

        price = entities.get("price")
        if pd.notna(price) and str(price).strip():
            amount = float(str(price).replace("$", "").replace(",", ""))
            formatted_price = f"${amount:,.2f}".removesuffix(".00")
            facts.append(f"listed at {formatted_price}")

        # Start with the structured facts when they are available.
        summary = [f"The listing shows {', '.join(facts)}."] if facts else []

        features = self._features_from_listing(remarks, entities)
        if features:
            summary.append(f"Features include {' and '.join(features)}.")
            if not facts:
                excerpt = self.extractive_summary(remarks, entities, num_sentences=1)
                if excerpt:
                    summary.insert(0, excerpt)
        else:
            # Use original remarks when no feature phrases are available.
            excerpt = self.extractive_summary(remarks, entities)
            if excerpt:
                summary.append(excerpt)

        return " ".join(summary)
