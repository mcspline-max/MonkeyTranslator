#!/bin/bash

# --- CONFIGURATION ---
# This points to the raw text version of your installer on GitHub
GITHUB_URL="https://raw.githubusercontent.com/mcspline-max/MonkeyTranslator/main/installer.py"
# ---------------------

# 1. Setup UI
cd "$(dirname "$0")"
clear
echo "======================================================="
echo "      🐒 MonkeyTranslator Web Installer"
echo "======================================================="
echo ""
echo "This will download the latest installer from GitHub"
echo "and install the plugin to DaVinci Resolve."
echo ""
echo "🔑 Administrator privileges are required."
echo "Please enter your Mac password below to proceed."
echo "(Note: Characters will not appear while typing)"
echo "-------------------------------------------------------"

# 2. Elevate privileges right away to avoid timeout later
sudo -v

# Keep sudo alive in the background
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

echo ""
echo "⬇️  Fetching installer logic..."

# 3. Download the Python script to the /tmp directory
# We use /tmp so we don't leave garbage files on the user's desktop
curl -L -o /tmp/monkey_installer.py "$GITHUB_URL"

# Check if download succeeded
if [ ! -f /tmp/monkey_installer.py ]; then
    echo "❌ Error: Could not download installer. Check your internet."
    read -p "Press [Enter] to exit..."
    exit 1
fi

echo "🚀 Running Python Installer..."
echo "-------------------------------------------------------"

# 4. Run the downloaded script using system python
sudo python3 /tmp/monkey_installer.py

# 5. Clean up
rm /tmp/monkey_installer.py

echo ""
echo "-------------------------------------------------------"
echo "Process finished."
# Pause so the user can read the "Success" message from Python
read -p "Press [Enter] to close this window..."