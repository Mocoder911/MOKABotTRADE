"""
MOKABot Telegram Support Bot
@aimokabot - Technical support bot for MOKABot trading system
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = "8989474621:AAE__nslSBkxlhC3eXG8FMzYj9KGLVLbYnU"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================
# MESSAGES
# ============================================
WELCOME_MESSAGE = """
🤖 *مرحباً بك في بوت دعم MOKABot!*

أنا البوت الرسمي للدعم الفني لنظام MOKABot للتداول الآلي.

📋 *الأوامر المتاحة:*
/start - رسالة الترحيب هذه
/menu - عرض القائمة الرئيسية
/setup - خطوات تثبيت البوت
/settings - شرح الإعدادات
/troubleshoot - حل المشاكل الشائعة
/pairs - العملات المدعومة
/strategy - شرح الاستراتيجية
/contact - التواصل مع الدعم

💡 *اكتب أي سؤال وهنرد عليك في أقرب وقت!*
"""

MENU_MESSAGE = """
📋 *القائمة الرئيسية*

اختر من الأوامر التالية:

🔧 /setup - خطوات التثبيت
⚙️ /settings - الإعدادات
🔍 /troubleshoot - حل المشاكل
💱 /pairs - العملات المدعومة
📊 /strategy - الاستراتيجية
📞 /contact - تواصل معنا
"""

SETUP_MESSAGE = """
🔧 *خطوات تثبيت MOKABot:*

*1. المتطلبات:*
• Python 3.10+
• MetaTrader 5 Terminal
• حساب تداول (FP Markets / Exness)

*2. التثبيت:*
```
git clone https://github.com/Mocoder911/MOKABotTRADE
cd MOKABotTRADE
pip install -r requirements.txt
```

*3. الإعداد:*
• انسخ `.env.local` وعدّل القيم
• أضف بيانات حساب MT5
• أضف Supabase URL و Keys

*4. التشغيل:*
```
python mt5_bridge_multi.py
```

⚠️ *تأكد إن MT5 Terminal مفتوح قبل التشغيل!*
"""

SETTINGS_MESSAGE = """
⚙️ *شرح الإعدادات:*

*📊 Basket_Take_Profit:*
الربح المستهدف لكل صفقة (بالدولار)
القيمة الحالية: $5

*📏 Grid_Step:*
المسافة بين كل صفقة وأخرى (بالنقاط)
القيمة الحالية: 100 نقطة

*🔢 Max_Open_Positions:*
أقصى عدد صفقات مفتوحة لكل عملة
القيمة الحالية: 1

*📦 Fixed_Lot_Size:*
حجم اللوت الثابت
القيمة الحالية: 0.02

*🚫 Excluded_Symbols:*
العملات المستبعدة
القيمة: XAU, XAG, BTC, ETH, OIL

*🛡️ max_spread:*
أقصى سبريد مسموح (بالنقاط)
القيمة الحالية: 100 نقطة
"""

TROUBLESHOOT_MESSAGE = """
🔍 *حل المشاكل الشائعة:*

*❌ البوت مبيتصلش بـ MT5:*
• تأكد إن MT5 Terminal مفتوح
• تأكد إن الحساب مسجل دخول
• تأكد من بيانات الاتصال في .env

*❌ مفيش صفقات بتتفتح:*
• تحقق من الرصيد الكافي
• تحقق من السبريد (ميفوتش الحد الأقصى)
• تحقق من إعدادات Market Watch

*❌ Error: No money:*
• الرصيد مش كافي لفتح صفقات
• قلل حجم اللوت أو زود الرصيد

*❌ Daily drawdown limit exceeded:*
• البوت وقف بسبب الخسارة اليومية
• انتظر حتى اليوم التالي أو عدّل الحد

*❌ Market closed:*
• السوق مقفول (ويكند أو عطلة)
• استنى لحد ما السوق يفتح
"""

PAIRS_MESSAGE = """
💱 *العملات المدعومة:*

✅ *7 عملات رئيسية فقط:*
USD, EUR, GBP, JPY, AUD, CAD, CHF

*الأزواج المتاحة (21 زوج):*
EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
EURGBP, EURJPY, GBPJPY, AUDJPY, CADJPY, CHFJPY
EURAUD, EURCAD, GBPAUD, GBPCAD, AUDCAD, AUDCHF
CADCHF, EURCHF, GBPCHF

🚫 *مستبعد:*
XAU (ذهب), XAG (فضة), BTC (بيتكوين)
ETH (إيثيريوم), OIL (نفط), NZD, SGD, DKK, CZK
"""

STRATEGY_MESSAGE = """
📊 *شرح الاستراتيجية:*

