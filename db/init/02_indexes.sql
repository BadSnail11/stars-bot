-- users
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);
CREATE INDEX IF NOT EXISTS idx_users_blocked ON users (is_blocked);

-- required_channels
CREATE UNIQUE INDEX IF NOT EXISTS uq_required_channels_channel ON required_channels (channel_username);

-- orders
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);
CREATE INDEX IF NOT EXISTS idx_orders_paid_at ON orders (paid_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_type ON orders (type);
CREATE INDEX IF NOT EXISTS idx_orders_currency ON orders (currency);

-- broadcasts
CREATE INDEX IF NOT EXISTS idx_broadcasts_status ON broadcasts (status);
CREATE INDEX IF NOT EXISTS idx_broadcasts_created_at ON broadcasts (created_at);

-- pricing_rules
CREATE INDEX IF NOT EXISTS idx_pricing_rules_active ON pricing_rules (item_type, is_active);