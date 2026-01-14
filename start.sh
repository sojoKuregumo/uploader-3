#!/bin/bash
# 1. Update and install MegaCMD (No sudo needed on Render)
wget -q https://mega.nz/linux/repo/xUbuntu_22.04/amd64/megacmd-xUbuntu_22.04_amd64.deb
apt-get update -qq && apt-get install -qq ./megacmd-xUbuntu_22.04_amd64.deb -y

# 2. Run the main Python script
python3 main.py
