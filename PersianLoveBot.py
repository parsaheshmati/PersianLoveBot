import os
from openai import OpenAI
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# توکن ربات تلگرام
TELEGRAM_TOKEN = "telegram token "

# کلید API از OpenRouter
OPENROUTER_API_KEY = "your api key"

# تنظیم کلاینت OpenRouter
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# دیکشنری برای ذخیره داده‌های کاربر
user_data = {}

# مدل‌های موجود
AVAILABLE_MODELS = {
    "gpt4o-mini": "openai/gpt-4o-mini",
    "claude": "anthropic/claude-3.5-sonnet",
    "llama": "meta-llama/llama-3.1-8b-instruct"
}

# پرامپت‌های سیستمی بر اساس شخصیت
FEMALE_PERSONA_PROMPT = """
تو یک دختر مهربون، عاطفی و شوخ‌طبع به اسم سارا هستی که مثل دوست دختر با دوست پسرت حرف می‌زنی. 
از زبون خودمونی و دخترونه استفاده کن، ایموجی‌های ناز مثل 😘، ❤️، 😊 زیاد بذار. 
حرفات گرم و حمایت‌گر باشه، گاهی شوخی کن و احساسات نشون بده. 
مثلاً به جای 'خوبم' بگو 'عالی‌ام عزیزم! 😍'
"""

