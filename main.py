import asyncio
import os
import subprocess
import threading
import sys
import tempfile
import json
from datetime import datetime
from flask import Flask, request, jsonify
from pyrogram import Client, filters, types

print("🟢 SCRIPT STARTED - INITIALIZING...", flush=True)

# --- FLASK APP for Webhooks ---
web_app = Flask(__name__)

# --- CONFIG ---
QUALITY_TAG = "1080p"  # Change this for 720p / 360p
SLEEP_TIME = 0

# Get credentials from environment
MEGA_SESSION_TOKEN = os.environ.get("MEGA_SESSION_TOKEN", "").strip()
API_ID = os.environ.get("UPLOADER_API_ID")
API_HASH = os.environ.get("UPLOADER_API_HASH")
BOT_TOKEN = os.environ.get("UPLOADER_BOT_TOKEN")

# Check environment variables
print("🔍 Checking environment variables...", flush=True)
print(f"API_ID: {'✅' if API_ID else '❌'}", flush=True)
print(f"API_HASH: {'✅' if API_HASH else '❌'}", flush=True)
print(f"BOT_TOKEN: {'✅' if BOT_TOKEN else '❌'}", flush=True)
print(f"MEGA_SESSION_TOKEN: {'✅' if MEGA_SESSION_TOKEN else '❌'}", flush=True)

if not all([API_ID, API_HASH, BOT_TOKEN]):
    print("❌ Missing required environment variables!", flush=True)
    sys.exit(1)

MEGA_ROOT = "/Root/AnimeDownloads"

# Initialize Pyrogram client
app = Client(
    f"uploader_{QUALITY_TAG}_webhook",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
    no_updates=True  # We'll handle updates via webhook
)

# Global variable to track if bot is ready
bot_ready = False

