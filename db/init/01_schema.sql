-- пользователи
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  tg_user_id BIGINT UNIQUE NOT NULL,
  username TEXT,
  first_name TEXT,
  last_name TEXT,
  lang_code VARCHAR(8),
  balance DECIMAL(18,6) NOT NULL DEFAULT 0,
  accepted_offer_at TIMESTAMP,               -- когда подтвердил оферту
  is_blocked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- обязательные каналы для подписки
CREATE TABLE IF NOT EXISTS required_channels (
  id BIGSERIAL PRIMARY KEY,
  channel_username TEXT NOT NULL,    -- @channel
  is_active BOOLEAN DEFAULT TRUE,
  bot_key BIGINT REFERENCES user_bots(id) ON DELETE CASCADE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- покупки/заказы (поля из ТЗ под статистику)
CREATE TABLE IF NOT EXISTS orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id),
  username TEXT,                     -- username покупателя (снимок)
  recipient TEXT,                    -- получатель (для чеков/подарков)
  type VARCHAR(16) CHECK (type IN ('stars','premium')),
  amount BIGINT,                     -- кол-во звёзд или месяцев премки
  price DECIMAL(18,2),               -- сколько оплатил (в выбранной валюте)
  income DECIMAL(18,2),              -- наша прибыль (нетто)
  currency VARCHAR(8),               -- 'USDT','RUB','TON' и т.п.
  status VARCHAR(32),                -- pending/paid/failed/refunded
  message TEXT,                      -- финальное сообщение пользователю
  gateway_payload JSONB,             -- сырые данные провайдера/fragment
  created_at TIMESTAMP DEFAULT NOW(),
  paid_at TIMESTAMP
);

-- рассылки (админ-бот)
CREATE TABLE IF NOT EXISTS broadcasts (
  id BIGSERIAL PRIMARY KEY,
  author_user_id BIGINT,             -- админ кто запустил
  text TEXT NOT NULL,
  inline_keyboard JSONB,
  status VARCHAR(16) DEFAULT 'draft',-- draft/sent/failed/partial
  created_at TIMESTAMP DEFAULT NOW(),
  sent_at TIMESTAMP
);

-- прайсинг/наценки (тон/звезды в моменте + ручные цены RUB/USDT)
CREATE TABLE IF NOT EXISTS pricing_rules (
  id BIGSERIAL PRIMARY KEY,
  item_type VARCHAR(16) CHECK (item_type IN ('stars','premium')),
  mode VARCHAR(16) CHECK (mode IN ('dynamic','manual')) NOT NULL,
  markup_percent DECIMAL(8,3),       -- для dynamic (TON)
  manual_price DECIMAL(18,6),        -- для manual (RUB/USDT)
  currency VARCHAR(8),               -- 'RUB','USDT','TON'
  is_active BOOLEAN DEFAULT TRUE,
  bot_id BIGINT UNIQUE REFERENCES user_bots(id) ON DELETE CASCADE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referrals (
  id BIGSERIAL PRIMARY KEY,
  referrer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  referee_id  BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_bots (
  id BIGSERIAL PRIMARY KEY,
  owner_user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  tg_bot_token TEXT NOT NULL,
  tg_bot_id BIGINT UNIQUE,
  bot_username TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
