"""Compact Tool Registry & Contextual Filter for Hope UltraLight:
Supplies only 3 to 6 compact tool schemas per turn, keeping CPU prompt prefill under 300 tokens!
"""

import logging
import asyncio
import inspect
from typing import Dict, Any, List, Callable, Optional, Tuple
from tools.web import web_search, fetch_page, summarize_url, company_brief, deep_research, find_job_leads
from tools.memory import remember, recall, create_task, list_tasks, complete_task, cancel_task
from tools.gmail import mail_search, mail_read, mail_draft, mail_send
from tools.calendar import cal_list, cal_add, cal_delete
from tools.sheets import sheet_append
from tools.github import gh_issues, gh_read_file
from tools.system_info import format_pc_report, clean_temp_files
from tools.radar import get_tech_radar_summary
from tools.deep_research import conduct_deep_research
from tools.terminal import run_command, launch_app
from tools.filesystem import list_dir, read_file, write_file, search_files
from tools.desktop import list_running_apps, kill_process, capture_screenshot

logger = logging.getLogger(__name__)


async def pc_status() -> str:
    return format_pc_report()


async def clean_temp() -> str:
    return clean_temp_files()


async def tech_radar() -> str:
    return await get_tech_radar_summary()


async def deep_dossier(topic: str) -> str:
    res = await conduct_deep_research(topic)
    return res["summary"]

