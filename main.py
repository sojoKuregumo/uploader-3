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

# 👇 ADD YOUR SESSION TOKEN HERE (from mega-session command)
MEGA_SESSION_TOKEN = "YOUR_SESSION_TOKEN_HERE"  # Replace with your actual token
# Get this by running: mega-session on your local machine
# 👆

MEGA_ROOT = "/Root/AnimeDownloads"

def mega_login_with_session():
    """
    Login to MEGA using session token (more reliable than password)
    """
    print("🔑 Attempting Mega Login with Session Token...", flush=True)
    try:
        # Find mega-cmd binary
        mega_cmd_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
        
        if not os.path.exists(mega_cmd_path):
            print(f"❌ mega-cmd not found at: {mega_cmd_path}", flush=True)
            # Try alternative path
            mega_cmd_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd-server")
            if not os.path.exists(mega_cmd_path):
                print(f"❌ mega-cmd-server also not found", flush=True)
                return False
        
        # First, check if already logged in
        print("🔍 Checking current login status...", flush=True)
        check_cmd = f'echo "whoami" | {mega_cmd_path} -console 2>&1'
        proc = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        
        if "Not logged in" not in proc.stdout and "ERROR" not in proc.stdout:
            print(f"✅ Already logged in: {proc.stdout[:100]}...", flush=True)
            return True
        
        # Login using session token
        print(f"🔑 Logging in with session token...", flush=True)
        
        # Create a temporary script to handle the login
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
            # Write MEGAcmd commands to file
            f.write(f'session {MEGA_SESSION_TOKEN}\n')
            f.write('whoami\n')
            f.write('exit\n')
            script_path = f.name
        
        # Execute the script
        login_cmd = f'{mega_cmd_path} -console < "{script_path}"'
        proc = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
        
        # Clean up temp file
        os.unlink(script_path)
        
        if "Login successful" in proc.stdout or "Welcome" in proc.stdout or proc.returncode == 0:
            print("✅ Mega Login Successful with Session Token!", flush=True)
            
            # Verify login
            verify_cmd = f'echo "whoami" | {mega_cmd_path} -console'
            verify = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            if "Not logged in" not in verify.stdout:
                print(f"✅ Verified: {verify.stdout.strip()}", flush=True)
                return True
            else:
                print(f"⚠️ Login seemed successful but verification failed: {verify.stdout}", flush=True)
                return False
        else:
            print(f"❌ Session Login Failed: {proc.stdout[:200]}", flush=True)
            
            # Try alternative method
            print("🔄 Trying alternative session login method...", flush=True)
            alt_cmd = f'echo "session {MEGA_SESSION_TOKEN}" | {mega_cmd_path} -console'
            alt_proc = subprocess.run(alt_cmd, shell=True, capture_output=True, text=True)
            
            if "Login successful" in alt_proc.stdout or alt_proc.returncode == 0:
                print("✅ Alternative session login successful!", flush=True)
                return True
            
            return False
            
    except Exception as e:
        print(f"❌ Exception during Mega Session Login: {e}", flush=True)
        import traceback
        traceback.print_exc()
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
    in_memory=True
)

@app.on_message(filters.command("ping"))
async def ping(client, message):
    print(f"🔔 Ping received from {message.chat.id}", flush=True)
    await message.reply_text(f"✅ {QUALITY_TAG} Bot is ONLINE!\nChat ID: `{message.chat.id}`")

@app.on_message(filters.command("mega_status"))
async def mega_status(client, message):
    """Check MEGA login status"""
    print(f"🔍 MEGA status check from {message.chat.id}", flush=True)
    
    mega_cmd_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
    if not os.path.exists(mega_cmd_path):
        await message.reply("❌ MEGA-CMD not found")
        return
    
    check_cmd = f'echo "whoami" | {mega_cmd_path} -console'
    proc = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
    
    if "Not logged in" in proc.stdout:
        await message.reply("❌ MEGA: Not logged in")
    else:
        await message.reply(f"✅ MEGA: {proc.stdout.strip()}")

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

    # 4. Check MEGA login first
    mega_cmd_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
    if not os.path.exists(mega_cmd_path):
        return await message.reply("❌ MEGA-CMD not installed")
    
    # 5. Check if folder exists in Mega
    mega_folder = f"{MEGA_ROOT}/{folder_name}"
    
    print(f"🔍 Checking Mega folder: {mega_folder}", flush=True)
    
    # Create a script to list files
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
        f.write(f'ls "{mega_folder}"\n')
        f.write('exit\n')
        script_path = f.name
    
    list_cmd = f'{mega_cmd_path} -console < "{script_path}"'
    res = subprocess.run(list_cmd, shell=True, capture_output=True, text=True)
    os.unlink(script_path)
    
    if "ERROR" in res.stdout or "not found" in res.stdout.lower():
        print(f"❌ Mega LS Failed: {res.stdout[:500]}", flush=True)
        return await message.reply(f"❌ Mega Error: Folder `{folder_name}` not found or access denied.")
    
    # 6. Filter files by quality
    lines = [line.strip() for line in res.stdout.strip().split('\n') if line.strip()]
    # Find lines that look like file listings (not command prompts or status messages)
    all_files = []
    for line in lines:
        # Skip MEGA prompt lines and command echoes
        if line.startswith('MEGA>') or line.startswith('ls ') or 'bytes used' in line:
            continue
        if line and not line.startswith('[') and not line.startswith('Total'):  # Skip summary lines
            all_files.append(line)
    
    target_files = [f for f in all_files if QUALITY_TAG in f.lower() or f"_{QUALITY_TAG[:-1]}_" in f.lower()]
    
    if not target_files:
        print(f"❌ No {QUALITY_TAG} files found. Total files: {len(all_files)}", flush=True)
        return await message.reply(f"❌ No {QUALITY_TAG} files found.")

    status = await message.reply(f"🚀 **{QUALITY_TAG} Started** | Files: `{len(target_files)}`")

    # 7. Download and upload loop
    uploaded = 0
    for filename in target_files:
        print(f"⬇️ Downloading: {filename}", flush=True)
        local_path = os.path.join(os.getcwd(), filename)
        
        # Create download script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
            f.write(f'get "{mega_folder}/{filename}" "{local_path}"\n')
            f.write('exit\n')
            script_path = f.name
        
        download_cmd = f'{mega_cmd_path} -console < "{script_path}"'
        dl_result = subprocess.run(download_cmd, shell=True, capture_output=True, text=True)
        os.unlink(script_path)
        
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
    
    # Try Mega login with session token
    if not mega_login_with_session():
        print("⚠️ Mega login failed, but continuing...", flush=True)
    else:
        print("✅ Mega login successful!", flush=True)
    
    print("🤖 Starting Telegram Client...", flush=True)
    await app.start()
    
    # Get bot info to confirm it's running
    me = await app.get_me()
    print(f"✅ BOT IS RUNNING: @{me.username} (ID: {me.id})", flush=True)
    print("🎯 Listening for commands...", flush=True)
    
    # Send a test message to yourself (optional)
    # Replace YOUR_CHAT_ID with your actual Telegram ID
    # try:
    #     await app.send_message(YOUR_CHAT_ID, f"✅ {QUALITY_TAG} Bot started successfully!")
    # except:
    #     pass
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Bot stopped by user", flush=True)
    except Exception as e:
        print(f"💥 Unexpected error: {e}", flush=True)
        import traceback
        traceback.print_exc()
