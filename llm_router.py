
import json
import requests
import os

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat"
)
MODEL = "llama3.2:3b"



def route(question: str) -> dict:
    system = """
You classify Russian and Kazakh procurement questions.
Return ONLY JSON.

Allowed intents:
- get_contract: show information about a contract
- get_anomalies: list price anomalies
- explain_anomaly: explain a specific item/position
- unknown: unsupported request

JSON fields: intent, contract_id, unit_id.
Use null for unused IDs.
Never invent IDs. Never write SQL.

Examples:
Question: Покажи договор 22218552
{"intent":"get_contract","contract_id":22218552,"unit_id":null}

Question: Баға ауытқуларын көрсет
{"intent":"get_anomalies","contract_id":null,"unit_id":null}

Question: Почему позиция 50819071 подозрительная?
{"intent":"explain_anomaly","contract_id":null,"unit_id":50819071}

Question: 50819071 позициясының бағасын түсіндір
{"intent":"explain_anomaly","contract_id":null,"unit_id":50819071}

Question: Сколько стоит картошка?
{"intent":"unknown","contract_id":null,"unit_id":null}

- get_volume_anomalies: list unusually large procurement quantities

Examples:
Question: Покажи аномалии объёмов закупок
{"intent":"get_volume_anomalies","contract_id":null,"unit_id":null}

Question: Сатып алу көлемінің ауытқуларын көрсет
{"intent":"get_volume_anomalies","contract_id":null,"unit_id":null}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": question}
            ]
        },
        timeout=120
    )
    response.raise_for_status()

    data = json.loads(response.json()["message"]["content"])

    intent = data.get("intent")
    allowed = {
        "get_contract",
        "get_anomalies",
        "get_volume_anomalies",
        "explain_anomaly",
        "unknown"
    }
    result = {
        "intent": "unknown",
        "contract_id": None,
        "unit_id": None
    }

    if intent not in allowed:
        return result

    if intent in {"get_anomalies", "get_volume_anomalies", "unknown"}:
        result["intent"] = intent
        return result

    key = (
        "contract_id" if intent == "get_contract"
        else "unit_id"
    )
    value = data.get(key)

    # ID must be an integer explicitly present in the question.
    if type(value) is not int:
        return result

    import re
    numbers = re.findall(r"\d+", question)
    if str(value) not in numbers:
        return result

    result["intent"] = intent
    result[key] = value
    return result



if __name__ == "__main__":
    questions = [
        "Покажи договор 22218552",
        "Какие закупки имеют аномально высокие цены?",
        "22218552 келісімшартын көрсет",
        "Баға ауытқуларын көрсет",
        "Сколько стоит килограмм картошки?"
    ]

    for question in questions:
        print("\nВопрос:", question)
        try:
            print("Маршрут:", route(question))
        except Exception as exc:
            print("Ошибка:", exc)
