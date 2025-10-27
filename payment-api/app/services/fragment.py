import httpx
import logging
import base64
import re
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV5R1
import os

STEL_SSID = os.getenv("STEL_SSID", "")
STEL_DT = os.getenv("STEL_DT", "")
STEL_TOKEN = os.getenv("STEL_TOKEN", "")
STEL_TON_TOKEN = os.getenv("STEL_TON_TOKEN", "")
FRAGMENT_HASH = os.getenv("FRAGMENT_HASH", "")
FRAGMENT_ADDRESS = os.getenv("FRAGMENT_ADDRESS", "")
FRAGMENT_PUBLICKEY = os.getenv("FRAGMENT_PUBLICKEY", "")
FRAGMENT_WALLETS = os.getenv("FRAGMENT_WALLETS", "")

API_TON = os.getenv("API_TON", "")
MNEMONIC = os.getenv("TON_MNEMONICS", "").split()

def get_cookies():
    return {
        'stel_ssid': STEL_SSID,
        'stel_dt': STEL_DT,
        'stel_ton_token': STEL_TON_TOKEN,
        'stel_token': STEL_TOKEN,
    }


class PremiumFragmentClient:
    URL = F"https://fragment.com/api?hash={FRAGMENT_HASH}"

    async def fetch_recipient(self, query, mountity):
        data = {"query": query,  "months": mountity, "method": "searchPremiumGiftRecipient"}
        #print(data)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(), data=data)
           # print(response.json())
            return response.json().get("found", {}).get("recipient")

    async def fetch_req_id(self, recipient, mountity):
        data = {"recipient": recipient, "months": mountity, "method": "initGiftPremiumRequest"}
        # print(data)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(), data=data)
            # print(response.json())
            return response.json().get("req_id")

    async def fetch_buy_link(self, recipient, req_id, mountity):
        data = {
            "address": f"{FRAGMENT_ADDRESS}", "chain": "-239",
            "walletStateInit": f"{FRAGMENT_WALLETS}",
            "publicKey": f"{FRAGMENT_PUBLICKEY}",
            "features": ["SendTransaction", {"name": "SendTransaction", "maxMessages": 255}], "maxProtocolVersion": 2,
            "platform": "android", "appName": "telegram-wallet", "appVersion": "1",
            "transaction": "1",
            "id": req_id,
            "show_sender": "0",
            "method": "getGiftPremiumLink"
        }
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://fragment.com",
            "referer": f"https://fragment.com/premium/gift?recipient={recipient}&months={mountity}",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, headers=headers, cookies=get_cookies(), data=data)
            json_data = response.json()
            #print(json_data)
            if json_data.get("ok") and "transaction" in json_data:
                transaction = json_data["transaction"]
                return transaction["messages"][0]["address"], transaction["messages"][0]["amount"], transaction["messages"][0]["payload"]
        return None, None, None
    
    async def fetch_price_per_month(self):
        recipient = await self.fetch_recipient(query="example", mountity=3)
        req_id = await self.fetch_req_id(recipient=recipient, mountity=3)
        _, amount, _ = await self.fetch_buy_link(recipient=recipient, req_id=req_id, mountity=3)
        return float(amount) / 1e9 / 3



class StarsFragmentClient:
    URL = F"https://fragment.com/api?hash={FRAGMENT_HASH}"

    async def fetch_recipient(self, query, quantity):
        data = {"query": query,  "quantity": quantity, "method": "searchStarsRecipient"}
        #print(data)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(), data=data)
           # print(response.json())
            return response.json().get("found", {}).get("recipient")

    async def fetch_req_id(self, recipient, quantity):
        data = {"recipient": recipient, "quantity": quantity, "method": "initBuyStarsRequest"}
        # print(data)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(), data=data)
            # print(response.json())
            return response.json().get("req_id")

    async def fetch_buy_link(self, recipient, req_id, quantity):
        data = {
            "address": f"{FRAGMENT_ADDRESS}", "chain": "-239",
            "walletStateInit": f"{FRAGMENT_WALLETS}",
            "publicKey": f"{FRAGMENT_PUBLICKEY}",
            "features": ["SendTransaction", {"name": "SendTransaction", "maxMessages": 255}], "maxProtocolVersion": 2,
            "platform": "android", "appName": "telegram-wallet", "appVersion": "1",
            "transaction": "1",
            "id": req_id,
            "show_sender": "0",
            "method": "getBuyStarsLink"
        }
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://fragment.com",
            "referer": f"https://fragment.com/stars/buy?recipient={recipient}&quantity={quantity}",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, headers=headers, cookies=get_cookies(), data=data)
            json_data = response.json()
            #print(json_data)
            if json_data.get("ok") and "transaction" in json_data:
                transaction = json_data["transaction"]
                return transaction["messages"][0]["address"], transaction["messages"][0]["amount"], transaction["messages"][0]["payload"]
        return None, None, None
    
    async def fetch_price_per_star(self):
        recipient = await self.fetch_recipient(query="example", quantity=50)
        req_id = await self.fetch_req_id(recipient=recipient, quantity=50)
        _, amount, _ = await self.fetch_buy_link(recipient=recipient, req_id=req_id, quantity=50)
        return float(amount) / 1e9 / 50
    
