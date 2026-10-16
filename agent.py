
import os
import re
from decimal import Decimal

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_contract(contract_id: int):
    sql = """
        SELECT
            c.id,
            c.contract_number_sys,
            c.fin_year,
            c.customer_bin,
            c.supplier_bin,
            c.contract_sum,
            COUNT(u.id) AS units_count
        FROM contracts c
        LEFT JOIN contract_units u ON u.contract_id = c.id
        WHERE c.id = %s
        GROUP BY
            c.id, c.contract_number_sys, c.fin_year,
            c.customer_bin, c.supplier_bin, c.contract_sum
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (contract_id,))
            return cur.fetchone()



def get_anomalies(limit: int = 10):
    sql = """
        WITH valid_items AS (
            SELECT
                unit_id,
                contract_id,
                enstru,
                unit_code,
                season,
                price,
                quantity
            FROM fair_price_seasonal_v1
            WHERE price_consistent = TRUE
        ),
        stats AS (
            SELECT
                *,
                SUM(price * quantity) OVER (
                    PARTITION BY enstru, unit_code, season
                ) AS seasonal_value,
                SUM(quantity) OVER (
                    PARTITION BY enstru, unit_code, season
                ) AS seasonal_qty,
                SUM(price * quantity) OVER (
                    PARTITION BY enstru, unit_code, season, contract_id
                ) AS seasonal_own_value,
                SUM(quantity) OVER (
                    PARTITION BY enstru, unit_code, season, contract_id
                ) AS seasonal_own_qty,
                COUNT(*) OVER (
                    PARTITION BY enstru, unit_code, season
                ) AS seasonal_n,
                COUNT(*) OVER (
                    PARTITION BY enstru, unit_code, season, contract_id
                ) AS seasonal_own_n,

                SUM(price * quantity) OVER (
                    PARTITION BY enstru, unit_code
                ) AS global_value,
                SUM(quantity) OVER (
                    PARTITION BY enstru, unit_code
                ) AS global_qty,
                SUM(price * quantity) OVER (
                    PARTITION BY enstru, unit_code, contract_id
                ) AS global_own_value,
                SUM(quantity) OVER (
                    PARTITION BY enstru, unit_code, contract_id
                ) AS global_own_qty,
                COUNT(*) OVER (
                    PARTITION BY enstru, unit_code
                ) AS global_n,
                COUNT(*) OVER (
                    PARTITION BY enstru, unit_code, contract_id
                ) AS global_own_n
            FROM valid_items
        ),
        benchmarks AS (
            SELECT
                *,
                (seasonal_value - seasonal_own_value)
                    / NULLIF(seasonal_qty - seasonal_own_qty, 0)
                    AS seasonal_weighted_price,
                seasonal_n - seasonal_own_n AS seasonal_comparable_n,

                (global_value - global_own_value)
                    / NULLIF(global_qty - global_own_qty, 0)
                    AS global_weighted_price,
                global_n - global_own_n AS global_comparable_n
            FROM stats
        ),
        selected AS (
            SELECT
                *,
                CASE
                    WHEN season IS NOT NULL
                     AND seasonal_comparable_n >= 10
                     AND seasonal_weighted_price > 0
                    THEN seasonal_weighted_price
                    ELSE global_weighted_price
                END AS weighted_price,
                CASE
                    WHEN season IS NOT NULL
                     AND seasonal_comparable_n >= 10
                     AND seasonal_weighted_price > 0
                    THEN seasonal_comparable_n
                    ELSE global_comparable_n
                END AS comparable_n
            FROM benchmarks
        )
        SELECT
            unit_id,
            contract_id,
            enstru,
            price,
            ROUND(weighted_price::numeric, 2),
            ROUND(
                ((price / NULLIF(weighted_price, 0) - 1) * 100)::numeric,
                2
            ),
            comparable_n
        FROM selected
        WHERE comparable_n >= 10
          AND weighted_price > 0
          AND price > weighted_price * 1.30
          AND price < weighted_price * 3
        ORDER BY
            ((price / weighted_price) - 1) DESC
        LIMIT %s
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()

def answer(question: str):
    text = question.lower().strip()

    is_kz = any(word in text for word in (
        "келісімшарт", "шартты", "көрсет",
        "ауытқу", "баға", "қымбат", "сатып алу"
    ))

    anomaly_query = any(word in text for word in (
        "аномал", "завыш", "ауытқу", "қымбат"
    ))

    if anomaly_query:
        rows = get_anomalies()

        if not rows:
            return (
                "Баға ауытқулары табылмады."
                if is_kz else
                "Кандидаты на ценовые аномалии не найдены."
            )

        result = [
            "Бағаның ықтимал ауытқулары:\n"
            if is_kz else
            "Предварительные ценовые сигналы:\n"
        ]

        for row in rows:
            unit_id, contract_id, enstru, price, benchmark, deviation, n = row

            if is_kz:
                result.append(
                    f"Позиция {unit_id}, шарт {contract_id}: "
                    f"бағасы {price} ₸, бағдар {benchmark} ₸, "
                    f"ауытқу +{deviation}%, "
                    f"салыстырылған позициялар: {n}."
                )
            else:
                result.append(
                    f"Позиция {unit_id}, договор {contract_id}: "
                    f"цена {price} ₸, ориентир {benchmark} ₸, "
                    f"отклонение +{deviation}%, "
                    f"сопоставляемых позиций: {n}."
                )

        result.append(
            "\nЕскерту: ЕНСТРУ сәйкестігі тауарлардың "
            "техникалық сипаттамалары бірдей екенін білдірмейді."
            if is_kz else
            "\nВажно: совпадение ЕНСТРУ не гарантирует "
            "сопоставимости технических характеристик."
        )

        return "\n".join(result)

    match = re.search(r"\b\d{7,12}\b", text)

    if match:
        contract_id = int(match.group())
        row = get_contract(contract_id)

        if row is None:
            return (
                f"{contract_id} нөмірлі шарт табылмады."
                if is_kz else
                f"Договор {contract_id} не найден."
            )

        (
            contract_id, number, year,
            customer, supplier, amount, units_count
        ) = row

        if is_kz:
            return (
                f"Шарт: {number or contract_id}\n"
                f"ID: {contract_id}\n"
                f"Жыл: {year}\n"
                f"Тапсырыс берушінің БСН: {customer}\n"
                f"Жеткізушінің БСН: {supplier}\n"
                f"Сома: {amount} ₸\n"
                f"Позициялар саны: {units_count}"
            )

        return (
            f"Договор: {number or contract_id}\n"
            f"ID: {contract_id}\n"
            f"Год: {year}\n"
            f"Заказчик (БИН): {customer}\n"
            f"Поставщик (БИН): {supplier}\n"
            f"Сумма: {amount} ₸\n"
            f"Позиций: {units_count}"
        )

    return (
        "Шарттың ID нөмірі бойынша іздеу және баға "
        "ауытқуларын көрсету қолжетімді."
        if is_kz else
        "Поддерживаются поиск договора по ID "
        "и просмотр предварительных ценовых аномалий."
    )


