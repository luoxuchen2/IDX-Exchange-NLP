"""Week 5: Read MySQL listings, create embeddings, and save the index.

Run from project root: python -m scripts.build_embeddings --limit 10000
Set MYSQL_USER and MYSQL_PASSWORD as environment variables, or enter credentials at prompts.
"""
import argparse
import getpass
import json
import os
from pathlib import Path

import mysql.connector

from scripts.semantic_search import SemanticSearcher


def get_listings(limit):
    """Fetch listing text plus basic metadata; don't assume the table has an 'id' column."""
    user = os.environ.get("MYSQL_USER") or input("MySQL username [root]: ").strip() or "root"
    password = os.environ.get("MYSQL_PASSWORD") or getpass.getpass("MySQL password: ")
    connection = mysql.connector.connect(
        host="127.0.0.1", port=3306, user=user,
        password=password, database="real_estate"
    )
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            # SQL columns are known, trusted identifiers. LIMIT is validated below.
            # The row_index we assign is the stable mapping inside this saved snapshot.
            cursor.execute(
                """SELECT L_City, L_SystemPrice, L_Remarks
                   FROM rets_property
                   WHERE L_Remarks IS NOT NULL AND TRIM(L_Remarks) <> ''
                   ORDER BY L_City, L_SystemPrice, L_Remarks
                   LIMIT %s""",
                (limit,),
            )
            return cursor.fetchall()  # Fetch all rows before closing this cursor.
        finally:
            cursor.close()
    finally:
        connection.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10000,
                    help="Use 10k for speed testing; increase for more listings")
    ap.add_argument("--output", default="data/models")
    args = ap.parse_args()
    if args.limit < 1:
        ap.error("--limit must be positive")

    rows = get_listings(args.limit)
    if not rows:
        raise RuntimeError("No nonempty listing remarks found")

    # A metadata row and its FAISS vector share the same row_index.
    listing_text = [row["L_Remarks"] for row in rows]
    searcher = SemanticSearcher()
    searcher.build_index(listing_text)
    searcher.save(args.output)

    # Save city and price for interpreting search results later.
    metadata = [
        {"row_index": i, "city": row["L_City"], "price": row["L_SystemPrice"]}
        for i, row in enumerate(rows)
    ]
    path = Path(args.output) / "listing_metadata.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(rows)} listings in {args.output}")


if __name__ == "__main__":
    main()
