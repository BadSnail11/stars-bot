# file: send_ton_tontools.py
# pip install TonTools

import asyncio
import os
# from TonTools import TonCenterClient, Wallet
from tonutils.wallet.data import WalletV5Data
from tonutils.client.toncenter import ToncenterV2Client
from tonutils.wallet import WalletV5R1
from tonutils.utils import normalize_hash
import asyncio


# --- Настройки (замените на свои) ---
TON_API_KEY = os.getenv("TON_API_KEY", "ВАШ_TONCENTER_API_KEY")
# MNEMONIC = os.getenv("TON_MNEMONIC", "ваша мнемоническая фраза здесь через пробел")
TON_WALLET = os.getenv("TON_WALLET", "")
COMMENT = "Payment via TonTools"
WALLET_VERSION = "w5"  # варианты: "v5r1", "v4r2", "v3r2". Можно оставить None — TonTools подберёт сам.

def _mnemonics() -> list[str]:
    raw = os.getenv("TON_MNEMONICS", "")
    return [w.strip() for w in raw.replace(",", " ").split() if w.strip()]

async def create_withdraw_request(amount: float, address: str) -> str:

    client = ToncenterV2Client(api_key=TON_API_KEY)

    wallet, public_key, private_key, mnemonic = WalletV5R1.from_mnemonic(client=client, mnemonic=_mnemonics())
    
    tx = await wallet.transfer(
        destination=address,
        amount=amount,
        body="From stars shop"
    )

    return tx

async def check_withdraw_status(tx_hash: str) -> bool:
    await asyncio.sleep(300)
    client = ToncenterV2Client(api_key=TON_API_KEY)

    txs = await client.get_transactions(TON_WALLET, 5)

    status = False

    for tx in txs:
        hs = normalize_hash(tx.in_msg).hex()
        if hs == tx_hash.lower():
            status = not tx.description.aborted

    return status


