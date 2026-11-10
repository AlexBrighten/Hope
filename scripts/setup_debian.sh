#!/usr/bin/env bash
# ==============================================================================
# Hope UltraLight — Automated Debian Linux Setup (Target: Laptop i7-6600U / 8GB)
# ==============================================================================
set -e

echo "🌟 Installing Hope UltraLight on Debian Linux..."

# 1. Update and install base dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip curl git sqlite3

# 2. Check and Install Ollama
if ! command -v ollama &> /dev/null; then
    echo "🧠 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama is already installed."
fi

# Ensure Ollama service is active
sudo systemctl enable --now ollama || true

# 3. Pull Qwen 2.5 3B model (sized for 8GB RAM CPU inference)
echo "📥 Pulling qwen2.5:3b-instruct model into Ollama..."
ollama pull qwen2.5:3b-instruct

# 4. Create Python Virtual Environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Environment Template Setup
if [ ! -f .env ]; then
    echo "📝 Generating .env from template..."
    cp .env.example .env
    echo "⚠️ Please edit .env with: nano .env"
fi

# 6. Install systemd service for 24/7 background operation
echo "⚙️ Setting up systemd service..."
USER_NAME=$(whoami)
SERVICE_PATH="/etc/systemd/system/hope.service"

sudo sed "s/%I/$USER_NAME/g" scripts/hope.service | sudo tee $SERVICE_PATH > /dev/null
sudo systemctl daemon-reload

echo "================================================================="
echo "✅ Hope UltraLight setup complete!"
echo ""
echo "Next Steps:"
echo "1. Configure your keys: nano .env"
echo "   (Add TELEGRAM_BOT_TOKEN and ALLOWED_TELEGRAM_USER_ID)"
echo "2. Enable and start 24/7 background service:"
echo "   sudo systemctl enable --now hope"
echo "3. Check logs:"
echo "   sudo journalctl -u hope -f"
echo "================================================================="

