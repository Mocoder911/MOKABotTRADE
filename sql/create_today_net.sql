-- Create today_net table for storing daily net profit calculated by bridge
CREATE TABLE IF NOT EXISTS today_net (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    account_id TEXT NOT NULL,
    net_profit DECIMAL(10, 2) NOT NULL DEFAULT 0,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date DATE NOT NULL DEFAULT CURRENT_DATE
);

-- Create index for fast lookup
CREATE INDEX IF NOT EXISTS idx_today_net_user_date ON today_net(user_id, date);

-- Grant permissions
ALTER TABLE today_net ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own today_net" ON today_net;
CREATE POLICY "Users can view their own today_net" ON today_net
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage today_net" ON today_net;
CREATE POLICY "Service role can manage today_net" ON today_net
    FOR ALL USING (true);
