-- Portfolio holdings and financial profile

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    shares DECIMAL NOT NULL DEFAULT 0,
    cost_basis DECIMAL,
    acquired_date DATE,
    account_type VARCHAR(20) NOT NULL DEFAULT 'taxable' CHECK (account_type IN ('taxable', 'ira', 'roth_ira', '401k')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(discord_id, symbol, account_type)
);

CREATE TABLE IF NOT EXISTS financial_profile (
    discord_id BIGINT PRIMARY KEY,
    annual_income DECIMAL,
    investment_horizon VARCHAR(50),
    goals JSONB DEFAULT '[]',
    tax_bracket VARCHAR(10),
    monthly_investment DECIMAL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_discord_id ON portfolio_holdings(discord_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_symbol ON portfolio_holdings(symbol);
