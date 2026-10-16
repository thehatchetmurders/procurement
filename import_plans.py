import os
import json
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data/raw/plans")

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
                id BIGINT PRIMARY KEY,
                subject_bin TEXT,
                fin_year INTEGER,
                name_ru TEXT,
                enstru_code TEXT,
                unit_code TEXT,
                quantity NUMERIC,
                price NUMERIC,
                amount NUMERIC,
                raw_data JSONB)
        """)


with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:

        for path in sorted(DATA_DIR.glob("plans_batch_*.json")):
            plans = json.loads(path.read_text(encoding="utf-8"))

            for plan in plans:
                cur.execute("""
                    INSERT INTO plans (
                        id,
                        subject_bin,
                        fin_year,
                        name_ru,
                        enstru_code,
                        unit_code,
                        quantity,
                        price,
                        amount,
                        raw_data
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        subject_bin = EXCLUDED.subject_bin,
                        fin_year = EXCLUDED.fin_year,
                        name_ru = EXCLUDED.name_ru,
                        enstru_code = EXCLUDED.enstru_code,
                        unit_code = EXCLUDED.unit_code,
                        quantity = EXCLUDED.quantity,
                        price = EXCLUDED.price,
                        amount = EXCLUDED.amount,
                        raw_data = EXCLUDED.raw_data
                """, (
                    plan["id"],
                    plan.get("subjectBiin"),
                    plan.get("plnPointYear"),
                    plan.get("nameRu"),
                    plan.get("refEnstruCode"),
                    plan.get("refUnitsCode"),
                    plan.get("count"),
                    plan.get("price"),
                    plan.get("amount"),
                    Jsonb(plan)
                ))

        cur.execute("SELECT COUNT(*) FROM plans")
        print("Plans in DB:", cur.fetchone()[0])