import asyncio
import os
import re
import subprocess
import threading
from flask import Flask
from pyrogram import Client, filters, idle

# --- RENDER HEALTH CHECK ---
web_app = Flask(__name__)
@web_app.route('/')
def health_check(): return "720p Uploader is Online", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
# HARDCODED CREDENTIALS
MEGA_EMAIL = 'opcnlbnl@gmail.com'
MEGA_PASSWORD = 'Reigen@100%'

QUALITY_TAG = "720p"
SLEEP_TIME = 20         # 20-second delay for 720p bot
MEGA_ROOT = "/Root/AnimeDownloads"
TARGET_CHAT_ID = -1003392399992

def mega_login():
    try:
        login_cmd = f'mega-login "{MEGA_EMAIL}" "{MEGA_PASSWORD}"'
        subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
        print("✅ 720p Mega Login successful")
        return True
    except Exception as e:
        print(f"❌ Mega Login failed: {e}")
        return False

# Pyrogram Client Setup
app = Client(
    "uploader_720p",
    api_id=int(os.environ.get("UPLOADER_API_ID")),
    api_hash=os.environ.get("UPLOADER_API_HASH")),
    bot_token=os.environ.get("UPLOADER_BOT_TOKEN")),
    ipv6=False,
    workers=16
)

@app.on_message(filters.command("ping"))
async def ping(client, message):
    await message.reply_text(f"✅ {QUALITY_TAG} Uploader is ONLINE!")

@app.on_message(filters.command(["upload", "fastupload"]))
async def upload_handler(client, message):
    cmd_text = message.text.lower()
    if "-all" not in cmd_text and "-720" not in cmd_text:
        return

    # [cite_start]Staggered delay for 720p bot [cite: 107, 110]
    await asyncio.sleep(SLEEP_TIME)

    parts = message.text.split()
    folder_name = next((p.strip('"\'') for p in parts[1:] if not p.startswith('-')), None)
    if not folder_name: return

    mega_folder = f"{MEGA_ROOT}/{folder_name}"
    
    # [cite_start]List files from Mega [cite: 5, 121]
    res = subprocess.run(f'mega-ls "{mega_folder}"', shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        return await message.reply(f"❌ Mega folder `{folder_name}` not found.")

    all_files = res.stdout.strip().split('\n')
    # [cite_start]Filter for 720p quality [cite: 18, 112]
    target_files = [f for f in all_files if QUALITY_TAG in f.lower() or "_720_" in f]

    if not target_files:
        return await message.reply(f"❌ No {QUALITY_TAG} files found.")

    status = await message.reply(f"🚀 **{QUALITY_TAG} Started** | Files: `{len(target_files)}`")

    for filename in target_files:
        local_path = f"./{filename}"
        # [cite_start]Download file [cite: 24, 110]
        subprocess.run(f'mega-get "{mega_folder}/{filename}" "{local_path}"', shell=True)
        
        if os.path.exists(local_path):
            try:
                await client.send_document(
                    chat_id=TARGET_CHAT_ID,
                    document=local_path,
                    force_document=True
                )
            except Exception as e:
                print(f"Upload error: {filename} - {e}")
            finally:
                if os.path.exists(local_path): os.remove(local_path)
    
    await status.edit_text(f"✅ **{QUALITY_TAG} UPLOAD COMPLETE**")

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    mega_login()
    await app.start()
    print(f"✅ {QUALITY_TAG} Uploader Started")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
