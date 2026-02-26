import requests
import time
import json
import os

# ================= CONFIG =================
BOT_TOKEN = "8729306597:AAEIpxB8JurlTgQNLCes7s5OWOSQlm6b6ME"
CHAT_ID = "7086039959"
WALLET_ADDRESS = "0xc1016d1bfc6244fd51fcf5c8dc1b10afc52be6d1"
POLL_INTERVAL = 20
BASE_URL = "https://data-api.polymarket.com"
# ==========================================

seen_trade_ids = set()
DATA_FILE = "trades.json"
STATS_FILE = "stats.json"

# ===== load open trades =====
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        open_trades = json.load(f)
else:
    open_trades = {}

def save_trades():
    with open(DATA_FILE, "w") as f:
        json.dump(open_trades, f)

# ===== load stats =====
if os.path.exists(STATS_FILE):
    with open(STATS_FILE, "r") as f:
        stats = json.load(f)
else:
    stats = {
        "total": 0,
        "wins": 0,
        "losses": 0,
        "profit": 0
    }

def save_stats():
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

# ===== telegram sender =====
def send_telegram(message, reply_to=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    r = requests.post(url, data=payload)
    try:
        return r.json()["result"]["message_id"]
    except:
        return None

# ===== get trades =====
def get_recent_trades():
    try:
        url = f"{BASE_URL}/activity"
        params = {"user": WALLET_ADDRESS, "limit": 30}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

# ===== format trade =====
def format_trade(trade):
    side = trade.get("side", "").upper()
    market = trade.get("title", "Unknown")[:80]
    outcome = trade.get("outcome", "?")
    price = float(trade.get("price", 0)) * 100
    size = float(trade.get("size", 0))
    usdc = float(trade.get("usdcSize", 0))
    asset = f"{market}-{outcome}"

    market_link = f"https://polymarket.com/event/{trade.get('slug','')}"

    # ================= BUY =================
    if side == "BUY":
        msg = (
            f"🟢 <b>BUY</b>\n"
            f"━━━━━━━━━━━━\n"
            f"📊 <b>{market}</b>\n"
            f"🎯 Outcome: {outcome}\n"
            f"💰 Price: {price:.1f}¢\n"
            f"📦 Shares: {size:.2f}\n"
            f"💵 Value: ${usdc:.2f}\n"
            f"🔗 <a href='{market_link}'>Open Market</a>"
        )

        msg_id = send_telegram(msg)

        open_trades[asset] = {
            "buy_price": price,
            "buy_value": usdc,
            "msg_id": msg_id,
            "market": market,
            "outcome": outcome
        }
        save_trades()
        return

    # ================= SELL =================
    if side == "SELL":
        if asset in open_trades:
            buy_data = open_trades[asset]
            buy_price = buy_data["buy_price"]
            buy_value = buy_data["buy_value"]
            reply_msg = buy_data["msg_id"]

            profit_pct = ((price - buy_price) / buy_price) * 100 if buy_price else 0
            profit_usd = usdc - buy_value

            stats["total"] += 1
            stats["profit"] += profit_usd
            if profit_usd > 0:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
            save_stats()

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
                f"━━━━━━━━━━━━\n"
                f"📊 <b>{market}</b>\n"
                f"🎯 Outcome: {outcome}\n"
                f"💰 Sell Price: {price:.1f}¢\n"
                f"💵 Exit Value: ${usdc:.2f}\n"
                f"📈 PnL: {profit_pct:.1f}% (${profit_usd:.2f})"
            )

            send_telegram(sell_msg, reply_to=reply_msg)

            del open_trades[asset]
            save_trades()
            return

        else:
            send_telegram(f"🔴 SELL {market} {outcome} @ {price:.1f}¢")

# ===== stats command =====
def check_commands():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        res = requests.get(url).json()

        for update in res.get("result", []):
            if "message" in update:
                text = update["message"].get("text", "")
                chat = update["message"]["chat"]["id"]

                if text == "/stats":
                    total = stats["total"]
                    wins = stats["wins"]
                    losses = stats["losses"]
                    profit = stats["profit"]
                    winrate = (wins/total*100) if total>0 else 0

                    msg = (
                        f"📊 <b>Wallet Stats</b>\n"
                        f"Total Trades: {total}\n"
                        f"🟢 Wins: {wins}\n"
                        f"🔴 Losses: {losses}\n"
                        f"🏆 Winrate: {winrate:.1f}%\n"
                        f"💰 Total Profit: ${profit:.2f}"
                    )

                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        data={"chat_id": chat, "text": msg, "parse_mode":"HTML"}
                    )

        if res.get("result"):
            last = res["result"][-1]["update_id"]
            requests.get(f"{url}?offset={last+1}")

    except:
        pass

# ===== monitor loop =====
def monitor():
    print(f"Bot started tracking {WALLET_ADDRESS}")
    send_telegram(f"🤖 <b>Bot Started</b>\nTracking:\n<code>{WALLET_ADDRESS}</code>")

    while True:
        try:
            trades = get_recent_trades()
            for t in reversed(trades):
                tid = t.get("id") or t.get("txHash") or str(t)
                if tid not in seen_trade_ids:
                    seen_trade_ids.add(tid)
                    format_trade(t)
                    print("New trade sent")

        except Exception as e:
            print("Error:", e)

        check_commands()
        time.sleep(POLL_INTERVAL)

# ===== start =====
if __name__ == "__main__":
    monitor()
