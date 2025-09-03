import json
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === Your details ===
API_ID = 23006101
API_HASH = "289a7b9cc2ac4b82bff408d530021300"
BOT_TOKEN = "8447xxxxxx"   # hide token in real usage
ADMIN_ID = 7965760336
SOURCE_CHANNEL = -1002841190050

# === Storage file ===
STORAGE_FILE = "videos.json"

# === Client ===
app = Client("multi_video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Load saved videos ---
if os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "r") as f:
        data = json.load(f)
else:
    data = {"videos": {}, "targets": {}}

channel_videos = {int(k): set(v) for k, v in data.get("videos", {}).items()}
forward_target = {int(k): v for k, v in data.get("targets", {}).items()}

SOURCE_CHANNEL_ID = None   # will resolve dynamically


def save_data():
    """Save videos to file"""
    with open(STORAGE_FILE, "w") as f:
        json.dump({
            "videos": {k: list(v) for k, v in channel_videos.items()},
            "targets": forward_target
        }, f)


# --- /start ---
@app.on_message(filters.command("start") & filters.private & filters.user(ADMIN_ID))
async def start_cmd(client, message):
    await message.reply_text(
        "✅ Bot is running!\n\n"
        "Commands:\n"
        "• /scan – collect all old videos\n"
        "• /menu – show forwarding menu"
    )


# --- /menu ---
@app.on_message(filters.command("menu") & filters.private & filters.user(ADMIN_ID))
async def menu_cmd(client, message):
    await message.reply_text(
        "📋 Control Menu:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Select All", callback_data="select_all")],
            [InlineKeyboardButton("📤 Forward All", callback_data="forward")],
            [InlineKeyboardButton("🗑 Clear", callback_data="clear")]
        ])
    )


# --- Scan old videos ---
@app.on_message(filters.command("scan") & filters.private & filters.user(ADMIN_ID))
async def scan_cmd(client, message):
    global SOURCE_CHANNEL_ID
    channel_videos[ADMIN_ID] = set()

    try:
        chat = await client.get_chat(SOURCE_CHANNEL)
        SOURCE_CHANNEL_ID = chat.id
    except Exception as e:
        return await message.reply_text(
            f"❌ Could not access channel.\nError: {e}\n\n"
            "👉 Make sure bot is ADMIN in the channel."
        )

    status_msg = await message.reply_text(f"🔍 Scanning *{chat.title}* for old videos...")

    total = 0
    count = 0

    async for _ in client.get_chat_history(SOURCE_CHANNEL_ID):
        total += 1

    async for msg in client.get_chat_history(SOURCE_CHANNEL_ID):
        count += 1
        if msg.video:
            channel_videos[ADMIN_ID].add(msg.id)
            save_data()

        if count % 100 == 0 or count == total:
            percent = int((count / total) * 100)
            await status_msg.edit(
                f"🔍 Scanning {chat.title}...\n"
                f"{percent}% — Videos found: {len(channel_videos[ADMIN_ID])}\n"
                f"Checked: {count}/{total}"
            )

    await status_msg.edit(
        f"✅ Scan Complete!\n"
        f"Total Messages: {total}\n"
        f"Videos Found: {len(channel_videos[ADMIN_ID])}"
    )


# --- Collect new videos ---
@app.on_message(filters.video & filters.channel)
async def collect_new(client, message):
    global SOURCE_CHANNEL_ID
    if SOURCE_CHANNEL_ID is None:
        SOURCE_CHANNEL_ID = SOURCE_CHANNEL

    if message.chat.id != SOURCE_CHANNEL_ID:
        return

    if ADMIN_ID not in channel_videos:
        channel_videos[ADMIN_ID] = set()
    channel_videos[ADMIN_ID].add(message.id)
    save_data()

    await client.send_message(
        ADMIN_ID,
        f"🎥 New video stored. Total collected: {len(channel_videos[ADMIN_ID])}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Select All", callback_data="select_all")],
            [InlineKeyboardButton("📤 Forward All", callback_data="forward")],
            [InlineKeyboardButton("🗑 Clear", callback_data="clear")]
        ])
    )


# --- Handle buttons ---
@app.on_callback_query()
async def handle_callbacks(client, cq):
    uid = cq.from_user.id
    if uid != ADMIN_ID:
        return await cq.answer("Not authorized", show_alert=True)

    if uid not in channel_videos:
        channel_videos[uid] = set()

    if cq.data == "select_all":
        await cq.answer("✅ All videos selected")
        await cq.message.edit_text(
            "All videos are ready. Choose next action:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Forward All", callback_data="forward")],
                [InlineKeyboardButton("🗑 Clear", callback_data="clear")]
            ])
        )

    elif cq.data == "forward":
        if not channel_videos[uid]:
            return await cq.answer("No videos selected!", show_alert=True)
        forward_target[uid] = None
        save_data()
        await cq.message.edit_text("📌 Send me the @username or chat ID of the target channel/group (in private).")

    elif cq.data == "clear":
        channel_videos[uid] = set()
        save_data()
        await cq.message.edit_text("🗑 Selection cleared!")


# --- Forward videos ---
@app.on_message(filters.private & filters.text & filters.user(ADMIN_ID))
async def set_forward_target(client, message):
    uid = message.from_user.id
    global SOURCE_CHANNEL_ID

    if forward_target.get(uid) is None:
        target = message.text.strip()
        try:
            chat = await client.get_chat(target)
            forward_target[uid] = chat.id
        except:
            try:
                forward_target[uid] = int(target)
            except:
                return await message.reply_text("❌ Invalid target. Send @username or numeric ID.")
        save_data()

        total = len(channel_videos[uid])
        done = 0
        status = await message.reply_text(f"📤 Forwarding {total} videos...")

        for mid in list(channel_videos[uid]):
            try:
                await client.copy_message(
                    chat_id=forward_target[uid],
                    from_chat_id=SOURCE_CHANNEL_ID,
                    message_id=mid
                )
                done += 1
                if done % 10 == 0 or done == total:
                    await status.edit(f"⏩ Forwarding: {done}/{total}")
            except Exception as e:
                print("Error forwarding:", e)

        channel_videos[uid] = set()
        forward_target[uid] = None
        save_data()
        await status.edit("✅ All videos forwarded!")


print("🚀 Bot started. Use /start in private chat.")
app.run()
