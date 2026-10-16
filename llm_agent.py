
from llm_router import route
from agent import get_contract, get_anomalies
import requests
from agent import explain_anomaly
import re
from volume_anomalies import get_volume_anomalies

def answer_with_llm(question: str) -> str:
    decision = route(question)
    intent = decision["intent"]

    if intent == "get_volume_anomalies":
        rows = get_volume_anomalies(limit=5)

        if not rows:
            return "Необычные объёмы закупок не найдены."

        is_kz = any(
            word in question.lower()
            for word in ("көлем", "сатып алу", "ауытқу")
        )

        lines = [
            "Сатып алу көлемінің ықтимал ауытқулары:"
            if is_kz else
            "Предварительные аномалии объёмов закупок:"
        ]

        for unit_id, cid, enstru, unit_code, qty, median, ratio, n in rows:
            if is_kz:
                lines.append(
                    f"Позиция {unit_id}, шарт {cid}: "
                    f"саны {qty:.2f}, медиана {median:.2f}, "
                    f"ауытқу ×{ratio:.2f}, "
                    f"салыстырылған позициялар: {n}."
                )
            else:
                lines.append(
                    f"Позиция {unit_id}, договор {cid}: "
                    f"количество {qty:.2f}, медиана {median:.2f}, "
                    f"превышение ×{ratio:.2f}, "
                    f"сопоставимых позиций: {n}."
                )

        lines.append(
            "\nБұл алдын ала сигнал. Сатып алу көлемі "
            "тапсырыс берушінің қажеттілігіне байланысты болуы мүмкін."
            if is_kz else
            "\nЭто предварительный сигнал. Большой объём "
            "может объясняться потребностями заказчика."
        )

        return "\n".join(lines)

    if intent == "explain_anomaly":
        unit_id = decision["unit_id"]

        is_kz = any(
            word in question.lower()
            for word in (
                "позициясының", "түсіндір",
                "баға", "неге", "қымбат"
            )
        )

        return generate_explanation(
            unit_id,
            language="kz" if is_kz else "ru"
        )
    is_kz = any(
        word in question.lower()
        for word in (
            "келісімшарт", "шартын", "көрсет",
            "ауытқу", "баға", "қымбат"
        )
    )

    if intent == "get_contract":
        contract_id = decision["contract_id"]
        row = get_contract(contract_id)

        if row is None:
            return (
                f"{contract_id} нөмірлі шарт табылмады."
                if is_kz else
                f"Договор {contract_id} не найден."
            )

        cid, number, year, customer, supplier, amount, units = row

        if is_kz:
            return (
                f"Шарт: {number or cid}\n"
                f"ID: {cid}\n"
                f"Жыл: {year}\n"
                f"Тапсырыс берушінің БСН: {customer}\n"
                f"Жеткізушінің БСН: {supplier}\n"
                f"Сома: {amount} ₸\n"
                f"Позициялар саны: {units}"
            )

        return (
            f"Договор: {number or cid}\n"
            f"ID: {cid}\n"
            f"Год: {year}\n"
            f"Заказчик (БИН): {customer}\n"
            f"Поставщик (БИН): {supplier}\n"
            f"Сумма: {amount} ₸\n"
            f"Позиций: {units}"
        )

    if intent == "get_anomalies":
        rows = get_anomalies(limit=5)

        if not rows:
            return (
                "Баға ауытқулары табылмады."
                if is_kz else
                "Ценовые аномалии не найдены."
            )

        lines = [
            "Бағаның ықтимал ауытқулары:"
            if is_kz else
            "Предварительные ценовые сигналы:"
        ]

        for unit_id, cid, enstru, price, benchmark, deviation, n in rows:
            if is_kz:
                lines.append(
                    f"Позиция {unit_id}, шарт {cid}: "
                    f"{price:.2f} ₸, салыстырмалы баға "
                    f"{benchmark:.2f} ₸, "
                    f"ауытқу +{deviation:.2f}%, "
                    f"салыстырылған позициялар: {n}."
                )
            else:
                lines.append(
                    f"Позиция {unit_id}, договор {cid}: "
                    f"{price:.2f} ₸, ориентир "
                    f"{benchmark:.2f} ₸, "
                    f"отклонение +{deviation:.2f}%, "
                    f"сопоставимых позиций: {n}."
                )

        lines.append(
            "\nЕскерту: ЕНСТРУ сәйкестігі тауарлардың "
            "техникалық сипаттамалары бірдей екенін білдірмейді."
            if is_kz else
            "\nВажно: совпадение ЕНСТРУ не гарантирует "
            "сопоставимости технических характеристик."
        )

        return "\n".join(lines)

    return (
        "Сұрауды түсінбедім. Шарттың ID нөмірін немесе "
        "баға ауытқуларын сұраңыз."
        if is_kz else
        "Не понял запрос. Можно запросить договор по ID "
        "или предварительные ценовые аномалии."
    )



