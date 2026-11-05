import logging
import time
import aiohttp
import os
import threading
from flask import Flask
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from config import BOT_TOKEN, ADMIN_ID, BOT_NAME
import database as db

# ===== إعدادات Flask لـ Render =====
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "مبرمج الظل يعمل!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    web_app.run(host='0.0.0.0', port=port)

# ===== إعدادات البوت =====
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("ShadowBot")

start_time = time.time()

def is_admin(uid): return uid == ADMIN_ID

# ===== /start =====
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if db.is_banned(u.id):
        await update.message.reply_text("⛔ أنت محظور من استخدام البوت.")
        return
    db.add_user(u.id, u.username, u.first_name)
    db.log_action(u.id, "start")
    kb = [
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
         InlineKeyboardButton("🕐 الوقت", callback_data="time")],
        [InlineKeyboardButton("ℹ️ عن البوت", callback_data="about"),
         InlineKeyboardButton("🌐 IP Info", callback_data="ipinfo")],
    ]
    await update.message.reply_text(
        f"🖤 **{BOT_NAME}**\nأهلاً {u.first_name}. أنا بوت الظل — جاهز لأي عمل.\n\nاستخدم /help للأوامر.",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
    )

# ===== /help =====
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db.log_action(update.effective_user.id, "help")
    text = (
        f"🖤 **أوامر {BOT_NAME}:**\n\n"
        "**عامة:**\n"
        "/start - البداية\n/help - القائمة\n/ping - فحص الاستجابة\n"
        "/time - الوقت\n/id - معلوماتك\n/ip <ip> - معلومات IP\n"
        "/short <url> - اختصار رابط\n\n"
        "**أدمن:**\n"
        "/stats - إحصائيات\n/users - عدد المستخدمين\n"
        "/ban <id> - حظر\n/unban <id> - إلغاء حظر\n"
        "/broadcast <msg> - بث\n/logs - سجل التدقيق\n"
        "/backup - نسخة احتياطية\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ===== /ping =====
async def ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db.log_action(update.effective_user.id, "ping")
    t = time.time()
    msg = await update.message.reply_text("🏓 ...")
    ms = round((time.time() - t) * 1000, 2)
    await msg.edit_text(f"🏓 **Pong!** `{ms} ms`", parse_mode="Markdown")

# ===== /time =====
async def time_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db.log_action(update.effective_user.id, "time")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(f"🕐 `{now}`", parse_mode="Markdown")

# ===== /id =====
async def id_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db.log_action(update.effective_user.id, "id")
    u = update.effective_user
    role = "👑 مشرف" if is_admin(u.id) else "👤 مستخدم"
    await update.message.reply_text(
        f"👤 **معلوماتك:**\nالاسم: {u.first_name}\n"
        f"المعرف: @{u.username or 'لا يوجد'}\n"
        f"الايدي: `{u.id}`\nالصلاحية: {role}",
        parse_mode="Markdown"
    )

# ===== /ip =====
async def ip_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db.log_action(update.effective_user.id, "ip")
    if not ctx.args:
        await update.message.reply_text("الاستخدام: `/ip 8.8.8.8`", parse_mode="Markdown")
        return
    ip = ctx.args[0]
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"http://ip-api.com/json/{ip}", timeout=10) as r:
                data = await r.json()
        if data.get("status") == "success":
            txt = (
                f"🌐 **معلومات IP:**\n"
                f"IP: `{data['query']}`\n"
                f"الدولة: {data['country']} ({data['countryCode']})\n"
                f"المدينة: {data.get('city','—')}\n"
                f"المزود: {data.get('isp','—')}\n"
                f"خط العرض/الطول: {data['lat']}, {data['lon']}"
            )
        else:
            txt = "❌ IP غير صالح أو لا يوجد بيانات."
        await update.message.reply_text(txt, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")

# ===== /short =====
async def short_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db.log_action(update.effective_user.id, "short")
    if not ctx.args:
        await update.message.reply_text("الاستخدام: `/short https://example.com`", parse_mode="Markdown")
        return
    url = ctx.args[0]
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://tinyurl.com/api-create.php?url={url}", timeout=10) as r:
                short = await r.text()
        await update.message.reply_text(f"🔗 الرابط المختصر:\n`{short}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")

# ===== /stats =====
async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمشرف فقط."); return
    db.log_action(update.effective_user.id, "stats")
    up = int(time.time() - start_time)
    h, m, s = up // 3600, (up % 3600) // 60, up % 60
    await update.message.reply_text(
        f"📊 **إحصائيات {BOT_NAME}:**\n\n"
        f"👥 المستخدمون: `{db.count_users()}`\n"
        f"⏱ التشغيل: `{h}س {m}د {s}ث`",
        parse_mode="Markdown"
    )

# ===== /users =====
async def users_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمشرف فقط."); return
    db.log_action(update.effective_user.id, "users")
    await update.message.reply_text(f"👥 عدد المستخدمين: `{db.count_users()}`", parse_mode="Markdown")

# ===== /ban /unban =====
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمشرف فقط."); return
    if not ctx.args:
        await update.message.reply_text("الاستخدام: `/ban <id>`", parse_mode="Markdown"); return
    try:
        uid = int(ctx.args[0])
        db.set_banned(uid, True)
        db.log_action(update.effective_user.id, "ban", str(uid))
        await update.message.reply_text(f"🚫 تم حظر `{uid}`", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ ID غير صالح.")

async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمشرف فقط."); return
    if not ctx.args:
        await update.message.reply_text("الاستخدام: `/unban <id>`", parse_mode="Markdown"); return
    try:
        uid = int(ctx.args[0])
        db.set_banned(uid, False)
        db.log_action(update.effective_user.id, "unban", str(uid))
        await update.message.reply_text(f"✅ تم إلغاء حظر `{uid}`", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ ID غير صالح.")

# ===== /broadcast =====
async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمشرف فقط."); return
    if not ctx.args:
        await update.message.reply_text("الاستخدام: `/broadcast <رسالة>`", parse_mode="Markdown"); return
    msg = " ".join(ctx.args)
    users = db.all_users()
    ok = 0
    for uid in users:
        try:
            await ctx.bot.send_message(uid, f"📢 **بث:**\n{msg}", parse_mode="Markdown")
            ok += 1
        except: pass
    db.log_action(update.effective_user.id, "broadcast", f"sent={ok}")
    await update.message.reply_text(f"✅ تم الإرسال لـ `{ok}/{len(users)}`", parse_mode="Markdown")

# ===== /logs =====
async def logs_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمشرف فقط."); return
    import sqlite3
    conn = sqlite3.connect("shadowbot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, action, details, created_at FROM audit_log ORDER BY id DESC LIMIT 15")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("📭 السجل فارغ."); return
    txt = "📋 **آخر 15 عملية:**\n\n"
    for r in rows:
        txt += f"• `{r[3][:19]}` | {r[0]} | {r[1]} {r[2] or ''}\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

# ===== /backup =====
async def backup_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمشرف فقط."); return
    db.log_action(update.effective_user.id, "backup")
    try:
        with open("shadowbot.db", "rb") as f:
            await update.message.reply_document(f, filename="shadowbot_backup.db", caption="🗄 نسخة احتياطية من قاعدة البيانات.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")

# ===== ملفات =====
async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if db.is_banned(u.id):
        await update.message.reply_text("⛔ أنت محظور."); return
    f = update.message.document
    if f:
        db.save_file(u.id, f.file_name, f.file_id)
        db.log_action(u.id, "upload", f.file_name)
        await update.message.reply_text(f"📥 تم حفظ الملف: `{f.file_name}`", parse_mode="Markdown")

# ===== أزرار =====
async def buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "time":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await q.edit_message_text(f"🕐 `{now}`", parse_mode="Markdown")
    elif q.data == "my_stats":
        uid = q.from_user.id
        role = "👑 مشرف" if is_admin(uid) else "👤 مستخدم"
        await q.edit_message_text(f"📊 **إحصائياتك:**\nالصلاحية: {role}\nالايدي: `{uid}`", parse_mode="Markdown")
    elif q.data == "about":
        await q.edit_message_text(
            f"🖤 **{BOT_NAME} v2.0**\nبوت مخصص كامل المميزات.\n"
            "قاعدة بيانات، إدارة، بث، أدوات شبكة.",
            parse_mode="Markdown"
        )
    elif q.data == "ipinfo":
        await q.edit_message_text("🌐 استخدم: `/ip 8.8.8.8`", parse_mode="Markdown")

# ===== echo =====
async def echo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if db.is_banned(u.id):
        await update.message.reply_text("⛔ أنت محظور."); return
    db.add_user(u.id, u.username, u.first_name)
    db.log_action(u.id, "message", update.message.text[:50])
    await update.message.reply_text(f"🖤 سمعتك: «{update.message.text}»")

# ===== دالة التشغيل الأساسية =====
def run_bot():
    if not BOT_TOKEN:
        print("❌ ضع التوكن في Environment Variables أولاً.")
        return
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("time", time_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("ip", ip_cmd))
    app.add_handler(CommandHandler("short", short_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))
    app.add_handler(CommandHandler("backup", backup_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info(f"🖤 {BOT_NAME} يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# ===== نقطة البداية =====
if __name__ == "__main__":
    # تشغيل البوت في Thread منفصل عشان Flask يشتغل في الخلفية
    t = threading.Thread(target=run_bot)
    t.start()
    
    # تشغيل Flask عشان Render ميقفلش الخدمة
    run_flask()
