import telegram
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = "توکن_بات_تو"

async def start(update, context):
    await update.message.reply_text("ربات Render با موفقیت روشن شد!")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

app.run_webhook(
    listen="0.0.0.0",
    port=10000,
    url_path=TOKEN,
    webhook_url=f"https://your-app-name.onrender.com/{TOKEN}"
)
