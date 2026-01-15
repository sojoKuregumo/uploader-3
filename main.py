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
    print(f"🌐 Starting Flask on port {port}", flush=True)
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- CONFIG ---
QUALITY_TAG = "1080p"  # Change this for 720p / 360p
SLEEP_TIME = 0

MEGA_EMAIL = 'opcnlbnl@gmail.com'
MEGA_PASSWORD = 'Reigen@100%'
MEGA_ROOT = "/Root/AnimeDownloads"

def mega_login():
    print("🔑 Attempting Mega Login...", flush=True)
    try:
        # First, check if mega-cmd exists
        mega_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
        if not os.path.exists(mega_path):
            print(f"❌ MegaCMD not found at: {mega_path}", flush=True)
            return False
            
        # Check version
        ver = subprocess.run([mega_path, "--version"], capture_output=True, text=True)
        if ver.returncode != 0:
            print(f"❌ MegaCMD version check failed: {ver.stderr}", flush=True)
            return False
            
        print(f"✅ MegaCMD found: {ver.stdout}", flush=True)
        
        # Login using mega-login command
        login_cmd = f'{mega_path}-login "{MEGA_EMAIL}" "{MEGA_PASSWORD}"'
        proc = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
        
        if "Already logged in" in proc.stdout or "Login successful" in proc.stdout or proc.returncode == 0:
            print("✅ Mega Login Successful!", flush=True)
            return True
        else:
            print(f"❌ Login Failed Output: {proc.stdout} {proc.stderr}", flush=True)
            return False
    except Exception as e:
        print(f"❌ Exception during Mega Login: {e}", flush=True)
        return False

# Check environment variables
print("🔍 Checking environment variables...", flush=True)
api_id = os.environ.get("UPLOADER_API_ID")
api_hash = os.environ.get("UPLOADER_API_HASH")
bot_token = os.environ.get("UPLOADER_BOT_TOKEN")

if not all([api_id, api_hash, bot_token]):
    print("❌ Missing environment variables!", flush=True)
    print(f"API_ID: {'✅' if api_id else '❌'}")
    print(f"API_HASH: {'✅' if api_hash else '❌'}")
    print(f"BOT_TOKEN: {'✅' if bot_token else '❌'}")
    sys.exit(1)

print("✅ Environment variables found!", flush=True)

# Setup Bot
print("🤖 Setting up Pyrogram Client...", flush=True)
app = Client(
    f"uploader_{QUALITY_TAG}",
    api_id=int(api_id),
    api_hash=api_hash,
    bot_token=bot_token,
    ipv6=False,
    workers=16,
    in_memory=True  # Added for better performance
)

@app.on_message(filters.command("ping"))
async def ping(client, message):
    print(f"🔔 Ping received from {message.chat.id}", flush=True)
    await message.reply_text(f"✅ {QUALITY_TAG} Bot is ONLINE!\nChat ID: `{message.chat.id}`")

@app.on_message(filters.command(["upload", "fastupload"]))
async def upload_handler(client, message):
    cmd_text = message.text.lower()
    print(f"📥 Command received: {cmd_text}", flush=True)
    
    # 1. Filter by quality
    if "-all" not in cmd_text and f"-{QUALITY_TAG[:-1]}" not in cmd_text:
        print(f"❌ Skipping - wrong quality tag", flush=True)
        return

    # 2. Delay if needed
    if SLEEP_TIME > 0:
        await message.reply(f"⏳ {QUALITY_TAG} Waiting {SLEEP_TIME}s...")
        await asyncio.sleep(SLEEP_TIME)

    # 3. Parse folder name
    parts = message.text.split()
    folder_name = next((p.strip('"\'').strip() for p in parts[1:] if not p.startswith('-')), None)
    
    if not folder_name:
        return await message.reply("❌ Usage: `/upload FolderName -all`")

    # 4. Check if folder exists in Mega
    mega_folder = f"{MEGA_ROOT}/{folder_name}"
    mega_cmd = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
    
    print(f"🔍 Checking Mega folder: {mega_folder}", flush=True)
    res = subprocess.run(f'{mega_cmd} -ls "{mega_folder}"', shell=True, capture_output=True, text=True)
    
    if res.returncode != 0:
        print(f"❌ Mega LS Failed: {res.stderr}", flush=True)
        return await message.reply(f"❌ Mega Error: Folder `{folder_name}` not found or Login issue.")

    # 5. Filter files by quality
    all_files = [f.strip() for f in res.stdout.strip().split('\n') if f.strip()]
    target_files = [f for f in all_files if QUALITY_TAG in f.lower() or f"_{QUALITY_TAG[:-1]}_" in f.lower()]

    if not target_files:
        return await message.reply(f"❌ No {QUALITY_TAG} files found.")

    status = await message.reply(f"🚀 **{QUALITY_TAG} Started** | Files: `{len(target_files)}`")

    # 6. Download and upload loop
    uploaded = 0
    for filename in target_files:
        print(f"⬇️ Downloading: {filename}", flush=True)
        local_path = os.path.join(os.getcwd(), filename)
        
        # Download from Mega
        download_cmd = f'{mega_cmd} -get "{mega_folder}/{filename}" "{local_path}"'
        dl_result = subprocess.run(download_cmd, shell=True, capture_output=True, text=True)
        
        if os.path.exists(local_path):
            try:
                print(f"📤 Uploading to Telegram: {filename}", flush=True)
                await client.send_document(
                    chat_id=message.chat.id,
                    document=local_path,
                    force_document=True,
                    caption=filename
                )
                uploaded += 1
                print(f"✅ Uploaded: {filename}", flush=True)
            except Exception as e:
                print(f"❌ Telegram Upload Fail: {e}", flush=True)
            finally:
                os.remove(local_path)
        else:
            print(f"❌ Download failed for: {filename}", flush=True)
    
    await status.edit_text(f"✅ **{QUALITY_TAG} Done.** Uploaded: `{uploaded}/{len(target_files)}` files")

async def main():
    print("🚀 Starting services...", flush=True)
    
    # Start Flask in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask thread started", flush=True)
    
    # Try Mega login
    if not mega_login():
        print("⚠️ Mega login failed, but continuing...", flush=True)
    
    print("🤖 Starting Telegram Client...", flush=True)
    await app.start()
    
    # Get bot info to confirm it's running
    me = await app.get_me()
    print(f"✅ BOT IS RUNNING: @{me.username} (ID: {me.id})", flush=True)
    print("🎯 Listening for commands...", flush=True)
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Bot stopped by user", flush=True)
    except Exception as e:
        print(f"💥 Unexpected error: {e}", flush=True)
