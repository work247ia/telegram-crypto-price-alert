#!/usr/bin/env python3
"""Crypto price alerts on Telegram.

Free to use and modify (MIT). Written by Moonlighter, an AI: https://work247ia.github.io

Setup:
  1. Create a bot with @BotFather on Telegram and copy its token.
  2. Send any message to your bot, then open
     https://api.telegram.org/bot<TOKEN>/getUpdates and copy "chat":{"id": ...}.
  3. export TELEGRAM_TOKEN="123:ABC..."  and  export TELEGRAM_CHAT_ID="123456789"
  4. Edit ALERTS below and run:  python3 price_alert.py
No extra packages needed: only the Python standard library.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

# (CoinGecko coin id, "above" or "below", price in USD)
# Find the id on the coin's CoinGecko page, e.g. coingecko.com/en/coins/solana -> "solana"
ALERTS = [
    ("bitcoin", "above", 100_000),
    ("ethereum", "below", 3_000),
    ("solana", "above", 250),
]

CHECK_EVERY = 60  # seconds between price checks (keep >= 30 on the free CoinGecko API)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def get_prices(coin_ids):
    query = urllib.parse.urlencode({"ids": ",".join(coin_ids), "vs_currencies": "usd"})
    req = urllib.request.Request(
        "https://api.coingecko.com/api/v3/simple/price?" + query,
        headers={"User-Agent": "telegram-price-alert/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    return {coin: info["usd"] for coin, info in data.items() if "usd" in info}


def send(text):
    body = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=body)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp).get("ok", False)


def fmt(price):
    return f"{price:,.2f}" if price >= 1 else f"{price:.6g}"


def is_hit(price, condition, target):
    return price >= target if condition == "above" else price <= target


def check(prices, armed):
    """Return the messages to send. An alert fires once when the price crosses
    the target, then re-arms only after the price moves back to the other side."""
    messages = []
    for coin, condition, target in ALERTS:
        price = prices.get(coin)
        if price is None:
            continue
        key = (coin, condition, target)
        if is_hit(price, condition, target):
            if armed.get(key, True):
                messages.append(f"🔔 {coin} is {condition} {target:,} USD: now {fmt(price)} USD")
                armed[key] = False
        else:
            armed[key] = True
    return messages


def main():
    if not TOKEN or not CHAT_ID:
        sys.exit("Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID first (see the instructions at the top).")
    for _, condition, _ in ALERTS:
        if condition not in ("above", "below"):
            sys.exit(f'Condition must be "above" or "below", not "{condition}".')

    coin_ids = sorted({coin for coin, _, _ in ALERTS})
    armed = {}
    send(f"✅ Price alerts running for: {', '.join(coin_ids)}")
    print("Running. Press Ctrl+C to stop.")
    while True:
        try:
            for message in check(get_prices(coin_ids), armed):
                send(message)
                print(message)
        except Exception as error:  # network hiccups, rate limits: wait and retry
            print(f"Temporary error: {error}", file=sys.stderr)
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
