import requests
import time
import json
import os

# ================== CONFIG ==================

BOT_TOKEN = "8729306597:AAEIpxB8JurlTgQNLCes7s5OWOSQlm6b6ME"
CHAT_ID = "7086039959"
WALLET_ADDRESS = "0x1016d1bfc6244fd51fcf5c8dc1b10afc52be6d1"

BASE_URL = "https://data-api.polymarket.com"
POLL_INTERVAL = 25

DATA_FILE = "trades.json"
STATS_FILE = "stats.json"

PROFILE_LINK = f"https://polymarket.com/profile/{WALLET_ADDRESS}"

# ================== TELEGRAM ==================

def send_telegram(message, reply_to=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        if reply_to:
            data["reply_to_message_id"] = reply_to

        requests.post(url, data=data, timeout=10)

    except Exception as e:
        print("Telegram error:", e)
```

# ================== LOAD DATA ==================

if os.path.exists(DATA_FILE):
with open(DATA_FILE, "r") as f:
open_trades = json.load(f)
else:
open_trades = {}

if os.path.exists(STATS_FILE):
with open(STATS_FILE, "r") as f:
stats = json.load(f)
else:
stats = {"total":0,"wins":0,"losses":0,"profit":0}

def save_data():
with open(DATA_FILE,"w") as f:
json.dump(open_trades,f)

def save_stats():
with open(STATS_FILE,"w") as f:
json.dump(stats,f)

# ================== FETCH TRADES ==================

def get_trades():
url = f"{BASE_URL}/activity"
params = {"user": WALLET_ADDRESS, "limit": 40}
try:
r = requests.get(url, params=params, timeout=15)
if r.status_code == 200:
return r.json()
except:
pass
return []

# ================== FORMAT ==================

def format_trade(trade):
side = trade.get("side","").upper()
market = trade.get("title","Unknown")[:90]
outcome = trade.get("outcome","?")
price = float(trade.get("price",0))*100
size = float(trade.get("size",0))
usdc = float(trade.get("usdcSize",0))
slug = trade.get("slug")

```
if slug:
    market_link = f"https://polymarket.com/event/{slug}"
else:
    market_link = "https://polymarket.com"

asset = f"{market}-{outcome}"

# ================= BUY =================
if side == "BUY":
    msg = (
        f"🟢 <b>BUY</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 <b>{market}</b>\n"
        f"🎯 Outcome: {outcome}\n"
        f"💰 Price: {price:.2f}¢\n"
        f"📦 Shares: {size:.2f}\n"
        f"💵 Value: ${usdc:.2f}\n\n"
        f"🔗 <a href='{market_link}'>Open Market</a>\n"
        f"👤 <a href='{PROFILE_LINK}'>Wallet Profile</a>"
    )

    msg_id = send_telegram(msg)

    open_trades[asset] = {
        "buy_price": price,
        "buy_value": usdc,
        "msg_id": msg_id
    }
    save_data()
    return

# ================= SELL =================
if side == "SELL":
    if asset in open_trades:
        buy = open_trades[asset]
        buy_price = buy["buy_price"]
        buy_value = buy["buy_value"]
        reply_id = buy["msg_id"]

        profit_pct = ((price-buy_price)/buy_price)*100 if buy_price else 0
        profit_usd = usdc - buy_value

        stats["total"] += 1
        stats["profit"] += profit_usd

        if profit_usd > 0:
            stats["wins"] += 1
        else:
            stats["losses"] += 1

        save_stats()

        # emoji logic
        if profit_pct >= 50:
            emoji="🚀"
        elif profit_pct >= 15:
            emoji="🟢"
        elif profit_pct >= 0:
            emoji="🟡"
        else:
            emoji="🔴"

        sell_msg = (
            f"{emoji} <b>SELL CLOSED</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📊 <b>{market}</b>\n"
            f"🎯 Outcome: {outcome}\n"
            f"💰 Sell Price: {price:.2f}¢\n"
            f"💵 Exit: ${usdc:.2f}\n"
            f"📈 PnL: {profit_pct:.1f}% (${profit_usd:.2f})\n\n"
            f"🔗 <a href='{market_link}'>Open Market</a>"
        )

        send_telegram(sell_msg, reply_to=reply_id)

        del open_trades[asset]
        save_data()
```

# ================= STATS =================

def send_stats():
total=stats["total"]
wins=stats["wins"]
losses=stats["losses"]
profit=stats["profit"]
winrate=(wins/total*100) if total>0 else 0

```
msg=(
    f"📊 <b>Wallet Stats</b>\n"
    f"Total Trades: {total}\n"
    f"🟢 Wins: {wins}\n"
    f"🔴 Losses: {losses}\n"
    f"🏆 Winrate: {winrate:.1f}%\n"
    f"💰 Total Profit: ${profit:.2f}"
)
send_telegram(msg)
```

# ================= COMMAND LISTENER =================

last_update=0
def check_commands():
global last_update
url=f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
params={"offset":last_update+1,"timeout":2}
try:
r=requests.get(url,params=params,timeout=10).json()
for u in r.get("result",[]):
last_update=u["update_id"]
text=u.get("message",{}).get("text","")
if text=="/stats":
send_stats()
except:
pass

# ================= MAIN LOOP =================

print("Bot running...")
seen=set()

while True:
try:
trades=get_trades()
for t in reversed(trades):
tid=t.get("id") or str(t)
if tid not in seen:
seen.add(tid)
format_trade(t)
print("Trade sent")

```
    check_commands()
    time.sleep(POLL_INTERVAL)

except Exception as e:
    print("Error:",e)
    time.sleep(10)
```

