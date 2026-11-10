# 🌟 Hope UltraLight — Autonomous Personal Executive AI Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Architecture: 3--Tier](https://img.shields.io/badge/Architecture-3--Tier%20Brain-purple.svg)](#-3-tier-brain-architecture)
[![Interface: Telegram](https://img.shields.io/badge/Interface-Telegram%20Bot-2CA5E0.svg?logo=telegram&logoColor=white)](#-telegram-commands--usage)
[![Zero Open Ports](https://img.shields.io/badge/Network-0%20Open%20Ports%20(Behind%20NAT)-success.svg)](#-why-telegram-long-polling)

**Hope UltraLight** is a lean, single-process, privacy-conscious personal executive AI agent built on a **3-Tier Brain Architecture** and powered entirely through **Telegram**. 

Designed to run 24/7 on modest edge hardware (Intel Core i7-6600U / i3-N305 with 8 GB RAM on Debian Linux or Windows), Hope completely eliminates heavy browser runtimes, RPC bloat, and fragile VPN tunnels—delivering instant mobile responsiveness and **$0.00 operational spend**.

---

## 📑 Table of Contents

- [⚡ Core Superpowers](#-core-superpowers)
- [🏗️ 3-Tier Brain Architecture](#️-3-tier-brain-architecture)
- [📱 Why Telegram Long-Polling?](#-why-telegram-long-polling)
- [🚀 Quick Start](#-quick-start)
  - [Debian Linux (24/7 Laptop Server)](#on-debian-linux-laptop--247-background-service)
  - [Windows (Development)](#on-windows-development)
- [🔑 Step-by-Step Integration Setup](#-step-by-step-integration-setup)
  - [1. Telegram Bot & Single-User Lock](#1-telegram-bot--single-user-lock)
  - [2. Tier 1: Local Ollama Model](#2-tier-1-local-ollama-model)
  - [3. Tier 2: OpenRouter Free Cloud Workhorse](#3-tier-2-openrouter-free-cloud-workhorse)
  - [4. Tier 3: Google Gemini Fallback & Audio](#4-tier-3-google-gemini-fallback--audio)
  - [5. Google Workspace (Unified OAuth for Gmail, Calendar, Sheets)](#5-google-workspace-unified-oauth)
  - [6. GitHub Integration (Read-First)](#6-github-integration-read-first)
- [📱 Telegram Commands & 1-Click Approvals](#-telegram-commands--1-click-approvals)
  - [Command Directory](#command-directory)
  - [1-Click Lock-Screen Approval Workflow](#1-click-lock-screen-approval-workflow)
- [⏰ Automated Routines & Scheduler](#-automated-routines--scheduler)
- [🛡️ Strict Privacy Boundaries & Safeguards](#️-strict-privacy-boundaries--safeguards)
- [🧪 Diagnostics & Automated Testing](#-diagnostics--automated-testing)
- [📂 Project Directory Structure](#-project-directory-structure)
- [❓ Troubleshooting & FAQ](#-troubleshooting--faq)

---

## ⚡ Core Superpowers

| Service | What Hope UltraLight Does |
| :--- | :--- |
| **📱 Telegram Hub** | Native mobile (iOS & Android) and desktop executive interface, voice message transcription, status updates, and interactive inline buttons. |
| **🔒 Strict Privacy Partition** | Private emails, calendar entries, and personal notes stay strictly on Tier 1 (Ollama). Never sent to cloud AI without explicit confirmation. |
| **🌐 Ultra-Fast Research** | Sub-second web search and article distillation (`duckduckgo_search` + `httpx` + `trafilatura`) using only ~20 MB RAM (vs 800 MB for Chrome). |
| **✉️ Gmail Integration** | Search unread emails, read decoded messages, create drafts for review, and send emails (with 1-click Telegram approval). |
| **📅 Google Calendar** | View upcoming schedule, schedule new meetings, and delete events (with 1-click approval). |
| **📊 Google Sheets** | Append rows to track founder research, market leads, and meeting summaries. |
| **🐙 GitHub (Read-First)** | Inspect repository issues, pull requests, and read source files via GitHub REST API. |
| **🧠 SQLite Second Brain** | Enduring facts and preferences saved to SQLite and automatically exported to `workspace/memory.md`. |
| **⏰ Automated Routines** | 8:00 AM executive morning brief, periodic inbox triage, and 2:00 AM nightly memory consolidation via APScheduler. |

---

## 🏗️ 3-Tier Brain Architecture

Hope dynamically directs queries across three model tiers using a **deterministic, sub-millisecond rule-based router** (<1 ms), protecting your private data and preserving API quotas:

```mermaid
flowchart TD
    UserPhone(["📱 User on Mobile (Telegram iOS/Android)"]) <-->|Outbound Long Polling<br/>0 open ports / No VPN| Bot["bot.py: Telegram Daemon"]
    UserDesktop(["💻 User on Desktop (Telegram Desktop)"]) <-->|Instant Outbound HTTPS| Bot

    Bot --> Router["brain/router.py: Rule-Based Router (<1 ms)"]

    subgraph Providers [brain/providers.py: Config-Driven Provider Chain]
        Router -->|Private Data: Gmail, Calendar, Personal Memory| Local["Tier 1: Local Ollama<br/>qwen2.5:3b-instruct (Q4)<br/>0 tokens, 100% private"]
        Router -->|Public: Web Research, Company Briefs, Code| Free["Tier 2: OpenRouter Free<br/>thinkingmachines/inkling-2-small:free<br/>17B/594B MoE, 115 tok/s, 1M context"]
        Router -->|Fallback, /gemini, Voice Notes| Gem["Tier 3: Gemini 2.5 Flash<br/>(Daily Quota Protected)"]
        
        Free -. on 429 / 5xx / timeout .-> Gem
        Local -. on failure .-> PrivatePrompt["Privacy Guard: Ask User Permission Before Cloud Escalation"]
    end

    Local & Free & Gem <--> Registry["tools/registry.py: Compact Tool Registry<br/>(3-6 schemas per turn)"]

    subgraph Tools Suite [Direct Async Python Tools - No Puppeteer / No FastMCP]
        Registry --> Web["tools/web.py: DDG + httpx + trafilatura (~20MB RAM)"]
        Registry --> GM["tools/gmail.py: Gmail API"]
        Registry --> GC["tools/calendar.py: Calendar API"]
        Registry --> GS["tools/sheets.py: Sheets API"]
        Registry --> GH["tools/github.py: GitHub REST API (Read-First)"]
        Registry --> Mem["tools/memory.py: SQLite + Markdown Sync"]
    end

    Registry --> Gate{"Mutating Action?<br/>(Send Email, Cal Delete)"}
    Gate -->|Yes| Pending["workspace/hope.db: pending_actions"]
    Pending -->|Inline Keyboard Callback| Bot
    Bot -->|User taps [Approve] / [Reject]| Pending

    Sched["APScheduler: Morning Brief (8:00), Inbox Triage, Nightly Memory Distill"] --> Bot
    DB[("SQLite: hope.db<br/>(memories, approvals, usage_counters, response_cache)")] --- Registry
```

### The 3 Model Tiers Breakdown

| Tier | Provider & Model | Role & Scope | Speed / Footprint | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Local Private)** | **Ollama**<br/>`qwen2.5:3b-instruct` (Q4) | Email & calendar summaries, personal notes, casual chat, and offline fallback. **Private data never leaves this tier.** | ~5–8 tok/s on CPU<br/>~2.3 GB RAM | **$0.00**<br/>(0 API tokens) |
| **Tier 2 (Free Cloud)** | **OpenRouter**<br/>`thinkingmachines/inkling-2-small:free` | Deep public research, founder & company lookups, coding, multi-step tool calls, and long documents. | ~115 tok/s<br/>1M context | **$0.00**<br/>(Free Tier) |
| **Tier 3 (Cloud Fallback)** | **Google Gemini**<br/>`gemini-2.5-flash` | Automatic failover when Tier 2 hits rate limits (429/timeout), and voice note transcription. | Ultra-fast cloud<br/>Quota tracked | **$0.00**<br/>(Google AI Studio) |

---

## 📱 Why Telegram Long-Polling?

Previous versions of executive agents relied on custom Progressive Web Apps (PWAs), WebSockets, Server-Sent Events, and mesh networks like Tailscale. In practice, this created endless maintenance headaches:
- Tailscale tunnels frequently drop on mobile when iOS/Android puts background VPNs to sleep.
- Mobile browsers kill WebSocket connections when the screen locks.
- Staged push services (like ntfy.sh) require installing extra apps and subscribing to public topics.

**The Telegram Advantage:**
1. **Outbound HTTPS Only (`getUpdates`)**: Hope connects *outbound* to Telegram's secure API servers. It works 100% reliably behind residential NAT, corporate Wi-Fi, routers, and firewalls with **zero port forwarding, zero dynamic DNS, and zero VPNs**.
2. **Native Push Notifications**: Works out of the box on iPhone, Apple Watch, Android, iPad, Mac, and Windows with lock-screen previews, vibration, and audio alerts.
3. **Interactive Inline Keyboards**: Review pending email drafts or meeting deletions and tap **`[ ✅ Approve & Execute ]`** right on your phone screen.
4. **Single-User Lock**: Hope strictly checks `message.from_user.id == ALLOWED_TELEGRAM_USER_ID`. Unrecognized messages from anyone else are silently dropped.

---

## 🚀 Quick Start

### On Debian Linux (Laptop / 24/7 Background Service)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Hope.git
   cd Hope
   ```

2. **Run the automated setup script**:
   ```bash
   chmod +x scripts/setup_debian.sh
   ./scripts/setup_debian.sh
   ```
   *This installs Python 3, venv, and Ollama, pulls `qwen2.5:3b-instruct`, installs dependencies, generates `.env`, and sets up the systemd service.*

3. **Configure your keys**:
   ```bash
   nano .env
   ```

4. **Enable & start the 24/7 background service**:
   ```bash
   sudo systemctl enable --now hope
   ```

5. **Inspect live service logs**:
   ```bash
   sudo journalctl -u hope -f
   ```

---

### On Windows (Development)

1. **Clone the repository and open PowerShell**:
   ```powershell
   git clone https://github.com/your-username/Hope.git
   cd Hope
   ```

2. **Run the automated setup script**:
   ```powershell
   .\scripts\setup_windows.ps1
   ```

3. **Configure `.env`**:
   Copy `.env.example` to `.env` (if not already copied) and add your tokens.

4. **Run system diagnostics**:
   ```powershell
   python smoke_test.py
   ```

5. **Start Hope Telegram daemon**:
   ```powershell
   python bot.py
   ```

---

## 🔑 Step-by-Step Integration Setup

### 1. Telegram Bot & Single-User Lock
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, follow the prompts, and copy your **Bot Token** (e.g. `123456789:ABCdefGHI...`).
3. Open [@userinfobot](https://t.me/userinfobot) on Telegram to get your numeric **User ID** (e.g. `987654321`).
4. Add them to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ALLOWED_TELEGRAM_USER_ID=987654321
   ```

---

### 2. Tier 1: Local Ollama Model
Hope uses `qwen2.5:3b-instruct` (Q4) for its edge reasoning and strict JSON tool-calling capabilities.
1. Install Ollama:
   - **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`
   - **Windows**: Download from [ollama.com/download](https://ollama.com/download)
2. Pull the recommended model:
   ```bash
   ollama pull qwen2.5:3b-instruct
   ```
3. Start the Ollama server:
   ```bash
   ollama serve
   ```

---

### 3. Tier 2: OpenRouter Free Cloud Workhorse
1. Create a free account at [OpenRouter](https://openrouter.ai/).
2. Navigate to [OpenRouter Keys](https://openrouter.ai/keys) and generate an API key.
3. Add to `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENROUTER_MODEL=thinkingmachines/inkling-2-small:free
   ```

---

### 4. Tier 3: Google Gemini Fallback & Audio
1. Get a free API key at [Google AI Studio](https://aistudio.google.com/).
2. Add to `.env`:
   ```env
   GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   GEMINI_MODEL=gemini-2.5-flash
   ```

---

### 5. Google Workspace (Unified OAuth)
*A single authorization file activates Gmail, Google Calendar, and Google Sheets.*

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project named `Hope-Executive`.
3. In **APIs & Services → Library**, enable:
   - **Gmail API**
   - **Google Calendar API**
   - **Google Sheets API**
   - **Google Drive API**
4. Go to **APIs & Services → Credentials**:
   - Click **Create Credentials → OAuth client ID**.
   - Select **Desktop App**.
   - Download the JSON credentials and save as `credentials.json` in the root of `Hope/`.
5. Run the 1-click authorization helper on your desktop:
   ```bash
   python scripts/auth_google.py
   ```
   *Your browser will open. Approve the permissions once—Hope saves `token.json` and refreshes it silently in the future.*

---

### 6. GitHub Integration (Read-First)
1. Go to [GitHub Fine-Grained Personal Access Tokens](https://github.com/settings/tokens?type=beta).
2. Select repository access (choose specific repositories).
3. Grant permissions: `Issues (read-only)`, `Contents (read-only)`.
4. Add to `.env`:
   ```env
   GITHUB_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxx
   ```

---

## 📱 Telegram Commands & 1-Click Approvals

### Command Directory

| Command | Action |
| :--- | :--- |
| `/status` | Real-time diagnostic report: brain health, model connectivity, and quota usage. |
| `/brief` | Instantly generates and delivers today's executive morning briefing. |
| `/deep <prompt>` | Escalates to OpenRouter with `reasoning_effort="high"` for complex logic and math. |
| `/local <prompt>` | Forces Tier 1 local Ollama execution (0 cloud tokens, 100% private). |
| `/free <prompt>` | Forces Tier 2 OpenRouter Inkling 2 Small execution. |
| `/gemini <prompt>` | Forces Tier 3 Gemini 2.5 Flash execution. |
| `/mem` | Displays current long-term memory facts stored in SQLite. |

---

### 1-Click Lock-Screen Approval Workflow

Whenever Hope stages a high-impact mutating action:
- Sending an email (`mail_send`)
- Deleting a calendar event (`cal_delete`)

Hope generates an action UUID (`act_a1b2c3d4`), stages it in SQLite with a **30-minute expiry window**, and delivers an interactive card to your Telegram chat and phone lock-screen:

```text
⚠️ Approval Required

Action: Send email to founder@techcorp.com
Subject: Introduction & Executive Briefing
Preview:
Hi Alex, following up on our discussion regarding solid-state battery infrastructure...

[ ✅ Approve & Execute ]   [ ❌ Reject ]
```

- Tap **`[ ✅ Approve & Execute ]`**: The tool executes immediately, and the message updates in-place with the timestamp and confirmation ID.
- Tap **`[ ❌ Reject ]`**: Cancels the action immediately.
- **Replay Protection**: Approved actions are marked `executed` in SQLite and cannot be triggered twice.

---

## ⏰ Automated Routines & Scheduler

Hope uses **APScheduler** to handle autonomous recurring routines without competing with live chat for CPU resources:

1. **☀️ Executive Morning Briefing (8:00 AM Daily)**:
   - Queries Google Calendar for today's agenda.
   - Scans unread high-priority emails in Gmail.
   - Distills them using **Tier 1 (Local Ollama)** so your private data never touches the cloud.
   - Sends a formatted briefing card directly to your Telegram chat.
2. **📬 Inbox Triage (Every 2 Hours)**:
   - Scans unread messages and flags important client communications.
3. **🌙 Nightly Memory Consolidation (2:00 AM Daily)**:
   - Runs while the machine is idle.
   - Cleans up and exports memories to `workspace/memory.md`.

---

## 🛡️ Strict Privacy Boundaries & Safeguards

Hope includes ironclad privacy safeguards engineered into its core:

1. **Strict Privacy Boundary**:
   - Queries touching Gmail, Calendar, personal memories, or files are hard-routed to **Tier 1 (Local Ollama)**.
   - If Ollama is offline or encounters an error on a private query, Hope displays a **Privacy Guard** alert and stops. It will **never silently forward private emails or schedules to cloud AI**.
2. **Deterministic Routing (<1 ms)**:
   - Routing decisions use fast regex and keyword pattern matching rather than an extra LLM call, eliminating 4–6 seconds of latency.
3. **Single-User Lock**:
   - Only messages from `ALLOWED_TELEGRAM_USER_ID` are processed. All other updates are dropped.
4. **Git Safeguards**:
   - `.gitignore` strictly covers: `.env`, `credentials.json`, `token.json`, `workspace/`, `*.db`, and `venv/`. Your private keys, tokens, and databases are never committed to version control.

---

## 🧪 Diagnostics & Automated Testing

### 1. Run System Smoke Test
Check your local setup, API keys, database, and Ollama connectivity:
```bash
python smoke_test.py
```

### 2. Run Automated Unit Test Suite
Hope includes 12 automated unit tests covering router latency, provider failover, SQLite caching, contextual filtering, and approval lifecycle:
```bash
python -m unittest discover tests
```

Expected output:
```text
Ran 12 tests in 0.314s

OK
```

---

## 📂 Project Directory Structure

```text
Hope/
├── bot.py                     # Main Telegram daemon (async long polling)
├── config.py                  # Configuration loader & environment validation
├── database.py                # SQLite manager (quotas, cache, approvals, memory)
├── scheduler.py               # APScheduler background routines (briefing, triage)
├── requirements.txt           # Minimal, fast dependencies (no node/puppeteer)
├── smoke_test.py              # CLI diagnostic utility
├── .env.example               # Environment variables template
├── .gitignore                 # Safe ignore rules
├── README.md                  # Comprehensive documentation
│
├── brain/                     # 3-Tier Brain System
│   ├── __init__.py            # Brain exports
│   ├── router.py              # Rule-based router (<1 ms intent & privacy triage)
│   ├── providers.py           # Provider chain, failover, quota checks & cache
│   ├── local_brain.py         # Ollama client (qwen2.5:3b-instruct)
│   ├── openrouter_brain.py    # OpenRouter client (inkling-2-small:free)
│   └── gemini_brain.py        # Gemini 2.5 Flash client (fallback & voice)
│
├── tools/                     # Compact, Async Tool Suite
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
├── workspace/                 # Safe local data directory (git-ignored)
│   ├── hope.db                # SQLite database
│   └── memory.md              # Exported markdown memory notes
│
├── scripts/                   # Automated Installers & Helpers
│   ├── setup_debian.sh        # 1-click Debian Linux installer (with systemd)
│   ├── setup_windows.ps1      # 1-click Windows setup
│   ├── auth_google.py         # 1-click Google OAuth helper
│   └── hope.service           # systemd unit file for 24/7 background service
│
└── tests/                     # Automated Test Suite
    ├── test_router.py         # Tests privacy boundaries & <5ms latency
    ├── test_providers.py      # Tests failover (429/timeout), quotas & cache
    ├── test_tools.py          # Tests contextual filtering & memory recall
    └── test_approval.py       # Tests approval lifecycle & replay protection
```

---

## ❓ Troubleshooting & FAQ

#### Q: How do I pull the latest changes on my laptop without git merge conflicts?
**A**: Run:
```bash
git fetch origin
git reset --hard origin/main
git clean -fd
```
This guarantees your local files perfectly mirror the remote repository.

#### Q: Will Ollama slow down my laptop (8 GB RAM)?
**A**: Not with Hope UltraLight! We deliberately sized Tier 1 for `qwen2.5:3b-instruct` (~2.3 GB RAM). It leaves over **5.5 GB of RAM completely free** for your operating system.

#### Q: Google OAuth displays "Google hasn't verified this app"
**A**: When authorizing your personal Google Cloud OAuth app in testing mode:
1. Click **Advanced**.
2. Click **Go to Hope-Executive (unsafe)**.
3. Grant access. This is standard for private desktop applications.

#### Q: How do I change the morning briefing time?
**A**: In `scheduler.py`, locate the `CronTrigger(hour=8, minute=0)` line and adjust it to your preferred hour.

#### Q: What happens if OpenRouter hits a rate limit?
**A**: Hope UltraLight handles this automatically! On HTTP 429, 5xx, or timeout, the request cascades seamlessly to **Tier 3 (Google Gemini 2.5 Flash)** without interrupting your turn.

---

<p align="center">
  <b>Hope UltraLight</b> — Built for speed, privacy, and true personal autonomy.
</p>
