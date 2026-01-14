# --- main.py for 720p Branch ---
QUALITY_TAG = "720p"
# ... (Keep Imports and Flask Server from 1080p script) ...

@app.on_message(filters.command(["upload", "fastupload"]))
async def fast_upload_720(client, message):
    cmd_text = message.text.lower()
    
    # React only to -all or -720
    if "-all" not in cmd_text and "-720" not in cmd_text:
        return

    # Staggered start to avoid MegaCMD conflicts
    await asyncio.sleep(20) 

    # ... (Folder extraction logic) ...

    # FILTER: Only keep 720p files [cite: 102]
    target_files = [f for f in all_files if "720p" in f.lower() or "_720_" in f]
    
    if not target_files:
        return await message.reply(f"❌ No 720p files found in `{folder_name}`")

    # ... (Upload logic from 1080p script) ...
