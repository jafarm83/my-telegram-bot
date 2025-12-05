import os
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update
from telegram.ext import ContextTypes

# توکن از Environment Variable می‌آید
TOKEN = os.environ.get("BOT_TOKEN")

# مسیر ساده برای webhook (نباید توکن در URL باشد)
WEBHOOK_PATH = "/webhook"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات Render با موفقیت روشن شد!")

# ساخت اپلیکیشن
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

# اجرا با webhook
app.run_webhook(
    listen="0.0.0.0",      # همه IP ها
    port=int(os.environ.get("PORT", 10000)),  # پورت Render
    url_path=WEBHOOK_PATH, 
    webhook_url=f"https://your-app-name.onrender.com{WEBHOOK_PATH}"
)
