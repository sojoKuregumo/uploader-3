import asyncio
import os
import subprocess
import threading
import sys
import tempfile
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

# Get MEGA session token from environment (you added this in Render dashboard)
MEGA_SESSION_TOKEN = os.environ.get("MEGA_SESSION_TOKEN", "").strip()

if not MEGA_SESSION_TOKEN:
    print("⚠️ WARNING: MEGA_SESSION_TOKEN not found in environment!", flush=True)
    print("⚠️ MEGA uploads will fail. Please set MEGA_SESSION_TOKEN in Render environment variables.", flush=True)

MEGA_ROOT = "/Root/AnimeDownloads"

def mega_login_with_session():
    """
    Login to MEGA using session token
    """
    if not MEGA_SESSION_TOKEN:
        print("❌ Cannot login: No MEGA session token provided", flush=True)
        return False
    
    print("🔑 Attempting Mega Login with Session Token...", flush=True)
    
    try:
        # Find mega-cmd binary
        mega_cmd_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
        
        if not os.path.exists(mega_cmd_path):
            print(f"❌ mega-cmd not found at: {mega_cmd_path}", flush=True)
            return False
        
        # Create a temporary script with MEGA commands
        with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
            # Use the session command to login
            f.write(f'session {MEGA_SESSION_TOKEN}\n')
            f.write('whoami\n')  # Check if login worked
            f.write('exit\n')
            script_path = f.name
        
        # Execute the script
        cmd = f'{mega_cmd_path} -console < "{script_path}"'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Clean up
        os.unlink(script_path)
        
        # Check result
        output = proc.stdout.lower()
        if "welcome" in output or "login successful" in output or "already logged in" in output:
            print("✅ Mega Login Successful with Session Token!", flush=True)
            
            # Verify by checking whoami
            verify_cmd = f'echo "whoami" | {mega_cmd_path} -console'
            verify = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            if "not logged in" not in verify.stdout.lower():
                username_line = [line for line in verify.stdout.split('\n') if 'email' in line.lower() or '@' in line]
                if username_line:
                    print(f"✅ Logged in as: {username_line[0].strip()}", flush=True)
                return True
            else:
                print(f"⚠️ Login seemed successful but verification failed", flush=True)
                return False
        else:
            print(f"❌ Session Login Failed. Output: {proc.stdout[:500]}", flush=True)
            print(f"❌ Error: {proc.stderr[:500]}", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ Exception during Mega Session Login: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

# Check Telegram environment variables
print("🔍 Checking Telegram environment variables...", flush=True)
api_id = os.environ.get("UPLOADER_API_ID")
api_hash = os.environ.get("UPLOADER_API_HASH")
bot_token = os.environ.get("UPLOADER_BOT_TOKEN")

if not all([api_id, api_hash, bot_token]):
    print("❌ Missing Telegram environment variables!", flush=True)
    print(f"API_ID: {'✅' if api_id else '❌'}")
    print(f"API_HASH: {'✅' if api_hash else '❌'}")
    print(f"BOT_TOKEN: {'✅' if bot_token else '❌'}")
    sys.exit(1)

print("✅ Telegram environment variables found!", flush=True)

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
    
    if "not logged in" in proc.stdout.lower():
        await message.reply("❌ MEGA: Not logged in")
    else:
        # Extract email from output
        email_line = [line for line in proc.stdout.split('\n') if '@' in line]
        if email_line:
            await message.reply(f"✅ MEGA: Logged in as {email_line[0].strip()}")
        else:
            await message.reply(f"✅ MEGA: Logged in\n```{proc.stdout[:200]}```")

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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
        f.write(f'ls "{mega_folder}"\n')
        f.write('exit\n')
        script_path = f.name
    
    list_cmd = f'{mega_cmd_path} -console < "{script_path}"'
    res = subprocess.run(list_cmd, shell=True, capture_output=True, text=True)
    os.unlink(script_path)
    
    # Check for errors
    if "error" in res.stdout.lower() or "not found" in res.stdout.lower() or res.returncode != 0:
        print(f"❌ Mega LS Failed: {res.stdout[:500]}", flush=True)
        return await message.reply(f"❌ Mega Error: Folder `{folder_name}` not found or access denied.")
    
    # 6. Extract file names from output
    lines = res.stdout.split('\n')
    all_files = []
    
    for line in lines:
        line = line.strip()
        # Skip empty lines and command prompts
        if not line or line.startswith('MEGA>') or line.startswith('ls ') or 'bytes used' in line.lower():
            continue
        # Skip summary lines
        if line.startswith('[') or line.startswith('Total ') or 'folder' in line.lower() and 'file' in line.lower():
            continue
        # This should be a file name
        if line:
            all_files.append(line)
    
    # 7. Filter files by quality
    target_files = [f for f in all_files if QUALITY_TAG in f.lower() or f"_{QUALITY_TAG[:-1]}_" in f.lower()]
    
    if not target_files:
        print(f"❌ No {QUALITY_TAG} files found. Total files in folder: {len(all_files)}", flush=True)
        return await message.reply(f"❌ No {QUALITY_TAG} files found in `{folder_name}`.")

    status = await message.reply(f"🚀 **{QUALITY_TAG} Upload Started**\nFiles: `{len(target_files)}`")

    # 8. Download and upload loop
    uploaded = 0
    failed = 0
    
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
                print(f"❌ Telegram Upload Fail for {filename}: {e}", flush=True)
                failed += 1
            finally:
                try:
                    os.remove(local_path)
                except:
                    pass
        else:
            print(f"❌ Download failed for: {filename}", flush=True)
            failed += 1
    
    result_text = f"✅ **{QUALITY_TAG} Upload Complete**\n"
    result_text += f"• Success: `{uploaded}`\n"
    result_text += f"• Failed: `{failed}`\n"
    result_text += f"• Total: `{len(target_files)}`"
    
    await status.edit_text(result_text)

async def main():
    print("🚀 Starting services...", flush=True)
    
    # Start Flask in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask thread started", flush=True)
    
    # Try Mega login with session token
    if MEGA_SESSION_TOKEN:
        if mega_login_with_session():
            print("✅ Mega login successful!", flush=True)
        else:
            print("⚠️ Mega login failed", flush=True)
    else:
        print("⚠️ Skipping Mega login (no session token)", flush=True)
    
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
        import traceback
        traceback.print_exc()
