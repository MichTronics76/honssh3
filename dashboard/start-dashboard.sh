#!/bin/bash

# HonSSH Dashboard Startup Script
# Professional monitoring interface for HonSSH

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
API_PORT=5000

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         HonSSH Dashboard Setup & Launcher                 ║"
echo "║         Professional SSH Honeypot Monitoring              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "[✓] Virtual environment created"
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install/update dependencies
echo "[*] Installing dashboard dependencies..."
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "[✓] Dependencies installed"

# Check if HonSSH config exists
CONFIG_FILE="$SCRIPT_DIR/../honssh.cfg"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="$SCRIPT_DIR/../honssh.cfg.default"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[!] Error: HonSSH configuration file not found!"
    echo "    Please ensure honssh.cfg or honssh.cfg.default exists"
    exit 1
fi

echo "[✓] Configuration file found: $CONFIG_FILE"
echo ""

# Check MySQL connection
echo "[*] Checking MySQL database connection..."
python3 - <<EOF
import sys
import configparser
import MySQLdb

config = configparser.ConfigParser()
config.read('$CONFIG_FILE')

try:
    db = MySQLdb.connect(
        host=config.get('output-mysql', 'host'),
        db=config.get('output-mysql', 'database'),
        user=config.get('output-mysql', 'username'),
        passwd=config.get('output-mysql', 'password'),
        port=int(config.get('output-mysql', 'port'))
    )
    db.close()
    print('[✓] Database connection successful')
except Exception as e:
    print('[!] Database connection failed:', str(e))
    print('    Please check your MySQL configuration in honssh.cfg')
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "Please ensure:"
    echo "  1. MySQL is running"
    echo "  2. Database credentials in honssh.cfg are correct"
    echo "  3. HonSSH database schema is imported (utils/honssh.sql)"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                   Starting Dashboard                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Dashboard will be available at:"
echo "  • API:       http://localhost:$API_PORT/api/health"
echo "  • Dashboard: http://localhost:$API_PORT"
echo ""
echo "To view the dashboard, open dashboard/index.html in your browser"
echo "or use: python3 -m http.server 8080 (in dashboard directory)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the API server
cd "$SCRIPT_DIR"
python3 api.py