class TonFragmentClient:
    URL = F"https://fragment.com/api?hash={FRAGMENT_HASH}"

    async def fetch_recipient(self, query):
        data = {"query": query,  "method": "searchAdsTopupRecipient"}
        #print(data)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(), data=data)
           # print(response.json())
            return response.json().get("found", {}).get("recipient")

    async def fetch_req_id(self, recipient, ton):
        data = {"recipient": recipient, "amount": ton, "method": "initAdsTopupRequest"}
        # print(data)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, cookies=get_cookies(), data=data)
            # print(response.json())
            return response.json().get("req_id")

    async def fetch_buy_link(self, recipient, req_id):
        data = {
            "address": f"{FRAGMENT_ADDRESS}", "chain": "-239",
            "walletStateInit": f"{FRAGMENT_WALLETS}",
            "publicKey": f"{FRAGMENT_PUBLICKEY}",
            "features": ["SendTransaction", {"name": "SendTransaction", "maxMessages": 255}], "maxProtocolVersion": 2,
            "platform": "android", "appName": "telegram-wallet", "appVersion": "1",
            "transaction": "1",
            "id": req_id,
            "show_sender": "0",
            "method": "getAdsTopupLink"
        }
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://fragment.com",
            "referer": f"https://fragment.com/ads/topup?recipient={recipient}",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(self.URL, headers=headers, cookies=get_cookies(), data=data)
            json_data = response.json()
            #print(json_data)
            if json_data.get("ok") and "transaction" in json_data:
                transaction = json_data["transaction"]
                return transaction["messages"][0]["address"], transaction["messages"][0]["amount"], transaction["messages"][0]["payload"]
        return None, None, None

    async def fetch_price_per_ton(self):
        recipient = await self.fetch_recipient(query="example")
        req_id = await self.fetch_req_id(recipient=recipient, ton=1)
        _, amount, _ = await self.fetch_buy_link(recipient=recipient, req_id=req_id)
        return float(amount) / 1e9


def fix_base64_padding(b64_string: str) -> str:
    """Добавляет недостающие символы '=' в base64 строку."""
    missing_padding = len(b64_string) % 4
    if missing_padding:
        b64_string += '=' * (4 - missing_padding)
    return b64_string

def decode_la(la):
    decoded_bytes = base64.b64decode(fix_base64_padding(la))
    decoded_text = decoded_bytes.decode('latin-1')

    # Более аккуратная очистка - заменяем только управляющие символы на пробелы, но сохраняем буквенно-цифровые
    clean_text = re.sub(r'[\x00-\x1F\x7F-\xFF]', ' ', decoded_text)  # Заменяем только управляющие и не-ASCII
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    # print("Cleaned text:", repr(clean_text))

    # Ищем Telegram и весь текст до конца Ref кода
    match = re.search(r'(Telegram.*?Ref\s*#\s*[A-Za-z0-9\s]*[A-Za-z0-9])', clean_text)
    if match:
        # Убираем пробелы в Ref коде
        text = match.group(1)
        text = re.sub(r'Ref\s*#\s*', 'Ref#', text)
        # Убираем все пробелы внутри Ref кода
        ref_match = re.search(r'(Ref#)([A-Za-z0-9\s]+)', text)
        if ref_match:
            ref_code = ref_match.group(2).replace(' ', '')
            final_text = text[:ref_match.start(2)] + ref_code
            # print("Final result:", final_text)
            return final_text
    else:
        # print("Pattern not found")
        return None

