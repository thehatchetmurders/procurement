import json
from pathlib import Path

import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

DATA_DIR = Path("data/raw/plans")

found_ids = set()
missing_ids = set()

for path in sorted(DATA_DIR.glob("plans_batch_*.json")):
    records = json.loads(path.read_text(encoding="utf-8"))
    found_ids.update(record["id"] for record in records)

for path in sorted(DATA_DIR.glob("plans_missing_*.json")):
    missing_ids.update(
        json.loads(path.read_text(encoding="utf-8"))
    )

print("=== PLANS AUDIT ===")
print("Found plans:", len(found_ids))
print("Missing plans:", len(missing_ids))
print("Overlap:", len(found_ids & missing_ids))
print("Total accounted:", len(found_ids | missing_ids))

assert not found_ids & missing_ids

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT plan_id
            FROM contract_units
            WHERE plan_id IS NOT NULL
        """)
        expected_ids = {row[0] for row in cur.fetchall()}

        print("Expected plans:", len(expected_ids))
        print(
            "Unaccounted IDs:",
            len(expected_ids - found_ids - missing_ids)
        )
        print(
            "Unexpected IDs:",
            len((found_ids | missing_ids) - expected_ids)
        )

        assert found_ids | missing_ids == expected_ids

        cur.execute("""
            SELECT
                c.fin_year,
                COUNT(*) AS total_units,
                COUNT(*) FILTER (
                    WHERE u.plan_id = ANY(%s)
                ) AS missing_plan_units
            FROM contract_units u
            JOIN contracts c ON c.id = u.contract_id
            GROUP BY c.fin_year
            ORDER BY c.fin_year
        """, (list(missing_ids),))

        print("\n=== MISSING PLAN LINKS BY YEAR ===")
        for year, total, missing in cur.fetchall():
            print(
                f"{year}: {missing}/{total} "
                f"({missing / total:.2%})"
            )

print("\nAUDIT FINISHED")