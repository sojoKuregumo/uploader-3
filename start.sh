#!/bin/bash
# 1. Download MegaCMD
wget -q https://mega.nz/linux/repo/xUbuntu_22.04/amd64/megacmd-xUbuntu_22.04_amd64.deb

# 2. Install using dpkg (Force installation without sudo)
# Render allows dpkg if dependencies are already in the base image
dpkg -x megacmd-xUbuntu_22.04_amd64.deb .
export PATH=$PATH:$(pwd)/usr/bin

# 3. Start the bot
python3 main.py
