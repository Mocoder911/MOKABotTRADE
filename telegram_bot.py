"""
MOKABot Telegram Support Bot
@aimokabot - Technical support bot for MOKABot trading system
With MT5 integration for balance reports and trade notifications
"""

import logging
import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    JobQueue,
)

# ============================================
# CONFIGURATION
# ============================================
BOT_TOKEN = "8989474621:AAE__nslSBkxlhC3eXG8FMzYj9KGLVLbYnU"

# MT5 Configuration
MT5_ACCOUNT_ID = 84128321
MT5_PASSWORD = "Mody@2024"
MT5_SERVER = "FPMarketsSC-Live"

# Chat ID for notifications (set via /setchat command)
NOTIFICATION_CHAT_ID = None

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Try to import MT5
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 not installed - MT5 features disabled")

# Track positions for change detection
last_positions = {}

# ============================================
# MESSAGES
# ============================================
WELCOME_MESSAGE = """
🤖 *مرحباً بك في بوت دعم MOKABot!*

أنا البوت الرسمي للدعم الفني لنظام MOKABot للتداول الآلي.

📋 *الأوامر المتاحة:*
/start - رسالة الترحيب هذه
/menu - عرض القائمة الرئيسية
/balance - عرض الرصيد الحالي
/positions - عرض الصفقات المفتوحة
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

💰 /balance - الرصيد الحالي
📊 /positions - الصفقات المفتوحة
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
# MT5 FUNCTIONS
# ============================================

def connect_mt5():
    """Connect to MT5 terminal."""
    if not MT5_AVAILABLE:
        return False, "MetaTrader5 not installed"
    
    if not mt5.initialize():
        return False, f"MT5 initialization failed: {mt5.last_error()}"
    
    # Login to account
    authorized = mt5.login(
        login=MT5_ACCOUNT_ID,
        password=MT5_PASSWORD,
        server=MT5_SERVER
    )
    
    if not authorized:
        return False, f"MT5 login failed: {mt5.last_error()}"
    
    return True, "Connected"


def get_account_info():
    """Get account balance and equity."""
    success, msg = connect_mt5()
    if not success:
        return None, msg
    
    account_info = mt5.account_info()
    if account_info is None:
        return None, "Failed to get account info"
    
    return {
        "balance": account_info.balance,
        "equity": account_info.equity,
        "profit": account_info.profit,
        "margin": account_info.margin,
        "free_margin": account_info.margin_free,
        "margin_level": account_info.margin_level if account_info.margin > 0 else 0,
    }, "OK"


def get_open_positions():
    """Get all open positions."""
    success, msg = connect_mt5()
    if not success:
        return [], msg
    
    positions = mt5.positions_get()
    if positions is None:
        return [], "No positions"
    
    result = []
    for pos in positions:
        result.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == 0 else "SELL",
            "volume": pos.volume,
            "price_open": pos.price_open,
            "price_current": pos.price_current,
            "profit": pos.profit + pos.swap,
            "time": datetime.fromtimestamp(pos.time).strftime("%Y-%m-%d %H:%M"),
        })
    
    return result, "OK"


# ============================================
# NOTIFICATION FUNCTIONS
# ============================================

async def send_notification(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send notification to registered chat."""
    global NOTIFICATION_CHAT_ID
    
    if NOTIFICATION_CHAT_ID is None:
        logger.warning("No chat ID registered for notifications")
        return
    
    try:
        await context.bot.send_message(
            chat_id=NOTIFICATION_CHAT_ID,
            text=message,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


async def hourly_balance_report(context: ContextTypes.DEFAULT_TYPE):
    """Send hourly balance report."""
    account_info, msg = get_account_info()
    
    if account_info is None:
        await send_notification(context, f"❌ فشل جلب بيانات الحساب:\n{msg}")
        return
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    message = f"""
💰 *تقرير الرصيد - {now}*

💵 *الرصيد:* ${account_info['balance']:.2f}
📊 *الموجودات:* ${account_info['equity']:.2f}
📈 *الربح/الخسارة:* ${account_info['profit']:.2f}
💳 *الهامش المستخدم:* ${account_info['margin']:.2f}
💵 *الهامش الحر:* ${account_info['free_margin']:.2f}
📊 *مستوى الهامش:* {account_info['margin_level']:.2f}%
"""
    
    await send_notification(context, message)


async def check_position_changes(context: ContextTypes.DEFAULT_TYPE):
    """Check for position changes and send notifications."""
    global last_positions
    
    positions, msg = get_open_positions()
    
    if msg != "OK":
        return
    
    current_positions = {p["ticket"]: p for p in positions}
    current_tickets = set(current_positions.keys())
    last_tickets = set(last_positions.keys())
    
    # New positions opened
    new_tickets = current_tickets - last_tickets
    for ticket in new_tickets:
        pos = current_positions[ticket]
        message = f"""
🟢 *صفقة جديدة!*

💱 العملة: {pos['symbol']}
📊 النوع: {pos['type']}
📦 الحجم: {pos['volume']} Lot
💰 سعر الفتح: {pos['price_open']}
🕐 الوقت: {pos['time']}
"""
        await send_notification(context, message)
    
    # Positions closed
    closed_tickets = last_tickets - current_tickets
    for ticket in closed_tickets:
        pos = last_positions[ticket]
        message = f"""
🔴 *صفقة مقفلة!*

💱 العملة: {pos['symbol']}
📊 النوع: {pos['type']}
📦 الحجم: {pos['volume']} Lot
💰 الربح/الخسارة: ${pos['profit']:.2f}
🕐 الوقت: {pos['time']}
"""
        await send_notification(context, message)
    
    # Update last positions
    last_positions = current_positions


# ============================================
# COMMAND HANDLERS
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


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command - show current balance."""
    await update.message.reply_text("⏳ جاري جلب البيانات...")
    
    account_info, msg = get_account_info()
    
    if account_info is None:
        await update.message.reply_text(f"❌ فشل جلب البيانات:\n{msg}")
        return
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    message = f"""
💰 *تقرير الرصيد*
🕐 {now}

💵 *الرصيد:* ${account_info['balance']:.2f}
📊 *الموجودات:* ${account_info['equity']:.2f}
📈 *الربح/الخسارة:* ${account_info['profit']:.2f}
💳 *الهامش المستخدم:* ${account_info['margin']:.2f}
💵 *الهامش الحر:* ${account_info['free_margin']:.2f}
📊 *مستوى الهامش:* {account_info['margin_level']:.2f}%
"""
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /positions command - show open positions."""
    await update.message.reply_text("⏳ جاري جلب الصفقات...")
    
    positions, msg = get_open_positions()
    
    if not positions:
        await update.message.reply_text("📭 مفيش صفقات مفتوحة حالياً.")
        return
    
    total_profit = sum(p["profit"] for p in positions)
    
    message = f"📊 *الصفقات المفتوحة ({len(positions)} صفقة)*\n"
    message += f"💰 *إجمالي الربح/الخسارة:* ${total_profit:.2f}\n\n"
    
    for pos in positions[:20]:  # Limit to 20 positions
        emoji = "🟢" if pos["profit"] >= 0 else "🔴"
        message += f"{emoji} *{pos['symbol']}* | {pos['type']} | {pos['volume']}L | ${pos['profit']:.2f}\n"
    
    if len(positions) > 20:
        message += f"\n... و {len(positions) - 20} صفقة أخرى"
    
    await update.message.reply_text(message, parse_mode="Markdown")


async def setchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setchat command - register chat for notifications."""
    global NOTIFICATION_CHAT_ID
    
    NOTIFICATION_CHAT_ID = update.effective_chat.id
    
    await update.message.reply_text(
        f"✅ تم تسجيل هذا الشات للإشعارات!\n"
        f"Chat ID: {NOTIFICATION_CHAT_ID}\n\n"
        f"هتوصلك إشعارات كل ساعة بالرصيد،"
        f"وكمان عند فتح/إقفال أي صفقة."
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
    elif any(word in text for word in ["رصيد", "balance"]):
        await update.message.reply_text(
            "💰 اكتب /balance عشان تشوف الرصيد الحالي.",
        )
    elif any(word in text for word in ["صفقات", "positions"]):
        await update.message.reply_text(
            "📊 اكتب /positions عشان تشوف الصفقات المفتوحة.",
        )
    else:
        # Forward unknown messages to support
        await update.message.reply_text(
            "📨 تم استلام رسالتك.\n"
            "هنترد عليك في أقرب وقت.\n\n"
            "💡 جرب تكتب /menu عشان تشوف الأوامر المتاحة.",
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.warning(f"Update {update} caused error {context.error}")


async def post_init(application: Application):
    """Initialize job queue after bot starts."""
    # Schedule hourly balance report
    application.job_queue.run_repeating(
        hourly_balance_report,
        interval=3600,  # Every hour (3600 seconds)
        first=10,  # First run after 10 seconds
    )
    
    # Schedule position check every 30 seconds
    application.job_queue.run_repeating(
        check_position_changes,
        interval=30,  # Every 30 seconds
        first=5,  # First run after 5 seconds
    )
    
    logger.info("Job queue started: hourly reports + position monitoring")


# ============================================
# MAIN
# ============================================

def main():
    """Start the bot."""
    logger.info("Starting MOKABot Support Bot (@aimokabot)...")

    # Create application with job queue
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("positions", positions_command))
    application.add_handler(CommandHandler("setchat", setchat_command))
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
