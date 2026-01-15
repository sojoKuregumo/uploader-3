#!/bin/bash
# 1. Download MegaCMD
wget -q https://mega.nz/linux/repo/xUbuntu_22.04/amd64/megacmd-xUbuntu_22.04_amd64.deb

# 2. Extract it locally (Bypassing sudo/root requirement)
dpkg -x megacmd-xUbuntu_22.04_amd64.deb ./mega_local

# 3. Add the local bin folder to the system PATH so python can find 'mega-login'
export PATH="$PWD/mega_local/usr/bin:$PATH"
export LD_LIBRARY_PATH="$PWD/mega_local/usr/lib:$LD_LIBRARY_PATH"

# 4. Start the bot
python3 main.py