# Compact tool metadata
TOOL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Research tools
    "web_search": {
        "function": web_search,
        "category": "research",
        "schema": {
            "name": "web_search",
            "description": "Search DuckDuckGo for live web information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query terms"},
                    "max_results": {"type": "integer", "description": "Max results to return (default: 5)"}
                },
                "required": ["query"]
            }
        }
    },
    "fetch_page": {
        "function": fetch_page,
        "category": "research",
        "schema": {
            "name": "fetch_page",
            "description": "Scrape and extract clean text from a web URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Webpage URL to fetch"}
                },
                "required": ["url"]
            }
        }
    },
    "company_brief": {
        "function": company_brief,
        "category": "research",
        "schema": {
            "name": "company_brief",
            "description": "Comprehensive lookup for a company or founder overview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Company name or founder name"}
                },
                "required": ["query"]
            }
        }
    },
    "deep_research": {
        "function": deep_research,
        "category": "research",
        "schema": {
            "name": "deep_research",
            "description": "Perform multi-source web research by searching and opening the strongest results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research question or topic"},
                    "max_sources": {"type": "integer", "description": "Number of sources to open (default: 3)"}
                },
                "required": ["query"]
            }
        }
    },
    "find_job_leads": {
        "function": find_job_leads,
        "category": "research",
        "schema": {
            "name": "find_job_leads",
            "description": "Find current public job or business-lead opportunities for a role and location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "Role, skill, or service to find"},
                    "location": {"type": "string", "description": "Location or remote preference"},
                    "max_sources": {"type": "integer", "description": "Number of sources to open"}
                },
                "required": ["role"]
            }
        }
    },

    # Memory tools
    "remember": {
        "function": remember,
        "category": "memory",
        "schema": {
            "name": "remember",
            "description": "Save an enduring fact or user preference to long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Topic or key identifier"},
                    "value": {"type": "string", "description": "Information or preference to remember"},
                    "category": {"type": "string", "description": "Category (e.g. personal, work, preferences)"}
                },
                "required": ["key", "value"]
            }
        }
    },
    "recall": {
        "function": recall,
        "category": "memory",
        "schema": {
            "name": "recall",
            "description": "Retrieve stored user facts from memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search filter"}
                }
            }
        }
    },
    "create_task": {
        "function": create_task,
        "category": "tasks",
        "schema": {
            "name": "create_task",
            "description": "Create a persistent task, optionally with an ISO-8601 due datetime.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short task title"},
                    "description": {"type": "string", "description": "Optional task details"},
                    "due_at": {"type": "string", "description": "Optional ISO-8601 due datetime with timezone"},
                    "priority": {"type": "string", "description": "low, medium, or high"}
                },
                "required": ["title"]
            }
        }
    },
    "list_tasks": {
        "function": list_tasks,
        "category": "tasks",
        "schema": {
            "name": "list_tasks",
            "description": "List persistent tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "pending, completed, cancelled, or all"},
                    "limit": {"type": "integer", "description": "Maximum tasks to return"}
                }
            }
        }
    },
    "complete_task": {
        "function": complete_task,
        "category": "tasks",
        "schema": {
            "name": "complete_task",
            "description": "Mark a persistent task complete.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string", "description": "Task ID"}},
                "required": ["task_id"]
            }
        }
    },
    "cancel_task": {
        "function": cancel_task,
        "category": "tasks",
        "schema": {
            "name": "cancel_task",
            "description": "Cancel a persistent task.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string", "description": "Task ID"}},
                "required": ["task_id"]
            }
        }
    },

    # Gmail tools
    "mail_search": {
        "function": mail_search,
        "category": "mail",
        "schema": {
            "name": "mail_search",
            "description": "Search user's Gmail messages (e.g. 'is:unread', 'from:x').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query (default: 'is:unread')"},
                    "max_results": {"type": "integer", "description": "Max emails to list"}
                }
            }
        }
    },
    "mail_read": {
        "function": mail_read,
        "category": "mail",
        "schema": {
            "name": "mail_read",
            "description": "Read decoded email contents by message ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "Gmail message ID"}
                },
                "required": ["message_id"]
            }
        }
    },
    "mail_draft": {
        "function": mail_draft,
        "category": "mail",
        "schema": {
            "name": "mail_draft",
            "description": "Save a draft in Gmail for the user to review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    "mail_send": {
        "function": mail_send,
        "category": "mail",
        "schema": {
            "name": "mail_send",
            "description": "Send an email (requires user approval).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body content"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },

    # Calendar tools
    "cal_list": {
        "function": cal_list,
        "category": "calendar",
        "schema": {
            "name": "cal_list",
            "description": "List upcoming Google Calendar events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Number of days ahead to scan (default: 7)"}
                }
            }
        }
    },
    "cal_add": {
        "function": cal_add,
        "category": "calendar",
        "schema": {
            "name": "cal_add",
            "description": "Schedule a new meeting/event on Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title/summary"},
                    "start_time": {"type": "string", "description": "Start ISO datetime (YYYY-MM-DDTHH:MM:SSZ)"},
                    "end_time": {"type": "string", "description": "End ISO datetime (YYYY-MM-DDTHH:MM:SSZ)"},
                    "description": {"type": "string", "description": "Optional notes"},
                    "location": {"type": "string", "description": "Optional location"}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        }
    },
    "cal_delete": {
        "function": cal_delete,
        "category": "calendar",
        "schema": {
            "name": "cal_delete",
            "description": "Delete a calendar event (requires user approval).",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Calendar event ID to delete"}
                },
                "required": ["event_id"]
            }
        }
    },

    # Sheets tool
    "sheet_append": {
        "function": sheet_append,
        "category": "sheets",
        "schema": {
            "name": "sheet_append",
            "description": "Append a row to a Google Sheet (for leads/research logging).",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id_or_url": {"type": "string", "description": "Sheet ID or full Google Sheet URL"},
                    "range_name": {"type": "string", "description": "Sheet and range (e.g. 'Sheet1!A1')"},
                    "values": {"type": "array", "description": "List of values for row columns"}
                },
                "required": ["spreadsheet_id_or_url", "range_name", "values"]
            }
        }
    },

    # GitHub tools
    "gh_issues": {
        "function": gh_issues,
        "category": "github",
        "schema": {
            "name": "gh_issues",
            "description": "List open issues/PRs from a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in 'owner/repo' format"},
                    "state": {"type": "string", "description": "Filter: 'open' or 'closed' (default: 'open')"}
                },
                "required": ["repo"]
            }
        }
    },
    "gh_read_file": {
        "function": gh_read_file,
        "category": "github",
        "schema": {
            "name": "gh_read_file",
            "description": "Read file contents from a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in 'owner/repo' format"},
                    "file_path": {"type": "string", "description": "File path inside repo (e.g. 'README.md')"},
                    "branch": {"type": "string", "description": "Optional branch name"}
                },
                "required": ["repo", "file_path"]
            }
        }
    },

    # System & Hardware Butler tools
    "pc_status": {
        "function": pc_status,
        "category": "system",
        "schema": {
            "name": "pc_status",
            "description": "Get real-time CPU, RAM, battery, disk space, and top memory-hogging processes on this PC.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    "clean_temp": {
        "function": clean_temp,
        "category": "system",
        "schema": {
            "name": "clean_temp",
            "description": "Clean temporary files on the laptop to safely free up disk storage.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    "tech_radar": {
        "function": tech_radar,
        "category": "research",
        "schema": {
            "name": "tech_radar",
            "description": "Fetch live trending engineering and tech discussions from Hacker News and trending GitHub repos.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    "deep_dossier": {
        "function": deep_dossier,
        "category": "research",
        "schema": {
            "name": "deep_dossier",
            "description": "Conduct autonomous multi-step deep research across multiple web sources and save an executive dossier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Subject or question to deeply research"}
                },
                "required": ["topic"]
            }
        }
    },

    # Terminal & OS Execution tools (Unleashed!)
    "run_command": {
        "function": run_command,
        "category": "system",
        "schema": {
            "name": "run_command",
            "description": "Execute a shell or PowerShell command on the host laptop. Non-destructive commands run automatically; destructive commands require approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The exact shell or PowerShell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"}
                },
                "required": ["command"]
            }
        }
    },
    "launch_app": {
        "function": launch_app,
        "category": "system",
        "schema": {
            "name": "launch_app",
            "description": "Launch an application, document, folder, or URL on the host desktop (e.g. 'notepad', 'calc', 'code .', 'd:\\Hope').",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "App name, executable path, folder path, or file URL"}
                },
                "required": ["target"]
            }
        }
    },

    # Filesystem Explorer tools
    "list_dir": {
        "function": list_dir,
        "category": "filesystem",
        "schema": {
            "name": "list_dir",
            "description": "List files and directories in a local folder with file sizes and modified dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list (default: current directory '.')"}
                }
            }
        }
    },
    "read_file": {
        "function": read_file,
        "category": "filesystem",
        "schema": {
            "name": "read_file",
            "description": "Read the text, code, or configuration contents of a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to read"},
                    "max_lines": {"type": "integer", "description": "Max lines to return (default: 150)"}
                },
                "required": ["path"]
            }
        }
    },
    "write_file": {
        "function": write_file,
        "category": "filesystem",
        "schema": {
            "name": "write_file",
            "description": "Create or overwrite a local file with content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to write"},
                    "content": {"type": "string", "description": "Full text or code content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    "search_files": {
        "function": search_files,
        "category": "filesystem",
        "schema": {
            "name": "search_files",
            "description": "Search for files on the laptop matching a keyword or pattern (e.g. '*.py', 'test*', 'report').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or wildcard pattern"},
                    "root_dir": {"type": "string", "description": "Root directory to begin search (default: '.')"}
                },
                "required": ["query"]
            }
        }
    },

    # Desktop & Process tools
    "list_running_apps": {
        "function": list_running_apps,
        "category": "system",
        "schema": {
            "name": "list_running_apps",
            "description": "List active interactive applications and high-RAM processes running on the laptop.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    "kill_process": {
        "function": kill_process,
        "category": "system",
        "schema": {
            "name": "kill_process",
            "description": "Terminate a process on the host laptop by process name or PID (protected system processes cannot be terminated).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Process name (e.g. 'chrome.exe') or PID (e.g. '1234')"}
                },
                "required": ["target"]
            }
        }
    },
    "capture_screenshot": {
        "function": capture_screenshot,
        "category": "system",
        "schema": {
            "name": "capture_screenshot",
            "description": "Capture a screenshot of the laptop's primary desktop screen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename to save screenshot (default: 'screenshot.png')"}
                }
            }
        }
    }
}


