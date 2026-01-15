import asyncio
import os
import re
import subprocess
import threading
from flask import Flask
from pyrogram import Client, filters, idle

# --- RENDER PORT CONFIGURATION ---
# Opens a web port so Render keeps the bot active
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "1080p Uploader is Online", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
QUALITY_TAG = "1080p"
MEGA_ROOT = "/Root/AnimeDownloads"
TARGET_CHAT_ID = -1003392399992

def mega_login():
    email = os.environ.get("MEGA_EMAIL")
    password = os.environ.get("MEGA_PASSWORD")
    if email and password:
        check = subprocess.run('mega-whoami', shell=True, capture_output=True, text=True)
        if "Account e-mail:" in check.stdout:
            return True
        login_cmd = f'mega-login "{email}" "{password}"'
        subprocess.run(login_cmd, shell=True)
        return True
    return False

# Pyrogram Client Setup
app = Client(
    "uploader_1080p",
    api_id=int(os.environ.get("UPLOADER_API_ID")),
    api_hash=os.environ.get("UPLOADER_API_HASH"),
    bot_token=os.environ.get("UPLOADER_BOT_TOKEN"),
    workers=16
)

# --- COMMANDS ---

@app.on_message(filters.command("ping"))
async def ping_handler(client, message):
    """Checks if the bot is alive"""
    await message.reply_text(f"✅ {QUALITY_TAG} Uploader is ONLINE!")

@app.on_message(filters.command(["upload", "fastupload"]))
async def fast_upload_1080(client, message):
    """Main upload logic for 1080p files"""
    cmd_text = message.text.lower()
    
    # Only react if '-all' or '-1080' is in the command
    if "-all" not in cmd_text and "-1080" not in cmd_text:
        return

    parts = message.text.split()
    folder_name = None
    for part in parts[1:]:
        if not part.startswith('-'):
            folder_name = part.strip('"\'')
            break
            
    if not folder_name:
        return await message.reply("❌ Please provide a folder name.")

    # List files from Mega
    mega_folder = f"{MEGA_ROOT}/{folder_name}"
    cmd = f'mega-ls "{mega_folder}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        return await message.reply(f"❌ Folder `{folder_name}` not found in Mega.")
    
    all_files = result.stdout.strip().split('\n')
    # FILTER: Specifically look for 1080p files [cite: 18, 25]
    target_files = [f for f in all_files if "1080p" in f.lower() or "_1080_" in f]

    if not target_files:
        return await message.reply(f"❌ No 1080p files found in `{folder_name}`")

    status_msg = await message.reply(f"🚀 **1080p Uploader Started**\nFiles: `{len(target_files)}`")

    for filename in target_files:
        local_path = f"./{filename}"
        # Download from Mega [cite: 6, 24]
        subprocess.run(f'mega-get "{mega_folder}/{filename}" "{local_path}"', shell=True)
        
        if os.path.exists(local_path):
            try:
                # Send to Telegram [cite: 26, 27]
                await client.send_document(
                    chat_id=TARGET_CHAT_ID,
                    document=local_path,
                    force_document=True
                )
            except Exception as e:
                print(f"Upload error: {e}")
            finally:
                if os.path.exists(local_path):
                    os.remove(local_path)
    
    await status_msg.edit_text(f"✅ **1080p UPLOAD COMPLETE**\nFolder: `{folder_name}`")

async def main():
    # Start the Health Check server in background [cite: 4]
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Login and start bot [cite: 2, 42]
    mega_login()
    await app.start()
    print("✅ 1080p Uploader Bot Online on Render")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
