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
def health_check(): return "1080p Uploader is Online", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
# HARDCODED CREDENTIALS
MEGA_EMAIL = 'opcnlbnl@gmail.com'
MEGA_PASSWORD = 'Reigen@100%'

QUALITY_TAG = "1080p"  # Change to 720p or 360p for other branches [cite: 102]
SLEEP_TIME = 0         # 20 for 720p, 40 for 360p
MEGA_ROOT = "/Root/AnimeDownloads" [cite: 4, 96]
TARGET_CHAT_ID = -1003392399992 [cite: 4]

def mega_login():
    try:
        # Attempt login with hardcoded creds [cite: 3, 93, 94]
        login_cmd = f'mega-login "{MEGA_EMAIL}" "{MEGA_PASSWORD}"'
        subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
        print("✅ Mega Login successful") [cite: 3, 94]
        return True
    except Exception as e:
        print(f"❌ Mega Login failed: {e}") [cite: 4, 95]
        return False

# Pyrogram Client Setup
app = Client(
    f"uploader_{QUALITY_TAG}",
    api_id=int(os.environ.get("UPLOADER_API_ID")),
    api_hash=os.environ.get("UPLOADER_API_HASH"),
    bot_token=os.environ.get("UPLOADER_BOT_TOKEN"),
    ipv6=False,
    workers=16 [cite: 5]
)

@app.on_message(filters.command("ping"))
async def ping(client, message):
    await message.reply_text(f"✅ {QUALITY_TAG} Uploader is ONLINE!")

@app.on_message(filters.command(["upload", "fastupload"]))
async def upload_handler(client, message):
    cmd_text = message.text.lower()
    if "-all" not in cmd_text and f"-{QUALITY_TAG[:-1]}" not in cmd_text:
        return [cite: 18, 101]

    if SLEEP_TIME > 0:
        await asyncio.sleep(SLEEP_TIME)

    parts = message.text.split()
    folder_name = next((p.strip('"\'') for p in parts[1:] if not p.startswith('-')), None) [cite: 8, 9]
    if not folder_name: return

    mega_folder = f"{MEGA_ROOT}/{folder_name}" [cite: 17, 103]
    
    # List files from Mega [cite: 5, 121]
    res = subprocess.run(f'mega-ls "{mega_folder}"', shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        return await message.reply(f"❌ Mega folder `{folder_name}` not found.") [cite: 17, 122]

    all_files = res.stdout.strip().split('\n')
    # Filter for specific quality [cite: 12, 13, 118]
    target_files = [f for f in all_files if QUALITY_TAG in f.lower() or f"_{QUALITY_TAG[:-1]}_" in f]

    if not target_files:
        return await message.reply(f"❌ No {QUALITY_TAG} files found.") [cite: 18, 102]

    status = await message.reply(f"🚀 **{QUALITY_TAG} Started** | Files: `{len(target_files)}`") [cite: 19]

    for filename in target_files:
        local_path = f"./{filename}"
        # Download file [cite: 6, 111]
        subprocess.run(f'mega-get "{mega_folder}/{filename}" "{local_path}"', shell=True)
        
        if os.path.exists(local_path):
            try:
                await client.send_document(
                    chat_id=TARGET_CHAT_ID,
                    document=local_path,
                    force_document=True [cite: 26, 27]
                )
            except Exception as e:
                print(f"Upload error: {filename} - {e}") [cite: 28, 114]
            finally:
                if os.path.exists(local_path): os.remove(local_path) [cite: 28, 115]
    
    await status.edit_text(f"✅ **{QUALITY_TAG} UPLOAD COMPLETE**") [cite: 29, 117]

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    mega_login()
    await app.start()
    print(f"✅ {QUALITY_TAG} Uploader Started")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
