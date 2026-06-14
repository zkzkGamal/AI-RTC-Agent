#!/bin/bash

# AI-RTC-Agent Unified Workspace Orchestrator
# Gracefully manages, validates, and launches all 4 tiers of the voice agent stack.
# Logs all services to the logs/ directory and automatically opens the browser when ready.

# Color definitions
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

clear

# Banner logo
echo -e "${MAGENTA}  ███████╗██╗  ██╗███████╗██╗  ██╗"
echo -e "  ╚══███╔╝██║ ██╔╝╚══███╔╝██║ ██╔╝"
echo -e "    ███╔╝ █████╔╝   ███╔╝ █████╔╝ "
echo -e "   ███╔╝  ██╔═██╗  ███╔╝  ██╔═██╗ "
echo -e "  ███████╗██║  ██╗███████╗██║  ██╗"
echo -e "  ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝${NC}"
echo -e "${CYAN}==================================================${NC}"
echo -e "${GREEN}       AI-RTC-Agent Core Workspace Launcher       ${NC}"
echo -e "${CYAN}==================================================${NC}"

# Check system prerequisites
check_prereq() {
    local cmd=$1
    local name=$2
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${RED}❌ Error: $name is not installed or not in PATH.${NC}"
        return 1
    else
        echo -e "${GREEN}✔ $name is installed.${NC}"
        return 0
    fi
}

echo -e "\n${YELLOW}🔍 Checking system prerequisites...${NC}"
prereq_failed=0

check_prereq "python3" "Python 3" || prereq_failed=1
check_prereq "node" "Node.js" || prereq_failed=1
check_prereq "npm" "NPM Package Manager" || prereq_failed=1
check_prereq "ffmpeg" "FFmpeg Audio Encoder (Required by Whisper STT)" || prereq_failed=1
check_prereq "curl" "Curl Network Utility" || prereq_failed=1

if [ $prereq_failed -ne 0 ]; then
    echo -e "\n${RED}⚠️  Missing system dependencies. Please install them before proceeding.${NC}"
    echo -e "Refer to ${BLUE}DEVELOPMENT.md${NC} for platform-specific installation instructions."
    exit 1
fi

echo -e "${GREEN}🎉 All system prerequisites met!${NC}"

# Setup environment templates if they don't exist
setup_env() {
    local env_path=$1
    local example_path=$2
    if [ ! -f "$env_path" ]; then
        if [ -f "$example_path" ]; then
            cp "$example_path" "$env_path"
            echo -e "${YELLOW}📝 Created $env_path from example template.${NC}"
        else
            touch "$env_path"
            echo -e "${YELLOW}📝 Created empty $env_path file.${NC}"
        fi
    fi
}

echo -e "\n${YELLOW}⚙️  Verifying configuration files...${NC}"
setup_env "mcp_app/.env" "mcp_app/.env.example"
setup_env "agent/.env" "agent/.env.example"

# Ensure log directory exists
echo -e "\n${YELLOW}📁 Creating logs directory...${NC}"
mkdir -p logs
echo -e "${GREEN}✔ logs/ directory is ready.${NC}"

# PID tracking array
PIDS=()

# Graceful termination handler
cleanup() {
    echo -e "\n\n${RED}🛑 Terminating all services...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -15 "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
        fi
    done
    echo -e "${GREEN}✨ Clean exit. All background processes shut down.${NC}"
    exit 0
}

# Trap termination signals
trap cleanup SIGINT SIGTERM EXIT

# Start FastMCP server (Port 8005)
echo -e "\n${BLUE}1. Starting FastMCP Server (Port 8005)...${NC}"
python3 mcp_app/main.py > >(tee logs/mcp_app.log) 2>&1 &
MCP_PID=$!
PIDS+=($MCP_PID)
echo -e "   └─ FastMCP Server running with PID ${CYAN}$MCP_PID${NC} (Log: logs/mcp_app.log)"

# Start FastAPI Agent Server (Port 8001)
echo -e "\n${BLUE}2. Starting FastAPI Agent Server (Port 8001)...${NC}"
cd agent || exit 1
uvicorn main:socket_app --host 0.0.0.0 --port 8001 --workers 1 > >(tee ../logs/agent.log) 2>&1 &
AGENT_PID=$!
PIDS+=($AGENT_PID)
cd ..
echo -e "   └─ Agent Server running with PID ${CYAN}$AGENT_PID${NC} (Log: logs/agent.log)"

# Start WebRTC Audio Server (Port 8080)
echo -e "\n${BLUE}3. Starting WebRTC Backend Server (Port 8080)...${NC}"
python3 server/main.py > >(tee logs/server.log) 2>&1 &
SERVER_PID=$!
PIDS+=($SERVER_PID)
echo -e "   └─ WebRTC Backend running with PID ${CYAN}$SERVER_PID${NC} (Log: logs/server.log)"

# Start React Frontend (Port 3001)
echo -e "\n${BLUE}4. Starting Vite React Client (Port 3001)...${NC}"
cd client || exit 1
npm run dev > >(tee ../logs/client.log) 2>&1 &
CLIENT_PID=$!
PIDS+=($CLIENT_PID)
cd ..
echo -e "   └─ React client running with PID ${CYAN}$CLIENT_PID${NC} (Log: logs/client.log)"

# Wait for all services to load
echo -e "\n${YELLOW}⏳ Waiting for all services to initialize...${NC}"

wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=$3
    echo -ne "   - Waiting for $name (Port $port)... "
    for ((i=1; i<=max_wait; i++)); do
        if curl -s -o /dev/null "http://localhost:$port/"; then
            echo -e "${GREEN}Ready!${NC}"
            return 0
        fi
        sleep 1
    done
    echo -e "${RED}Timeout! Check log file.${NC}"
    return 1
}

wait_for_port 8005 "FastMCP Server" 30
wait_for_port 8001 "FastAPI Agent" 15
wait_for_port 8080 "WebRTC Backend" 15
wait_for_port 3001 "React Client" 15

# Browser open function
open_browser() {
    local url=$1
    echo -e "\n${CYAN}🌐 Launching default browser at $url...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url"
        else
            echo -e "${RED}⚠️  xdg-open not found. Please navigate to $url manually.${NC}"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        open "$url"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        start "$url"
    else
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url"
        elif command -v open &> /dev/null; then
            open "$url"
        else
            echo -e "${YELLOW}👉 Please navigate to: $url${NC}"
        fi
    fi
}

open_browser "http://localhost:3001"

echo -e "\n${GREEN}🚀 All services are running and verified live!${NC}"
echo -e "${CYAN}--------------------------------------------------${NC}"
echo -e "📱 Vite React Client:   ${GREEN}http://localhost:3001${NC}"
echo -e "🔊 WebRTC Backend:      ${GREEN}http://localhost:8080${NC}"
echo -e "🤖 FastAPI Agent API:   ${GREEN}http://localhost:8001${NC}"
echo -e "🛠️  FastMCP Server API:   ${GREEN}http://localhost:8005${NC}"
echo -e "${CYAN}--------------------------------------------------${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services simultaneously.${NC}\n"

# Keep the shell open to trap Ctrl+C and pipe the logs
while true; do
    sleep 1
done
