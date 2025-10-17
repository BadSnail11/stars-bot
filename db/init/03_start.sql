INSERT INTO user_bots (tg_bot_token, tg_bot_id, bot_username, is_super)
VALUES ('8255159117:AAGSYPbLAtfFKhIlEQUvDf8swnFptujKXMc', '8255159117', '@stars_frag_bot', true);

INSERT INTO pricing_rules (item_type, mode, manual_price, currency, bot_id)
VALUES ('stars', 'manual', 1, 'RUB', 1);

INSERT INTO pricing_rules (item_type, mode, manual_price, currency, bot_id)
VALUES ('premium', 'manual', 1, 'RUB', 1);

INSERT INTO pricing_rules (item_type, mode, manual_price, currency, bot_id)
VALUES ('ton', 'manual', 1, 'RUB', 1);