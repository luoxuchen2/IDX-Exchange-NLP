"""Create a reproducible 250-remark annotation draft from a CSV.

Usage:
 python scripts/prepare_labels.py data/week2_cleaned.csv --text-column cleaned_remarks

The generated spans are AUTO-LABELS ONLY. Manually verify each example,
correct misses/false matches, and save verified spans as the gold standard.
"""
import argparse
import csv
import json
import random
from pathlib import Path
from entity_extractor import EntityExtractor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--text-column", default="cleaned_remarks")
    parser.add_argument("--count", type=int, default=250)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--output", type=Path, default=Path("data/week3_annotation_draft.jsonl"))
    args = parser.parse_args()
    with args.csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if args.text_column not in (reader.fieldnames or []):
            raise ValueError(f"Column {args.text_column!r} not found. Available: {reader.fieldnames}")
        rows = [row[args.text_column] for row in reader if row.get(args.text_column, "").strip()]
    rng = random.Random(args.seed)
    selected = rng.sample(rows, min(args.count, len(rows)))
    extractor = EntityExtractor()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for i, text in enumerate(selected):
            spans = [{k: span[k] for k in ("start", "end", "label")}
                     for span in extractor.extract_spans(text)]
            f.write(json.dumps({"id": i, "text": text, "entities": spans,
                                "verified": False}, ensure_ascii=False) + "\n")
    print(f"Wrote {len(selected)} annotation drafts to {args.output}")


if __name__ == "__main__":
    main()
