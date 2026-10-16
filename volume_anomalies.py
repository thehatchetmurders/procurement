
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_volume_anomalies(limit=10):
    sql = """
    WITH latest_contracts AS (
        SELECT id
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY COALESCE(NULLIF(root_id, 0), id)
                    ORDER BY sign_date DESC NULLS LAST, id DESC
                ) AS rn
            FROM contracts
        ) t
        WHERE rn = 1
    ),
    items AS (
        SELECT
            u.id AS unit_id,
            u.contract_id,
            u.enstru_codes[1] AS enstru,
            p.unit_code,
            u.quantity
        FROM contract_units u
        JOIN latest_contracts lc
            ON lc.id = u.contract_id
        JOIN plans p
            ON p.id = u.plan_id
        WHERE u.quantity > 0
          AND COALESCE(u.deleted, 0) = 0
          AND u.enstru_codes[1] IS NOT NULL
          AND p.unit_code IS NOT NULL
    ),
    benchmarks AS (
        SELECT
            enstru,
            unit_code,
            COUNT(*) AS comparable_n,
            COUNT(DISTINCT contract_id) AS contracts_n,
            percentile_cont(0.5)
                WITHIN GROUP (ORDER BY quantity)
                AS median_quantity
        FROM items
        GROUP BY enstru, unit_code
        HAVING COUNT(*) >= 10
           AND COUNT(DISTINCT contract_id) >= 5
    )
    SELECT
        i.unit_id,
        i.contract_id,
        i.enstru,
        i.unit_code,
        i.quantity,
        ROUND(b.median_quantity::numeric, 2),
        ROUND(
            (i.quantity / NULLIF(b.median_quantity, 0))::numeric,
            2
        ) AS volume_ratio,
        b.comparable_n
    FROM items i
    JOIN benchmarks b
        ON b.enstru = i.enstru
       AND b.unit_code = i.unit_code
    WHERE b.median_quantity > 0
      AND i.quantity > b.median_quantity * 3
    ORDER BY volume_ratio DESC
    LIMIT %s
    """

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()


if __name__ == "__main__":
    rows = get_volume_anomalies()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    u.id,
                    p.name_ru,
                    p.unit_code,
                    u.quantity,
                    u.item_price
                FROM contract_units u
                JOIN plans p ON p.id = u.plan_id
                WHERE u.id IN (
                    46868648, 45282299, 57455696,
                    53541340, 45254030
                )
                ORDER BY u.id
            """)

            print("\nПРОВЕРКА ТОВАРОВ:")
            for item in cur.fetchall():
                print(item)
    for row in rows:
        (
            unit_id, contract_id, enstru, unit_code,
            quantity, median, ratio, n
        ) = row

        print(
            f"Позиция: {unit_id}\n"
            f"Договор: {contract_id}\n"
            f"ЕНСТРУ: {enstru}\n"
            f"Количество: {quantity}\n"
            f"Медианный объём: {median}\n"
            f"Превышение: x{ratio}\n"
            f"Сопоставимых позиций: {n}\n"
        )
