import os
import time
import requests

from dotenv import load_dotenv

load_dotenv()

URL = "https://ows.goszakup.gov.kz/v3/graphql"
TOKEN = os.getenv("GOSZAKUP_API_TOKEN")

if not TOKEN:
    raise RuntimeError("GOSZAKUP_API_TOKEN is missing")


class GoszakupClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        })

    def execute(self, query, variables=None):
        for attempt in range(3):
            try:
                response = self.session.post(
                    URL,
                    json={
                        "query": query,
                        "variables": variables or {},
                    },
                    timeout=60,
                )

                response.raise_for_status()
                result = response.json()

                if result.get("errors"):
                    raise RuntimeError(result["errors"])

                return result

            except (requests.RequestException, ValueError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    def fetch_all(self, query, root_field, variables=None,
                  limit=200, max_pages=None):

        variables = dict(variables or {})
        after = None
        seen_ids = set()
        records = []
        page = 0

        while True:
            page += 1

            page_vars = {
                **variables,
                "limit": limit,
                "after": after,
            }

            result = self.execute(query, page_vars)

            batch = result.get("data", {}).get(root_field) or []
            page_info = result.get(
                "extensions", {}
            ).get("pageInfo", {})

            for item in batch:
                record_id = item["id"]

                if record_id not in seen_ids:
                    seen_ids.add(record_id)
                    records.append(item)

            print(
                f"Page {page}: "
                f"{len(batch)} records, "
                f"total collected: {len(records)}"
            )

            if not batch:
                break

            next_after = page_info.get("lastId")

            if not next_after or next_after == after:
                raise RuntimeError(
                    f"Pagination cursor stalled: {next_after}"
                )

            if not page_info.get("hasNextPage", False):
                break

            after = next_after

            if max_pages is not None and page >= max_pages:
                break
        expected = page_info.get("totalCount")

        if max_pages is None and expected is not None:
            if len(records) != expected:
                raise RuntimeError(
                    f"Incomplete extraction: "
                    f"collected={len(records)}, expected={expected}"
                )
        return records