def generate_explanation(unit_id: int, language="ru") -> str:
    data = explain_anomaly(unit_id)

    if data is None:
        return f"Недостаточно данных для позиции {unit_id}."

    facts = (
        f"ID позиции: {data['unit_id']}\n"
        f"ID договора: {data['contract_id']}\n"
        f"ЕНСТРУ: {data['enstru']}\n"
        f"Единица измерения: {data['unit_code']}\n"
        f"Цена: {data['price']:.2f} ₸\n"
        f"Средневзвешенный ориентир: "
        f"{data['weighted_price']:.2f} ₸\n"
        f"Отклонение: {data['deviation_pct']:+.2f}%\n"
        f"Количество сопоставляемых позиций: "
        f"{data['comparable_n']}\n"
    )

    target_language = (
        "Kazakh" if language == "kz" else "Russian"
    )

    system = f"""
You are a procurement price analysis assistant.

Write a brief explanation in {target_language}.

Use ONLY the provided facts.
Do not invent numbers, causes, violations or suppliers.
Do not claim corruption or proven overpricing.
Explain that ENSTRU and unit code do not guarantee
identical technical specifications.
The benchmark is quantity-weighted and excludes
positions from the analyzed contract.
Comparable count means positions, NOT contracts.

Do not reproduce numeric values in your explanation:
Python will append the verified figures separately.
Write 2-3 short sentences.

Do not mention unit IDs, contract IDs, counts,
percentages, prices or any digits.
Do not use English or French words.
Do not explain the calculation of comparable_n.
Focus only on what the price deviation means
and why it is not proof of a violation.
"""

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.2:3b",
            "stream": False,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": facts},
            ],
        },
        timeout=120,
    )
    response.raise_for_status()

    explanation = response.json()["message"]["content"].strip()

    # Модель не является источником числовых фактов.
    # Проверенные значения выводятся отдельно через Python.
    #
    # Пока не допускаем свободную интерпретацию модели
    # в финальный ответ без проверки утверждений.

    deviation = data["deviation_pct"]

    if language == "kz":
        if deviation > 30:
            explanation = (
                "Позицияның бағасы салыстырмалы деңгейден "
                "айтарлықтай жоғары. Бұл қосымша тексеруді "
                "қажет ететін алдын ала баға сигналы. "
                "ЕНСТРУ мен өлшем бірлігінің сәйкестігі "
                "тауарлардың техникалық сипаттамалары "
                "бірдей екенін білдірмейді."
            )
        else:
            explanation = (
                "Баға ауытқуы белгіленген оң шектен аспайды. "
                "ЕНСТРУ мен өлшем бірлігінің сәйкестігі "
                "тауарлардың толық салыстырмалы екенін "
                "білдірмейді."
            )
    else:
        if deviation > 30:
            explanation = (
                "Цена позиции существенно превышает "
                "рассчитанный средневзвешенный ориентир. "
                "Это предварительный сигнал для дополнительной "
                "проверки, а не доказательство завышения цены. "
                "Совпадение ЕНСТРУ и единицы измерения не "
                "гарантирует идентичности технических характеристик."
            )
        else:
            explanation = (
                "Отклонение цены не превышает установленный "
                "положительный порог. При этом совпадение ЕНСТРУ "
                "и единицы измерения не гарантирует полной "
                "сопоставимости товаров."
            )

    if language == "kz":
        header = (
            f"Позиция: {data['unit_id']}\n"
            f"Шарт: {data['contract_id']}\n"
            f"ЕНСТРУ: {data['enstru']}\n"
            f"Бағасы: {data['price']:.2f} ₸\n"
            f"Салыстырмалы баға: "
            f"{data['weighted_price']:.2f} ₸\n"
            f"Ауытқу: {data['deviation_pct']:+.2f}%\n"
            f"Салыстырылған позициялар: "
            f"{data['comparable_n']}"
        )
    else:
        header = (
            f"Позиция: {data['unit_id']}\n"
            f"Договор: {data['contract_id']}\n"
            f"ЕНСТРУ: {data['enstru']}\n"
            f"Цена: {data['price']:.2f} ₸\n"
            f"Ориентир: {data['weighted_price']:.2f} ₸\n"
            f"Отклонение: {data['deviation_pct']:+.2f}%\n"
            f"Сопоставимых позиций: "
            f"{data['comparable_n']}"
        )

    title = "Түсіндірме" if language == "kz" else "Объяснение"
    return f"{header}\n\n{title}:\n{explanation}"


if __name__ == "__main__":
    print("Локальный LLM-агент запущен. Для выхода: exit")

    while True:
        question = input("\nВы: ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        if not question:
            continue

        try:
            print("\nАгент:", answer_with_llm(question))
        except Exception as exc:
            print("Ошибка:", exc)


