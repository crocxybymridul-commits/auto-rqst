import logging
import os
import sqlite3
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application, ChatJoinRequestHandler, CommandHandler, ContextTypes
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
ADMIN_ID = int(os.environ["ADMIN_ID"])
DB_PATH = os.getenv("DATABASE_PATH", "/data/letter.db")
if DB_PATH == "/data/letter.db":
    os.makedirs("/data", exist_ok=True)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
log = logging.getLogger("LETTER")
paused = False


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            result TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def record(user_id, username, result, detail=""):
    with db() as conn:
        conn.execute(
            "INSERT INTO approvals(user_id, username, result, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, username or "", result, detail[:500],
             datetime.now(timezone.utc).isoformat())
        )


def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.effective_message.reply_text("LETTER is running.")
        return
    await update.effective_message.reply_text(
        "LETTER — Join Request Manager\n\n"
        "/status — approval statistics\n"
        "/pause — pause automatic approvals\n"
        "/resume — resume automatic approvals\n"
        "/help — commands\n\n"
        "This version automatically handles NEW join requests."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.effective_message.reply_text(
        "/status - show totals\n"
        "/pause - stop approving new requests\n"
        "/resume - start approving new requests"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    with db() as conn:
        approved = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE result='approved'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE result='failed'"
        ).fetchone()[0]
    await update.effective_message.reply_text(
        f"LETTER STATUS: {'PAUSED' if paused else 'ACTIVE'}\n"
        f"New requests approved: {approved}\n"
        f"Failures: {failed}\n"
        f"Existing backlog: Not accessible through Bot API."
    )


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global paused
    if not is_admin(update):
        return
    paused = True
    await update.effective_message.reply_text("Automatic approval paused.")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global paused
    if not is_admin(update):
        return
    paused = False
    await update.effective_message.reply_text("Automatic approval resumed.")


async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global paused
    request = update.chat_join_request
    if not request or request.chat.id != CHANNEL_ID:
        return
    if paused:
        log.info("Request left pending because LETTER is paused: user_id=%s", request.from_user.id)
        return

    try:
        # The bot must be a channel administrator with Invite Users permission.
        await context.bot.approve_chat_join_request(
            chat_id=CHANNEL_ID,
            user_id=request.from_user.id,
        )
        record(request.from_user.id, request.from_user.username, "approved")
        log.info("Approved join request: user_id=%s", request.from_user.id)
    except Exception as exc:
        record(request.from_user.id, request.from_user.username, "failed", str(exc))
        log.exception("Could not approve request for user_id=%s", request.from_user.id)


async def post_init(app: Application):
    me = await app.bot.get_me()
    log.info("LETTER started as @%s", me.username)
    try:
        member = await app.bot.get_chat_member(CHANNEL_ID, me.id)
        log.info("Bot channel status: %s", member.status)
        if member.status != "administrator":
            log.error("Bot is not an administrator in the configured channel.")
    except Exception:
        log.exception("Could not verify channel access. Check CHANNEL_ID and bot permissions.")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.run_polling(
        allowed_updates=["message", "chat_join_request"],
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