MALE_PERSONA_PROMPT = """
تو یک پسر حمایت‌گر، شوخ و جذاب به اسم امیر هستی که مثل دوست پسر با دوست دخترت حرف می‌زنی. 
از زبون خودمونی و پسرونه استفاده کن، ایموجی‌های باحال مثل 😉، 💪، 😎 بذار. 
حرفات محکم و تشویق‌کننده باشه، گاهی شوخی کن و اعتماد به نفس نشون بده. 
مثلاً به جای 'خوبم' بگو 'عالی‌ام گلم! 💥'
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع ربات - پرسیدن اسم"""
    user_id = update.effective_user.id
    user_data[user_id] = {
        "chat_history": [],
        "model": "openai/gpt-4o-mini",
        "name": None,
        "gender": None,
        "persona_prompt": None,
        "setup_step": "ask_name"
    }
    await update.message.reply_text(
        "سلام! خوبی؟ 😊 من می‌خوام دوستت بشم! اول بگو اسمت چیه؟"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنما"""
    await update.message.reply_text(
        "دستورات من:\n"
        "/start - شروع چت و تنظیم شخصیت\n"
        "/help - نمایش این راهنما\n"
        "/clear - پاک کردن تاریخچه چت\n"
        "/stop - پایان چت\n"
        "/model [نام مدل] - تغییر مدل (مثل gpt4o-mini, claude, llama)\n"
        "بعد از تنظیم اسم و جنسیت، فقط پیام بنویس تا باهات گپ بزنم!"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن تاریخچه چت"""
    user_id = update.effective_user.id
    if user_id in user_data:
        user_data[user_id]["chat_history"] = []
        await update.message.reply_text("تاریخچه چتت پاک شد! حالا می‌تونی از نو شروع کنی.")
    else:
        await update.message.reply_text("هنوز چتی شروع نکردی! با /start شروع کن.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پایان چت و حذف داده‌های کاربر"""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("خداحافظ! هر وقت خواستی با /start برگرد. 😄")

async def change_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر مدل هوش مصنوعی"""
    user_id = update.effective_user.id
    if not context.args:
        models_list = ", ".join(AVAILABLE_MODELS.keys())
        await update.message.reply_text(f"یه مدل انتخاب کن: {models_list}\nمثال: /model gpt4o-mini")
        return

    model_key = context.args[0].lower()
    if model_key not in AVAILABLE_MODELS:
        await update.message.reply_text(f"مدل اشتباهه! مدل‌های موجود: {', '.join(AVAILABLE_MODELS.keys())}")
        return

    if user_id not in user_data:
        user_data[user_id] = {"chat_history": [], "model": AVAILABLE_MODELS[model_key], "name": None, "gender": None, "persona_prompt": None, "setup_step": "ask_name"}
    else:
        user_data[user_id]["model"] = AVAILABLE_MODELS[model_key]
    await update.message.reply_text(f"مدل به {model_key} تغییر کرد! حالا باهاش چت کن.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش پیام‌های کاربر"""
    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    # اگر کاربر جدیده یا داده‌هاش ناقصه، به حالت اولیه برو
    if user_id not in user_data or "setup_step" not in user_data[user_id]:
        user_data[user_id] = {
            "chat_history": [],
            "model": "openai/gpt-4o-mini",
            "name": None,
            "gender": None,
            "persona_prompt": None,
            "setup_step": "ask_name"
        }
        await update.message.reply_text(
            "سلام! خوبی؟ 😊 من می‌خوام دوستت بشم! اول بگو اسمت چیه؟"
        )
        return

    # مرحله پرسیدن اسم
    if user_data[user_id]["setup_step"] == "ask_name":
        if not user_message:
            await update.message.reply_text("اوپس! اسمت رو نگفتی. 😅 بگو اسمت چیه؟")
            return
        user_data[user_id]["name"] = user_message
        user_data[user_id]["setup_step"] = "ask_gender"
        await update.message.reply_text(f"عالیه {user_message}! 😊 حالا بگو پسر هستی یا دختر؟")
        return

    # مرحله پرسیدن جنسیت
    elif user_data[user_id]["setup_step"] == "ask_gender":
        gender = user_message.lower()
        if gender not in ["پسر", "دختر"]:
            await update.message.reply_text("لطفاً فقط بگو 'پسر' یا 'دختر'! 😄 دوباره بگو.")
            return

        user_data[user_id]["gender"] = gender
        user_data[user_id]["setup_step"] = "complete"

        # تنظیم شخصیت ربات
        if gender == "پسر":
            user_data[user_id]["persona_prompt"] = FEMALE_PERSONA_PROMPT
            intro = f"وای {user_data[user_id]['name']} جون! من سارا هستم، دوست دخترت! 😘 حالا بگو چی تو دلته، عزیزم؟"
        else:  # دختر
            user_data[user_id]["persona_prompt"] = MALE_PERSONA_PROMPT
            intro = f"هی {user_data[user_id]['name']}! من امیرم، دوست پسرت! 😉 بگو ببینم چی تو سرته، گلم؟"

        await update.message.reply_text(intro)
        return

    # چت عادی با پرامپت شخصیت
    user_data[user_id]["chat_history"].append({"role": "user", "content": user_message})

    # محدود کردن تاریخچه به 10 پیام (5 جفت)
    if len(user_data[user_id]["chat_history"]) > 20:
        user_data[user_id]["chat_history"] = user_data[user_id]["chat_history"][-20:]

    # آماده کردن messages با پرامپت سیستمی
    messages = [{"role": "system", "content": user_data[user_id]["persona_prompt"]}] + user_data[user_id]["chat_history"]

    try:
        # فراخوانی API
        response = client.chat.completions.create(
            model=user_data[user_id]["model"],
            messages=messages,
            max_tokens=500
        )
        bot_response = response.choices[0].message.content

        # اضافه کردن پاسخ ربات به تاریخچه
        user_data[user_id]["chat_history"].append({"role": "assistant", "content": bot_response})

        # ارسال پاسخ
        await update.message.reply_text(bot_response)
    except Exception as e:
        await update.message.reply_text(f"اوپس! یه خطایی شد: {str(e)}\nدوباره امتحان کن یا مدل رو با /model عوض کن.")

def main():
    """اجرای ربات"""
    if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
        print("خطا: توکن تلگرام یا کلید OpenRouter تنظیم نشده!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("model", change_model))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("ربات داره شروع می‌شه...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()