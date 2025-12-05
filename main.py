
import logging
import re
import asyncio
import aiohttp
import time
import urllib.parse
from collections import deque
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import NetworkError, TimedOut
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import random

# ----------------- تنظیمات -----------------


BOT_TOKEN = '8363277121:AAH4wGsId1uUUucQavaG8uvb31mknRkDT5Q'
TARGET_CHAT_ID = '@proxy_iran2024'

# لینک منبع (نسخه RAW)
GITHUB_SOURCE = 'https://raw.githubusercontent.com/Argh94/telegram-proxy-scraper/main/proxy.txt'

CHECK_INTERVAL = 120  # اجرا هر 2 دقیقه
PING_TIMEOUT = 1.5    # تایم‌اوت سخت‌گیرانه (ثانیه)
PING_RETRIES = 3      # تعداد دفعات تست هر پروکسی برای اطمینان از پایداری

# تنظیمات تعداد (4 دسته 4 تایی = 16 پروکسی)
REQUIRED_COUNT = 16

# جملات زیبا
PERSIAN_QUOTES = [
    "موفقیت مجموعه‌ای از تلاش‌های کوچک است که هر روز تکرار می‌شوند.",
    "سختی‌ها برای این نیستند که تو را متوقف کنند، بلکه برای اینند که تو را آماده کنند.",
    "آینده‌ات را با کارهایی که امروز انجام می‌دهی بساز، نه با کارهایی که فردا قصد داری انجام دهی.",
    "رویاها تاریخ انقضا ندارند، نفسی تازه بکش و دوباره تلاش کن.",
    "شجاعت یعنی ترسیدن و لرزیدن، اما برداشتن قدم اول.",
]

# ----------------- متغیرهای سراسری -----------------

HISTORY_SET = set()
UNTESTED_QUEUE = deque()

# ----------------- تنظیمات لاگ -----------------
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- توابع شبکه و تست -----------------

def parse_proxy_info(proxy_url):
    """استخراج IP و پورت"""
    try:
        # هندل کردن لینک‌های tg:// و https://t.me
        url_for_parse = proxy_url.replace('tg://', 'http://').replace('t.me', 'http://')
        parsed = urllib.parse.urlparse(url_for_parse)
        qs = urllib.parse.parse_qs(parsed.query)
        
        server = qs.get('server', [None])[0]
        port = qs.get('port', [None])[0]
        
        if server and port:
            return server, int(port)
    except Exception:
        pass
    return None, None

async def measure_latency_average(ip, port, retries=3):
    """
    تست دقیق: چندین بار پینگ می‌گیرد و میانگین را برمی‌گرداند.
    اگر حتی یک بار خطا دهد، False برمی‌گرداند (حذف پروکسی ناپایدار).
    """
    latencies = []
    
    for _ in range(retries):
        start_time = time.time()
        try:
            # تست اتصال TCP (شبیه سازی هندشیک اولیه)
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=PING_TIMEOUT)
            
            # محاسبه زمان رفت و برگشت
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)
            
            writer.close()
            await writer.wait_closed()
            
            # وقفه کوتاه بین تست‌ها برای واقعی‌تر شدن
            await asyncio.sleep(0.1)
            
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False, 9999
        except Exception:
            return False, 9999

    # محاسبه میانگین تاخیر
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        return True, int(avg_latency)
    
    return False, 9999

async def fetch_source_proxies():
    """دانلود پروکسی‌ها با مدیریت خطای شبکه"""
    global UNTESTED_QUEUE, HISTORY_SET
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(GITHUB_SOURCE) as response:
                if response.status == 200:
                    text = await response.text()
                    matches = re.findall(r'(tg://proxy\?[\w=&.-]+|https://t\.me/proxy\?[\w=&.-]+)', text)
                    
                    new_added = 0
                    for link in matches:
                        clean_link = link.replace('tg://', 'https://t.me/')
                        if clean_link not in HISTORY_SET and clean_link not in UNTESTED_QUEUE:
                            UNTESTED_QUEUE.append(clean_link)
                            new_added += 1
                    
                    if new_added > 0:
                        logger.info(f"📥 {new_added} پروکسی جدید دانلود شد. صف فعلی: {len(UNTESTED_QUEUE)}")
                else:
                    logger.warning(f"⚠️ خطای سرور گیت‌هاب: {response.status}")
    except aiohttp.ClientError as e:
        logger.error(f"❌ خطای شبکه در دانلود لیست: {e}")
    except Exception as e:
        logger.error(f"❌ خطای ناشناخته در دانلود: {e}")

# ----------------- منطق اصلی ربات -----------------

