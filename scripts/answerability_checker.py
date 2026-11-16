import re

import nltk
import pandas as pd
class AnswerabilityChecker:
    def __init__(self, parser, schema_validator, taxonomy):
        self.parser = parser
        self.validator = schema_validator
        self.taxonomy = taxonomy

    def parse_request(self, query):
        """Parse once and pass the same filters to validation and search."""
        return self.parser.parse(query)

    def check_pre_query(self, query, filters=None):
        if not isinstance(query, str) or not query.strip():
            return False, "Enter a listing search to get started."

        if filters is None:
            filters = self.parse_request(query)

        for phrase, filter_key in self.taxonomy.items():
            mentioned = re.search(
                rf"(?<!\w){re.escape(phrase)}(?!\w)", query, re.IGNORECASE
            )
            if mentioned and filters.get(filter_key) is None:
                return False, f"I couldn't apply the requested criterion: {phrase}."

        if not filters:
            return False, "I couldn't identify a supported listing search."

        valid, errors = self.validator.validate_query(filters)
        if not valid:
            return False, "I couldn't apply these filters: " + ", ".join(
                map(str, errors)
            )

        return True, "The search can run."

    def check_post_query(self, query, results_df, requested_columns=()):
        if len(results_df.index) == 0:
            return False, "No listings matched your criteria."

        missing_columns = [
            column
            for column in requested_columns
            if column not in results_df or results_df[column].isna().all()
        ]
        if missing_columns:
            fields = ", ".join(column.replace("_", " ") for column in missing_columns)
            return False, f"I found matching listings, but these fields are unavailable: {fields}."

        if results_df.isna().all().all():
            return False, "The matching listings have no returned data."

        return True, "Results found."


def search_listings(query, checker, fetch_listings, requested_columns=()):
    """fetch_listings takes validated Week 4 filters and returns a DataFrame."""
    filters = checker.parse_request(query) if isinstance(query, str) and query.strip() else {}
    answerable, message = checker.check_pre_query(query, filters)
    if not answerable:
        return {"answerable": False, "message": message, "results": []}

    results = fetch_listings(filters)
    answerable, message = checker.check_post_query(query, results, requested_columns)

    return {
        "answerable": answerable,
        "message": message,
        "results": results.to_dict("records") if answerable else [],
    }