{\rtf1\ansi\ansicpg1252\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import os\
import time\
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup\
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler\
\
# Load the token from environment variables\
TOKEN = os.environ.get("BOT_TOKEN")\
\
# Dictionary to keep track of user sessions\
user_sessions = \{\}\
\
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    user_id = update.effective_user.id\
    user_sessions[user_id] = \{\
        "start_time": time.time(),\
        "country": None,\
        "payment": None,\
        "username": None\
    \}\
    await update.message.reply_text(\
        "Welcome! Please tell me your country."\
    )\
\
async def country(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    user_id = update.effective_user.id\
    if user_id in user_sessions:\
        user_sessions[user_id]["country"] = update.message.text\
        await update.message.reply_text(\
            "Got it! Now, please tell me your preferred payment type: hourly, commission, or both."\
        )\
\
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    user_id = update.effective_user.id\
    if user_id in user_sessions:\
        user_sessions[user_id]["payment"] = update.message.text.lower()\
        await update.message.reply_text(\
            "Thanks! Now, please provide your Telegram username (without @)."\
        )\
\
async def username(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    user_id = update.effective_user.id\
    if user_id in user_sessions:\
        user_sessions[user_id]["username"] = update.message.text\
        await update.message.reply_text(\
            "All set! I'll now monitor the group. Only messages from now on will be considered."\
        )\
\
async def stop_search(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    user_id = update.effective_user.id\
    if user_id in user_sessions:\
        user_sessions.pop(user_id, None)\
    await update.message.reply_text("Search stopped. The bot will no longer forward messages.")\
\
async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):}