# file: send_ton_tontools.py
# pip install TonTools

import asyncio
import os
# from TonTools import TonCenterClient, Wallet
from tonutils.wallet.data import WalletV5Data
from tonutils.client.toncenter import ToncenterV2Client
from tonutils.wallet import WalletV5R1


# --- Настройки (замените на свои) ---
TON_API_KEY = os.getenv("TON_API_KEY", "ВАШ_TONCENTER_API_KEY")
# MNEMONIC = os.getenv("TON_MNEMONIC", "ваша мнемоническая фраза здесь через пробел")
TON_WALLET = os.getenv("TON_WALLET", "")
COMMENT = "Payment via TonTools"
WALLET_VERSION = "w5"  # варианты: "v5r1", "v4r2", "v3r2". Можно оставить None — TonTools подберёт сам.

def _mnemonics() -> list[str]:
    raw = os.getenv("TON_MNEMONICS", "")
    return [w.strip() for w in raw.replace(",", " ").split() if w.strip()]

async def create_withdraw_request(amount: float, address: str):

    client = ToncenterV2Client(api_key=TON_API_KEY)

    wallet, public_key, private_key, mnemonic = WalletV5R1.from_mnemonic(client=client, mnemonic=_mnemonics())

    # Инициализация кошелька. Если версия не указана, TonTools попытается определить подходящую.
    
    tx = await wallet.transfer(
        destination=address,
        amount=amount,
    )
    # Проверим адрес и баланс (необязательно)
    # balance = await wallet.get_balance()
    # print("Wallet address:", await wallet.)
    # balance_nano = await wallet.get_balance()  # в нанотонах
    # print("Current balance (nanoTON):", balance_nano)

    # # Отправка TON. TonTools сам получит seqno и сформирует сообщение.
    # tx = await wallet.transfer_ton(
    #     destination_address=address,
    #     amount=amount,   # в TON, не в nano
    #     message=COMMENT,     # текстовый комментарий (опционально)
    #     send_mode=3,         # pay gas separately; стандартный безопасный режим
    #     # timeout=60           # сек — валидность сообщения (актуально для W5)
    # )

    return tx
    # В tx обычно возвращается словарь с информацией/хэшем отправки (может отличаться по версии)
    # print("Transfer sent:", tx)

