import os

import psycopg
from dotenv import load_dotenv

from goszakup_client import GoszakupClient

load_dotenv()

QUERY = """
query ($ids: [Int], $limit: Int) {
  Plans(
    filter: {id: $ids}
    limit: $limit
  ) {
    id
    subjectBiin
    plnPointYear
    nameRu
    refEnstruCode
    refUnitsCode
    count
    price
    amount
  }
}
"""

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT plan_id
            FROM contract_units
            WHERE plan_id IS NOT NULL
            ORDER BY plan_id
            LIMIT 10
        """)

        ids = [row[0] for row in cur.fetchall()]

print("Requested:", ids)

client = GoszakupClient()

result = client.execute(
    QUERY,
    variables={
        "ids": ids,
        "limit": 20,
    },
)

plans = result.get("data", {}).get("Plans") or []

received = {p["id"] for p in plans}
requested = set(ids)

print("Received:", sorted(received))
print("Missing:", sorted(requested - received))
print("Unexpected:", sorted(received - requested))
print("PageInfo:", result.get("extensions", {}).get("pageInfo"))

assert received == requested, "Not all plans were returned"

print("\nBATCH TEST PASSED")