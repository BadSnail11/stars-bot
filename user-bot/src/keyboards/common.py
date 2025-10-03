from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def offer_kb(agree_cb: str, disagree_cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="Согласен", callback_data=agree_cb)
    kb.button(text="Не согласен", callback_data=disagree_cb)
    return kb.as_markup()

def check_subs_kb(channels: list[str], check_cb: str):
    kb = InlineKeyboardBuilder()
    for ch in channels:
        ch_name = ch.lstrip("@")
        kb.button(text=f"Подписаться: {ch}", url=f"https://t.me/{ch_name}")
    kb.button(text="Проверить подписку ✅", callback_data=check_cb)
    return kb.as_markup()

def main_menu_kb() -> types.ReplyKeyboardMarkup:
    kb = [
        [types.KeyboardButton(text="⭐ Купить звёзды"), types.KeyboardButton(text="👑 Премиум")],
        # [types.KeyboardButton(text="👑 Премиум")],
        [types.KeyboardButton(text="🧾 История заказов"), types.KeyboardButton(text="🆘 Поддержка")],
        [types.KeyboardButton(text="👥 Реферальная программа"), types.KeyboardButton(text="🤖 Создать свой бот")],
        [types.KeyboardButton(text="📄 Оферта")],
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def who_kb(self_cb: str, gift_cb: str, cancel_cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Себе", callback_data=self_cb)
    kb.button(text="🎁 Подарок", callback_data=gift_cb)
    kb.button(text="Отмена", callback_data=cancel_cb)
    return kb.as_markup()

def cancel_kb(cancel_cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="Отмена", callback_data=cancel_cb)
    return kb.as_markup()
