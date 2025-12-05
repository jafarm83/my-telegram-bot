import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# دریافت توکن از Environment Variable
TOKEN = os.environ.get("8363277121:AAH4wGsId1uUUucQavaG8uvb31mknRkDT5Q")
if not TOKEN:
    raise ValueError("❌ توکن ربات پیدا نشد! مطمئن شوید که Environment Variable درست تنظیم شده است.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات Railway با موفقیت روشن شد!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
