
import argparse
from collections import Counter
import json
from pathlib import Path
from entity_extractor import EntityExtractor


def evaluate(path):
    extractor = EntityExtractor()
    tp = fp = fn = 0
    per_label = {}
    errors = []
    total = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("verified") is not True:
            raise ValueError(f"Line {line_number} is not manually verified; refusing to score pseudo-labels")
        text = record["text"]
        gold = {(e["start"], e["end"], e["label"]) for e in record["entities"]}
        pred = {(e["start"], e["end"], e["label"]) for e in extractor.extract_spans(text)}
        total += 1
        tp += len(gold & pred)
        fp += len(pred - gold)
        fn += len(gold - pred)
        for label in {x[2] for x in gold | pred}:
            counts = per_label.setdefault(label, Counter())
            counts["tp"] += sum(x[2] == label for x in gold & pred)
            counts["fp"] += sum(x[2] == label for x in pred - gold)
            counts["fn"] += sum(x[2] == label for x in gold - pred)
        if gold != pred:
            errors.append({"id": record.get("id", line_number), "text": text,
                           "false_positives": sorted(pred - gold),
                           "false_negatives": sorted(gold - pred)})

    def scores(t, p, n):
        precision = t / (t + p) if t + p else 0.0
        recall = t / (t + n) if t + n else 0.0
        return precision, recall, (2 * precision * recall / (precision + recall)
                                   if precision + recall else 0.0)

    print(f"Verified examples: {total}")
    print("LABEL       PRECISION RECALL F1  TP FP FN")
    for label, counts in [("MICRO", Counter(tp=tp, fp=fp, fn=fn))] + sorted(per_label.items()):
        p, r, f = scores(counts["tp"], counts["fp"], counts["fn"])
        print(f"{label:11} {p:9.3f} {r:6.3f} {f:5.3f} "
              f"{counts['tp']:3} {counts['fp']:2} {counts['fn']:2}")
    out = path.with_name("week3_error_analysis.json")
    out.write_text(json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(errors)} mismatch records to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gold_jsonl", type=Path)
    args = parser.parse_args()
    evaluate(args.gold_jsonl)
