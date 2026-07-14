import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sheets

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["TELEGRAM_TOKEN"]

HELP = (
    "/newlist <name> — create a list and switch to it\n"
    "/switch <name> — set active list\n"
    "/lists — show all lists\n"
    "/list — show items in active list\n"
    "/done <number> — remove item by number\n"
    "Just type anything to add to your active list"
)


async def _active(update: Update) -> str | None:
    chat_id = update.effective_chat.id
    name = sheets.get_active_list(chat_id)
    if not name:
        await update.message.reply_text("No active list. Use /switch <name> or /newlist <name>.")
    return name


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"List bot ready!\n\n{HELP}")


async def newlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /newlist <name>")
        return
    name = " ".join(context.args)
    sheets.create_list(name)
    sheets.set_active_list(update.effective_chat.id, name)
    await update.message.reply_text(f"Created '{name}' and switched to it.")


async def switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /switch <name>")
        return
    name = " ".join(context.args)
    if name not in sheets.get_lists():
        await update.message.reply_text(f"List '{name}' not found. Use /lists to see available lists.")
        return
    sheets.set_active_list(update.effective_chat.id, name)
    await update.message.reply_text(f"Switched to '{name}'.")


async def lists_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_lists = sheets.get_lists()
    if not all_lists:
        await update.message.reply_text("No lists yet. Use /newlist <name> to create one.")
        return
    current = sheets.get_active_list(update.effective_chat.id)
    lines = [f"{'▶ ' if l == current else '  '}{l}" for l in all_lists]
    await update.message.reply_text("\n".join(lines))


async def list_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = await _active(update)
    if not name:
        return
    items = sheets.get_items(name)
    if not items:
        await update.message.reply_text(f"'{name}' is empty.")
        return
    lines = "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    await update.message.reply_text(f"*{name}*\n{lines}", parse_mode="Markdown")


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = await _active(update)
    if not name:
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /done <number>")
        return
    removed = sheets.remove_item(name, int(context.args[0]) - 1)
    if removed is None:
        await update.message.reply_text("Item not found.")
    else:
        await update.message.reply_text(f"Removed: {removed}")


async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = await _active(update)
    if not name:
        return
    sheets.add_item(name, update.message.text)
    await update.message.reply_text(f"Added to {name} ✓")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newlist", newlist))
    app.add_handler(CommandHandler("switch", switch))
    app.add_handler(CommandHandler("lists", lists_cmd))
    app.add_handler(CommandHandler("list", list_items))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_item))
    app.run_polling()


if __name__ == "__main__":
    main()
