import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = "8729306597:AAEIpxB8JurlTgQNLCes7s5OWOSQlm6b6ME"
CHAT_ID = "7086039959"
WALLET_ADDRESS = "0xc1016d1bfc6244fd51fcf5c8dc1b10afc52be6d1"
POLL_INTERVAL = 20

BASE_URL = "https://data-api.polymarket.com"
seen_trade_ids = set()
open_trades = {}

def send_telegram(message, reply_to=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

def get_recent_trades():
    try:
        url = f"{BASE_URL}/activity"
        params = {"user": WALLET_ADDRESS, "limit": 20}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def format_trade(trade):
    side = trade.get("side", "").upper()
    market = trade.get("title", "Unknown Market")[:60]
    outcome = trade.get("outcome", "?")
    price = float(trade.get("price", 0)) * 100
    size = float(trade.get("size", 0))
    usdc = float(trade.get("usdcSize", 0))

    trade_key = f"{market}-{outcome}"

    if side == "BUY":
        message = (
            f"🟢 BUY\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Market:</b> {market}\n"
            f"🎯 <b>Outcome:</b> {outcome}\n"
            f"💰 <b>Price:</b> {price:.1f}¢\n"
            f"📦 <b>Shares:</b> {size:.2f}\n"
            f"💵 <b>USDC:</b> ${usdc:.2f}\n"
            f"🔗 <a href='https://polymarket.com/profile/{WALLET_ADDRESS}'>View Profile</a>"
        )

        sent = send_telegram(message)
        if sent and sent.get("ok"):
            msg_id = sent["result"]["message_id"]
            open_trades[trade_key] = {
                "price": price,
                "msg_id": msg_id
            }

    elif side == "SELL":
        if trade_key in open_trades:
            buy_price = open_trades[trade_key]["price"]
            msg_id = open_trades[trade_key]["msg_id"]
            profit = ((price - buy_price) / buy_price) * 100 if buy_price else 0

            message = (
                f"🔴 SELL\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Market:</b> {market}\n"
                f"🎯 <b>Outcome:</b> {outcome}\n"
                f"💰 <b>Sell Price:</b> {price:.1f}¢\n"
                f"📦 <b>Shares:</b> {size:.2f}\n"
                f"💵 <b>USDC:</b> ${usdc:.2f}\n"
                f"📈 <b>Profit:</b> {profit:.1f}%"
            )

            send_telegram(message, reply_to=msg_id)
            del open_trades[trade_key]
        else:
            message = f"🔴 SELL {market} {outcome} @ {price:.1f}¢"
            send_telegram(message)

def monitor():
    print(f"Bot started! Tracking: {WALLET_ADDRESS}")
    trades = get_recent_trades()
    for t in trades:
        seen_trade_ids.add(t.get("id") or t.get("txHash") or str(t))
    send_telegram(f"🤖 <b>Bot Started!</b>\n👛 Tracking:\n<code>{WALLET_ADDRESS}</code>")
    while True:
        try:
            trades = get_recent_trades()
            for trade in reversed(trades):
                tid = trade.get("id") or trade.get("txHash") or str(trade)
                if tid not in seen_trade_ids:
                    seen_trade_ids.add(tid)
                    send_telegram(format_trade(trade))
                    print("New trade sent!")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":

    monitor()