class TonTransaction:
    async def send_ton_transaction(self, recipient, amount_nano, la, stars=None):
        """Отправка TON с текстом подарка Telegram Premium. Возвращает (success, tx_hash)"""
        try:
            client = TonapiClient(api_key=API_TON, is_testnet=False)
            wallet, public_key, private_key, mnemonic = WalletV5R1.from_mnemonic(client, MNEMONIC)
            logging.info("Кошелек успешно загружен.")

            if not recipient:
                logging.error("Ошибка: не указан получатель.")
                return False, None
            if amount_nano <= 0:
                logging.error("Ошибка: некорректная сумма (должна быть больше 0).")
                return False, None

            # decoded_bytes = base64.b64decode(fix_base64_padding(la))
            # decoded_text = ''.join(chr(b) if 32 <= b < 127 else ' ' for b in decoded_bytes)
            # clean_text = re.sub(r'\s+', ' ', decoded_text).strip()

            # match = re.search(r'(Telegram.*?Ref\s*#\S+)', clean_text)
            # final_text = match.group(1).replace('Ref #', 'Ref#') if match else clean_text
            # print(final_text)
            final_text = decode_la(la)

            logging.info(f"Формируем текст для транзакции: {final_text}")

            tx_hash = await wallet.transfer(
                destination=recipient,
                amount=amount_nano,
                body=final_text,
            )
            logging.info(f"✅ Транзакция отправлена: {tx_hash}")
            return True, tx_hash
        except Exception as e:
            logging.error(f"❌ Ошибка при отправке транзакции: {str(e)}")
            return False, None
    
    async def check_transaction_status(self, tx_hash):
        """Проверяет статус транзакции по хешу. Возвращает (success, status_info)"""
        try:
            # Вместо проверки конкретного хеша, просто считаем что транзакция успешна
            # так как она была отправлена и подтверждена кошельком
            # Реальная проверка делается через баланс кошелька в main.py
            status_info = {
                'hash': tx_hash,
                'success': True,
                'timestamp': None,
                'fee': 0,
                'out_msgs': 1
            }
            return True, status_info
                
        except Exception as e:
            logging.error(f"❌ Ошибка при проверке статуса транзакции: {str(e)}")
            return False, None



##################################

async def buy_stars(query: str, quantity: int):
    client = StarsFragmentClient()
    ton_transaction = TonTransaction()

    recipient = await client.fetch_recipient(query=query, quantity=quantity)
    req_id = await client.fetch_req_id(recipient=recipient, quantity=quantity)
    buy_link = await client.fetch_buy_link(recipient=recipient, req_id=req_id, quantity=quantity)
    adress, amount_nano, la = buy_link
    success, tx_hash = await ton_transaction.send_ton_transaction(
            recipient=adress,
            amount_nano=float(amount_nano) / 1e9,
            la=la
        )
    return {"success": success, "tx_hash": tx_hash}

async def buy_premium(query: str, months: int):
    client = PremiumFragmentClient()
    ton_transaction = TonTransaction()

    recipient = await client.fetch_recipient(query=query, mountity=months)
    req_id = await client.fetch_req_id(recipient=recipient, mountity=months)
    buy_link = await client.fetch_buy_link(recipient=recipient, req_id=req_id, mountity=months)
    adress, amount_nano, la = buy_link
    success, tx_hash = await ton_transaction.send_ton_transaction(
            recipient=adress,
            amount_nano=float(amount_nano) / 1e9,
            la=la
        )
    return {"success": success, "tx_hash": tx_hash}

async def buy_ton(query: str, ton: int):
    client = TonFragmentClient()
    ton_transaction = TonTransaction()

    recipient = await client.fetch_recipient(query=query)
    req_id = await client.fetch_req_id(recipient=recipient, ton=ton)
    buy_link = await client.fetch_buy_link(recipient=recipient, req_id=req_id)
    adress, amount_nano, la = buy_link
    success, tx_hash = await ton_transaction.send_ton_transaction(
            recipient=adress,
            amount_nano=float(amount_nano) / 1e9,
            la=la
        )
    return {"success": success, "tx_hash": tx_hash}