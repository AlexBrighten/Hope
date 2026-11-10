"""Background Automation & Scheduling for Hope UltraLight (APScheduler):
Morning executive briefing (8:00 AM), inbox triage, and nightly memory distillation.
Uses Tier 1 (local private Ollama) so private data never touches cloud AI.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import config
from database import db
from brain.persona import HOPE_PERSONA
from brain.local_brain import local_brain
from tools.calendar import cal_list
from tools.gmail import mail_search
from tools.web import deep_research
from tools.memory import remember

logger = logging.getLogger(__name__)


class HopeScheduler:
    def __init__(self, bot_app=None):
        self.scheduler = AsyncIOScheduler(timezone=config.timezone)
        self.bot_app = bot_app

    async def send_telegram_alert(self, text: str):
        """Send proactive notification to user's Telegram."""
        if not self.bot_app or not config.allowed_user_id:
            logger.warning("Cannot send alert: Bot instance or user ID not configured")
            return
        try:
            await self.bot_app.bot.send_message(
                chat_id=config.allowed_user_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send scheduled Telegram alert: {e}")

    async def morning_briefing_job(self):
        """Compile and deliver 8:00 AM executive morning brief."""
        logger.info("Executing Morning Briefing job...")
        try:
            # 1. Fetch private schedule and inbox
            cal_summary = await cal_list(days_ahead=1, max_results=10)
            inbox_summary = await mail_search(query="is:unread", max_results=5)

            # 2. Local distillation
            prompt = (
                f"You are Hope, preparing a concise executive briefing. "
                f"Create a concise, motivating executive morning briefing for the owner today ({datetime.now().strftime('%A, %B %d')}).\n\n"
                f"Schedule:\n{cal_summary}\n\n"
                f"Unread Emails:\n{inbox_summary}\n\n"
                f"Keep it brief with clean bullet points and clear action items."
            )

            res = await local_brain.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=HOPE_PERSONA
            )
            briefing_text = res.get("content", "")
            if not briefing_text:
                briefing_text = f"☀️ **Good Morning! Here is your agenda:**\n\n{cal_summary}\n\n{inbox_summary}"

            await self.send_telegram_alert(f"☀️ **Hope Executive Briefing**\n\n{briefing_text}")
        except Exception as e:
            logger.error(f"Morning briefing failed: {e}")

    async def inbox_triage_job(self):
        """Check for unread emails every 2 hours."""
        logger.info("Running background inbox triage...")
        try:
            inbox_summary = await mail_search(query="is:unread", max_results=3)
            if "No messages found" not in inbox_summary and "Error" not in inbox_summary:
                await self.send_telegram_alert(f"📬 **Inbox Triage Update**:\n\n{inbox_summary}")
        except Exception as e:
            logger.debug(f"Inbox triage skipped or failed: {e}")

    async def nightly_memory_distill_job(self):
        """Consolidate memories and export markdown at 2:00 AM."""
        logger.info("Running nightly memory distillation...")
        try:
            db.export_memory_to_markdown()
            logger.info("Exported memories to workspace/memory.md successfully.")
        except Exception as e:
            logger.error(f"Nightly memory distillation failed: {e}")

    async def autonomous_research_job(self):
        """Run configured research watches and deliver findings while the user is away."""
        for query in config.autonomous_research_queries:
            try:
                findings = await deep_research(query)
                await self.send_telegram_alert(f"🔎 **Hope Research Watch**\n\n{findings[:3800]}")
            except Exception as e:
                logger.error("Autonomous research failed for %r: %s", query, e)

    async def task_reminder_job(self):
        """Deliver each due task reminder once."""
        for task in db.get_due_tasks():
            if not db.mark_task_reminded(task["id"]):
                continue
            details = f"\n{task['description']}" if task["description"] else ""
            await self.send_telegram_alert(
                f"⏰ **Task reminder**\n\n"
                f"**{task['title']}** ({task['priority']} priority){details}\n\n"
                f"Task ID: `{task['id']}`"
            )

    def start(self):
        """Register jobs and start scheduler."""
        # 1. Morning brief at 8:00 AM daily
        self.scheduler.add_job(
            self.morning_briefing_job,
            CronTrigger(hour=8, minute=0),
            id="morning_briefing",
            replace_existing=True
        )

        # 2. Inbox triage every 2 hours between 9:00 AM and 7:00 PM
        self.scheduler.add_job(
            self.inbox_triage_job,
            IntervalTrigger(hours=2),
            id="inbox_triage",
            replace_existing=True
        )

        # 3. Nightly memory distillation at 2:00 AM
        self.scheduler.add_job(
            self.nightly_memory_distill_job,
            CronTrigger(hour=2, minute=0),
            id="nightly_distill",
            replace_existing=True
        )
        if config.autonomous_research_queries:
            self.scheduler.add_job(
                self.autonomous_research_job,
                "interval",
                hours=max(1, config.autonomous_research_interval_hours),
                id="autonomous_research",
                replace_existing=True
            )
        self.scheduler.add_job(
            self.task_reminder_job,
            IntervalTrigger(minutes=1),
            id="task_reminders",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Hope Scheduler started (Morning briefing, inbox triage, memory distill registered).")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()


scheduler = HopeScheduler()
