
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

sql = """
SELECT
    u.id AS unit_id,
    c.id AS contract_id,
    p.name_ru,
    u.enstru_codes[1] AS enstru,
    p.unit_code,
    u.item_price,
    u.quantity,
    u.total_sum,
    c.fin_year
FROM contract_units u
JOIN contracts c ON c.id = u.contract_id
LEFT JOIN plans p ON p.id = u.plan_id
WHERE u.id IN (
    50819071, 55969102, 49587232, 58260938,
    45847314, 58022854, 56507073, 51823180,
    55969146, 49379596, 53423418, 45554616,
    48629575, 56745413, 48736451, 56194897,
    46352152, 57004577, 45709279, 49596962
)
ORDER BY u.id;
"""

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        print("unit_id | contract_id | enstru | unit_code | "
              "price | weighted_price | comparable_n | deviation_pct")
        for row in cur.fetchall():
            print(row)
