CREATE TABLE IF NOT EXISTS contracts (
    id BIGINT PRIMARY KEY,
    root_id BIGINT,
    parent_id BIGINT,
    contract_number_sys TEXT,
    customer_bin VARCHAR(12),
    supplier_bin VARCHAR(12),
    fin_year INTEGER,
    sign_date TIMESTAMP,
    status_id INTEGER,
    contract_sum NUMERIC(20, 2),
    contract_sum_wnds NUMERIC(20, 2),
    fakt_sum_wnds NUMERIC(20, 2),
    index_date TIMESTAMP,
    raw_data JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS contract_units (
    id BIGINT PRIMARY KEY,
    contract_id BIGINT NOT NULL
        REFERENCES contracts(id),
    root_id BIGINT,
    parent_id BIGINT,
    lot_id BIGINT,
    plan_id BIGINT,
    enstru_codes TEXT[],
    item_price NUMERIC(20, 4),
    item_price_wnds NUMERIC(20, 4),
    quantity NUMERIC(20, 4),
    total_sum NUMERIC(20, 2),
    total_sum_wnds NUMERIC(20, 2),
    contract_sum_wnds NUMERIC(20, 2),
    fakt_sum_wnds NUMERIC(20, 2),
    deleted INTEGER,
    raw_data JSONB NOT NULL
);

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

CREATE INDEX IF NOT EXISTS idx_contracts_customer_year
    ON contracts(customer_bin, fin_year);

CREATE INDEX IF NOT EXISTS idx_contracts_supplier
    ON contracts(supplier_bin);

CREATE INDEX IF NOT EXISTS idx_units_contract
    ON contract_units(contract_id);

CREATE INDEX IF NOT EXISTS idx_units_enstru
    ON contract_units USING GIN(enstru_codes);