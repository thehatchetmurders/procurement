import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data/raw/contracts")
BINS_FILE = Path("bins.txt")
YEARS = [2024, 2025, 2026]

bins = [
    line.strip()
    for line in BINS_FILE.read_text(encoding="utf-8-sig").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]

bins = list(dict.fromkeys(bins))

missing = []
invalid = []
all_contract_ids = set()
duplicates = 0
year_counts = Counter()
total_units = 0
empty_units = 0

for bin_value in bins:
    for year in YEARS:
        path = DATA_DIR / f"contracts_{bin_value}_{year}.json"

        if not path.exists():
            missing.append(str(path))
            continue

        try:
            with path.open(encoding="utf-8") as f:
                contracts = json.load(f)

            if not isinstance(contracts, list):
                raise ValueError("Expected JSON array")

            for contract in contracts:
                contract_id = contract["id"]

                if contract_id in all_contract_ids:
                    duplicates += 1

                all_contract_ids.add(contract_id)

                if contract.get("customerBin") != bin_value:
                    raise ValueError(
                        f"Wrong BIN: contract {contract_id}"
                    )

                if contract.get("finYear") != year:
                    raise ValueError(
                        f"Wrong year: contract {contract_id}"
                    )

                units = contract.get("ContractUnits") or []

                total_units += len(units)

                if not units:
                    empty_units += 1

            year_counts[year] += len(contracts)

        except Exception as exc:
            invalid.append((str(path), str(exc)))

print("\n=== DATA VALIDATION ===")
print("Organizations:", len(bins))
print("Expected files:", len(bins) * len(YEARS))
print("Missing files:", len(missing))
print("Invalid files:", len(invalid))
print("Unique contracts:", len(all_contract_ids))
print("Duplicate contract IDs:", duplicates)
print("Contract units:", total_units)
print("Contracts without units:", empty_units)

for year in YEARS:
    print(f"{year}: {year_counts[year]} contracts")

if missing:
    print("\nMISSING:", missing)

if invalid:
    print("\nINVALID:", invalid)

if missing or invalid or duplicates:
    raise SystemExit("Validation failed")

print("\nVALIDATION PASSED")