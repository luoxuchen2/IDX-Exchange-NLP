"""Validate parsed filters against a curated snapshot of database constraints."""
import json
from pathlib import Path


class SchemaValidator:
    ALLOWED = frozenset({
        'price_min', 'price_max', 'bedrooms', 'bedrooms_min', 'bedrooms_max',
        'bathrooms', 'bathrooms_min', 'bathrooms_max', 'city',
        'amenities', 'exclude_amenities',
    })

    def __init__(self, schema_path='data/schema.json'):
        with open(schema_path, encoding='utf-8') as handle:
            self.schema = json.load(handle)
        self.valid_cities = {city.casefold(): city for city in self.schema['valid_cities']}
        self.price_min = self.schema.get('price_min', 100000)
        self.price_max = self.schema.get('price_max', 10000000)
        self.bedrooms_max = self.schema.get('bedrooms_max', 10)
        self.bathrooms_max = self.schema.get('bathrooms_max', 15)
        from scripts.query_parser import QueryParser
        self.amenities = set(QueryParser.AMENITIES)

    def validate_query(self, filters):
        errors = []
        if not isinstance(filters, dict):
            return False, ['Filters must be a dictionary']
        for key in filters:
            if key not in self.ALLOWED:
                errors.append(f'Unsupported filter: {key}')
        for key in ('price_min', 'price_max'):
            if key in filters:
                value = filters[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not self.price_min <= value <= self.price_max:
                    errors.append(f'{key} outside allowed range {self.price_min}–{self.price_max}')
        for base, max_allowed in (('bedrooms', self.bedrooms_max), ('bathrooms', self.bathrooms_max)):
            for key in (base, base + '_min', base + '_max'):
                if key in filters:
                    val = filters[key]
                    # Half baths are permitted; fractional bedrooms aren't.
                    allowed_step = 0.5 if base == 'bathrooms' else 1
                    if (isinstance(val, bool) or not isinstance(val, (float, int)) or not 0 <= val <= max_allowed or val % allowed_step):
                        errors.append(f'{key} must be 0–{max_allowed} in increments of {allowed_step}')
        if 'city' in filters:
            city = filters['city']
            if not isinstance(city, str) or city.strip().casefold() not in self.valid_cities:
                errors.append(f"City {city!r} not found in database city list")
        for key in ('amenities', 'exclude_amenities'):
            if key in filters:
                entries = filters[key]
                if not isinstance(entries, list) or any(not isinstance(a, str) or a not in self.amenities for a in entries):
                    errors.append(f'{key} contains invalid amenities')
        for lo, hi in (('price_min', 'price_max'), ('bedrooms_min', 'bedrooms_max'), ('bathrooms_min', 'bathrooms_max')):
            if lo in filters and hi in filters and isinstance(filters[lo], (int, float)) and isinstance(filters[hi], (int, float)) and filters[lo] > filters[hi]:
                errors.append(f'{lo} exceeds {hi}')
        for field in ('bedrooms', 'bathrooms'):
            if field in filters and (field + '_min' in filters or field + '_max' in filters):
                errors.append(f'Cannot combine exact {field} with a range for the same field')
        for amenity in set(filters.get('amenities', []) if isinstance(filters.get('amenities', []), list) else []):
            if amenity in filters.get('exclude_amenities', []):
                errors.append(f'{amenity} cannot be both required and excluded')
        return not errors, errors
