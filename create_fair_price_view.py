
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

sql = """
CREATE OR REPLACE VIEW fair_price_v1 AS
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
        c.fin_year,
        u.item_price AS price,
        u.quantity,
        u.total_sum
    FROM contract_units u
    JOIN latest_contracts lc ON lc.id = u.contract_id
    JOIN contracts c ON c.id = u.contract_id
    JOIN plans p ON p.id = u.plan_id
    WHERE u.item_price > 0
      AND u.quantity > 0
      AND COALESCE(u.deleted, 0) = 0
      AND u.enstru_codes[1] IS NOT NULL
      AND p.unit_code IS NOT NULL
),
benchmarks AS (
    SELECT
        enstru,
        unit_code,
        COUNT(*) AS n,
        COUNT(DISTINCT contract_id) AS n_contracts,
        percentile_cont(0.5)
            WITHIN GROUP (ORDER BY price) AS median_price
    FROM items
    GROUP BY enstru, unit_code
    HAVING COUNT(DISTINCT contract_id) >= 5
)
SELECT
    i.*,
    b.n,
    b.n_contracts,
    ROUND(b.median_price::numeric, 2) AS fair_price,
    ROUND(
    ((i.price / NULLIF(b.median_price, 0) - 1) * 100)::numeric,
    2
    ) AS deviation_pct,
    CASE
        WHEN ABS(i.price * i.quantity - i.total_sum)
             <= GREATEST(1, ABS(i.total_sum) * 0.01)
        THEN TRUE
        ELSE FALSE
    END AS price_consistent
FROM items i
JOIN benchmarks b
    ON b.enstru = i.enstru
   AND b.unit_code = i.unit_code
WHERE b.median_price > 0;
"""

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        cur.execute("""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE deviation_pct > 30),
                COUNT(*) FILTER (WHERE NOT price_consistent)
            FROM fair_price_v1;
        """)
        print(
            "Total, above 30%, inconsistent:",
            cur.fetchone()
        )
