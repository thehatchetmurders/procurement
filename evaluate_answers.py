
from decimal import Decimal
from agent import get_contract
from llm_agent import answer_with_llm

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
    data = get_contract(contract_id)

    if data is None:
        print(f"FAIL {contract_id}: contract_not_found")
        continue

    (
        returned_id,
        contract_number,
        fin_year,
        customer_bin,
        supplier_bin,
        contract_sum,
        units_count,
    ) = data

    answer = answer_with_llm(
        f"Расскажи о договоре {contract_id}"
    )

    expected = {
        "contract_number": f"Договор: {contract_number}",
        "id": f"ID: {returned_id}",
        "year": f"Год: {fin_year}",
        "customer": f"Заказчик (БИН): {customer_bin}",
        "supplier": f"Поставщик (БИН): {supplier_bin}",
        "sum": f"Сумма: {Decimal(str(contract_sum)):.2f} ₸",
        "units": f"Позиций: {units_count}",
    }

    for name, value in expected.items():
        total += 1
        success = value in answer
        passed += int(success)

        print(
            f"{'OK' if success else 'FAIL'} "
            f"{contract_id}: {name}"
        )

accuracy = passed / total * 100 if total else 0

print(f"\nФактические поля: {passed}/{total}")
print(f"Field accuracy: {accuracy:.1f}%")