def get_contextual_tools(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return compact tool schemas tailored for the turn context, with fallback to general unleashed tools."""
    selected = []

    if category == "mail":
        keys = ["mail_search", "mail_read", "mail_draft", "mail_send"]
    elif category == "calendar":
        keys = ["cal_list", "cal_add", "cal_delete"]
    elif category == "research":
        keys = ["web_search", "fetch_page", "deep_dossier", "tech_radar", "company_brief"]
    elif category == "github":
        keys = ["gh_issues", "gh_read_file", "run_command", "web_search"]
    elif category == "sheets":
        keys = ["sheet_append", "web_search"]
    elif category == "memory":
        keys = ["remember", "recall"]
    elif category == "tasks":
        keys = ["create_task", "list_tasks", "complete_task", "cancel_task"]
    elif category == "system":
        keys = ["pc_status", "run_command", "launch_app", "list_running_apps", "kill_process", "capture_screenshot", "clean_temp"]
    elif category == "filesystem":
        keys = ["list_dir", "read_file", "write_file", "search_files", "run_command"]
    else:
        # Default unleashed general tools
        keys = ["web_search", "pc_status", "run_command", "list_dir", "read_file", "launch_app", "remember", "recall"]

    for k in keys:
        if k in TOOL_DEFINITIONS:
            selected.append({"type": "function", "function": TOOL_DEFINITIONS[k]["schema"]})

    return selected


async def dispatch_tool_call(name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a registered tool by name with arguments."""
    entry = TOOL_DEFINITIONS.get(name)
    if not entry:
        return f"Unknown tool: '{name}'"

    func = entry["function"]
    try:
        if inspect.iscoroutinefunction(func):
            return await func(**arguments)
        return func(**arguments)
    except Exception as e:
        logger.error(f"Error executing tool {name} with args {arguments}: {e}")
        return f"Tool execution failed: {e}"
