#!/bin/bash
set -e  # Exit on error

echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

echo "📦 Downloading MegaCMD..."
wget -q https://mega.nz/linux/repo/xUbuntu_22.04/amd64/megacmd-xUbuntu_22.04_amd64.deb

echo "📂 Extracting MegaCMD..."
mkdir -p mega_local
dpkg -x megacmd-xUbuntu_22.04_amd64.deb ./mega_local

echo "🔧 Setting up environment..."
export PATH="$(pwd)/mega_local/usr/bin:$PATH"
export LD_LIBRARY_PATH="$(pwd)/mega_local/usr/lib:$LD_LIBRARY_PATH"

# Test if mega-cmd is accessible
echo "🧪 Testing MEGA-CMD..."
if [ -f "$(pwd)/mega_local/usr/bin/mega-cmd" ]; then
    echo "✅ MEGA-CMD found at $(pwd)/mega_local/usr/bin/mega-cmd"
else
    echo "❌ MEGA-CMD not found!"
    ls -la "$(pwd)/mega_local/usr/bin/" || true
fi

echo "🚀 Starting Python Script..."
python3 -u main.py
