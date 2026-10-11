import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from entity_extractor import EntityExtractor


def test_basic_extraction():
    result = EntityExtractor().extract_all('3 bedrooms, 2.5 baths, 1,850 sqft, $750,000, pool and garage.')
    assert result == {'bedrooms': 3, 'bathrooms': 2.5, 'price': 750000,
                      'sqft': 1850, 'amenities': ['pool', 'garage']}


def test_compact_forms():
    result = EntityExtractor().extract_all('4bd 3ba 2200 sf. Asking $1.2M. Solar panels.')
    assert result == {'bedrooms': 4, 'bathrooms': 3, 'price': 1200000,
                      'sqft': 2200, 'amenities': ['solar']}


def test_spans_align():
    text = '2br and 1 bath with a patio'
    assert all(text[e['start']:e['end']] == e['text'] for e in EntityExtractor().extract_spans(text))


def test_missing_data():
    assert EntityExtractor().extract_all('Wonderful mountain views') == {
        'bedrooms': None, 'bathrooms': None, 'price': None,
        'sqft': None, 'amenities': []}