async def process_proxies_job(context: ContextTypes.DEFAULT_TYPE):
    """جاب اصلی که هر 2 دقیقه اجرا می‌شود"""
    global UNTESTED_QUEUE, HISTORY_SET
    bot = context.bot
    logger.info("🔄 شروع سیکل تست دقیق پروکسی‌ها...")

    # اگر صف خالی است یا کم است، دانلود کن
    if len(UNTESTED_QUEUE) < 50:
        await fetch_source_proxies()

    healthy_proxies = []

    # تست پروکسی‌ها تا رسیدن به 16 عدد
    # برای جلوگیری از گیر کردن در حلقه بی نهایت، یک سقف تلاش (Max Attempts) می‌گذاریم
    attempts = 0
    max_attempts = 100 # حداکثر 100 پروکسی را در هر دور چک کن

    while len(healthy_proxies) < REQUIRED_COUNT and UNTESTED_QUEUE and attempts < max_attempts:
        attempts += 1
        proxy_url = UNTESTED_QUEUE.popleft()
        HISTORY_SET.add(proxy_url) # مارک کردن به عنوان دیده شده
        
        ip, port = parse_proxy_info(proxy_url)
        if ip and port:
            is_stable, avg_ping = await measure_latency_average(ip, port, retries=PING_RETRIES)
            
            if is_stable:
                healthy_proxies.append({'url': proxy_url, 'ping': avg_ping})
                logger.info(f"✅ پروکسی تایید شد (Ping Avg: {avg_ping}ms) - {len(healthy_proxies)}/{REQUIRED_COUNT}")

    # اگر تعداد کافی پیدا شد
    if len(healthy_proxies) >= REQUIRED_COUNT:
        # مرتب‌سازی بر اساس پینگ (از کم به زیاد)
        healthy_proxies.sort(key=lambda x: x['ping'])
        
        # انتخاب 16 تای برتر
        top_16 = healthy_proxies[:REQUIRED_COUNT]
        
        # دسته‌بندی هوشمند بر اساس سرعت (Tier Logic)
        # فرض: موبایل نیاز به پینگ پایین‌تر دارد
        categories = {
            "mci": top_16[0:4],       # 4 تای فوق سریع -> همراه اول
            "irancell": top_16[4:8],  # 4 تای سریع -> ایرانسل
            "rightel": top_16[8:12],  # 4 تای متوسط -> رایتل
            "wifi": top_16[12:16]     # 4 تای معمولی -> وای‌فای
        }
        
        await send_formatted_message(bot, categories)
    else:
        logger.warning(f"⚠️ تعداد کافی ({len(healthy_proxies)}) پروکسی پایدار پیدا نشد. تلاش مجدد در دور بعد.")

async def send_formatted_message(bot, cats):
    """ارسال پیام دسته‌بندی شده به کانال"""
    quote = random.choice(PERSIAN_QUOTES)
    
    msg = f"<i>{quote}</i>\n\n"
    msg += "—" * 20 + "\n"
    msg += "<b>🚀 لیست جدید پروکسی‌های پایدار و پرسرعت</b>\n"
    msg += "📡 تفکیک شده بر اساس پایداری شبکه\n\n"

    # تابع کمکی برای ساخت بخش‌ها
    def build_section(title, proxies, emoji):
        section = f"{emoji} <b>{title}</b>\n"
        for i, item in enumerate(proxies, 1):
            section += f"🔗 <a href='{item['url']}'>اتصال {i}</a>  "
            if i % 2 == 0: section += "\n"
        return section + "\n"

    msg += build_section("مخصوص همراه اول (MCI)", cats['mci'], "🔵")
    msg += build_section("مخصوص ایرانسل (Irancell)", cats['irancell'], "🟡")
    msg += build_section("مخصوص رایتل (Rightel)", cats['rightel'], "🟣")
    msg += build_section("مخصوص وای‌فای (WiFi/ADSL)", cats['wifi'], "⚪️")

    msg += "—" * 20 + "\n"
    msg += f"🆔 <b><a href='https://t.me/proxy_iran2024'>@proxy_iran2024</a></b>"

    # تلاش برای ارسال با مکانیزم Retry
    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            logger.info("📤 پیام با موفقیت ارسال شد.")
            break
        except (NetworkError, TimedOut) as e:
            logger.error(f"⚠️ خطا در ارسال پیام (تلاش {attempt+1}): {e}")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"❌ خطای غیرقابل بازگشت در ارسال: {e}")
            break

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ربات فعال شد.\nمتد تست: میانگین‌گیری پینگ (3x) برای تضمین پایداری.")

# ----------------- اجرا -----------------

if __name__ == '__main__':
    print("--- ربات پروکسی پیشرفته (Multi-Ping Stability Check) ---")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    
    job_queue = application.job_queue
    
    # اجرا هر 120 ثانیه
    job_queue.run_repeating(
        process_proxies_job,
        interval=CHECK_INTERVAL,
        first=5
    )
    
    application.run_polling()
