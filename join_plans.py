import os
import json
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("""
        SELECT
            COUNT(*) AS total_units,
            COUNT(p.id) AS matched_units,
            COUNT(*) - COUNT(p.id) AS unmatched_units
        FROM contract_units u
        LEFT JOIN plans p ON p.id = u.plan_id;
""")

print(cur.fetchone())