*🎯 نوع الاستراتيجية:*
Grid Trading مع Basket Take Profit

*📈 دخول الصفقة:*
• RSI(14) < 30 → شراء
• RSI(14) > 70 → بيع
• MACD crossover → شراء
• MACD crossunder → بيع

*💰 Basket Take Profit:*
لما إجمالي ربح العملة يوصل $5 → إقفال كل صفقاتها

*🔄 إعادة الفتح:*
لما صفقة تقفل بربح → يفتح غيرها تلقائياً

*🛡️ الحماية:*
• فلتر سبريد (max 3 pips)
• Emergency Stop (equity < $100)
• حد أقصى 20 صفقة إجمالية
"""

CONTACT_MESSAGE = """
📞 *تواصل معنا:*

🌐 *GitHub:*
https://github.com/Mocoder911/MOKABotTRADE

📊 *Dashboard:*
https://moka-bot-trade.vercel.app

💬 *للدعم الفني:*
ابعت رسالتك هنا وهنرد عليك في أقرب وقت

⏰ *ساعات الدعم:*
يومياً من 10 صباحاً - 10 مساءً (توقيت القاهرة)
"""

# ============================================
# HANDLERS
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode="Markdown",
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command."""
    await update.message.reply_text(
        MENU_MESSAGE,
        parse_mode="Markdown",
    )


async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setup command."""
    await update.message.reply_text(
        SETUP_MESSAGE,
        parse_mode="Markdown",
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command."""
    await update.message.reply_text(
        SETTINGS_MESSAGE,
        parse_mode="Markdown",
    )


async def troubleshoot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /troubleshoot command."""
    await update.message.reply_text(
        TROUBLESHOOT_MESSAGE,
        parse_mode="Markdown",
    )


async def pairs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pairs command."""
    await update.message.reply_text(
        PAIRS_MESSAGE,
        parse_mode="Markdown",
    )


async def strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /strategy command."""
    await update.message.reply_text(
        STRATEGY_MESSAGE,
        parse_mode="Markdown",
    )


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /contact command."""
    await update.message.reply_text(
        CONTACT_MESSAGE,
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages."""
    text = update.message.text.lower()

    # Auto-responses for common keywords
    if any(word in text for word in ["سبريد", "spread"]):
        await update.message.reply_text(
            "🛡️ *فلتر السبريد:*\n"
            "البوت بيمنع فتح صفقات لو السبريد أكبر من 3 pips.\n"
            "ده بيحميك من الدخول في أوقات volatilty عالية.\n\n"
            "اكتب /settings لمزيد من التفاصيل.",
            parse_mode="Markdown",
        )
    elif any(word in text for word in ["ربح", "profit", "خسارة", "loss"]):
        await update.message.reply_text(
            "💰 *الربح والخسارة:*\n"
            "• Basket TP: $5 لكل عملة\n"
            "• لما الربح يوصل $5 → الصفقات بتقفل تلقائياً\n"
            "• مفيش Stop Loss - البوت بيستنى الربح\n\n"
            "اكتب /strategy لمزيد من التفاصيل.",
            parse_mode="Markdown",
        )
    elif any(word in text for word in ["تثبيت", "install", "setup"]):
        await update.message.reply_text(
            "🔧 اكتب /setup عشان تشوف خطوات التثبيت.",
        )
    elif any(word in text for word in ["عملات", "pairs", "currencies"]):
        await update.message.reply_text(
            "💱 اكتب /pairs عشان تشوف العملات المدعومة.",
        )
    elif any(word in text for word in ["مساعدة", "help", "مساعد"]):
        await update.message.reply_text(
            "💡 اكتب /menu عشان تشوف كل الأوامر المتاحة.",
        )
    else:
        # Forward unknown messages to support
        await update.message.reply_text(
            "📨 تم استلام رسالتك.\n"
            "هynetرد عليك في أقرب وقت.\n\n"
            "💡 جرب تكتب /menu عشان تشوف الأوامر المتاحة.",
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.warning(f"Update {update} caused error {context.error}")


# ============================================
# MAIN
# ============================================

def main():
    """Start the bot."""
    logger.info("Starting MOKABot Support Bot (@aimokabot)...")

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("setup", setup_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("troubleshoot", troubleshoot_command))
    application.add_handler(CommandHandler("pairs", pairs_command))
    application.add_handler(CommandHandler("strategy", strategy_command))
    application.add_handler(CommandHandler("contact", contact_command))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    application.add_error_handler(error_handler)

    # Start polling
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
