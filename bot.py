"""Hope UltraLight — Main Telegram Daemon & Autonomous Agent Orchestrator:
Runs single async long-polling process with zero open ports, 1-click approvals, and 3-tier routing.
"""

import sys
import logging
import asyncio
from pathlib import Path
from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import config
from database import db
from brain.router import router, RouteDecision
from brain.providers import provider_manager
from tools.registry import get_contextual_tools, dispatch_tool_call
from tools.approval import execute_approved_action, reject_action
from tools.memory import get_all_memories_text
from scheduler import scheduler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("hope_bot")


def is_authorized(update: Update) -> bool:
    """Security filter: Allow only the configured owner."""
    user = update.effective_user
    if not user or not config.allowed_user_id:
        return False
    return user.id == config.allowed_user_id


async def unauthorized_warning(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text("⛔ Unauthorized access. This private instance is locked to its owner.")


async def safe_reply(message, text: str, reply_markup=None):
    """Safely send or reply to a message, falling back to plain text if Markdown parsing fails."""
    try:
        return await message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        logger.warning(f"Markdown parse failed ({e}), falling back to plain text.")
        return await message.reply_text(text, reply_markup=reply_markup)


# ------------------------------------------------------------------------------
# Command Handlers
# ------------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    msg = (
        "🌟 **Hope UltraLight Agent Ready**\n\n"
        "Your autonomous personal executive AI is active and connected.\n\n"
        "**Available Commands:**\n"
        "• `/status` — System health, brain status & quota usage\n"
        "• `/brief` — Generate today's executive morning briefing\n"
        "• `/deep <prompt>` — Deep reasoning mode via OpenRouter\n"
        "• `/local <prompt>` — Force local Ollama (0 cloud tokens)\n"
        "• `/free <prompt>` — Force OpenRouter Inkling 2 Small\n"
        "• `/gemini <prompt>` — Force Gemini 2.5 Flash\n"
        "• `/mem` — View long-term memory notes\n\n"
        "_Tip: Send a text message, search query, or meeting request naturally!_"
    )
    await safe_reply(update.message, msg)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    ollama_health = await provider_manager.local.check_health()
    openrouter_health = await provider_manager.openrouter.check_health()
    gemini_health = await provider_manager.gemini.check_health()

    or_usage = db.get_provider_usage_today("openrouter")
    gem_usage = db.get_provider_usage_today("gemini")
    ol_usage = db.get_provider_usage_today("ollama")

    status_text = (
        "📊 **Hope UltraLight Health & Quota Report**\n\n"
        f"🧠 **Tier 1: Local Ollama (`{config.ollama_model}`)**\n"
        f"• Status: {'🟢 Online' if ollama_health.get('online') else '🔴 Offline'}\n"
        f"• Model Installed: {'✅ Yes' if ollama_health.get('installed') else '⚠️ Not Found'}\n"
        f"• Today's Queries: {ol_usage['request_count']} requests\n\n"
        f"⚡ **Tier 2: OpenRouter Free (`{config.openrouter_model}`)**\n"
        f"• Status: {'🟢 Ready' if openrouter_health.get('configured') else '⚪ Missing API Key'}\n"
        f"• Daily Quota: {or_usage['request_count']} / {config.daily_openrouter_limit} requests\n\n"
        f"☁️ **Tier 3: Gemini Fallback (`{config.gemini_model}`)**\n"
        f"• Status: {'🟢 Ready' if gemini_health.get('configured') else '⚪ Missing API Key'}\n"
        f"• Daily Quota: {gem_usage['request_count']} / {config.daily_gemini_limit} requests\n\n"
        f"🛡️ **Approvals & Security**:\n"
        f"• Mutating Gate: {'🔒 Enabled' if config.require_approval else '⚠️ Direct Execution'}\n"
        f"• Timezone: `{config.timezone}`"
    )
    await safe_reply(update.message, status_text)


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    status_msg = await safe_reply(update.message, "☀️ *Compiling your executive morning briefing...*")
    await scheduler.morning_briefing_job()
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass


async def cmd_mem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    text = get_all_memories_text()
    await safe_reply(update.message, text)


