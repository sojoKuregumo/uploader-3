#!/bin/bash
# 1. Download MegaCMD
echo "📦 Downloading MegaCMD..."
wget -q https://mega.nz/linux/repo/xUbuntu_22.04/amd64/megacmd-xUbuntu_22.04_amd64.deb

# 2. Extract locally (Bypassing sudo)
echo "📂 Extracting MegaCMD..."
dpkg -x megacmd-xUbuntu_22.04_amd64.deb ./mega_local

# 3. Add to PATH so Python can see it
export PATH="$(pwd)/mega_local/usr/bin:$PATH"
export LD_LIBRARY_PATH="$(pwd)/mega_local/usr/lib:$LD_LIBRARY_PATH"

# 4. Start Bot with UNBUFFERED output
echo "🚀 Starting Python Script..."
python3 -u main.py
