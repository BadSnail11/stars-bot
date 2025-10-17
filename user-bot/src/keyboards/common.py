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

# def main_menu_kb() -> types.ReplyKeyboardMarkup:
#     kb = [
#         [types.KeyboardButton(text="⭐ Купить звёзды"), types.KeyboardButton(text="👑 Премиум")],
#         # [types.KeyboardButton(text="👑 Премиум")],
#         [types.KeyboardButton(text="🧾 История заказов"), types.KeyboardButton(text="🆘 Поддержка")],
#         [types.KeyboardButton(text="👥 Реферальная программа"), types.KeyboardButton(text="🤖 Создать свой бот")],
#         [types.KeyboardButton(text="📄 Оферта")],
#     ]
#     return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def main_menu_kb() -> types.InlineKeyboardMarkup:
    # kb = [
    #     [types.KeyboardButton(text="⭐ Купить звёзды"), types.KeyboardButton(text="👑 Премиум")],
    #     [types.KeyboardButton(text="🧾 История заказов"), types.KeyboardButton(text="🆘 Поддержка")],
    #     [types.KeyboardButton(text="👥 Реферальная программа"), types.KeyboardButton(text="🤖 Создать свой бот")],
    #     [types.KeyboardButton(text="📄 Оферта")],
    # ]
    kb = InlineKeyboardBuilder()
    kb.row(*[types.InlineKeyboardButton(text="⭐ Купить звёзды", callback_data="stars"), types.InlineKeyboardButton(text="👑 Премиум", callback_data="premium")])
    kb.row(*[types.InlineKeyboardButton(text="💎 Купить TON", callback_data="ton")])
    kb.row(*[types.InlineKeyboardButton(text="🧾 История заказов", callback_data="history"), types.InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")])
    kb.row(*[types.InlineKeyboardButton(text="👥 Реферальная программа", callback_data="referal"), types.InlineKeyboardButton(text="🤖 Создать свой бот", callback_data="create_bot")])
    kb.row(*[types.InlineKeyboardButton(text="📄 Оферта", callback_data="offer")])
    # return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    return kb.as_markup()

def who_kb(self_cb: str, gift_cb: str, cancel_cb: str):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎯 Себе", callback_data=self_cb))
    kb.row(types.InlineKeyboardButton(text="🎁 Подарок", callback_data=gift_cb))
    kb.row(types.InlineKeyboardButton(text="Отмена", callback_data=cancel_cb))
    return kb.as_markup()

def cancel_kb(cancel_cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="Отмена", callback_data=cancel_cb)
    return kb.as_markup()

def payment_methods_kb(sbp_cb: str, ton_cb: str, other_cb: str, cancel_cb: str):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🏦 СБП", callback_data=sbp_cb))
    kb.row(types.InlineKeyboardButton(text="💎 TON", callback_data=ton_cb))
    kb.row(types.InlineKeyboardButton(text="🪙 Другая крипта", callback_data=other_cb))
    kb.row(types.InlineKeyboardButton(text="Отмена", callback_data=cancel_cb))
    return kb.as_markup()

def premium_duration_kb(m3_cb: str, m6_cb: str, m12_cb: str, cancel_cb: str):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="3 мес",  callback_data=m3_cb))
    kb.row(types.InlineKeyboardButton(text="6 мес",  callback_data=m6_cb))
    kb.row(types.InlineKeyboardButton(text="12 мес", callback_data=m12_cb))
    kb.row(types.InlineKeyboardButton(text="Отмена", callback_data=cancel_cb))
    return kb.as_markup()


def history_nav_kb(page: int, has_prev: bool, has_next: bool):
    kb = InlineKeyboardBuilder()
    if has_prev:
        kb.button(text="⬅️ Назад", callback_data=f"hist:{page-1}")
    kb.button(text=f"Стр. {page}", callback_data="hist:stay")
    if has_next:
        kb.button(text="Вперёд ➡️", callback_data=f"hist:{page+1}")
    return kb.as_markup()

def back_nav_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data=f"nav_back")
    return kb.as_markup()

def payment_kb(url: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить", url=url)
    kb.button(text="⬅️ В меню", callback_data="nav_back")
    return kb.as_markup()

