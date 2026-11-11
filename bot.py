"""Hope UltraLight — Main Telegram Daemon & Autonomous Agent Orchestrator:
Runs single async long-polling process with zero open ports, 1-click approvals, and 3-tier routing.
"""

import sys
import logging
import asyncio
from datetime import datetime
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
from brain.persona import (
    HOPE_PERSONA,
    get_active_persona_name,
    set_active_persona,
    get_persona_greeting,
    PERSONA_DEFINITIONS,
)
from brain.router import router, RouteDecision
from brain.providers import provider_manager
from tools.registry import get_contextual_tools, dispatch_tool_call
from tools.approval import execute_approved_action, reject_action
from tools.memory import get_all_memories_text
from tools.system_info import format_pc_report, clean_temp_files
from tools.radar import get_tech_radar_summary
from tools.deep_research import conduct_deep_research
from tools.gmail import mail_send
from tools.terminal import run_command, launch_app
from tools.filesystem import list_dir, read_file, search_files
from tools.desktop import list_running_apps, kill_process, capture_screenshot
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


async def start_scheduler(application: Application) -> None:
    """Attach the Telegram application and start scheduling inside its event loop."""
    scheduler.bot_app = application
    scheduler.start()


async def stop_scheduler(_application: Application) -> None:
    """Stop scheduled jobs before the Telegram application shuts down."""
    scheduler.shutdown()


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

    active_key = get_active_persona_name()
    active_name = PERSONA_DEFINITIONS.get(active_key, {}).get("name", "J.A.R.V.I.S.")
    greeting = get_persona_greeting()

    msg = (
        f"🌟 **{active_name} Online — Unleashed Mode**\n"
        f"_{greeting}_\n\n"
        "**💻 Host Machine Control (Unleashed):**\n"
        "• `/cmd <command>` — Run any shell/PowerShell command directly\n"
        "• `/ls [path]` — List local folder contents & file sizes\n"
        "• `/cat <path>` — Inspect any file content on the laptop\n"
        "• `/snap` — Capture live desktop screenshot and send as photo\n"
        "• `/apps` — List active applications & memory consumers\n"
        "• `/open <app>` — Launch desktop app, folder, or file\n"
        "• `/pc` — Hardware diagnostics (CPU, RAM, Battery, Disks)\n"
        "• `/clean` — Purge safe temp files to reclaim storage\n\n"
        "**🌐 Intelligence & Deep Reconnaissance:**\n"
        "• `/research <topic>` — Autonomous multi-page deep research dossier\n"
        "• `/radar` — Live Tech Radar (Hacker News top stories & GitHub trending)\n"
        "• `/deep <prompt>` — High-effort reasoning mode\n\n"
        "**🛡️ External Action Safeguards (Authorization Required):**\n"
        "• `/mail <to> | <sub\> | <msg>` — Outbound emails require 1-click [Approve]\n"
        "• Any external mutation (sending mail, modifying calendar) requires your instruction!\n\n"
        "**🎭 Persona & Customization:**\n"
        "• `/persona [name]` — Switch persona (`jarvis`, `edith`, `friday`, `classic`)\n"
        "• `/status` — System health and quota monitoring\n\n"
        "_Tip: Ask me anything naturally, e.g. 'Run git status and tell me what changed', 'Open VS Code', or 'Research DeepSeek R1'!_"
    )
    await safe_reply(update.message, msg)


