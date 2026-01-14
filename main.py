# --- main.py for 360p Branch ---
QUALITY_TAG = "360p"
# ... (Keep Imports and Flask Server from 1080p script) ...

@app.on_message(filters.command(["upload", "fastupload"]))
async def fast_upload_360(client, message):
    cmd_text = message.text.lower()
    
    # React only to -all or -360
    if "-all" not in cmd_text and "-360" not in cmd_text:
        return

    # Longer delay for sequence 
    await asyncio.sleep(40) 

    # ... (Folder extraction logic) ...

    # FILTER: Only keep 360p files [cite: 102]
    target_files = [f for f in all_files if "360p" in f.lower() or "_360_" in f]
    
    if not target_files:
        return await message.reply(f"❌ No 360p files found in `{folder_name}`")

    # ... (Upload logic from 1080p script) ...
