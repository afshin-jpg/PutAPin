import os
import json
import logging
import threading
import requests as http_requests
from flask import Flask, request, jsonify
import sheets

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

app = Flask(__name__)

HELP = (
    "/newlist <name> — create a list and switch to it\n"
    "/switch <name> — set active list\n"
    "/lists — show all lists\n"
    "/list — show items in active list\n"
    "/done <number> — remove item by number\n"
    "Just type anything to add to your active list"
)


def tg_send(chat_id, text):
    try:
        http_requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        logging.error(f"tg_send failed: {e}")


def register_webhook():
    if not WEBHOOK_URL:
        return
    url = f"{WEBHOOK_URL}/webhook"
    try:
        http_requests.get(
            f"https://api.telegram.org/bot{TOKEN}/deleteWebhook",
            params={"drop_pending_updates": "true"},
            timeout=10,
        )
        res = http_requests.post(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook",
            json={"url": url},
            timeout=10,
        )
        logging.info(f"Webhook set to {url}: {res.json()}")
    except Exception as e:
        logging.error(f"Webhook registration failed: {e}")


@app.route("/")
def health():
    return jsonify({"status": "ok"})


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json or {}
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id or not text:
        return jsonify({"ok": True})

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/start" or cmd == "/help":
            tg_send(chat_id, f"List bot ready!\n\n{HELP}")

        elif cmd == "/newlist":
            if not arg:
                tg_send(chat_id, "Usage: /newlist <name>")
            else:
                sheets.create_list(arg)
                sheets.set_active_list(chat_id, arg)
                tg_send(chat_id, f"Created '{arg}' and switched to it.")

        elif cmd == "/switch":
            if not arg:
                tg_send(chat_id, "Usage: /switch <name>")
            elif arg not in sheets.get_lists():
                tg_send(chat_id, f"List '{arg}' not found. Use /lists to see all.")
            else:
                sheets.set_active_list(chat_id, arg)
                tg_send(chat_id, f"Switched to '{arg}'.")

        elif cmd == "/lists":
            all_lists = sheets.get_lists()
            if not all_lists:
                tg_send(chat_id, "No lists yet. Use /newlist <name> to create one.")
            else:
                current = sheets.get_active_list(chat_id)
                lines = [f"{'▶ ' if l == current else '  '}{l}" for l in all_lists]
                tg_send(chat_id, "\n".join(lines))

        elif cmd == "/list":
            name = sheets.get_active_list(chat_id)
            if not name:
                tg_send(chat_id, "No active list. Use /switch <name> or /newlist <name>.")
            else:
                items = sheets.get_items(name)
                if not items:
                    tg_send(chat_id, f"'{name}' is empty.")
                else:
                    lines = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
                    tg_send(chat_id, f"*{name}*\n{lines}")

        elif cmd == "/done":
            name = sheets.get_active_list(chat_id)
            if not name:
                tg_send(chat_id, "No active list.")
            elif not arg.isdigit():
                tg_send(chat_id, "Usage: /done <number>")
            else:
                removed = sheets.remove_item(name, int(arg) - 1)
                if removed is None:
                    tg_send(chat_id, "Item not found.")
                else:
                    tg_send(chat_id, f"Removed: {removed}")

    else:
        name = sheets.get_active_list(chat_id)
        if not name:
            tg_send(chat_id, "No active list. Use /switch <name> or /newlist <name>.")
        else:
            sheets.add_item(name, text)
            tg_send(chat_id, f"Added to {name} ✓")

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    threading.Thread(target=register_webhook, daemon=True).start()
    logging.info(f"Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
