
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

sql = """
SELECT
    u.id,
    u.contract_id,
    u.item_price,
    u.quantity,
    u.total_sum,
    u.item_price_wnds,
    u.total_sum_wnds,
    p.name_ru,
    p.unit_code,
    p.price AS plan_price,
    p.quantity AS plan_quantity
FROM contract_units u
LEFT JOIN plans p ON p.id = u.plan_id
WHERE u.id IN (
    47645310,
    46325570,
    54961846
);
"""

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)

        columns = [col.name for col in cur.description]
        print(" | ".join(columns))

        for row in cur.fetchall():
            print(row)