def mega_login_with_session():
    """Login to MEGA using session token"""
    if not MEGA_SESSION_TOKEN:
        print("❌ No MEGA session token provided", flush=True)
        return False
    
    print("🔑 Attempting Mega Login with Session Token...", flush=True)
    
    try:
        mega_cmd_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
        
        if not os.path.exists(mega_cmd_path):
            print(f"❌ mega-cmd not found at: {mega_cmd_path}", flush=True)
            return False
        
        # Create script with session token
        with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
            f.write(f'session {MEGA_SESSION_TOKEN}\n')
            f.write('whoami\n')
            f.write('exit\n')
            script_path = f.name
        
        cmd = f'{mega_cmd_path} -console < "{script_path}"'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        os.unlink(script_path)
        
        output = proc.stdout.lower()
        if "welcome" in output or "login successful" in output:
            print("✅ Mega Login Successful!", flush=True)
            return True
        else:
            print(f"❌ Mega Login Failed: {proc.stdout[:500]}", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ Exception during Mega Login: {e}", flush=True)
        return False

# --- Flask Routes ---
@web_app.route('/')
def health_check():
    return jsonify({
        "status": "alive",
        "bot": "ready" if bot_ready else "starting",
        "quality": QUALITY_TAG,
        "time": datetime.now().isoformat()
    })

@web_app.route('/webhook', methods=['POST'])
async def webhook_handler():
    """Handle Telegram webhook updates"""
    try:
        update = types.Update(**request.json)
        
        if update.message and update.message.text:
            message = update.message
            text = message.text.lower()
            chat_id = message.chat.id
            
            print(f"📨 Message from {chat_id}: {text[:100]}", flush=True)
            
            # Handle /ping
            if text.startswith('/ping'):
                await app.send_message(chat_id, f"✅ {QUALITY_TAG} Bot is ONLINE!\nChat ID: `{chat_id}`")
                return jsonify({"status": "processed"})
            
            # Handle /chatid
            elif text.startswith('/chatid'):
                await app.send_message(chat_id, f"📱 Chat ID: `{chat_id}`")
                return jsonify({"status": "processed"})
            
            # Handle /upload
            elif text.startswith('/upload') or text.startswith('/fastupload'):
                # Process upload in background thread
                threading.Thread(
                    target=process_upload,
                    args=(chat_id, text, message.message_id)
                ).start()
                return jsonify({"status": "processing"})
        
        return jsonify({"status": "ignored"})
    
    except Exception as e:
        print(f"❌ Webhook error: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

def process_upload(chat_id, text, message_id):
    """Process upload command in a separate thread"""
    asyncio.run(_process_upload(chat_id, text, message_id))

async def _process_upload(chat_id, text, message_id):
    """Actual upload processing"""
    try:
        cmd_text = text.lower()
        
        # 1. Filter by quality
        if "-all" not in cmd_text and f"-{QUALITY_TAG[:-1]}" not in cmd_text:
            return
        
        # 2. Parse folder name
        parts = text.split()
        folder_name = next((p.strip('"\'').strip() for p in parts[1:] if not p.startswith('-')), None)
        
        if not folder_name:
            await app.send_message(chat_id, "❌ Usage: `/upload FolderName -all`")
            return
        
        # 3. Delay if needed
        if SLEEP_TIME > 0:
            await app.send_message(chat_id, f"⏳ {QUALITY_TAG} Waiting {SLEEP_TIME}s...")
            await asyncio.sleep(SLEEP_TIME)
        
        # 4. Check MEGA
        mega_cmd_path = os.path.join(os.getcwd(), "mega_local", "usr", "bin", "mega-cmd")
        if not os.path.exists(mega_cmd_path):
            await app.send_message(chat_id, "❌ MEGA-CMD not installed")
            return
        
        mega_folder = f"{MEGA_ROOT}/{folder_name}"
        
        # Create list script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
            f.write(f'ls "{mega_folder}"\n')
            f.write('exit\n')
            script_path = f.name
        
        list_cmd = f'{mega_cmd_path} -console < "{script_path}"'
        res = subprocess.run(list_cmd, shell=True, capture_output=True, text=True)
        os.unlink(script_path)
        
        if "error" in res.stdout.lower():
            await app.send_message(chat_id, f"❌ Folder `{folder_name}` not found")
            return
        
        # Extract files
        lines = [line.strip() for line in res.stdout.split('\n') if line.strip()]
        all_files = [line for line in lines if not line.startswith('MEGA>') and not line.startswith('ls ') 
                    and 'bytes used' not in line.lower() and not line.startswith('[')]
        
        target_files = [f for f in all_files if QUALITY_TAG in f.lower() or f"_{QUALITY_TAG[:-1]}_" in f.lower()]
        
        if not target_files:
            await app.send_message(chat_id, f"❌ No {QUALITY_TAG} files found")
            return
        
        status = await app.send_message(chat_id, f"🚀 **{QUALITY_TAG} Started**\nFiles: `{len(target_files)}`")
        
        # Download and upload
        uploaded = 0
        for filename in target_files:
            local_path = os.path.join(os.getcwd(), filename)
            
            # Download
            with tempfile.NamedTemporaryFile(mode='w', suffix='.megascript', delete=False) as f:
                f.write(f'get "{mega_folder}/{filename}" "{local_path}"\n')
                f.write('exit\n')
                script_path = f.name
            
            download_cmd = f'{mega_cmd_path} -console < "{script_path}"'
            subprocess.run(download_cmd, shell=True, capture_output=True, text=True)
            os.unlink(script_path)
            
            if os.path.exists(local_path):
                try:
                    await app.send_document(
                        chat_id=chat_id,
                        document=local_path,
                        force_document=True,
                        caption=filename
                    )
                    uploaded += 1
                finally:
                    try:
                        os.remove(local_path)
                    except:
                        pass
        
        await status.edit_text(f"✅ **{QUALITY_TAG} Done.**\nUploaded: `{uploaded}/{len(target_files)}`")
        
    except Exception as e:
        print(f"❌ Upload error: {e}", flush=True)
        try:
            await app.send_message(chat_id, f"❌ Upload failed: {str(e)[:200]}")
        except:
            pass

async def setup_bot():
    """Initialize the bot and set webhook"""
    global bot_ready
    
    print("🤖 Starting Telegram Client...", flush=True)
    await app.start()
    
    # Get bot info
    me = await app.get_me()
    print(f"✅ BOT CONNECTED: @{me.username} (ID: {me.id})", flush=True)
    
    # Set webhook
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        # Try to get from other env vars
        render_url = f"https://{os.environ.get('RENDER_SERVICE_NAME')}.onrender.com"
    
    if render_url:
        webhook_url = f"{render_url}/webhook"
        print(f"🔗 Setting webhook to: {webhook_url}", flush=True)
        
        try:
            # Remove any existing webhook first
            await app.delete_webhook()
            
            # Set new webhook
            result = await app.set_webhook(
                webhook_url,
                max_connections=40,
                allowed_updates=["message"]
            )
            
            if result:
                print("✅ Webhook set successfully!", flush=True)
                
                # Send test message
                try:
                    await app.send_message("me", f"✅ {QUALITY_TAG} Bot started!\nWebhook: {webhook_url}")
                    print("✅ Test message sent", flush=True)
                except:
                    print("⚠️ Could not send test message", flush=True)
            else:
                print("❌ Failed to set webhook", flush=True)
        except Exception as e:
            print(f"❌ Webhook error: {e}", flush=True)
    else:
        print("⚠️ No RENDER_EXTERNAL_URL found, using polling fallback", flush=True)
        # Fallback to polling (won't work well on Render)
    
    # MEGA login
    if MEGA_SESSION_TOKEN:
        if mega_login_with_session():
            print("✅ MEGA login successful", flush=True)
        else:
            print("⚠️ MEGA login failed", flush=True)
    
    bot_ready = True
    print("🎯 Bot is ready and listening via webhook!", flush=True)

def start_flask():
    """Start Flask server"""
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Starting Flask on port {port}", flush=True)
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def main():
    """Main entry point"""
    
    # Start bot setup in background
    print("🚀 Starting setup...", flush=True)
    
    # Run bot setup in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run setup
    loop.run_until_complete(setup_bot())
    
    # Start Flask (this will block)
    start_flask()

if __name__ == "__main__":
    main()
