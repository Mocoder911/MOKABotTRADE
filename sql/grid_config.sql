-- ═══════════════════════════════════════════════════════════════════════════════
-- MOKABotTRADE — Grid Configuration Table
-- ═══════════════════════════════════════════════════════════════════════════════
-- This table stores Grid EA parameters per MT5 account.
-- All values are read by the bridge at runtime (cached 30s).
-- Modify these values from Supabase Dashboard to change behavior without code changes.

CREATE TABLE IF NOT EXISTS grid_config (
    id              BIGSERIAL PRIMARY KEY,
    mt5_account_id  TEXT NOT NULL UNIQUE,
    lot_size        DOUBLE PRECISION NOT NULL DEFAULT 0.07,
    grid_step       INTEGER NOT NULL DEFAULT 500,
    max_orders      INTEGER NOT NULL DEFAULT 10,
    basket_profit   DOUBLE PRECISION NOT NULL DEFAULT 25.0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default configuration for the primary account
INSERT INTO grid_config (mt5_account_id, lot_size, grid_step, max_orders, basket_profit)
VALUES ('260904217', 0.07, 500, 10, 25.0)
ON CONFLICT (mt5_account_id) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Cleanup: Delete all old strategies (no longer used with Grid EA)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Uncomment the following lines to clear old strategy data:
-- DELETE FROM strategies;
-- DELETE FROM trade_signals;
-- DELETE FROM execution_log;

COMMENT ON TABLE grid_config IS 'Grid EA configuration per MT5 account — all parameters are DB-driven';
COMMENT ON COLUMN grid_config.lot_size IS 'Position size per grid order (lots)';
COMMENT ON COLUMN grid_config.grid_step IS 'Distance between grid orders in points';
COMMENT ON COLUMN grid_config.max_orders IS 'Maximum grid orders per symbol';
COMMENT ON COLUMN grid_config.basket_profit IS 'Target basket profit ($) to close all orders per symbol';
