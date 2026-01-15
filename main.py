import asyncio
import os
import subprocess
import threading
import sys
from flask import Flask
from pyrogram import Client, filters, idle

# Force print to show up immediately
print("🟢 SCRIPT STARTED - INITIALIZING...", flush=True)

# --- RENDER KEEPALIVE ---
web_app = Flask(__name__)
@web_app.route('/')
def health_check():
    return "Bot is Alive", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
# 👇 CHANGE THIS FOR 720p / 360p
QUALITY_TAG = "1080p" 
SLEEP_TIME = 0 
# 👆

MEGA_EMAIL = 'opcnlbnl@gmail.com'
MEGA_PASSWORD = 'Reigen@100%'
MEGA_ROOT = "/Root/AnimeDownloads"
# AUTO-DETECT CHAT ID logic is inside the command handler now

def mega_login():
    print("🔑 Attempting Mega Login...", flush=True)
    try:
        # Check version to verify PATH is correct
        ver = subprocess.run("mega-version", shell=True, capture_output=True, text=True)
        if ver.returncode != 0:
            print(f"❌ MegaCMD Binary not found in PATH: {os.environ['PATH']}", flush=True)
            return False
            
        # Login
        proc = subprocess.run(f'mega-login "{MEGA_EMAIL}" "{MEGA_PASSWORD}"', shell=True, capture_output=True, text=True)
        if "Already logged in" in proc.stdout or proc.returncode == 0:
            print("✅ Mega Login Successful!", flush=True)
            return True
        else:
            print(f"❌ Login Failed Output: {proc.stdout} {proc.stderr}", flush=True)
            return False
    except Exception as e:
        print(f"❌ Exception during Mega Login: {e}", flush=True)
        return False

# Setup Bot
print("🤖 Setting up Pyrogram Client...", flush=True)
app = Client(
    f"uploader_{QUALITY_TAG}",
    api_id=int(os.environ.get("UPLOADER_API_ID")),
    api_hash=os.environ.get("UPLOADER_API_HASH"),
    bot_token=os.environ.get("UPLOADER_BOT_TOKEN"),
    ipv6=False,
    workers=16
)

@app.on_message(filters.command("ping"))
async def ping(client, message):
    print(f"🔔 Ping received from {message.chat.id}", flush=True)
    await message.reply_text(f"✅ {QUALITY_TAG} Bot is ONLINE!\nChat ID: `{message.chat.id}`")

@app.on_message(filters.command(["upload", "fastupload"]))
async def upload_handler(client, message):
    cmd_text = message.text.lower()
    print(f"📥 Command received: {cmd_text}", flush=True)
    
    # 1. Filter
    if "-all" not in cmd_text and f"-{QUALITY_TAG[:-1]}" not in cmd_text:
        return

    # 2. Delay
    if SLEEP_TIME > 0:
        await message.reply(f"⏳ {QUALITY_TAG} Waiting {SLEEP_TIME}s...")
        await asyncio.sleep(SLEEP_TIME)

    # 3. Parse Folder
    parts = message.text.split()
    folder_name = next((p.strip('"\'') for p in parts[1:] if not p.startswith('-')), None)
    
    if not folder_name:
        return await message.reply("❌ Usage: `/upload FolderName -all`")

    # 4. Check Mega
    mega_folder = f"{MEGA_ROOT}/{folder_name}"
    # Use full path handling in case ENV is tricky
    res = subprocess.run(f'mega-ls "{mega_folder}"', shell=True, capture_output=True, text=True)
    
    if res.returncode != 0:
        print(f"❌ Mega LS Failed: {res.stderr}", flush=True)
        return await message.reply(f"❌ Mega Error: Folder `{folder_name}` not found or Login issue.")

    # 5. Filter Files
    all_files = res.stdout.strip().split('\n')
    target_files = [f for f in all_files if QUALITY_TAG in f.lower() or f"_{QUALITY_TAG[:-1]}_" in f]

    if not target_files:
        return await message.reply(f"❌ No {QUALITY_TAG} files found.")

    status = await message.reply(f"🚀 **{QUALITY_TAG} Started** | Files: `{len(target_files)}`")

    # 6. Upload Loop
    for filename in target_files:
        local_path = f"./{filename}"
        subprocess.run(f'mega-get "{mega_folder}/{filename}" "{local_path}"', shell=True)
        
        if os.path.exists(local_path):
            try:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=local_path,
                    force_document=True,
                    caption=filename
                )
            except Exception as e:
                print(f"❌ Telegram Upload Fail: {e}", flush=True)
            finally:
                os.remove(local_path)
    
    await status.edit_text(f"✅ **{QUALITY_TAG} Done.**")

async def main():
    # Start Flask
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Attempt Mega Login (But don't crash if it fails)
    mega_login()
    
    print("🚀 Starting Telegram Polling...", flush=True)
    await app.start()
    print("✅ BOT IS NOW LISTENING (Look for this line!)", flush=True)
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
