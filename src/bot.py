import logging
import asyncio
import json
import uuid
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from src.config import settings
from src.ai_engine import BlaineAIEngine
from src.tools.registry import tool_registry
from src.memory import memory_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("blaine.bot")

ai_engine = BlaineAIEngine()

def format_telegram_html(text: str) -> str:
    """Converts standard markdown tags to Telegram HTML and cleans up formatting."""
    if not text:
        return ""
    
    # Convert code blocks ```code``` -> <pre>code</pre>
    text = re.sub(r'```(?:[a-zA-Z]*\n)?(.*?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)
    # Convert bold **text** or __text__ -> <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.*?)__', r'<i>\1</i>', text)
    # Convert inline code `text` -> <code>text</code>
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    # Strip headers (#, ##, ###)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    return text.strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Introduces Blaine to the user."""
    welcome_text = (
        "Hey! I'm Blaine. It's great to connect.\n\n"
        "I'm here to help with whatever you need—whether that's chatting about ideas, managing your home setup, "
        "or archiving and syncing media whenever you drop a link.\n\n"
        "What's on your mind today?"
    )
    await update.message.reply_text(welcome_text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays real-time system & container diagnostics."""
    res = await tool_registry.execute_tool("get_system_diagnostics", {})
    msg = res.get("message", "System diagnostic completed.")
    await update.message.reply_text(format_telegram_html(msg), parse_mode="HTML")


async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears short-term conversational history for user."""
    user_id = update.effective_user.id
    memory_manager.clear_chat_history(user_id)
    await update.message.reply_text("Short-term chat history cleared. Long-term memory facts preserved.")


async def memories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays all stored long-term memories for the user."""
    user_id = update.effective_user.id
    res = await tool_registry.execute_tool("list_memories", {"user_id": user_id})
    msg = res.get("message", "No stored memories found.")
    await update.message.reply_text(f"🧠 <b>Memory Facts</b>:\n\n{format_telegram_html(msg)}", parse_mode="HTML")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming Telegram text messages."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    user_id = update.effective_user.id

    # Send typing indicator
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    except Exception:
        pass

    # Process message with Blaine AI Engine including user_id for memory
    ai_response = await ai_engine.parse_and_respond(user_text, user_id=user_id)

    reply_text = ai_response.get("reply_text", "")
    tool_calls = ai_response.get("tool_calls", [])

    if reply_text and reply_text.strip():
        formatted_reply = format_telegram_html(reply_text)
        await update.message.reply_text(formatted_reply, parse_mode="HTML")

    facts_saved_count = 0

    # Dispatch extracted tool calls
    for call in tool_calls:
        tool_name = call.get("name")
        args = call.get("arguments", {})
        args["user_id"] = user_id

        if tool_name == "archive_media":
            job_id = f"job-{uuid.uuid4().hex[:8]}"
            job_payload = {
                "job_id": job_id,
                "chat_id": update.effective_chat.id,
                "user_id": user_id,
                "payload": args
            }

            if aioredis and settings.REDIS_HOST:
                try:
                    r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
                    await r.rpush("blaine_jobs", json.dumps(job_payload))
                    logger.info(f"Enqueued job {job_id} to Redis.")
                except Exception as e:
                    logger.error(f"Failed to push job to Redis: {e}")

            await update.message.reply_text(
                f"📥 Archiving media... Job <code>{job_id}</code> queued.",
                parse_mode="HTML"
            )
        elif tool_name == "remember_user_fact":
            res = await tool_registry.execute_tool(tool_name, args)
            logger.info(f"Executed tool '{tool_name}': {res}")
            if res.get("is_new", False):
                facts_saved_count += 1
        elif tool_name in ["web_search", "get_weather", "get_system_diagnostics", "list_memories"]:
            # These tools are executed by ai_engine for 2nd turn synthesis; only run fallback if reply_text is empty
            if not reply_text:
                res = await tool_registry.execute_tool(tool_name, args)
                summary = res.get("summary") or res.get("message", "")
                if summary:
                    await update.message.reply_text(format_telegram_html(summary), parse_mode="HTML")
        else:
            res = await tool_registry.execute_tool(tool_name, args)
            logger.info(f"Executed tool '{tool_name}': {res}")
            
            if tool_name in ["forget_memory", "update_memory", "clear_all_memories", "clear_chat_history"]:
                if not reply_text:
                    msg = res.get("message", "Memory updated.")
                    await update.message.reply_text(f"🧠 {format_telegram_html(msg)}", parse_mode="HTML")
            elif tool_name in ["schedule_reminder", "cancel_reminder", "amend_reminder", "list_reminders"]:
                if not res.get("is_duplicate", False):
                    msg = res.get("message", "Reminder updated.")
                    await update.message.reply_text(f"⏰ {format_telegram_html(msg)}", parse_mode="HTML")

            elif tool_name == "manage_list":
                msg = res.get("message", "List updated.")
                await update.message.reply_text(format_telegram_html(msg), parse_mode="HTML")
            elif tool_name == "cloud_sync":
                msg = res.get("message", "Cloud sync queued.")
                await update.message.reply_text(format_telegram_html(msg), parse_mode="HTML")

    # Send a single aggregated confirmation if facts were saved and no prior conversational text was generated
    if facts_saved_count > 0 and (not reply_text or not reply_text.strip()):
        confirm_msg = "Got it! I've noted that down for you." if facts_saved_count == 1 else f"Got it! I've noted those {facts_saved_count} facts down for you."
        await update.message.reply_text(confirm_msg)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming Telegram location attachments."""
    if not update.message or not update.message.location:
        return

    loc = update.message.location
    lat, lon = loc.latitude, loc.longitude
    user_id = update.effective_user.id

    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    except Exception:
        pass

    res = await tool_registry.execute_tool("get_weather", {"latitude": lat, "longitude": lon, "user_id": user_id})

    if res.get("status") == "SUCCESS":
        loc_name = res.get("location_name", f"{lat:.2f}, {lon:.2f}")
        memory_manager.store_fact(user_id, "location", loc_name)
        msg = res.get("message", f"Weather fetched for {loc_name}.")
        await update.message.reply_text(f"📍 Location received & saved!\n\n{format_telegram_html(msg)}", parse_mode="HTML")
    else:
        err_msg = res.get("message", "Failed to retrieve weather for location.")
        await update.message.reply_text(f"Error fetching weather: {format_telegram_html(err_msg)}")


async def check_reminders_loop(app):
    """Background task polling SQLite for due reminders."""
    while True:
        try:
            pending = memory_manager.get_pending_reminders()
            for r in pending:
                r_id = r["id"]
                chat_id = r["chat_id"]
                text = r["reminder_text"]
                msg = f"⏰ <b>Reminder</b>: {format_telegram_html(text)}"
                await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
                memory_manager.mark_reminder_triggered(r_id)
                logger.info(f"Triggered reminder [{r_id}] for chat {chat_id}: '{text}'")
        except Exception as e:
            logger.error(f"Error in reminder loop: {e}")
        await asyncio.sleep(5)


async def post_init(app):
    """Starts background tasks after application initialization."""
    asyncio.create_task(check_reminders_loop(app))

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("qual|"):
        _, job_id, quality = data.split("|")
        await query.edit_message_text(f"Understood. Set format for job <code>{job_id}</code> to {quality}.", parse_mode="HTML")

def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is missing!")
        return

    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("forget", forget_command))
    app.add_handler(CommandHandler("memories", memories_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("Blaine Telegram Bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
