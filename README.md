# 🌟 Hope UltraLight — Autonomous Personal Executive AI Agent

**Hope UltraLight** is a lean, single-process, privacy-conscious personal executive AI agent built on a **3-Tier Brain Architecture** and powered entirely through **Telegram**:

- 🧠 **Tier 1 (Local Private Brain)**: Ollama (**`qwen2.5:3b-instruct`** Q4) running on edge CPU hardware (Intel Core i7-6600U / i3-N305, 8 GB RAM) for mail, calendar, personal memory, and offline triage with **0 cloud tokens** and **strict privacy isolation**.
- ⚡ **Tier 2 (Free Cloud Workhorse)**: OpenRouter (**`thinkingmachines/inkling-2-small:free`** — 17B/594B MoE, 1M context, 115 tok/s) for heavy public research, multi-step tool calls, code, and long documents without paying a penny.
- ☁️ **Tier 3 (Cloud Fallback & Audio)**: Google Gemini 2.5 Flash as automatic failover on 429/timeout and for transcribing voice notes. Protected by daily quota counters.
- 📱 **Telegram Executive Hub**: Outbound HTTPS long-polling daemon (0 open ports, 0 VPN, no Tailscale required). Instant lock-screen push notifications on iOS and Android with **1-click `[Approve]` and `[Reject]` inline buttons**.

---

## 📑 Table of Contents