def explain_anomaly(unit_id: int):
    sql = """
    WITH valid_items AS (
        SELECT
            unit_id,
            contract_id,
            enstru,
            unit_code,
            season,
            price,
            quantity
        FROM fair_price_seasonal_v1
        WHERE price_consistent = TRUE
    ),
    stats AS (
        SELECT *,
            SUM(price * quantity) OVER (
                PARTITION BY enstru, unit_code, season
            ) AS seasonal_value,
            SUM(quantity) OVER (
                PARTITION BY enstru, unit_code, season
            ) AS seasonal_qty,
            SUM(price * quantity) OVER (
                PARTITION BY enstru, unit_code, season, contract_id
            ) AS seasonal_own_value,
            SUM(quantity) OVER (
                PARTITION BY enstru, unit_code, season, contract_id
            ) AS seasonal_own_qty,
            COUNT(*) OVER (
                PARTITION BY enstru, unit_code, season
            ) AS seasonal_n,
            COUNT(*) OVER (
                PARTITION BY enstru, unit_code, season, contract_id
            ) AS seasonal_own_n,

            SUM(price * quantity) OVER (
                PARTITION BY enstru, unit_code
            ) AS global_value,
            SUM(quantity) OVER (
                PARTITION BY enstru, unit_code
            ) AS global_qty,
            SUM(price * quantity) OVER (
                PARTITION BY enstru, unit_code, contract_id
            ) AS global_own_value,
            SUM(quantity) OVER (
                PARTITION BY enstru, unit_code, contract_id
            ) AS global_own_qty,
            COUNT(*) OVER (
                PARTITION BY enstru, unit_code
            ) AS global_n,
            COUNT(*) OVER (
                PARTITION BY enstru, unit_code, contract_id
            ) AS global_own_n
        FROM valid_items
    ),
    benchmarks AS (
        SELECT *,
            (seasonal_value - seasonal_own_value)
                / NULLIF(seasonal_qty - seasonal_own_qty, 0)
                AS seasonal_weighted_price,
            seasonal_n - seasonal_own_n AS seasonal_comparable_n,

            (global_value - global_own_value)
                / NULLIF(global_qty - global_own_qty, 0)
                AS global_weighted_price,
            global_n - global_own_n AS global_comparable_n
        FROM stats
    ),
    selected AS (
        SELECT *,
            CASE
                WHEN season IS NOT NULL
                 AND seasonal_comparable_n >= 10
                 AND seasonal_weighted_price > 0
                THEN seasonal_weighted_price
                ELSE global_weighted_price
            END AS weighted_price,
            CASE
                WHEN season IS NOT NULL
                 AND seasonal_comparable_n >= 10
                 AND seasonal_weighted_price > 0
                THEN seasonal_comparable_n
                ELSE global_comparable_n
            END AS comparable_n,
            CASE
                WHEN season IS NOT NULL
                 AND seasonal_comparable_n >= 10
                 AND seasonal_weighted_price > 0
                THEN 'seasonal'
                ELSE 'global'
            END AS benchmark_level
        FROM benchmarks
    )
    SELECT
        unit_id,
        contract_id,
        enstru,
        unit_code,
        price,
        ROUND(weighted_price::numeric, 2),
        ROUND(
            ((price / NULLIF(weighted_price, 0) - 1) * 100)::numeric,
            2
        ),
        comparable_n,
        benchmark_level
    FROM selected
    WHERE unit_id = %s
      AND comparable_n >= 10
      AND weighted_price > 0
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (unit_id,))
            row = cur.fetchone()

    if row is None:
        return None

    keys = (
        "unit_id", "contract_id", "enstru",
        "unit_code", "price", "weighted_price",
        "deviation_pct", "comparable_n",
        "benchmark_level"
    )

    return dict(zip(keys, row))


if __name__ == "__main__":
    print("Procurement Agent v0.1")
    print("Введите 'exit' для выхода.\n")

    while True:
        question = input("Вы: ").strip()

        if question.lower() in ("exit", "quit", "выход"):
            break

        try:
            print("\nАгент:", answer(question), "\n")
        except Exception as exc:
            print(f"\nОшибка: {exc}\n")
