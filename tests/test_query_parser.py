import pytest
from scripts.query_parser import QueryParser
from scripts.schema_validator import SchemaValidator

@pytest.fixture
def parser():
    return QueryParser(cities=SchemaValidator('data/schema.json').schema['valid_cities'])

# 55 varied natural-language examples (some test a selected key rather than entire dict).
CASES = [
    ('3 bed under 700k in Irvine', 'bedrooms', 3),
    ('3 beds', 'bedrooms', 3),
    ('3br', 'bedrooms', 3),
    ('3 bedrooms', 'bedrooms', 3),
    ('3+ beds', 'bedrooms_min', 3),
    ('at least 3 beds', 'bedrooms_min', 3),
    ('min 4 bed', 'bedrooms_min', 4),
    ('up to 5 bedrooms', 'bedrooms_max', 5),
    ('max 2 beds', 'bedrooms_max', 2),
    ('2 bath', 'bathrooms', 2),
    ('2ba', 'bathrooms', 2),
    ('2 bathrooms', 'bathrooms', 2),
    ('2+ bath', 'bathrooms_min', 2),
    ('at least 2 bath', 'bathrooms_min', 2),
    ('3.5 baths', 'bathrooms', 3.5),
    ('under $700k', 'price_max', 700000),
    ('under 700k', 'price_max', 700000),
    ('under $700,000', 'price_max', 700000),
    ('below 700000', 'price_max', 700000),
    ('less than 700k', 'price_max', 700000),
    ('up to 700k', 'price_max', 700000),
    ('at most $700k', 'price_max', 700000),
    ('no more than 700k', 'price_max', 700000),
    ('max price 700k', 'price_max', 700000),
    ('budget of 700k', 'price_max', 700000),
    ('under 0.7m', 'price_max', 700000),
    ('under 1 million', 'price_max', 1000000),
    ('over 500k', 'price_min', 500000),
    ('above $500,000', 'price_min', 500000),
    ('at least 500k', 'price_min', 500000),
    ('starting at 500k', 'price_min', 500000),
    ('min price $600k', 'price_min', 600000),
    ('between 400k and 700k', 'price_min', 400000),
    ('between $400,000 and $700,000', 'price_max', 700000),
    ('from 400k to 800k', 'price_max', 800000),
    ('in Irvine', 'city', 'Irvine'),
    ('in Los Angeles', 'city', 'Los Angeles'),
    ('near Newport Beach', 'city', 'Newport Beach'),
    ('around Tustin', 'city', 'Tustin'),
    ('in San Diego under 800k', 'city', 'San Diego'),
    ('in Portland with pool', 'city', 'Portland'),
    ('with a pool', 'amenities', ['pool']),
    ('swimming pool', 'amenities', ['pool']),
    ('with garage', 'amenities', ['garage']),
    ('with parking', 'amenities', ['parking']),
    ('with a backyard', 'amenities', ['yard']),
    ('with fireplace', 'amenities', ['fireplace']),
    ('with balcony', 'amenities', ['balcony']),
    ('with patio', 'amenities', ['patio']),
    ('with solar panels', 'amenities', ['solar']),
    ('with air conditioning', 'amenities', ['air conditioning']),
    ('ocean view', 'amenities', ['view']),
    ('without pool', 'exclude_amenities', ['pool']),
    ('no garage', 'exclude_amenities', ['garage']),
    ('exclude fireplace', 'exclude_amenities', ['fireplace']),
    ('3 bed under 700k in Irvine with pool', 'price_max', 700000),
]

@pytest.mark.parametrize('query,key,expected', CASES)
def test_parse_patterns(parser, query, key, expected):
    assert parser.parse(query).get(key) == expected, (query, parser.parse(query))

@pytest.mark.parametrize('query,valid', [
    ('3 bed in Irvine under 700k', True),
    ('5 bed in Atlantis under 700k', False),
    ('12 bedrooms in Irvine', False),
    ('under 20m in Irvine', False),
    ('under 50k in Irvine', False),
    ('between 800k and 500k in Irvine', False),
    ('2 bath in Irvine', True),
])
def test_validation(parser, query, valid):
    validator = SchemaValidator('data/schema.json')
    assert validator.validate_query(parser.parse(query))[0] is valid

@pytest.mark.parametrize('text', [
    "Irvine' OR 1=1 --", "' ; DROP TABLE rets_property; --", "Irvine%", "Irvine_"
])
def test_sql_injection_in_city_is_not_executable(parser, text):
    validator = SchemaValidator('data/schema.json')
    with pytest.raises(ValueError):
        parser.to_sql({'city': text}, validator)


def test_parameterized_query(parser):
    sql, params = parser.to_sql(parser.parse('3 bed in Irvine under 700k with pool'), SchemaValidator('data/schema.json'))
    assert sql.count('%s') == len(params) == 4
    assert '700000' not in sql and 'Irvine' not in sql
    assert params == (700000, 3, 'Irvine', '%pool%')


def test_parameterized_valid_city_not_in_sql(parser):
    sql, params = parser.to_sql({'city': 'Irvine'}, SchemaValidator('data/schema.json'))
    assert 'Irvine' not in sql and params == ('Irvine',)


def test_reject_unsafe_filters(parser):
    with pytest.raises(ValueError):
        parser.to_sql({'city; DROP TABLE users': 'Irvine'}, SchemaValidator('data/schema.json'))


def test_reject_unsafe_column_identifiers():
    columns = QueryParser.DEFAULT_COLUMNS.copy()
    columns['city'] = 'L_City; DROP TABLE users'
    with pytest.raises(ValueError):
        QueryParser(columns=columns)


def test_sql_no_filters_requires_validation(parser):
    with pytest.raises(ValueError):
        parser.to_sql({})
    sql, params = parser.to_sql({}, SchemaValidator('data/schema.json'))
    assert sql == 'SELECT * FROM rets_property' and params == ()
