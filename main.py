import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# توکن ربات از Environment Variable
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات Render با موفقیت روشن شد!")

if __name__ == "__main__":
    # ساخت اپلیکیشن
    app = ApplicationBuilder().token(TOKEN).build()
    
    # اضافه کردن دستور /start
    app.add_handler(CommandHandler("start", start))
    
    # اجرای ربات با Polling (روی Render بهترین روش است)
    app.run_polling()
