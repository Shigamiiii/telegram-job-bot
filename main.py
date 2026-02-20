import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Load the token from environment variables
TOKEN = os.environ.get("BOT_TOKEN")

# Dictionary to keep track of user sessions
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_sessions[user_id] = {
        "start_time": time.time(),
        "country": None,
        "payment": None,
        "username": None
    }
    await update.message.reply_text(
        "Welcome! Please tell me your country."
    )

async def country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["country"] = update.message.text
        await update.message.reply_text(
            "Got it! Now, please tell me your preferred payment type: hourly, commission, or both."
        )

async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["payment"] = update.message.text.lower()
        await update.message.reply_text(
            "Thanks! Now, please provide your Telegram username (without @)."
        )

async def username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["username"] = update.message.text
        await update.message.reply_text(
            "All set! I'll now monitor the group. Only messages from now on will be considered."
        )

async def stop_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions.pop(user_id, None)
    await update.message.reply_text("Search stopped. The bot will no longer forward messages.")

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"User {user_id} said: {update.message.text}")
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop_search", stop_search))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_messages))

    app.run_polling()
