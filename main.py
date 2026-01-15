import asyncio
import os
import subprocess
import sys
import tempfile
from pyrogram import Client, filters, idle

# Force print to show up immediately
print("🟢 SCRIPT STARTED - INITIALIZING...", flush=True)

# --- CONFIG ---
QUALITY_TAG = "1080p"
SLEEP_TIME = 0

# PythonAnywhere Specific: Hardcode paths or use relative paths
# We will put the mega-cmd binary in the same folder as this script
MEGA_BINARY_PATH = os.path.join(os.getcwd(), "mega-cmd")

# Get Tokens from Environment (or hardcode them if you trust your security)
MEGA_SESSION_TOKEN = os.environ.get("MEGA_SESSION_TOKEN", "").strip()
MEGA_ROOT = "/Root/AnimeDownloads"

def mega_login_with_session():
    if not MEGA_SESSION_TOKEN:
        print("❌ No MEGA session token provided")
        return False
    
    print("🔑 Attempting Mega Login...", flush=True)
    
    if not os.path.exists(MEGA_BINARY_PATH):
        print(f"❌ mega-cmd binary not found at: {MEGA_BINARY_PATH}")
        return False

    try:
        # Create a temporary script for login
        with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
            f.write(f'session {MEGA_SESSION_TOKEN}\n')
            f.write('whoami\n')
            f.write('exit\n')
            script_path = f.name
        
        # Execute
        cmd = f'{MEGA_BINARY_PATH} -console < "{script_path}"'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        os.unlink(script_path)
        
        if "welcome" in proc.stdout.lower() or "login successful" in proc.stdout.lower():
            print("✅ Mega Login Successful!")
            return True
        else:
            print(f"❌ Login Failed: {proc.stdout[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Login Exception: {e}")
        return False

# Telegram Config
api_id = os.environ.get("UPLOADER_API_ID")
api_hash = os.environ.get("UPLOADER_API_HASH")
bot_token = os.environ.get("UPLOADER_BOT_TOKEN")

if not all([api_id, api_hash, bot_token]):
    print("❌ Missing Telegram vars")
    sys.exit(1)

app = Client(
    f"PA_Uploader_{QUALITY_TAG}",
    api_id=int(api_id),
    api_hash=api_hash,
    bot_token=bot_token,
    workers=4
)

@app.on_message(filters.command("ping"))
async def ping(client, message):
    await message.reply_text(f"✅ PythonAnywhere Bot Online!\nChat ID: `{message.chat.id}`")

# ... [Keep your upload_handler function mostly the same, just update the binary path] ...
# Make sure to replace `mega_cmd_path` in your upload_handler with `MEGA_BINARY_PATH`

async def main():
    print("🚀 Starting Bot on PythonAnywhere...", flush=True)
    
    if MEGA_SESSION_TOKEN:
        mega_login_with_session()
    
    await app.start()
    me = await app.get_me()
    print(f"✅ BOT RUNNING: @{me.username}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
