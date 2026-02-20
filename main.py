import os
import json
import asyncio
from telethon import TelegramClient, events
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ── Credentials ──────────────────────────────────────────────────────────────
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ── Keywords ─────────────────────────────────────────────────────────────────
KEYWORDS = [
    "chat",
    "chatter",
    "onlyfans",
    "chat assistant",
    "chatters",
]

# ── Conversation steps ────────────────────────────────────────────────────────
COUNTRY, PAYMENT, USERNAME = range(3)

# ── Session storage ───────────────────────────────────────────────────────────
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

# ── Telethon client — uses saved session file, never asks for code ────────────
userbot = TelegramClient("userbot_session", API_ID, API_HASH)


# ════════════════════════════════════════════════════════════════════════════
#  REGISTRATION BOT HANDLERS
# ════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_sessions[user_id] = {"country": None, "payment": None, "username": None}
    save_sessions(user_sessions)
    await update.message.reply_text(
        "👋 Welcome! Let's get you set up.\n\nStep 1 of 3: What country are you in?"
    )
    return COUNTRY


async def collect_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_sessions[user_id]["country"] = update.message.text.strip()
    save_sessions(user_sessions)
    await update.message.reply_text(
        "✅ Got it!\n\nStep 2 of 3: What is your preferred payment type?\nReply with: hourly, commission, or both"
    )
    return PAYMENT


async def collect_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    payment = update.message.text.strip().lower()
    if payment not in ["hourly", "commission", "both"]:
        await update.message.reply_text("⚠️ Please reply with: hourly, commission, or both")
        return PAYMENT
    user_sessions[user_id]["payment"] = payment
    save_sessions(user_sessions)
    await update.message.reply_text(
        "✅ Got it!\n\nStep 3 of 3: What is your Telegram username? (without the @)"
    )
    return USERNAME


async def collect_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.message.text.strip().replace("@", "")
    user_sessions[user_id]["username"] = username
    save_sessions(user_sessions)
    await update.message.reply_text(
        f"🎉 You're all set!\n\n"
        f"📍 Country: {user_sessions[user_id]['country']}\n"
        f"💰 Payment: {user_sessions[user_id]['payment']}\n"
        f"👤 Forward to: @{username}\n\n"
        f"I'll monitor groups and forward matching messages to you.\n"
        f"Use /stop to stop receiving messages."
    )
    return ConversationHandler.END


async def stop_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        user_sessions.pop(user_id)
        save_sessions(user_sessions)
        await update.message.reply_text("🛑 Stopped. Use /start to register again.")
    else:
        await update.message.reply_text("You're not registered. Use /start to begin.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Use /start to try again.")
    return ConversationHandler.END


# ════════════════════════════════════════════════════════════════════════════
#  GROUP MESSAGE MONITOR (Telethon)
# ════════════════════════════════════════════════════════════════════════════

@userbot.on(events.NewMessage)
async def handle_group_message(event):
    if not event.is_group and not event.is_channel:
        return

    message_text = event.raw_text or ""
    message_text_lower = message_text.lower()

    matched_keyword = None
    for keyword in KEYWORDS:
        if keyword in message_text_lower:
            matched_keyword = keyword
            break

    if not matched_keyword:
        return

    chat = await event.get_chat()
    message_id = event.message.id
    chat_username = getattr(chat, "username", None)

    if chat_username:
        message_link = f"https://t.me/{chat_username}/{message_id}"
    else:
        chat_id_str = str(chat.id).lstrip("-")
        message_link = f"https://t.me/c/{chat_id_str}/{message_id}"

    sender = await event.get_sender()
    sender_name = getattr(sender, "first_name", "Unknown")
    sender_username = f"@{sender.username}" if getattr(sender, "username", None) else "no username"
    group_name = getattr(chat, "title", "Unknown Group")

    forward_message = (
        f"🔔 *New match found!*\n\n"
        f"📌 Keyword: `{matched_keyword}`\n"
        f"👤 Sent by: {sender_name} ({sender_username})\n"
        f"💬 Group: {group_name}\n\n"
        f"📝 Message:\n{message_text[:500]}\n\n"
        f"🔗 [View message]({message_link})"
    )

    sessions = load_sessions()
    for uid, session in sessions.items():
        if not session.get("username"):
            continue
        try:
            await userbot.send_message(
                session["username"],
                forward_message,
                parse_mode="md",
                link_preview=True,
            )
            print(f"✅ Forwarded to @{session['username']}")
        except Exception as e:
            print(f"❌ Could not forward to @{session['username']}: {e}")


# ════════════════════════════════════════════════════════════════════════════
#  MAIN — run everything in one async loop
# ════════════════════════════════════════════════════════════════════════════

async def main():
    # Connect userbot using saved session file (no login code needed)
    await userbot.connect()
    if not await userbot.is_user_authorized():
        print("❌ ERROR: Userbot session is not authorized. Please regenerate the session file.")
        return

    print("✅ Userbot connected successfully.")

    # Build and start the registration bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()

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

    print("✅ Registration bot is running...")

    # Run both concurrently in the same event loop
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("✅ Both userbot and registration bot are running!")

    # Keep running until disconnected
    await userbot.run_until_disconnected()

    # Cleanup
    await app.updater.stop()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
