
from collections import Counter

from llm_router import route
from evaluation_cases import TEST_CASES
import json

correct = 0
failures = []
by_intent = Counter()
by_intent_correct = Counter()

for index, (question, expected_intent, expected_id) in enumerate(
    TEST_CASES, start=1
):
    result = route(question)

    actual_intent = result["intent"]
    actual_id = (
        result["contract_id"]
        if actual_intent == "get_contract"
        else result["unit_id"]
        if actual_intent == "explain_anomaly"
        else None
    )

    success = (
        actual_intent == expected_intent
        and actual_id == expected_id
    )

    by_intent[expected_intent] += 1

    if success:
        correct += 1
        by_intent_correct[expected_intent] += 1
    else:
        failures.append(
            (index, question, expected_intent,
             expected_id, actual_intent, actual_id)
        )

    print(f"[{index:02d}/50] {'OK' if success else 'FAIL'}")

total = len(TEST_CASES)
accuracy = correct / total * 100

print(f"\nAccuracy маршрутизации: {accuracy:.1f}%")
print(f"Правильно: {correct}/{total}")

print("\nПо категориям:")
for intent, count in by_intent.items():
    passed = by_intent_correct[intent]
    print(f"{intent}: {passed}/{count}")

print("\nОшибки:")
for failure in failures:
    print(failure)

results = {
    "accuracy": round(accuracy, 1),
    "correct": correct,
    "total": total,
    "by_intent": {
        intent: {
            "correct": by_intent_correct[intent],
            "total": count
        }
        for intent, count in by_intent.items()
    },
    "failures": failures
}

with open("baseline_v1.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)