import requests
import time
import json
import os

# ================== CONFIG ==================
BOT_TOKEN = "8729306597:AAEIpxB8JurlTgQNLCes7s5OWOSQlm6b6ME"
CHAT_ID = "7086039959"

WALLET_ADDRESS = "0xc1016d1bfc6244fd51fcf5c8dc1b10afc52be6d1"
BASE_URL = "https://data-api.polymarket.com"
POLL_INTERVAL = 25

DATA_FILE = "open_trades.json"
# ============================================

def send_telegram(text, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    if reply_to:
        payload["reply_to_message_id"] = reply_to

    try:
        r = requests.post(url, json=payload, timeout=10)
        res = r.json()
        return res.get("result", {}).get("message_id")
    except Exception as e:
        print("Telegram error:", e)
        return None

# ---------- load saved buys ----------
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        open_trades = json.load(f)
else:
    open_trades = {}

def save_state():
    with open(DATA_FILE, "w") as f:
        json.dump(open_trades, f)

# ---------- get trades ----------
def get_trades():
    try:
        r = requests.get(
            f"{BASE_URL}/activity",
            params={"user": WALLET_ADDRESS, "limit": 30},
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

# ---------- format trade ----------
def handle_trade(trade):
    side = trade.get("side", "").upper()
    title = trade.get("title", "Unknown")[:90]
    outcome = trade.get("outcome", "?")
    price = float(trade.get("price", 0)) * 100
    usdc = float(trade.get("usdcSize", 0))
    slug = trade.get("slug")

    asset = f"{title}-{outcome}"

    market_link = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"
    profile_link = f"https://polymarket.com/profile/{WALLET_ADDRESS}"

    # ================= BUY =================
    if side == "BUY":
        msg = (
            f"🟢 <b>BUY</b>\n"
            f"━━━━━━━━━━━━\n"
            f"📊 <b>{title}</b>\n"
            f"🎯 Outcome: {outcome}\n"
            f"💰 Price: {price:.1f}¢\n"
            f"💵 Value: ${usdc:.2f}\n\n"
            f"🔗 <a href='{market_link}'>Open Market</a>\n"
            f"👤 <a href='{profile_link}'>Wallet Profile</a>"
        )

        msg_id = send_telegram(msg)

        open_trades[asset] = {
            "buy_price": price,
            "value": usdc,
            "msg_id": msg_id
        }
        save_state()
        return

    # ================= SELL =================
    if side == "SELL" and asset in open_trades:
        buy = open_trades[asset]
        profit = usdc - buy["value"]
        pct = ((price - buy["buy_price"]) / buy["buy_price"]) * 100 if buy["buy_price"] else 0

        if pct >= 50:
            emoji = "🚀"
        elif pct >= 15:
            emoji = "🟢"
        elif pct >= 0:
            emoji = "🟡"
        else:
            emoji = "🔴"

        sell_msg = (
            f"{emoji} <b>SELL CLOSED</b>\n"
            f"━━━━━━━━━━━━\n"
            f"📊 <b>{title}</b>\n"
            f"🎯 Outcome: {outcome}\n"
            f"💰 Exit: {price:.1f}¢\n"
            f"📈 PnL: {pct:.1f}% (${profit:.2f})\n\n"
            f"🔗 <a href='{market_link}'>Market</a>"
        )

        send_telegram(sell_msg, reply_to=buy.get("msg_id"))

        del open_trades[asset]
        save_state()

# ================= MAIN =================
def main():
    send_telegram(
        f"🤖 <b>Bot Started</b>\nTracking wallet:\n<code>{WALLET_ADDRESS}</code>"
    )

    seen = set()

    while True:
        try:
            trades = get_trades()

            for t in reversed(trades):
                tid = t.get("id") or t.get("txHash")
                if tid and tid not in seen:
                    seen.add(tid)
                    handle_trade(t)

        except Exception as e:
            print("Error:", e)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
