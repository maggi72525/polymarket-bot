import requests
import time
import json
import os
import threading

BOT_TOKEN = "8729306597:AAEIpxB8JurlTgQNLCes7s5OWOSQlm6b6ME"
CHAT_ID = "7086039959"
WALLET = "0xc1016d1bfc6244fd51fcf5c8dc1b10afc52be6d1"

DATA_FILE = "trades.json"

# ===== TELEGRAM =====
def send(text, reply=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    if reply:
        payload["reply_to_message_id"] = reply

    r = requests.post(url, json=payload)
    try:
        return r.json()["result"]["message_id"]
    except:
        return None

# ===== KEEP ALIVE =====
def alive():
    while True:
        print("bot alive...")
        time.sleep(60)

threading.Thread(target=alive, daemon=True).start()

# ===== LOAD DATA =====
if os.path.exists(DATA_FILE):
    with open(DATA_FILE,"r") as f:
        buys = json.load(f)
else:
    buys = {}

def save():
    with open(DATA_FILE,"w") as f:
        json.dump(buys,f)

# ===== GET TRADES =====
def get():
    url = "https://data-api.polymarket.com/activity"
    r = requests.get(url, params={"user":WALLET,"limit":40})
    if r.status_code==200:
        return r.json()
    return []

# ===== MAIN =====
print("BOT STARTED")

seen=set()

while True:
    try:
        trades=get()

        for t in reversed(trades):
            tid=t.get("id") or t.get("txHash")
            if not tid or tid in seen:
                continue

            seen.add(tid)

            side=t.get("side","").upper()
            title=t.get("title","Unknown")
            outcome=t.get("outcome","?")
            price=float(t.get("price",0))*100
            value=float(t.get("usdcSize",0))
            slug=t.get("slug")

            market=f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"
            profile=f"https://polymarket.com/profile/{WALLET}"

            key=f"{title}-{outcome}"

            # BUY
            if side=="BUY":
                msg=(
                    f"🟢 <b>BUY</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"📊 <b>{title}</b>\n"
                    f"🎯 Outcome: {outcome}\n"
                    f"💰 Price: {price:.1f}¢\n"
                    f"💵 Value: ${value:.2f}\n\n"
                    f"🔗 <a href='{market}'>Open Market</a>\n"
                    f"👤 <a href='{profile}'>Profile</a>"
                )

                mid=send(msg)
                if mid:
                    buys[key]=mid
                    save()

            # SELL
            if side=="SELL" and key in buys:
                reply_id=buys[key]

                sellmsg=(
                    f"🔴 <b>SELL</b>\n"
                    f"📊 {title}\n"
                    f"🎯 {outcome}\n"
                    f"💰 {price:.1f}¢\n"
                    f"💵 ${value:.2f}"
                )

                send(sellmsg, reply=reply_id)
                del buys[key]
                save()

    except Exception as e:
        print("error:",e)

    time.sleep(20)
