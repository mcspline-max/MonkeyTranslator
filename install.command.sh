#!/bin/bash

# 1. Navigate to the folder containing this script
# (This ensures it finds installer.py even if run from Downloads)
cd "$(dirname "$0")"

# 2. Clear terminal for a clean look
clear

echo "=========================================="
echo "   MonkeyTranslator Mac Installer"
echo "=========================================="
echo ""
echo "This installer requires Administrator privileges"
echo "to install files into the DaVinci Resolve folder."
echo ""
echo "Please enter your Mac password below to proceed."
echo "(Note: You will not see characters while typing)"
echo "------------------------------------------"

# 3. Run the Python script with sudo (Admin rights)
sudo python3 installer.py

# 4. Keep window open so user can read the success/error message
echo ""
echo "------------------------------------------"
echo "Process finished. You can close this window."
read -p "Press [Enter] to close..."