- [⚡ Core Superpowers](#-core-superpowers)
- [🏗️ 3-Tier Architecture](#️-3-tier-architecture)
- [🚀 Quick Start](#-quick-start)
  - [Debian Linux (Target Laptop / 24/7 Server)](#debian-linux-target-laptop--247-server)
  - [Windows (Development)](#windows-development)
- [🔑 Environment Configuration (`.env`)](#-environment-configuration-env)
- [📱 Telegram Commands & Usage](#-telegram-commands--usage)
- [🛡️ Privacy Boundaries & Human-in-the-Loop Safeguards](#️-privacy-boundaries--human-in-the-loop-safeguards)
- [🧪 Running Tests](#-running-tests)
- [📂 Project Directory Structure](#-project-directory-structure)

---

## ⚡ Core Superpowers

| Service | What Hope UltraLight Does |
| :--- | :--- |
| **📱 Telegram Hub** | Native mobile and desktop executive interface, voice message transcription, status updates, and interactive inline buttons. |
| **🔒 Strict Privacy Partition** | Private emails, calendar entries, and personal notes stay strictly on Tier 1 (Ollama). Never sent to cloud AI without confirmation. |
| **🌐 Ultra-Fast Research** | Sub-second web search and article distillation (`duckduckgo_search` + `httpx` + `trafilatura`) using only ~20 MB RAM (vs 800 MB for Chrome). |
| **✉️ Gmail Integration** | Search unread emails, read decoded messages, create drafts for review, and send emails (with 1-click Telegram approval). |
| **📅 Google Calendar** | View upcoming schedule, schedule new meetings, and delete events (with 1-click approval). |
| **📊 Google Sheets** | Append rows to track founder research, market leads, and meeting summaries. |
| **🐙 GitHub (Read-First)** | Inspect repository issues, pull requests, and read source files via GitHub REST API. |
| **🧠 SQLite Second Brain** | Enduring facts and preferences saved to SQLite and automatically exported to `workspace/memory.md`. |
| **⏰ Automated Routines** | 8:00 AM executive morning brief, periodic inbox triage, and 2:00 AM nightly memory consolidation via APScheduler. |

---

## 🏗️ 3-Tier Architecture

```mermaid
flowchart TD
    UserPhone(["📱 Telegram (Phone / Desktop)"]) <-->|Long Polling - 0 open ports| Bot["bot.py: Telegram Daemon"]
    Bot --> Router["brain/router.py: Rule-Based Router (<1 ms)"]

    subgraph Providers [Provider Chain with Failover & Quota Tracking]
        Router -->|Private: Mail, Calendar, Notes| Local["Tier 1: Local Ollama<br/>qwen2.5:3b-instruct (Q4)"]
        Router -->|Public: Research, Code, Docs| Free["Tier 2: OpenRouter Free<br/>thinkingmachines/inkling-2-small:free"]
        Router -->|Fallback, /gemini, Voice Notes| Gem["Tier 3: Gemini 2.5 Flash<br/>(Daily Quota Protected)"]
        
        Free -. on 429/timeout .-> Gem
        Local -. on failure .-> PrivatePrompt["Ask User Permission before Cloud Escalation"]
    end

    Local & Free & Gem <--> Registry["tools/registry.py: Compact Tool Registry<br/>(3-6 schemas per turn)"]

    subgraph Tools [Direct Async Python Tools - No FastMCP / No Puppeteer]
        Registry --> Web["tools/web.py: DDG + httpx + trafilatura"]
        Registry --> GM["tools/gmail.py: Gmail API"]
        Registry --> GC["tools/calendar.py: Calendar API"]
        Registry --> GS["tools/sheets.py: Sheets API"]
        Registry --> GH["tools/github.py: GitHub REST API"]
        Registry --> Mem["tools/memory.py: SQLite + Markdown Sync"]
    end

    Registry --> Gate{"Mutating Action?"}
    Gate -->|Yes| Pending["SQLite: pending_actions"]
    Pending -->|Inline Keyboard| Bot
    Bot -->|User taps [Approve] / [Reject]| Pending
```

---

## 🚀 Quick Start

### Debian Linux (Target Laptop / 24/7 Server)

1. **Clone repository and run automated installer**:
   ```bash
   git clone https://github.com/your-username/Hope.git
   cd Hope
   chmod +x scripts/setup_debian.sh
   ./scripts/setup_debian.sh
   ```

2. **Configure your credentials**:
   ```bash
   nano .env
   ```
   *(Fill in `TELEGRAM_BOT_TOKEN`, `ALLOWED_TELEGRAM_USER_ID`, and your API keys).*

3. **Start 24/7 background service**:
   ```bash
   sudo systemctl enable --now hope
   ```

4. **Inspect live logs**:
   ```bash
   sudo journalctl -u hope -f
   ```

---

### Windows (Development)

1. **Run PowerShell setup**:
   ```powershell
   .\scripts\setup_windows.ps1
   ```

2. **Configure `.env`**:
   Fill in your tokens in `.env`.

3. **Start Hope Telegram daemon**:
   ```powershell
   .\venv\Scripts\python.exe bot.py
   ```

---

## 🔑 Environment Configuration (`.env`)

```env
# 1. Telegram (Required)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz   # From @BotFather
ALLOWED_TELEGRAM_USER_ID=123456789                         # From @userinfobot

# 2. Tier 1: Local Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b-instruct
OLLAMA_KEEP_ALIVE=30m

# 3. Tier 2: OpenRouter Free Workhorse
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx           # Free at https://openrouter.ai/keys
OPENROUTER_MODEL=thinkingmachines/inkling-2-small:free

# 4. Tier 3: Gemini Fallback & Audio
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxx                  # Free at https://aistudio.google.com/
GEMINI_MODEL=gemini-2.5-flash

# 5. Security & Operation
REQUIRE_APPROVAL=true
TIMEZONE=Asia/Kolkata
```

---

## 📱 Telegram Commands & Usage

- `/start` or `/help` — Welcome screen and command directory.
- `/status` — Real-time health check of all 3 brain tiers and daily quota consumption.
- `/brief` — Instantly compiles and posts today's executive morning briefing.
- `/deep <query>` — Routes to OpenRouter with `reasoning_effort="high"` for complex logic.
- `/local <query>` — Forces local Ollama execution (0 tokens, 100% offline).
- `/free <query>` — Forces Tier 2 OpenRouter execution.
- `/gemini <query>` — Forces Tier 3 Gemini execution.
- `/mem` — Displays current long-term memory notes.

### Mutating Action Approvals
Whenever Hope is asked to send an email or delete a calendar event:
1. Hope stages the action in SQLite with a 30-minute expiry window.
2. An inline card appears in your Telegram chat and phone lock-screen:
   ```text
   ⚠️ Approval Required
   Action: Send email to client@example.com
   Subject: Project Proposal Update

   [ ✅ Approve & Execute ]   [ ❌ Reject ]
   ```
3. Tapping **Approve** immediately fires the action and edits the message in-place with the execution result.

---

## 🛡️ Privacy Boundaries & Human-in-the-Loop Safeguards

1. **Strict Privacy Partition**:
   - Queries touching Gmail, Calendar, or personal memories are hard-routed to **Tier 1 (Local Ollama)**.
   - If Ollama is offline or fails on a private query, Hope halts and displays a Privacy Guard warning. It will **never silently forward private emails or schedules to cloud models**.
2. **Replay-Protected Approvals**:
   - Every staged action has a unique UUID (`act_xxxxxxxx`). Once approved or rejected, it is permanently resolved in SQLite and cannot be re-executed.
3. **Single-User Lock**:
   - Any Telegram user whose ID does not match `ALLOWED_TELEGRAM_USER_ID` is silently dropped.

---

## 🧪 Running Tests

Run the full automated test suite (Router latency, Provider failover, Tool filtering, and Approval gate):

```bash
python -m unittest discover tests
```

---

## 📂 Project Directory Structure

```text
Hope/
├── bot.py                     # Main Telegram daemon (async long polling)
├── config.py                  # Configuration loader & validation
├── database.py                # SQLite manager (usage, cache, approvals, memory)
├── scheduler.py               # APScheduler routines (morning brief, triage)
├── requirements.txt           # Minimal, fast dependencies (no node/puppeteer)
├── .env.example               # Environment variables template
├── .gitignore                 # Safe ignore rules
├── README.md                  # Documentation
│
├── brain/
│   ├── __init__.py
│   ├── router.py              # Rule-based router (<1 ms intent & privacy triage)
│   ├── providers.py           # Provider chain, failover, quota checks & cache
│   ├── local_brain.py         # Ollama client (qwen2.5:3b-instruct)
│   ├── openrouter_brain.py    # OpenRouter client (inkling-2-small:free)
│   └── gemini_brain.py        # Gemini 2.5 Flash client (fallback & voice)
│
├── tools/
│   ├── __init__.py            # Tool dispatcher
│   ├── registry.py            # Compact tool schemas & contextual filter
│   ├── approval.py            # Pending actions & inline keyboard builder
│   ├── web.py                 # DuckDuckGo search + httpx + trafilatura
│   ├── gmail.py               # Gmail API (search, read, draft, send)
│   ├── calendar.py            # Calendar API (list, add, delete)
│   ├── sheets.py              # Sheets API (append rows)
│   ├── github.py              # GitHub REST API (read-first)
│   ├── google_auth.py         # Unified OAuth 2.0 flow
│   └── memory.py              # Long-term SQLite memory
│
├── workspace/                 # Local data directory (git-ignored)
│   ├── hope.db                # SQLite database
│   └── memory.md              # Exported markdown memories
│
├── scripts/
│   ├── setup_debian.sh        # 1-click Debian Linux installer (with systemd)
│   ├── setup_windows.ps1      # 1-click Windows setup
│   └── hope.service           # systemd unit file for 24/7 background running
│
└── tests/
    ├── test_router.py         # Tests privacy boundaries & <5ms latency
    ├── test_providers.py      # Tests failover (429/timeout), quotas & cache
    ├── test_tools.py          # Tests tool schemas & memory recall
    └── test_approval.py       # Tests approval lifecycle & replay protection
```

