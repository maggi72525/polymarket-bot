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
trade_history = {}

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
    market = trade.get("title", "Unknown Market")
    outcome = trade.get("outcome", "?")
    price = float(trade.get("price", 0)) * 100
    size = float(trade.get("size", 0))
    usdc = float(trade.get("usdcSize", 0))
    asset = trade.get("asset", market + outcome)

    market_slug = trade.get("slug", "")
    market_link = f"https://polymarket.com/event/{market_slug}" if market_slug else "https://polymarket.com"

    # ================= BUY =================
    if side == "BUY":
        msg = (
            f"🟢 <b>BUY</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>{market}</b>\n"
            f"🎯 Outcome: {outcome}\n"
            f"💰 Price: {price:.1f}¢\n"
            f"📦 Shares: {size:.2f}\n"
            f"💵 Value: ${usdc:.2f}\n"
            f"🔗 <a href='{market_link}'>Open Market</a>"
        )

        sent = send_telegram(msg)
        if sent and sent.get("ok"):
            msg_id = sent["result"]["message_id"]
            open_trades[asset] = {
                "buy_price": price,
                "buy_value": usdc,
                "msg_id": msg_id,
                "market": market,
                "outcome": outcome
            }

    # ================= SELL =================
    elif side == "SELL":
        if asset in open_trades:
            buy_data = open_trades[asset]
            buy_price = buy_data["buy_price"]
            buy_value = buy_data["buy_value"]
            msg_id = buy_data["msg_id"]

            profit_pct = ((price - buy_price) / buy_price) * 100 if buy_price else 0
            profit_usd = usdc - buy_value

            # emoji logic
            if profit_pct >= 50:
                emoji = "🚀"
            elif profit_pct >= 15:
                emoji = "🟢"
            elif profit_pct >= 0:
                emoji = "🟡"
            else:
                emoji = "🔴"

            sell_msg = (
                f"{emoji} <b>SELL CLOSED</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>{market}</b>\n"
                f"🎯 Outcome: {outcome}\n"
                f"💰 Sell Price: {price:.1f}¢\n"
                f"💵 Exit Value: ${usdc:.2f}\n"
                f"📈 PnL: {profit_pct:.1f}% (${profit_usd:.2f})"
            )

            send_telegram(sell_msg, reply_to=msg_id)
            del open_trades[asset]

        else:
            # fallback sell
            send_telegram(f"🔴 SELL {market} {outcome} @ {price:.1f}¢")
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

