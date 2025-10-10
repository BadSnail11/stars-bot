# src/services/referral.py

def build_ref_link(bot_username: str, tg_user_id: int) -> str:
    """
    Формирует стабильную deep-link ссылку:
    https://t.me/<bot_username>?start=ref_<tg_user_id>
    """
    username = bot_username.lstrip("@")
    return f"https://t.me/{username}?start={tg_user_id}"