async def cmd_persona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inspect or dynamically switch active AI personality."""
    if not is_authorized(update):
        return await unauthorized_warning(update)

    text = update.message.text or ""
    parts = text.strip().split()
    if len(parts) > 1:
        target = parts[1].lower()
        if target in PERSONA_DEFINITIONS:
            set_active_persona(target)
            defn = PERSONA_DEFINITIONS[target]
            greeting = get_persona_greeting()
            msg = (
                f"🎭 **Personality Matrix Reconfigured: {defn['name']}**\n"
                f"_{defn['tagline']}_\n\n"
                f"\"{greeting}\""
            )
            return await safe_reply(update.message, msg)
        else:
            options = ", ".join(f"`{k}`" for k in PERSONA_DEFINITIONS.keys())
            return await safe_reply(update.message, f"⚠️ Unknown persona '{target}'.\nAvailable: {options}")

    active = get_active_persona_name()
    lines = [
        f"🎭 **Current Personality**: `{PERSONA_DEFINITIONS[active]['name']}` ({PERSONA_DEFINITIONS[active]['tagline']})\n",
        "**Available Personas:**"
    ]
    for k, v in PERSONA_DEFINITIONS.items():
        prefix = "👉 " if k == active else "• "
        lines.append(f"{prefix}**{v['name']}** (`/persona {k}`)\n  _{v['description']}_")

    lines.append("\n_Usage: `/persona jarvis` or `/persona edith` to switch instantly!_")
    await safe_reply(update.message, "\n".join(lines))


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
        "📊 **Hope Health & Quota Report**\n\n"
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


async def cmd_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instant hardware butler report for the potato PC."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    report = format_pc_report()
    await safe_reply(update.message, report)


async def cmd_radar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instant Hacker News & GitHub trending tech radar."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    status_msg = await safe_reply(update.message, "📡 *Scanning Hacker News and GitHub trends...*")
    radar_report = await get_tech_radar_summary()
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass
    await safe_reply(update.message, radar_report)


async def cmd_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Autonomous deep research dossier generator."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    text = update.message.text or ""
    topic = text.replace("/research", "", 1).strip()
    if not topic:
        return await safe_reply(update.message, "ℹ️ Usage: `/research <topic or company>`\nExample: `/research Cursor AI vs Windsurf`")

    status_msg = await safe_reply(update.message, f"🔎 *Initiating deep research on '{topic}'...*\n_Formulating search vectors & scraping top web sources..._")
    dossier = await conduct_deep_research(topic)
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass
    await safe_reply(update.message, dossier["summary"])


async def cmd_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean safe temporary files on the laptop to reclaim disk space."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    res = clean_temp_files()
    await safe_reply(update.message, res)


async def cmd_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick direct email composer."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    text = update.message.text or ""
    raw = text.replace("/mail", "", 1).strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 3:
        return await safe_reply(
            update.message,
            "ℹ️ Usage: `/mail <to> | <subject> | <body>`\nExample: `/mail boss@work.com | Project Update | Hey, the deployment is finished.`"
        )
    to, subject, body = parts[0], parts[1], "|".join(parts[2:])
    res = await mail_send(to=to, subject=subject, body=body)
    if isinstance(res, dict) and "reply_markup" in res:
        await safe_reply(
            update.message,
            f"⚠️ **Authorization Required (External Transmission)**\n\n{res.get('description')}",
            reply_markup=res["reply_markup"]
        )
    else:
        await safe_reply(update.message, str(res.get("result", res)))


async def cmd_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct shell / PowerShell execution."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return await safe_reply(update.message, "ℹ️ Usage: `/cmd <powershell/bash command>`\nExample: `/cmd dir` or `/cmd git status`")
    cmd_str = parts[1].strip()
    status_msg = await safe_reply(update.message, f"⚡ *Executing:* `{cmd_str}`...")
    res = await run_command(cmd_str)
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass
    if isinstance(res, dict) and "reply_markup" in res:
        await safe_reply(
            update.message,
            f"⚠️ **Authorization Required (Destructive Command)**\n\n{res.get('description')}",
            reply_markup=res["reply_markup"]
        )
    else:
        await safe_reply(update.message, str(res))


async def cmd_ls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List local directory contents."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    target = parts[1].strip() if len(parts) > 1 else "."
    res = list_dir(target)
    await safe_reply(update.message, res)


async def cmd_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read a local file."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return await safe_reply(update.message, "ℹ️ Usage: `/cat <file_path>`\nExample: `/cat README.md`")
    target = parts[1].strip()
    res = read_file(target)
    await safe_reply(update.message, res)


async def cmd_snap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture screen and deliver photo directly to Telegram."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    status_msg = await safe_reply(update.message, "📸 *Capturing desktop screenshot...*")
    res = capture_screenshot()
    img_path = config.database_path.parent / "screenshot.png"
    if img_path.exists():
        try:
            with open(img_path, "rb") as photo:
                await update.message.reply_photo(photo=photo, caption="📸 Desktop Screenshot")
            if status_msg:
                await status_msg.delete()
            return
        except Exception as e:
            logger.error(f"Failed to send screenshot: {e}")
    if status_msg:
        await status_msg.delete()
    await safe_reply(update.message, res)


async def cmd_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active applications and heavy processes."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    res = list_running_apps()
    await safe_reply(update.message, res)


async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Launch an application or open a file/folder."""
    if not is_authorized(update):
        return await unauthorized_warning(update)
    text = update.message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return await safe_reply(update.message, "ℹ️ Usage: `/open <app or path>`\nExample: `/open notepad` or `/open .`")
    target = parts[1].strip()
    res = await launch_app(target)
    await safe_reply(update.message, res)


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

    chat_history = db.get_conversation_messages(str(chat_id), limit=12)
    messages = chat_history + [{"role": "user", "content": route.cleaned_query}]
    db.add_conversation_message(str(chat_id), "user", route.cleaned_query)

    system_prompt = (
        f"{HOPE_PERSONA}\n\n"
        f"The current local date and time is {datetime.now().astimezone().isoformat()}.\n"
        "UNLEASHED SYSTEM ACCESS & HOST CAPABILITIES:\n"
        "You are fully unleashed on the host laptop. You have direct tools to execute shell/PowerShell commands (`run_command`), "
        "inspect and create files (`list_dir`, `read_file`, `write_file`, `search_files`), "
        "manage apps, processes, and desktop (`launch_app`, `kill_process`, `capture_screenshot`, `list_running_apps`), "
        "diagnose hardware (`pc_status`, `clean_temp`), and conduct deep web research (`deep_dossier`, `web_search`). "
        "Be proactive: chain tools autonomously to achieve complete results. Never claim you lack local system access.\n\n"
        "EXTERNAL & MUTATING ACTION SAFEGUARD:\n"
        "Whenever you perform an EXTERNAL action (such as sending an email via `mail_send`, or deleting calendar events via `cal_delete`), "
        "invoking the tool automatically presents the owner with an interactive 1-click [Approve] / [Reject] button. "
        "All internal operations (file reads, writes, shell commands, hardware telemetry, web searches) execute with full autonomy."
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

        # 5. Autonomous Multi-Step Tool Loop (up to MAX_TOOL_STEPS = 5)
        step = 0
        MAX_TOOL_STEPS = 5
        while tool_calls and step < MAX_TOOL_STEPS:
            step += 1
            for tc in tool_calls:
                func_name = tc.get("name", "")
                func_args = tc.get("arguments", {})

                # Inform user of tool step
                status_msg = await update.message.reply_text(
                    f"⚡ *[Step {step}/{MAX_TOOL_STEPS}] Executing:* `{func_name}`...",
                    parse_mode="Markdown"
                )

                tool_result = await dispatch_tool_call(func_name, func_args)

                # Check if this tool staged an approval action (External transmission or critical destructive operation)
                if isinstance(tool_result, dict) and "reply_markup" in tool_result:
                    await status_msg.delete()
                    await safe_reply(
                        update.message,
                        f"⚠️ **Authorization Required (External/Critical Action)**\n\n{tool_result.get('description')}",
                        reply_markup=tool_result["reply_markup"]
                    )
                    return  # Stop and await owner confirmation tap

                messages.append({"role": "assistant", "content": f"Executed tool: {func_name}"})
                messages.append({"role": "user", "content": f"Tool '{func_name}' output:\n{str(tool_result)[:3000]}"})
                await status_msg.delete()

            # Follow up turn with provider
            follow_up = await provider_manager.chat(
                messages=messages,
                tools=tools,
                tier=route.tier,
                is_private=route.is_private,
                effort=route.reasoning_effort,
                system_prompt=system_prompt
            )
            tool_calls = follow_up.get("tool_calls", [])
            content = follow_up.get("content", str(tool_result) if 'tool_result' in locals() else "Done.")

        # 6. Send final reply
        if not content:
            content = "Done."

        db.add_conversation_message(str(chat_id), "assistant", content)

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

    app = (
        Application.builder()
        .token(config.telegram_bot_token)
        .post_init(start_scheduler)
        .post_shutdown(stop_scheduler)
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("mem", cmd_mem))
    app.add_handler(CommandHandler("persona", cmd_persona))
    app.add_handler(CommandHandler(["pc", "system"], cmd_pc))
    app.add_handler(CommandHandler("radar", cmd_radar))
    app.add_handler(CommandHandler("research", cmd_research))
    app.add_handler(CommandHandler("clean", cmd_clean))
    app.add_handler(CommandHandler("mail", cmd_mail))
    app.add_handler(CommandHandler(["cmd", "sh"], cmd_cmd))
    app.add_handler(CommandHandler(["ls", "dir"], cmd_ls))
    app.add_handler(CommandHandler("cat", cmd_cat))
    app.add_handler(CommandHandler(["snap", "screenshot"], cmd_snap))
    app.add_handler(CommandHandler("apps", cmd_apps))
    app.add_handler(CommandHandler("open", cmd_open))
    app.add_handler(CommandHandler(["deep", "jobs", "local", "free", "gemini"], handle_message))

    # Catch-all text messages and slash overrides
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("🚀 Hope UltraLight Telegram Bot is online and polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
