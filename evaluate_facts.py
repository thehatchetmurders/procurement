
from decimal import Decimal
from agent import get_contract

CONTRACT_IDS = [
    22218552,
    20266272,
    19505027,
    25474306,
    23585378,
]

passed = 0
total = 0

for contract_id in CONTRACT_IDS:
    result = get_contract(contract_id)

    total += 1

    if result is None:
        print(f"FAIL: договор {contract_id} не найден")
        continue
    (
            returned_id,
            contract_number,
            fin_year,
            customer_bin,
            supplier_bin,
            contract_sum,
            units_count,
    ) = result

    checks = {
        "correct_id": returned_id == contract_id,
        "valid_year": 2024 <= fin_year <= 2026,
        "nonnegative_sum": (
                contract_sum is not None
                and Decimal(str(contract_sum)) >= 0
        ),
        "has_units": units_count > 0,
        "has_customer": bool(customer_bin),
        "has_supplier": bool(supplier_bin),
    }

    for name, success in checks.items():
        total += 1
        passed += int(success)
        print(
            f"{'OK' if success else 'FAIL'} "
            f"{contract_id}: {name}"
        )

    passed += 1

accuracy = passed / total * 100
print(f"\nПроверок пройдено: {passed}/{total}")
print(f"Доля успешных проверок: {accuracy:.1f}%")
