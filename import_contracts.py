import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
DATA_DIR = Path("data/raw/contracts")


CONTRACT_SQL = """
INSERT INTO contracts (
    id, root_id, parent_id, contract_number_sys,
    customer_bin, supplier_bin, fin_year, sign_date,
    status_id, contract_sum, contract_sum_wnds,
    fakt_sum_wnds, index_date, raw_data
)
VALUES (
    %(id)s, %(root_id)s, %(parent_id)s,
    %(contract_number_sys)s, %(customer_bin)s,
    %(supplier_bin)s, %(fin_year)s, %(sign_date)s,
    %(status_id)s, %(contract_sum)s,
    %(contract_sum_wnds)s, %(fakt_sum_wnds)s,
    %(index_date)s, %(raw_data)s
)
ON CONFLICT (id) DO UPDATE SET
    root_id = EXCLUDED.root_id,
    parent_id = EXCLUDED.parent_id,
    contract_number_sys = EXCLUDED.contract_number_sys,
    customer_bin = EXCLUDED.customer_bin,
    supplier_bin = EXCLUDED.supplier_bin,
    fin_year = EXCLUDED.fin_year,
    sign_date = EXCLUDED.sign_date,
    status_id = EXCLUDED.status_id,
    contract_sum = EXCLUDED.contract_sum,
    contract_sum_wnds = EXCLUDED.contract_sum_wnds,
    fakt_sum_wnds = EXCLUDED.fakt_sum_wnds,
    index_date = EXCLUDED.index_date,
    raw_data = EXCLUDED.raw_data
"""

UNIT_SQL = """
INSERT INTO contract_units (
    id, contract_id, root_id, parent_id,
    lot_id, plan_id, enstru_codes,
    item_price, item_price_wnds, quantity,
    total_sum, total_sum_wnds,
    contract_sum_wnds, fakt_sum_wnds,
    deleted, raw_data
)
VALUES (
    %(id)s, %(contract_id)s, %(root_id)s,
    %(parent_id)s, %(lot_id)s, %(plan_id)s,
    %(enstru_codes)s, %(item_price)s,
    %(item_price_wnds)s, %(quantity)s,
    %(total_sum)s, %(total_sum_wnds)s,
    %(contract_sum_wnds)s, %(fakt_sum_wnds)s,
    %(deleted)s, %(raw_data)s
)
ON CONFLICT (id) DO UPDATE SET
    contract_id = EXCLUDED.contract_id,
    root_id = EXCLUDED.root_id,
    parent_id = EXCLUDED.parent_id,
    lot_id = EXCLUDED.lot_id,
    plan_id = EXCLUDED.plan_id,
    enstru_codes = EXCLUDED.enstru_codes,
    item_price = EXCLUDED.item_price,
    item_price_wnds = EXCLUDED.item_price_wnds,
    quantity = EXCLUDED.quantity,
    total_sum = EXCLUDED.total_sum,
    total_sum_wnds = EXCLUDED.total_sum_wnds,
    contract_sum_wnds = EXCLUDED.contract_sum_wnds,
    fakt_sum_wnds = EXCLUDED.fakt_sum_wnds,
    deleted = EXCLUDED.deleted,
    raw_data = EXCLUDED.raw_data
"""


def contract_params(c):
    return {
        "id": c["id"],
        "root_id": c.get("rootId"),
        "parent_id": c.get("parentId"),
        "contract_number_sys": c.get("contractNumberSys"),
        "customer_bin": c.get("customerBin"),
        "supplier_bin": c.get("supplierBiin"),
        "fin_year": c.get("finYear"),
        "sign_date": c.get("signDate"),
        "status_id": c.get("refContractStatusId"),
        "contract_sum": c.get("contractSum"),
        "contract_sum_wnds": c.get("contractSumWnds"),
        "fakt_sum_wnds": c.get("faktSumWnds"),
        "index_date": c.get("indexDate"),
        "raw_data": Jsonb(c),
    }


def unit_params(u, contract_id):
    return {
        "id": u["id"],
        "contract_id": contract_id,
        "root_id": u.get("rootId"),
        "parent_id": u.get("parentId"),
        "lot_id": u.get("lotId"),
        "plan_id": u.get("plnPointId"),
        "enstru_codes": u.get("refEnstruCode") or [],
        "item_price": u.get("itemPrice"),
        "item_price_wnds": u.get("itemPriceWnds"),
        "quantity": u.get("quantity"),
        "total_sum": u.get("totalSum"),
        "total_sum_wnds": u.get("totalSumWnds"),
        "contract_sum_wnds": u.get("contractSumWnds"),
        "fakt_sum_wnds": u.get("factSumWnds"),
        "deleted": u.get("deleted"),
        "raw_data": Jsonb(u),
    }


def main():
    files = sorted(DATA_DIR.glob("contracts_*.json"))

    #if len(files) != 81:
    #    raise RuntimeError(
    #        f"Expected 81 files, found {len(files)}"
    #    )

    with psycopg.connect(DATABASE_URL) as conn:
        total_contracts = 0
        total_units = 0

        for index, path in enumerate(files, start=1):
            with path.open(encoding="utf-8") as f:
                contracts = json.load(f)

            units = [
                unit_params(u, c["id"])
                for c in contracts
                for u in (c.get("ContractUnits") or [])
            ]

            with conn.transaction():
                with conn.cursor() as cur:
                    if contracts:
                        cur.executemany(
                            CONTRACT_SQL,
                            [contract_params(c) for c in contracts],
                        )

                    if units:
                        cur.executemany(UNIT_SQL, units)

            total_contracts += len(contracts)
            total_units += len(units)

            print(
                f"[{index}/{len(files)}] {path.name}: "
                f"{len(contracts)} contracts, "
                f"{len(units)} units"
            )

        print("\nIMPORT FINISHED")
        print("Contracts processed:", total_contracts)
        print("Units processed:", total_units)


if __name__ == "__main__":
    main()