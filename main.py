import asyncio
import os
import subprocess
import threading
from flask import Flask
from pyrogram import Client, filters, idle

# --- RENDER KEEPALIVE ---
web_app = Flask(__name__)
@web_app.route('/')
def health_check(): return "Bot is Alive", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- HARDCODED CONFIG ---
# 👇 CHANGE THESE FOR 720p / 360p REPOS
QUALITY_TAG = "360p" 
SLEEP_TIME = 40       # 20 for 720p, 40 for 360p
# 👆

MEGA_EMAIL = 'opcnlbnl@gmail.com'
MEGA_PASSWORD = 'Reigen@100%'
MEGA_ROOT = "/Root/AnimeDownloads"

def mega_login():
    """Login to Mega using the local path from start.sh"""
    try:
        # Check if we can see the command
        subprocess.run("mega-version", shell=True, check=True, capture_output=True)
        # Login
        subprocess.run(f'mega-login "{MEGA_EMAIL}" "{MEGA_PASSWORD}"', shell=True, check=True, capture_output=True)
        print("✅ Mega Login Successful")
        return True
    except Exception as e:
        print(f"❌ MegaCMD Not Found or Login Failed: {e}")
        return False

# Setup Bot
app = Client(
    f"uploader_{QUALITY_TAG}",
    api_id=int(os.environ.get("UPLOADER_API_ID")),
    api_hash=os.environ.get("UPLOADER_API_HASH"),
    bot_token=os.environ.get("UPLOADER_BOT_TOKEN"),
    ipv6=False, # Critical for Render
    workers=16
)

@app.on_message(filters.command("ping"))
async def ping(client, message):
    # This replies to the SAME group you typed in
    await message.reply_text(f"✅ {QUALITY_TAG} Bot is HERE and listening!")

@app.on_message(filters.command(["upload", "fastupload"]))
async def upload_handler(client, message):
    cmd_text = message.text.lower()
    
    # 1. Filter: Does command match this bot?
    if "-all" not in cmd_text and f"-{QUALITY_TAG[:-1]}" not in cmd_text:
        return

    # 2. Delay: Stagger start time
    if SLEEP_TIME > 0:
        await asyncio.sleep(SLEEP_TIME)

    # 3. Parse Folder Name
    parts = message.text.split()
    folder_name = next((p.strip('"\'') for p in parts[1:] if not p.startswith('-')), None)
    
    if not folder_name:
        return await message.reply("❌ Send: `/upload FolderName -all`")

    # 4. Check Mega
    mega_folder = f"{MEGA_ROOT}/{folder_name}"
    res = subprocess.run(f'mega-ls "{mega_folder}"', shell=True, capture_output=True, text=True)
    
    if res.returncode != 0:
        return await message.reply(f"❌ MegaCMD Error or Folder `{folder_name}` not found.")

    # 5. Filter Files by Quality
    all_files = res.stdout.strip().split('\n')
    target_files = [f for f in all_files if QUALITY_TAG in f.lower() or f"_{QUALITY_TAG[:-1]}_" in f]

    if not target_files:
        return await message.reply(f"❌ No {QUALITY_TAG} files found in `{folder_name}`.")

    status = await message.reply(f"🚀 **{QUALITY_TAG} Started** | Found: `{len(target_files)}` files")

    # 6. Download & Upload Loop
    for filename in target_files:
        local_path = f"./{filename}"
        # Download
        subprocess.run(f'mega-get "{mega_folder}/{filename}" "{local_path}"', shell=True)
        
        if os.path.exists(local_path):
            try:
                await client.send_document(
                    chat_id=message.chat.id, # <--- AUTO DETECT CHAT ID
                    document=local_path,
                    force_document=True,
                    caption=filename
                )
            except Exception as e:
                print(f"Upload Failed: {e}")
            finally:
                os.remove(local_path)
    
    await status.edit_text(f"✅ **{QUALITY_TAG} Done.**")

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    if mega_login():
        print("✅ Mega Ready")
    else:
        print("❌ Mega Failed (Check start.sh)")
    
    await app.start()
    print("✅ Bot Started")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
