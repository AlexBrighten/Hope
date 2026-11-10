# ==============================================================================
# Hope UltraLight — Windows Setup & Development Environment
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "🌟 Setting up Hope UltraLight on Windows..." -ForegroundColor Cyan

# 1. Create Python virtual environment if not present
if (-not (Test-Path "venv")) {
    Write-Host "🐍 Creating Python virtual environment (venv)..." -ForegroundColor Yellow
    python -m venv venv
}

# 2. Activate virtual environment and install requirements
Write-Host "📦 Installing Python requirements..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip
& .\venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Environment configuration
if (-not (Test-Path ".env")) {
    Write-Host "📝 Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️ Remember to fill in your keys in .env!" -ForegroundColor Magenta
}

# 4. Check Ollama
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "🧠 Ollama found. Pulling qwen2.5:3b-instruct..." -ForegroundColor Green
    ollama pull qwen2.5:3b-instruct
} else {
    Write-Host "ℹ️ Ollama not found on PATH. If you plan to use local Tier 1 on Windows, download from: https://ollama.com/download" -ForegroundColor Gray
}

Write-Host "`n✅ Setup completed successfully!" -ForegroundColor Green
Write-Host "To start the Telegram bot daemon:" -ForegroundColor Cyan
Write-Host ".\venv\Scripts\python.exe bot.py" -ForegroundColor White

