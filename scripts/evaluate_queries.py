"""Evaluate JSONL records: {\"query\": \"...\", \"expected\": {\"bedrooms\": 3}}.
Run: python -m scripts.evaluate_queries data/gold_queries.jsonl
"""
import json
import sys
from src.query_parser import QueryParser
from src.schema_validator import SchemaValidator


def main(path):
    validator = SchemaValidator('data/schema.json')
    parser = QueryParser(cities=validator.schema['valid_cities'])
    rows = [json.loads(line) for line in open(path, encoding='utf-8') if line.strip()]
    correct = 0
    for row in rows:
        predicted = parser.parse(row['query'])
        ok = predicted == row['expected']
        correct += ok
        if not ok:
            print(f"MISMATCH: {row['query']!r}\n expected={row['expected']}\n predicted={predicted}")
    accuracy = correct / len(rows) if rows else 0
    print(f'Exact-match accuracy: {correct}/{len(rows)} = {accuracy:.1%}')
    return accuracy


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Usage: python -m scripts.evaluate_queries data/gold_queries.jsonl')
    main(sys.argv[1])
