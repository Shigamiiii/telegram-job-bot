import os
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

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
    if user_id not in user_sessions:
        return

    session = user_sessions[user_id]
    message_time = time.time()

    if message_time >= session["start_time"]:
        keywords = ["chatter", "chatter assistant", "chat assistant", "support assistant"]
        text = update.message.text.lower()
        if any(word in text for word in keywords):
            # Forward message to user
            if session["username"]:
                await context.bot.send_message(
                    chat_id=session["username"],
                    text=f"From: @{update.message.from_user.username}\n\n{update.message.text}"
                )

# Setup the bot
app = ApplicationBuilder().token(TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, country))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, payment))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, username))
app.add_handler(CommandHandler("stopsearch", stop_search))
app.add_handler(MessageHandler(filters.ALL, filter_messages))

# Run the bot
app.run_polling()
