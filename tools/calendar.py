"""Google Calendar API Integration for Hope UltraLight:
List, schedule, and delete calendar events (with approval gate on deletes).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from googleapiclient.discovery import build
from tools.google_auth import google_auth
from tools.approval import stage_action, register_approvable_action
from config import config

logger = logging.getLogger(__name__)


def _get_calendar_service():
    creds = google_auth.get_credentials()
    if not creds:
        raise RuntimeError("Google OAuth credentials missing. Place `credentials.json` in root folder.")
    return build("calendar", "v3", credentials=creds)


async def cal_list(days_ahead: int = 7, max_results: int = 15) -> str:
    """List upcoming Google Calendar events."""
    try:
        service = _get_calendar_service()
        now = datetime.now(timezone.utc).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()

        events_res = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=end,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_res.get("items", [])
        if not events:
            return f"📅 No upcoming events found in the next {days_ahead} days."

        lines = [f"### 📅 Upcoming Schedule ({len(events)} events):\n"]
        for e in events:
            start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date"))
            summary = e.get("summary", "(No title)")
            loc = f" at {e['location']}" if "location" in e else ""
            lines.append(f"- **{start}**: {summary}{loc} (ID: `{e['id']}`)")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Calendar list error: {e}")
        return f"Calendar list error: {e}"


async def cal_add(summary: str, start_time: str, end_time: str, description: str = "", location: str = "") -> str:
    """Schedule a new event on Google Calendar (start_time & end_time in ISO format: YYYY-MM-DDTHH:MM:SSZ)."""
    try:
        service = _get_calendar_service()
        event_body = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time}
        }
        created = service.events().insert(calendarId="primary", body=event_body).execute()
        return f"📅 Event created: **{summary}**\nLink: {created.get('htmlLink')}\nID: `{created.get('id')}`"
    except Exception as e:
        logger.error(f"Calendar add error: {e}")
        return f"Failed to add calendar event: {e}"


async def _actual_delete_event(event_id: str) -> str:
    service = _get_calendar_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return f"Calendar event `{event_id}` was successfully deleted."


# Register approvable action
register_approvable_action("cal_delete", _actual_delete_event)


async def cal_delete(event_id: str) -> Dict[str, Any]:
    """Delete a calendar event (requires human confirmation)."""
    if config.require_approval:
        desc = f"Permanently delete calendar event with ID: `{event_id}`"
        return stage_action("cal_delete", {"event_id": event_id}, desc)
    else:
        res = await _actual_delete_event(event_id)
        return {"status": "executed", "result": res}

