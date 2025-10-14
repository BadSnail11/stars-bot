# src/handlers/test_fragment.py
from aiogram import Router, types
from aiogram.filters import Command, CommandObject
import os, json, textwrap
from ..services.fragment import buy_stars

def _is_admin(user_id: int) -> bool:
    raw = os.getenv("ADMIN_IDS", "")
    ids = {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}
    return user_id in ids

def get_router() -> Router:
    router = Router(name="test_fragment")

    @router.message(Command("test_stars"))
    async def test_stars(m: types.Message, command: CommandObject):
        # if not _is_admin(m.from_user.id):
        #     await m.answer("⛔ Недостаточно прав.")
        #     return

        if not command.args:
            await m.answer(
                "Использование:\n"
                "<code>/test_stars &lt;recipient&gt; &lt;qty&gt;</code>\n\n"
                "Примеры:\n"
                "<code>/test_stars @username 100</code>\n"
                "<code>/test_stars +79990001122 250</code>"
            )
            return

        parts = command.args.split()
        if len(parts) != 2:
            await m.answer("Нужно два аргумента: <recipient> <qty>")
            return

        recipient, qty_str = parts
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError()
        except Exception:
            await m.answer("Количество должно быть целым числом > 0.")
            return

        await m.answer(f"⏳ Отправляю в Fragment: {recipient}, {qty} ⭐ …")
        recipient = recipient[1::]
        try:
            resp = await buy_stars(recipient=recipient, quantity=qty)
            pretty = json.dumps(resp, ensure_ascii=False, indent=2)
            await m.answer(
                "✅ Fragment ответил:\n"
                f"<pre>{textwrap.shorten(pretty, width=3500, placeholder='…')}</pre>",
                parse_mode="HTML",
            )
        except Exception as e:
            await m.answer(f"❌ Ошибка вызова Fragment: <code>{e}</code>", parse_mode="HTML")

    return router
