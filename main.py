import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# توکن ربات از Environment Variable می‌آید
TOKEN = os.environ.get("8363277121:AAH4wGsId1uUUucQavaG8uvb31mknRkDT5Q")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات Railway با موفقیت روشن شد!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()  # بهترین روش برای Railway
