import json
import time
from pathlib import Path
import os
from goszakup_client import GoszakupClient

REFRESH = os.getenv("REFRESH_CONTRACTS", "0") == "1"
plans_env = os.environ.copy()
plans_env["REFRESH_PLANS"] = "1"
QUERY = """
query Contracts(
  $bin: String!
  $year: Int!
  $limit: Int
  $after: Int
) {
  Contract(
    filter: {
      customerBin: $bin
      finYear: $year
    }
    limit: $limit
    after: $after
  ) {
    id
    parentId
    rootId
    contractNumberSys
    customerBin
    supplierBiin
    finYear
    signDate
    refContractStatusId
    refContractTypeId
    contractSum
    contractSumWnds
    faktSumWnds
    indexDate

    ContractUnits {
      id
      rootId
      parentId
      contractRegistryId
      lotId
      plnPointId
      refEnstruCode
      itemPrice
      itemPriceWnds
      quantity
      totalSum
      totalSumWnds
      contractSumWnds
      factSumWnds
      deleted
    }
  }
}
"""


def load_bins(path="bins.txt"):
    bins = [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    if any(len(b) != 12 or not b.isdigit() for b in bins):
        raise ValueError("Некорректный БИН в bins.txt")

    return list(dict.fromkeys(bins))


def main():
    client = GoszakupClient()
    bins = load_bins()
    years = [2024, 2025, 2026]

    output_dir = Path("data/raw/contracts")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Organizations: {len(bins)}")
    print(f"Years: {years}")
    print(f"Total combinations: {len(bins) * len(years)}")

    summary = []
    failed = []
    for bin_value in bins:
        for year in years:
            output = output_dir / f"contracts_{bin_value}_{year}.json"

            # Уже сохранённые выгрузки не повторяем
            if output.exists() and not REFRESH:
                print(f"\nSKIP {bin_value} / {year}")
                continue

            print(f"\n{'=' * 60}")
            print(f"BIN: {bin_value} | YEAR: {year}")

            try:
                contracts = client.fetch_all(
                    query=QUERY,
                    root_field="Contract",
                    variables={
                        "bin": bin_value,
                        "year": year,
                    },
                    limit=100,
                    max_pages=None,
                )

                # Сначала временный файл, затем переименование:
                # неполная выгрузка не будет считаться готовой.
                temporary = output.with_suffix(".json.tmp")

                with temporary.open("w", encoding="utf-8") as f:
                    json.dump(contracts, f, ensure_ascii=False, indent=2)

                temporary.replace(output)

                summary.append({
                    "bin": bin_value,
                    "year": year,
                    "count": len(contracts),
                    "status": "success",
                })

                print(f"SAVED: {len(contracts)} contracts")

            except Exception as exc:
                print(f"ERROR: {bin_value} / {year}: {exc}")

                summary.append({
                    "bin": bin_value,
                    "year": year,
                    "count": None,
                    "status": "error",
                    "error": str(exc),
                })
                failed.append((bin_value, year, str(exc)))

            time.sleep(1)

    summary_path = Path("data/raw/contracts_summary.json")

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\nFINISHED")
    print("Summary:", summary_path)
    if failed:
        raise RuntimeError(
            f"Contract refresh failed for {len(failed)} "
            f"BIN/year combinations: {failed}"
        )


if __name__ == "__main__":
    main()