# ------------------------------------------------------------------------------
# Core Message Processing Engine
# ------------------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    user_text = update.message.text
    if not user_text:
        return

    chat_id = update.effective_chat.id
    # 1. Typing action
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    # 2. Deterministic Routing (<1 ms)
    route = router.route(user_text)
    logger.info(f"Route selected: Tier {route.tier} ({route.reason}), Private={route.is_private}")

    # 3. Contextual compact tools
    tools = get_contextual_tools(route.tool_category)

    messages = [
        {"role": "user", "content": route.cleaned_query}
    ]

    system_prompt = (
        "You are Hope, an autonomous personal executive AI agent. "
        "Be direct, concise, and helpful. Format output using clean Markdown. "
        "When needed, invoke appropriate tools to assist the user."
    )

    # 4. Execute turn through Provider Chain
    try:
        response = await provider_manager.chat(
            messages=messages,
            tools=tools,
            tier=route.tier,
            is_private=route.is_private,
            effort=route.reasoning_effort,
            system_prompt=system_prompt
        )

        tool_calls = response.get("tool_calls", [])
        content = response.get("content", "")

        # 5. Handle Tool Calls if generated
        if tool_calls:
            for tc in tool_calls:
                func_name = tc["name"]
                func_args = tc["arguments"]

                # Inform user of tool step
                status_msg = await update.message.reply_text(
                    f"⚙️ *Executing tool:* `{func_name}`...",
                    parse_mode="Markdown"
                )

                tool_result = await dispatch_tool_call(func_name, func_args)

                # Check if this tool staged an approval action
                if isinstance(tool_result, dict) and "reply_markup" in tool_result:
                    await status_msg.delete()
                    await safe_reply(
                        update.message,
                        f"⚠️ **Approval Required**\n\n{tool_result.get('description')}",
                        reply_markup=tool_result["reply_markup"]
                    )
                    return

                # Normal tool execution result: feed back to LLM for final synthesis
                await status_msg.edit_text(f"✅ Finished `{func_name}`. Synthesizing response...", parse_mode="Markdown")

                messages.append({"role": "assistant", "content": f"Executed {func_name}"})
                messages.append({"role": "user", "content": f"Tool '{func_name}' returned: {str(tool_result)[:3000]}"})

                follow_up = await provider_manager.chat(
                    messages=messages,
                    tier=route.tier,
                    is_private=route.is_private,
                    effort=route.reasoning_effort,
                    system_prompt=system_prompt
                )
                await status_msg.delete()
                content = follow_up.get("content", str(tool_result))

        # 6. Send final reply
        if not content:
            content = "Done."

        # Telegram 4096 character limit safety chunking
        if len(content) > 4000:
            for chunk in [content[i:i + 4000] for i in range(0, len(content), 4000)]:
                await safe_reply(update.message, chunk)
        else:
            await safe_reply(update.message, content)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await safe_reply(update.message, f"❌ An error occurred: `{e}`")


# ------------------------------------------------------------------------------
# Approval Callbacks ([Approve] / [Reject])
# ------------------------------------------------------------------------------
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(update):
        return await query.edit_message_text("⛔ Unauthorized.")

    data = query.data or ""
    logger.info(f"Received callback: {data}")

    if data.startswith("appr:"):
        action_id = data.split(":", 1)[1]
        result_text = await execute_approved_action(action_id)
        await query.edit_message_text(result_text, parse_mode="Markdown")

    elif data.startswith("rejc:"):
        action_id = data.split(":", 1)[1]
        result_text = reject_action(action_id)
        await query.edit_message_text(result_text, parse_mode="Markdown")


# ------------------------------------------------------------------------------
# Voice Note Handler
# ------------------------------------------------------------------------------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await unauthorized_warning(update)

    voice = update.message.voice
    if not voice:
        return

    status_msg = await update.message.reply_text("🎙️ *Processing voice note...*", parse_mode="Markdown")
    try:
        file = await context.bot.get_file(voice.file_id)
        temp_audio = Path("workspace") / f"voice_{voice.file_unique_id}.oga"
        temp_audio.parent.mkdir(parents=True, exist_ok=True)
        await file.download_to_drive(custom_path=str(temp_audio))

        # Transcribe via Gemini
        transcription = await provider_manager.gemini.transcribe_audio(temp_audio)
        temp_audio.unlink(missing_ok=True)

        if not transcription:
            await status_msg.edit_text("❌ Could not transcribe voice message.")
            return

        await status_msg.edit_text(f"🗣️ *Transcribed:* \"_{transcription}_\"\n\n_Processing instructions..._", parse_mode="Markdown")

        # Reuse normal message handler with transcribed text
        update.message.text = transcription
        await handle_message(update, context)

    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await status_msg.edit_text(f"❌ Failed to process voice note: {e}")


# ------------------------------------------------------------------------------
# Daemon Entry Point
# ------------------------------------------------------------------------------
def main():
    if not config.is_telegram_ready():
        logger.error("TELEGRAM_BOT_TOKEN and ALLOWED_TELEGRAM_USER_ID must be set in .env!")
        print("\n" + "=" * 60)
        print("⚠️ CONFIGURATION REQUIRED")
        print("Please configure your .env file with:")
        print("1. TELEGRAM_BOT_TOKEN (from @BotFather)")
        print("2. ALLOWED_TELEGRAM_USER_ID (from @userinfobot)")
        print("=" * 60 + "\n")
        sys.exit(1)

    app = Application.builder().token(config.telegram_bot_token).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("mem", cmd_mem))

    # Catch-all text messages and slash overrides
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Attach bot application to scheduler and start
    scheduler.bot_app = app
    scheduler.start()

    logger.info("🚀 Hope UltraLight Telegram Bot is online and polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

