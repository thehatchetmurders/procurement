from goszakup_client import GoszakupClient

MISSING_IDS = [
    63160979,
    63172905,
    63191727,
    63191750,
    63191773,
    63191787,
    63191847,
    63191857,
    63192049,
    63192082,
]

QUERY = """
query ($ids: [Int], $limit: Int) {
  Plans(filter: {id: $ids}, limit: $limit) {
    id
    subjectBiin
    plnPointYear
    nameRu
  }
}
"""

client = GoszakupClient()

print("=== Проверка одним пакетом ===")

result = client.execute(
    QUERY,
    {"ids": MISSING_IDS, "limit": 200},
)

records = result.get("data", {}).get("Plans") or []

print("Received:", [r["id"] for r in records])
print("PageInfo:", result.get("extensions", {}).get("pageInfo"))

print("\n=== Проверка по одному ID ===")

for plan_id in MISSING_IDS:
    result = client.execute(
        QUERY,
        {"ids": [plan_id], "limit": 10},
    )

    records = result.get("data", {}).get("Plans") or []

    print(
        f"{plan_id}: "
        f"{'FOUND' if records else 'NOT FOUND'}"
    )