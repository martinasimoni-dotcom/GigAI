#!/bin/bash

# GigAI Meeting Intelligence System - Setup Script
# This script sets up and runs the complete system

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                     GigAI MEETING INTELLIGENCE v0.3.0                      ║"
echo "║                         SYSTEM SETUP & START                              ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"

# 1. Check Python
echo ""
echo "[1] Checking Python..."
if ! command -v python &> /dev/null; then
    echo "ERROR: Python not found. Please install Python 3.11+"
    echo "Download from: https://www.python.org/"
    exit 1
fi
python --version

# 2. Install Python dependencies
echo ""
echo "[2] Installing Python dependencies..."
pip install -q fastapi==0.104.1 uvicorn==0.24.0 pydantic==2.5.0 sqlalchemy==2.0.23 python-multipart==0.0.6 aiofiles==23.2.1
echo "✓ Python dependencies installed"

# 3. Check Node.js
echo ""
echo "[3] Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Please install Node.js 18+"
    echo "Download from: https://nodejs.org/"
    exit 1
fi
node --version
npm --version

# 4. Install npm dependencies
echo ""
echo "[4] Installing npm dependencies..."
cd frontend
npm install -q
cd ..
echo "✓ npm dependencies installed"

# 5. Create environment file
echo ""
echo "[5] Creating environment configuration..."
cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
echo "✓ Environment config created"

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                            SETUP COMPLETE!                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "TERMINAL 1 - Start Backend (FastAPI):"
echo "  cd /c/Users/Asus/Desktop/GigAi"
echo "  python -m uvicorn src.gigai.dashboard.dashboard_api:create_dashboard_app --reload"
echo ""
echo "TERMINAL 2 - Start Frontend (React):"
echo "  cd /c/Users/Asus/Desktop/GigAi/frontend"
echo "  npm run dev"
echo ""
echo "Then open browser:"
echo "  http://localhost:3000"
echo ""
