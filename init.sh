#!/bin/bash

# EverCred POC - Development Environment Setup Script
# This script sets up and runs the complete development environment.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null || true
    [ -n "$BACKEND_PID" ] && pkill -P $BACKEND_PID 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && pkill -P $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Services stopped.${NC}"
}
trap cleanup EXIT

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   EverCred POC - Development Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
echo -e "  Python version: ${GREEN}$PYTHON_VERSION${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "  Node.js version: ${GREEN}$NODE_VERSION${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo -e "  npm version: ${GREEN}$NPM_VERSION${NC}"

echo ""

# Setup Python virtual environment
echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
cd "$SCRIPT_DIR/backend"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "  ${GREEN}Created virtual environment${NC}"
else
    echo -e "  ${GREEN}Virtual environment already exists${NC}"
fi

# Activate virtual environment
source .venv/bin/activate

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip > /dev/null 2>&1

# Create requirements.txt if it doesn't exist
if [ ! -f "requirements.txt" ]; then
    cat > requirements.txt << 'EOF'
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
langgraph>=0.2.0
duckdb>=0.9.0
httpx>=0.26.0
playwright>=1.41.0
python-multipart>=0.0.6
sse-starlette>=1.8.0
python-dotenv>=1.0.0
pydantic>=2.5.0
EOF
    echo -e "  ${GREEN}Created requirements.txt${NC}"
fi

pip install -r requirements.txt > /dev/null 2>&1
echo -e "  ${GREEN}Python dependencies installed${NC}"

# Install Playwright browsers
echo -e "${YELLOW}Installing Playwright browsers...${NC}"
playwright install chromium > /dev/null 2>&1
echo -e "  ${GREEN}Playwright Chromium installed${NC}"

# Setup frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm install > /dev/null 2>&1
    echo -e "  ${GREEN}Node.js dependencies installed${NC}"
else
    echo -e "  ${GREEN}Node.js dependencies already installed${NC}"
fi

# Setup environment file
cd "$SCRIPT_DIR"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "  ${GREEN}Created .env from .env.example${NC}"
    else
        cat > .env << 'EOF'
# EverCred POC Environment Configuration

# Mock Mode (default: true)
# When true: uses mock data providers, no external API calls needed
# When false: uses live APIs (NPI, DCA Playwright, Claude)
EVERCRED_MOCK_MODE=true

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Frontend Configuration
FRONTEND_PORT=3000

# Database path (relative to backend/)
DUCKDB_PATH=../data/evercred.duckdb

# LEIE CSV path (relative to backend/)
# Use UPDATED_test.csv for mock mode, UPDATED.csv for live mode
LEIE_CSV_PATH=../data/UPDATED_test.csv
EOF
        echo -e "  ${GREEN}Created .env with default configuration${NC}"
    fi
fi

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
cd "$SCRIPT_DIR/backend"
source .venv/bin/activate

# Run init_db.py if it exists
if [ -f "scripts/init_db.py" ]; then
    python scripts/init_db.py --csv ../data/oig/UPDATED.csv > /dev/null 2>&1
    echo -e "  ${GREEN}Database initialized with LEIE data${NC}"
else
    echo -e "  ${YELLOW}Skipping database init (script not yet created)${NC}"
fi

# Check mock mode status
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Configuration Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

source "$SCRIPT_DIR/.env" 2>/dev/null || true

if [ "$EVERCRED_MOCK_MODE" = "true" ] || [ -z "$EVERCRED_MOCK_MODE" ]; then
    echo -e "  Mode: ${GREEN}MOCK MODE (default)${NC}"
    echo -e "  - Using synthetic NPI responses"
    echo -e "  - Using mock DCA responses (no Playwright)"
    echo -e "  - Using test LEIE CSV"
    echo -e "  - Using MockLLMProvider"
else
    echo -e "  Mode: ${YELLOW}LIVE MODE${NC}"
    echo -e "  - Using real NPI Registry API"
    echo -e "  - Using Playwright DCA scraper"
    echo -e "  - Using production LEIE CSV"
    echo -e "  - Using Claude API (requires credentials)"
fi

echo ""

# Check for port conflicts before starting
echo -e "${YELLOW}Checking ports...${NC}"
PORT_CONFLICT=0
if lsof -i :8000 -sTCP:LISTEN -t 2>/dev/null | grep -q .; then
    echo -e "  ${RED}Port 8000 in use. Run: lsof -i :8000${NC}"
    lsof -i :8000 2>/dev/null || true
    PORT_CONFLICT=1
fi
if lsof -i :3000 -sTCP:LISTEN -t 2>/dev/null | grep -q .; then
    echo -e "  ${RED}Port 3000 in use. Run: lsof -i :3000${NC}"
    lsof -i :3000 2>/dev/null || true
    PORT_CONFLICT=1
fi
if [ $PORT_CONFLICT -eq 1 ]; then
    echo -e "${RED}Stop the processes above or kill them before restarting.${NC}"
    exit 1
fi

# Start backend
echo -e "${YELLOW}Starting backend server...${NC}"
cd "$SCRIPT_DIR/backend"
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo -e "  ${GREEN}Backend starting on http://localhost:8000${NC}"

sleep 2

# Start frontend
echo -e "${YELLOW}Starting frontend dev server...${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo -e "  ${GREEN}Frontend starting on http://localhost:3000${NC}"

sleep 3

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Services Running${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  ${GREEN}Backend API:${NC}  http://localhost:8000"
echo -e "  ${GREEN}API Docs:${NC}     http://localhost:8000/docs"
echo -e "  ${GREEN}Frontend:${NC}     http://localhost:3000"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo ""

# Wait for processes
wait
