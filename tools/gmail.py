"""Gmail API Integration for Hope UltraLight:
Search, read, draft, and send emails (with human-in-the-loop approval gate).
"""

import base64
import logging
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
from googleapiclient.discovery import build
from tools.google_auth import google_auth
from tools.approval import stage_action, register_approvable_action
from config import config

logger = logging.getLogger(__name__)


def _get_gmail_service():
    creds = google_auth.get_credentials()
    if not creds:
        raise RuntimeError("Google OAuth credentials missing. Place `credentials.json` in root folder.")
    return build("gmail", "v1", credentials=creds)


async def mail_search(query: str = "is:unread", max_results: int = 5) -> str:
    """Search Gmail messages by query (e.g. 'is:unread', 'from:boss', 'label:INBOX')."""
    try:
        service = _get_gmail_service()
        res = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = res.get("messages", [])

        if not messages:
            return f"No messages found matching query: `{query}`"

        output = [f"### ✉️ Gmail Search Results ({len(messages)}):\n"]
        for m in messages:
            msg = service.users().messages().get(userId="me", id=m["id"], format="metadata",
                                                 metadataHeaders=["Subject", "From", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            output.append(
                f"- **ID**: `{m['id']}`\n"
                f"  **From**: {headers.get('From', 'Unknown')}\n"
                f"  **Subject**: {headers.get('Subject', '(No subject)')}\n"
                f"  **Date**: {headers.get('Date', '')}\n"
            )
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Gmail search error: {e}")
        return f"Gmail search error: {e}"


async def mail_read(message_id: str) -> str:
    """Read and decode the full body of a Gmail message by message_id."""
    try:
        service = _get_gmail_service()
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

        body = ""
        payload = msg.get("payload", {})
        if "data" in payload.get("body", {}):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break

        if not body:
            body = msg.get("snippet", "(No readable plain text body found)")

        return (
            f"### ✉️ Message: {headers.get('Subject', '(No subject)')}\n"
            f"- **From**: {headers.get('From', 'Unknown')}\n"
            f"- **To**: {headers.get('To', 'Me')}\n"
            f"- **Date**: {headers.get('Date', '')}\n\n"
            f"**Body**:\n{body[:4000]}"
        )
    except Exception as e:
        logger.error(f"Gmail read error: {e}")
        return f"Failed to read message {message_id}: {e}"


async def mail_draft(to: str, subject: str, body: str) -> str:
    """Create a draft email in Gmail for manual review."""
    try:
        service = _get_gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return f"📝 Draft created successfully in Gmail!\nDraft ID: `{draft.get('id')}`\nTo: {to}\nSubject: {subject}"
    except Exception as e:
        logger.error(f"Gmail draft error: {e}")
        return f"Failed to create draft: {e}"


async def _actual_send_email(to: str, subject: str, body: str) -> str:
    """Internal helper to actually dispatch the email via Gmail API."""
    service = _get_gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent to {to} with subject '{subject}'. Message ID: `{sent.get('id')}`"


# Register approvable action
register_approvable_action("mail_send", _actual_send_email)


async def mail_send(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send an email (stages for approval if REQUIRE_APPROVAL is true)."""
    if config.require_approval:
        desc = f"Send email to **{to}** with subject **'{subject}'**\n\nPreview:\n{body[:300]}"
        return stage_action("mail_send", {"to": to, "subject": subject, "body": body}, desc)
    else:
        res = await _actual_send_email(to, subject, body)
        return {"status": "executed", "result": res}

