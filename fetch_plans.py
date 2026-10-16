import json
import os
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from goszakup_client import GoszakupClient

load_dotenv()

BATCH_SIZE = 100
OUTPUT_DIR = Path("data/raw/plans")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

QUERY = """
query ($ids: [Int], $limit: Int, $after: Int) {
  Plans(
    filter: {id: $ids}
    limit: $limit
    after: $after
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


def get_plan_ids():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT plan_id
                FROM contract_units
                WHERE plan_id IS NOT NULL
                ORDER BY plan_id
            """)
            return [row[0] for row in cur.fetchall()]


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def fetch_batch(client, ids):
    records = []
    after = None

    while True:
        result = client.execute(
            QUERY,
            {
                "ids": ids,
                "limit": 200,
                "after": after,
            },
        )

        batch = result.get("data", {}).get("Plans") or []
        page_info = result.get("extensions", {}).get("pageInfo", {})

        records.extend(batch)

        if not page_info.get("hasNextPage", False):
            break

        next_after = page_info.get("lastId")

        if not next_after or next_after == after:
            raise RuntimeError("Pagination cursor stalled")

        after = next_after

    by_id = {record["id"]: record for record in records}

    requested = set(ids)
    received = set(by_id)

    missing = requested - received
    unexpected = received - requested

    if unexpected:
        raise RuntimeError(
            f"Unexpected IDs: {sorted(unexpected)}"
        )

    return list(by_id.values()), sorted(missing)

    return list(by_id.values())


def save_json_atomic(path, records):
    temp_path = path.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def main():
    ids = get_plan_ids()
    client = GoszakupClient()

    batches = list(chunks(ids, BATCH_SIZE))

    print(f"Unique plan IDs: {len(ids)}")
    print(f"Batches: {len(batches)}")

    for index, batch_ids in enumerate(batches, start=1):
        path = OUTPUT_DIR / f"plans_batch_{index:04d}.json"

        missing_path = OUTPUT_DIR / f"plans_missing_{index:04d}.json"

        if (
                os.getenv("REFRESH_PLANS", "0") != "1"
                and path.exists()
                and missing_path.exists()
        ):
            with path.open("r", encoding="utf-8") as file:
                saved = json.load(file)

            with missing_path.open("r", encoding="utf-8") as file:
                saved_missing = json.load(file)

            saved_ids = {record["id"] for record in saved}
            missing_ids = set(saved_missing)

            if (
                    saved_ids.isdisjoint(missing_ids)
                    and saved_ids | missing_ids == set(batch_ids)
            ):
                print(
                    f"[{index}/{len(batches)}] SKIP "
                    f"(saved={len(saved_ids)}, missing={len(missing_ids)})"
                )
                continue

            raise RuntimeError(
                f"Existing batch has inconsistent coverage: {path}"
            )

        records, missing = fetch_batch(client, batch_ids)

        save_json_atomic(path, records)

        missing_path = OUTPUT_DIR / f"plans_missing_{index:04d}.json"

        # Создаём файл пропусков для каждого пакета,
        # даже если список пуст
        save_json_atomic(missing_path, missing)

        print(
            f"[{index}/{len(batches)}] "
            f"Saved {len(records)}/{len(batch_ids)} plans; "
            f"missing={len(missing)}"
        )

        time.sleep(0.5)

    print("\nPLANS DOWNLOAD FINISHED")


if __name__ == "__main__":
    main()