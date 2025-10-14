from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import types
from ..models import RequiredChannel
from typing import Optional

def admin_kb(is_super: bool = False, is_main: bool = False):
    kb = InlineKeyboardBuilder()
    kb.row(*[types.InlineKeyboardButton(text="💲 Цены", callback_data="pricing"), types.InlineKeyboardButton(text="📊 Статистика", callback_data="statistics")])
    if is_super:
        kb.row(*[types.InlineKeyboardButton(text="🔗 Каналы", callback_data="channels"), types.InlineKeyboardButton(text="📣 Рассылка", callback_data="broadcasts")])
    if is_main:
        kb.row(*[types.InlineKeyboardButton(text="Предоставить супер права", callback_data="super")])
    return kb.as_markup()

def nav_to_menu():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Назад", callback_data="back"))
    return kb.as_markup()

def pricing_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Изменить цены", callback_data="change_pricing"))
    kb.row(types.InlineKeyboardButton(text="Назад", callback_data="back"))
    return kb.as_markup()

def product_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Звезды", callback_data="change_stars"))
    kb.row(types.InlineKeyboardButton(text="Премиум", callback_data="change_premium"))
    kb.row(types.InlineKeyboardButton(text="Назад", callback_data="back"))
    return kb.as_markup()

def channels_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Добавить канал", callback_data="add_channel"))
    kb.row(types.InlineKeyboardButton(text="Удалить канал канал", callback_data="delete_channel"))
    kb.row(types.InlineKeyboardButton(text="Назад", callback_data="back"))
    return kb.as_markup()

def list_channels_kb(channels: list[RequiredChannel]):
    kb = InlineKeyboardBuilder()
    for channel in channels:
        kb.row(types.InlineKeyboardButton(text=channel.channel_username, callback_data=f"delete_id_{channel.id}"))
    kb.row(types.InlineKeyboardButton(text="Назад", callback_data="back"))
    return kb.as_markup()

def broadcasts_kb():
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 Создать рассылку", callback_data="broadcasts_create")],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])
    return kb

def stats_root_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📄 Заказы (экспорт)", callback_data="st_orders")],
        [types.InlineKeyboardButton(text="👥 Пользователи (экспорт)", callback_data="st_users")],
        [types.InlineKeyboardButton(text="🔎 Заказы пользователя (экспорт)", callback_data="st_user_orders")],
        [types.InlineKeyboardButton(text="⬅️ В меню", callback_data="back_to_menu")],
    ])

def orders_filter_kb(scope: str, user_id: Optional[int] = None):
    # scope: "all" | "user"
    uid_sfx = f"_{user_id}" if (scope == "user" and user_id is not None) else ""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Только успешные", callback_data=f"st_do_{scope}_paid{uid_sfx}"),
            types.InlineKeyboardButton(text="Все", callback_data=f"st_do_{scope}_all{uid_sfx}")
        ],
        [types.InlineKeyboardButton(text="⬅️ В разделы", callback_data="statistics")]
    ])

def file_to_menu():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Назад", callback_data="file_back"))
    return kb.as_markup()

def periods_kb(cbprefix: str, extra: Optional[str] = None):
    """
    cbprefix: 'st_do_all_paid', 'st_do_all_all', 'st_do_user_paid_<uid>', 'st_do_user_all_<uid>', 'st_do_users'
    формируем: {prefix}_period_<key>  (где key in 24h|7d|30d)
    """
    sfx = f"_{extra}" if extra else ""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🕐 24 часа", callback_data=f"{cbprefix}_period_24h{sfx}")
        ],
        [
            types.InlineKeyboardButton(text="📅 7 дней", callback_data=f"{cbprefix}_period_7d{sfx}")
        ],
        [
            types.InlineKeyboardButton(text="🗓 1 месяц", callback_data=f"{cbprefix}_period_30d{sfx}")
        ],
        [types.InlineKeyboardButton(text="⬅️ В разделы", callback_data="st_home")]
    ])