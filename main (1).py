import os
import json
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ── Load bot token ──────────────────────────────────────────────────────────
TOKEN = os.environ.get("BOT_TOKEN")

# ── Conversation steps ───────────────────────────────────────────────────────
COUNTRY, PAYMENT, USERNAME = range(3)

# ── Keywords to watch for in group messages ──────────────────────────────────
KEYWORDS = [
    "chat",
    "chatter",
    "onlyfans",
    "chat assistant",
    "chatters",
]

# ── File to save user sessions so data survives restarts ────────────────────
SESSIONS_FILE = "sessions.json"


def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)


user_sessions = load_sessions()


# ── /start command – begins registration ─────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_sessions[user_id] = {
        "start_time": time.time(),
        "country": None,
        "payment": None,
        "username": None,
    }
    save_sessions(user_sessions)
    await update.message.reply_text(
        "👋 Welcome! Let's get you set up.\n\nStep 1 of 3: What country are you in?"
    )
    return COUNTRY


# ── Step 1: collect country ──────────────────────────────────────────────────
async def collect_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_sessions[user_id]["country"] = update.message.text.strip()
    save_sessions(user_sessions)
    await update.message.reply_text(
        "✅ Got it!\n\nStep 2 of 3: What is your preferred payment type?\nReply with: hourly, commission, or both"
    )
    return PAYMENT


# ── Step 2: collect payment type ─────────────────────────────────────────────
async def collect_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    payment = update.message.text.strip().lower()

    if payment not in ["hourly", "commission", "both"]:
        await update.message.reply_text(
            "⚠️ Please reply with one of these options: hourly, commission, or both"
        )
        return PAYMENT

    user_sessions[user_id]["payment"] = payment
    save_sessions(user_sessions)
    await update.message.reply_text(
        "✅ Got it!\n\nStep 3 of 3: What is your Telegram username? (without the @)"
    )
    return USERNAME


# ── Step 3: collect username and finish registration ──────────────────────────
async def collect_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.message.text.strip().replace("@", "")
    user_sessions[user_id]["username"] = username
    save_sessions(user_sessions)

    country = user_sessions[user_id]["country"]
    payment = user_sessions[user_id]["payment"]

    await update.message.reply_text(
        f"🎉 You're all set!\n\n"
        f"📍 Country: {country}\n"
        f"💰 Payment: {payment}\n"
        f"👤 Forward to: @{username}\n\n"
        f"I'll now watch group messages and forward anything relevant to you.\n"
        f"Use /stop to stop receiving messages."
    )
    return ConversationHandler.END


# ── /stop command – unregisters the user ─────────────────────────────────────
async def stop_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        user_sessions.pop(user_id)
        save_sessions(user_sessions)
        await update.message.reply_text(
            "🛑 Stopped. You won't receive any more forwarded messages.\n"
            "Use /start to register again anytime."
        )
    else:
        await update.message.reply_text("You're not currently registered. Use /start to begin.")
    return ConversationHandler.END


# ── /cancel during registration ───────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Registration cancelled. Use /start to try again.")
    return ConversationHandler.END


# ── Filter group messages and forward matches ─────────────────────────────────
async def filter_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only handle messages from groups/supergroups
    if update.message is None:
        return
    if update.message.chat.type not in ["group", "supergroup"]:
        return

    message_text = update.message.text or ""
    message_text_lower = message_text.lower()

    # Check if message contains any keyword
    matched_keyword = None
    for keyword in KEYWORDS:
        if keyword in message_text_lower:
            matched_keyword = keyword
            break

    if not matched_keyword:
        return  # No match, ignore the message

    # Build the message link
    chat = update.message.chat
    message_id = update.message.message_id

    if chat.username:
        # Public group – link works for everyone
        message_link = f"https://t.me/{chat.username}/{message_id}"
    else:
        # Private group – link only works for members
        chat_id_str = str(chat.id).replace("-100", "")
        message_link = f"https://t.me/c/{chat_id_str}/{message_id}"

    sender = update.message.from_user
    sender_name = sender.full_name if sender else "Unknown"
    sender_username = f"@{sender.username}" if sender and sender.username else "no username"
    group_name = chat.title or "Unknown Group"

    # Forward to all registered users whose payment type matches (or is "both")
    for uid, session in user_sessions.items():
        if not session.get("username"):
            continue

        # Optional: filter by payment preference if message mentions it
        payment_pref = session.get("payment", "both")
        if payment_pref != "both":
            if payment_pref not in message_text_lower:
                # If their preference word isn't in the message, still forward
                # (keyword match is enough — remove this block to be stricter)
                pass

        forward_message = (
            f"🔔 *New match found!*\n\n"
            f"📌 Keyword: `{matched_keyword}`\n"
            f"👤 Sent by: {sender_name} ({sender_username})\n"
            f"💬 Group: {group_name}\n\n"
            f"📝 Message:\n{message_text[:500]}\n\n"
            f"🔗 [View message]({message_link})"
        )

        try:
            await context.bot.send_message(
                chat_id=f"@{session['username']}",
                text=forward_message,
                parse_mode="Markdown",
                disable_web_page_preview=False,
            )
        except Exception as e:
            print(f"Could not forward to @{session['username']}: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Conversation handler for registration flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_country)],
            PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_payment)],
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_username)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("stop", stop_search)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stop", stop_search))

    # Listen to ALL messages (including from groups the bot is added to)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, filter_group_messages)
    )

    print("Bot is running...")
    app.run_polling()
