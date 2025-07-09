
import os
import csv
import jdatetime
from datetime import datetime
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
ADMINS = list(map(int, os.environ.get("ADMINS", "").split(",")))
TZ = os.environ.get("TIMEZONE", "Asia/Tehran")
DATA_FILE = "prices.csv"
state = {}

weekday_map = {
    "Saturday": "شنبه",
    "Sunday": "یک‌شنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنج‌شنبه",
    "Friday": "جمعه"
}

async def send_main_menu(update_or_query, context):
    keyboard = [
        [InlineKeyboardButton("✅ ثبت قیمت جدید", callback_data="start_price")],
        [InlineKeyboardButton("📊 گزارش امروز", callback_data="daily_report")]
    ]
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text("می‌خوای چیکار کنی؟", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.edit_message_text("می‌خوای چیکار کنی؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("⛔ فقط ادمین‌ها به ربات دسترسی دارند.")
        return
    await send_main_menu(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in state or state[user_id].get("step") not in ["buy", "sell"]:
        return

    text = update.message.text.replace(",", "")
    if not text.isdigit():
        await update.message.reply_text("❗ لطفاً فقط عدد وارد کنید.")
        return

    if state[user_id]["step"] == "buy":
        state[user_id]["buy_price"] = int(text)
        state[user_id]["step"] = "sell"
        await update.message.reply_text("قیمت فروش مثقال رو وارد کن:")
    elif state[user_id]["step"] == "sell":
        state[user_id]["sell_price"] = int(text)
        buy = state[user_id]["buy_price"]
        sell = state[user_id]["sell_price"]
        buy_gram = int(buy / 4.3318)
        sell_gram = int(sell / 4.3318)

        tehran_now = datetime.now(timezone(TZ))
        jdate = jdatetime.date.fromgregorian(date=tehran_now.date())
        fa_day = weekday_map.get(jdate.strftime("%A"), "")
        date_str = jdate.strftime("%Y/%m/%d")

        msg = f"""📅 {fa_day} {date_str}
💰 آبشده نقدی ⬇️
◀️ هر مثقال:
🟢 فروش ما به شما : {sell:,}
🔴 خرید ما از شما : {buy:,}

◀️ هر گرم:
🟢 فروش ما به شما : {sell_gram:,}
🔴 خرید ما از شما : {buy_gram:,}

📞 جهت انجام معاملات لطفا تماس بگیرید:
09133650701 - 03132239231
📢 {CHANNEL_ID}
"""
        state[user_id]["preview"] = msg
        state[user_id]["step"] = "confirm"
        keyboard = [
            [InlineKeyboardButton("📤 ارسال به کانال", callback_data="send_confirm")],
            [InlineKeyboardButton("❌ لغو", callback_data="cancel")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_menu")]
        ]
        await update.message.reply_text("✅ پیش‌نمایش آماده‌ست. ارسال کنم؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "start_price":
        state[user_id] = {"step": "buy"}
        await query.edit_message_text("قیمت خرید مثقال رو وارد کن:")

    elif query.data == "send_confirm":
        msg = state[user_id].get("preview", "")
        if msg:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)
            with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now(), state[user_id]["buy_price"], state[user_id]["sell_price"], user_id])
            await query.edit_message_text("✅ قیمت ارسال شد.")
        state.pop(user_id, None)

    elif query.data == "cancel":
        state.pop(user_id, None)
        await query.edit_message_text("❌ عملیات لغو شد.")

    elif query.data == "back_to_menu":
        state.pop(user_id, None)
        await send_main_menu(query, context)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_buttons))

if __name__ == "__main__":
    app.run_polling()
