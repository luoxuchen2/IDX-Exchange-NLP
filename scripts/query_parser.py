"""Rule-based natural-language real estate query parser and safe SQL compiler."""
import re
from typing import Any, Mapping


class QueryParser:
    """Parse listing queries without executing SQL or trusting user-controlled identifiers."""

    AMENITIES = {
        'pool': (r'pool|swimming pool',),
        'garage': (r'garage|parking garage',),
        'parking': (r'parking|parking space',),
        'yard': (r'yard|backyard|garden',),
        'fireplace': (r'fireplace',),
        'balcony': (r'balcony',),
        'patio': (r'patio',),
        'solar': (r'solar(?: panels)?',),
        'air conditioning': (r'air conditioning|central air|a/c',),
        'view': (r'(?:ocean|mountain|city) view|view',),
        'laundry': (r'laundry|washer(?:/dryer)?',),
    }

    # Identifiers here are developer-controlled, never composed from user input.
    DEFAULT_COLUMNS = {
        'price': 'L_SystemPrice',
        'bedrooms': 'L_Keyword2',
        'bathrooms': 'L_Keyword3',  # VERIFY against the actual rets_property schema
        'city': 'L_City',          # VERIFY against the actual rets_property schema
        'remarks': 'L_Remarks',    # VERIFY against the actual rets_property schema
    }

    def __init__(self, cities=None, columns=None):
        self.cities = sorted(set(cities or []), key=len, reverse=True)
        self.columns = dict(self.DEFAULT_COLUMNS)
        if columns is not None:
            expected = set(self.DEFAULT_COLUMNS)
            if set(columns) != expected:
                raise ValueError(f'Column mapping must contain exactly: {sorted(expected)}')
            for value in columns.values():
                if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
                    raise ValueError('Unsafe SQL identifier in column mapping')
            self.columns = dict(columns)

    @staticmethod
    def _number(value: str) -> int:
        clean = value.replace(',', '').replace('$', '').replace(' ', '').lower()
        m = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(k|m|million|thousand)?', clean)
        if not m:
            raise ValueError(f'Invalid number: {value}')
        multiplier = {'k': 1000, 'thousand': 1000, 'm': 1000000, 'million': 1000000}.get(m.group(2), 1)
        return int(float(m.group(1)) * multiplier)

    def parse(self, query: str) -> dict[str, Any]:
        if not isinstance(query, str):
            raise TypeError('Query must be a string')
        q = re.sub(r'\s+', ' ', query.strip())
        result: dict[str, Any] = {}
        number = r'\$?\d[\d,]*(?:\.\d+)?\s*(?:million|thousand|[km])?'
        price_context = r'(?:price|priced|cost|budget|homes?|houses?|properties?|listings?)'

        between = re.search(rf'\bbetween\s+({number})\s+(?:and|to)\s+({number})', q, re.I)
        from_to = re.search(rf'\bfrom\s+({number})\s+to\s+({number})', q, re.I)
        if between or from_to:
            m = between or from_to
            result['price_min'] = self._number(m.group(1))
            result['price_max'] = self._number(m.group(2))
        else:
            # 'under 700k', 'below $700,000', 'max price 700k', 'budget of 700k'
            upper = re.search(rf'\b(?:under|below|less than|up to|at most|no more than|cheaper than)\s*({number})', q, re.I)
            upper = upper or re.search(rf'\b(?:max(?:imum)?\s*price|budget(?:\s+of)?|{price_context}\s+under)\s*[:=]?\s*({number})', q, re.I)
            lower = re.search(rf'\b(?:over|above|more than|at least|starting at|no less than)\s*({number})', q, re.I)
            lower = lower or re.search(rf'\bmin(?:imum)?\s*price\s*[:=]?\s*({number})', q, re.I)
            for m, key in ((upper, 'price_max'), (lower, 'price_min')):
                if m:
                    num = self._number(m.group(1))
                    # Ignore bare small counts in expressions like 'at least 3 beds'.
                    if num >= 1000 or re.search(r'\$|\b(?:price|budget)\b', m.group(0), re.I):
                        result[key] = num

        kinds = {'bedrooms': r'bedrooms?|beds?|br', 'bathrooms': r'bathrooms?|baths?|ba'}
        for field, word in kinds.items():
            # Phrases with the quantity before the type.
            m = re.search(rf'\b(at least|minimum|min|over|more than|up to|at most|max|under|no more than)?\s*(\d+(?:\.5)?)\s*(\+)?\s*(?:{word})\b', q, re.I)
            # Phrases with the type before the quantity.
            if not m:
                inverted = re.search(rf'\b({word})\s*(?:of|:|=|at least|minimum|min|max|up to)?\s*(\d+(?:\.5)?)\s*(\+)?\b', q, re.I)
                if inverted:
                    prefix = q[max(0, inverted.start()-18):inverted.start()].lower()
                    mode = 'at least' if re.search(r'at least|min(?:imum)?\s*$', prefix) else ''
                    val = float(inverted.group(1)) if inverted.group(1).replace('.','',1).isdigit() else float(inverted.group(2))
                    result[field + ('_min' if inverted.group(3) or mode else '')] = int(val) if val.is_integer() else val
                continue
            val = float(m.group(2))
            prefix = (m.group(1) or '').lower()
            if m.group(3) or prefix in ('at least', 'minimum', 'min', 'over', 'more than'):
                key = field + '_min'
            elif prefix in ('up to', 'at most', 'max', 'under', 'no more than'):
                key = field + '_max'
            else:
                key = field
            result[key] = int(val) if val.is_integer() else val

        # Match from an allowlist; fallback extracts possible unknown cities for validation.
        for city in self.cities:
            if re.search(r'(?<!\w)' + re.escape(city) + r'(?!\w)', q, re.I):
                result['city'] = city
                break
        if 'city' not in result:
            city_match = re.search(r'\b(?:in|near|around)\s+([A-Za-z][A-Za-z .\'-]*?)(?=\s+(?:with|without|under|below|over|above|between|at least|up to|no|and\s+\d|\d|for\s+under)\b|[,.;!?]|$)', q, re.I)
            if city_match:
                result['city'] = city_match.group(1).strip()

        include, exclude = [], []
        for amenity, patterns in self.AMENITIES.items():
            pattern = r'(?:' + '|'.join(patterns) + r')'
            matches = list(re.finditer(r'(?<!\w)' + pattern + r'(?!\w)', q, re.I))
            for hit in matches:
                prefix = q[max(0, hit.start()-22):hit.start()]
                negated = bool(re.search(r'\b(?:without|no|exclude|excluding|not|avoid)\s+(?:a\s+|an\s+|any\s+)?$', prefix, re.I))
                bucket = exclude if negated else include
                if amenity not in bucket:
                    bucket.append(amenity)
        if include:
            result['amenities'] = include
        if exclude:
            result['exclude_amenities'] = exclude
        return result

    def to_sql(self, filters: Mapping[str, Any], validator=None) -> tuple[str, tuple[Any, ...]]:
        """Return SQL and bind parameters, never execute raw user text as SQL."""
        if validator is None:
            raise ValueError('A SchemaValidator is required before SQL generation')
        valid, errors = validator.validate_query(filters)
        if not valid:
            raise ValueError('; '.join(errors))
        clauses, params = [], []
        for filter_key, col_key, op in (
            ('price_min', 'price', '>='), ('price_max', 'price', '<='),
            ('bedrooms', 'bedrooms', '='), ('bedrooms_min', 'bedrooms', '>='), ('bedrooms_max', 'bedrooms', '<='),
            ('bathrooms', 'bathrooms', '='), ('bathrooms_min', 'bathrooms', '>='), ('bathrooms_max', 'bathrooms', '<='),
            ('city', 'city', '='),
        ):
            if filter_key in filters:
                clauses.append(f'{self.columns[col_key]} {op} %s')
                params.append(filters[filter_key])
        for key, op in (('amenities', 'LIKE'), ('exclude_amenities', 'NOT LIKE')):
            for amenity in filters.get(key, []):
                clauses.append(f'{self.columns["remarks"]} {op} %s')
                # LIKE metacharacters are escaped in addition to SQL parameterization.
                literal = amenity.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                params.append('%' + literal + '%')
        sql = 'SELECT * FROM rets_property'
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        return sql, tuple(params)
