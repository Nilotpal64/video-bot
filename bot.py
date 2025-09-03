import asyncio
import sqlite3
from datetime import datetime, timedelta
from telebot import TeleBot, types
import threading
import time
import random
import os

# Bot configuration
BOT_TOKEN = "8397252795:AAGjwoDfF0SYyDWHmeHQbx64kPlxQIg4TjU"
ADMIN_ID = 7965760336
ADMIN_USERNAME = "@Premium2090"  # Only show this to users

# Point packages with prices
POINT_PACKAGES = {
    10: 5,   # 10 points for 5 Rs
    20: 10,  # 20 points for 10 Rs
    30: 15,  # 30 points for 15 Rs
    50: 25   # 50 points for 25 Rs
}

# QR Code configuration - update this path to your actual QR code image
QR_CODE_PATH = "payment_qr.jpg"  # Change this to your QR code file path

# Initialize bot
bot = TeleBot(BOT_TOKEN)

# Database setup
def init_db():
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    # Create videos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        caption TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP,
        points INTEGER DEFAULT 2,
        last_reset_date DATE DEFAULT CURRENT_DATE
    )
    ''')
    
    # Create video_access table for tracking views
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_access (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        video_id INTEGER NOT NULL,
        access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (video_id) REFERENCES videos (id)
    )
    ''')
    
    # Create purchases table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        points INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Function to reset daily points
def reset_daily_points():
    while True:
        now = datetime.now()
        # Calculate time until next midnight
        next_day = now + timedelta(days=1)
        midnight = datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0)
        seconds_until_midnight = (midnight - now).total_seconds()
        
        # Sleep until midnight
        time.sleep(seconds_until_midnight)
        
        # Reset points for all users
        conn = sqlite3.connect('video_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET points = 2 WHERE points < 2')
        conn.commit()
        conn.close()
        
        print("Daily points reset for all users")

# Start the daily reset thread
reset_thread = threading.Thread(target=reset_daily_points, daemon=True)
reset_thread.start()

# Store video in database
def store_video(file_id, user_id, caption=None):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO videos (file_id, user_id, caption)
    VALUES (?, ?, ?)
    ''', (file_id, user_id, caption))
    
    video_id = cursor.lastrowid
    
    # Update or insert user info
    user = bot.get_chat(user_id)
    cursor.execute('''
    INSERT OR REPLACE INTO users (id, username, first_name, last_name, last_interaction)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, user.username, user.first_name, user.last_name))
    
    conn.commit()
    conn.close()
    return video_id

# Delete video from database
def delete_video(video_id):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    # First delete access records
    cursor.execute('DELETE FROM video_access WHERE video_id = ?', (video_id,))
    
    # Then delete the video
    cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
    
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

# Get user points
def get_user_points(user_id):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else 0

# Update user points
def update_user_points(user_id, points):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET points = ? WHERE id = ?', (points, user_id))
    
    conn.commit()
    conn.close()

# Record video access
def record_video_access(user_id, video_id):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO video_access (user_id, video_id)
    VALUES (?, ?)
    ''', (user_id, video_id))
    
    conn.commit()
    conn.close()

# Get random video
def get_random_video(exclude_ids=[]):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    if exclude_ids:
        placeholders = ','.join('?' * len(exclude_ids))
        query = f'SELECT id, file_id, caption FROM videos WHERE id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT 1'
        cursor.execute(query, exclude_ids)
    else:
        cursor.execute('SELECT id, file_id, caption FROM videos ORDER BY RANDOM() LIMIT 1')
    
    video = cursor.fetchone()
    
    conn.close()
    return video

# Get all videos from database
def get_all_videos():
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, file_id, caption, user_id FROM videos ORDER BY timestamp DESC')
    videos = cursor.fetchall()
    
    conn.close()
    return videos

# Get video by ID
def get_video_by_id(video_id):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, file_id, caption, user_id FROM videos WHERE id = ?', (video_id,))
    video = cursor.fetchone()
    
    conn.close()
    return video

# Get user info
def get_user_info(user_id):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user

# Get all users
def get_all_users():
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users ORDER BY last_interaction DESC')
    users = cursor.fetchall()
    
    conn.close()
    return users

# Get stats
def get_stats():
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM videos')
    video_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM video_access')
    access_count = cursor.fetchone()[0]
    
    conn.close()
    return video_count, user_count, access_count

# Record purchase
def record_purchase(user_id, points, amount):
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO purchases (user_id, points, amount)
    VALUES (?, ?, ?)
    ''', (user_id, points, amount))
    
    purchase_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return purchase_id

# Create main menu markup
def create_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    watch_btn = types.KeyboardButton("🎥 Watch Video")
    points_btn = types.KeyboardButton("📊 My Points")
    upload_btn = types.KeyboardButton("📤 Upload Video")
    contact_btn = types.KeyboardButton("📞 Contact Admin")
    buy_btn = types.KeyboardButton("💳 Buy Points")
    
    # Add admin button if user is admin
    if user_id == ADMIN_ID:
        admin_btn = types.KeyboardButton("🛠️ Admin Panel")
        markup.add(watch_btn, points_btn, upload_btn, contact_btn, buy_btn, admin_btn)
    else:
        markup.add(watch_btn, points_btn, upload_btn, contact_btn, buy_btn)
    
    return markup

# Create buy points markup
def create_buy_points_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for points, price in POINT_PACKAGES.items():
        btn = types.InlineKeyboardButton(f"{points} points - ₹{price}", callback_data=f"buy_{points}")
        markup.add(btn)
    
    cancel_btn = types.InlineKeyboardButton("❌ Cancel", callback_data="buy_cancel")
    markup.add(cancel_btn)
    
    return markup

# Start command handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Initialize user with 2 points if not exists
    points = get_user_points(user_id)
    
    welcome_text = f"""
    🎬 *Welcome to Video Hub!* 🎬

    👋 Hello {user_name}!

    🌟 *What we offer:*
    - Store your videos securely
    - Discover amazing content from others
    - Simple and easy to use

    📌 *How to use:*
    - Tap 'Upload Video' to share your videos
    - Tap 'Watch Video' to enjoy content (uses 1 point)
    - You have *{points} points* remaining today
    - Points reset daily at midnight

    🔄 Use 'My Points' to check your balance
    💳 Use 'Buy Points' to get more points
    📞 Contact admin for more points or help

    🚀 *Get started by tapping a button below!*
    """
    
    bot.send_message(message.chat.id, welcome_text, 
                    reply_markup=create_main_menu(user_id),
                    parse_mode="Markdown")

# Points command handler
@bot.message_handler(commands=['points'])
def show_points(message):
    user_id = message.from_user.id
    points = get_user_points(user_id)
    
    points_text = f"""
    📊 *Your Points Status*
    
    🎯 Points available today: *{points}*
    
    You can watch *{points}* more videos today.
    
    🔄 Points reset daily at midnight.
    
    💳 Tap 'Buy Points' below to get more points!
    """
    
    # Add buy button if points are low
    markup = types.InlineKeyboardMarkup()
    if points < 5:
        buy_btn = types.InlineKeyboardButton("💳 Buy More Points", callback_data="buy_points")
        markup.add(buy_btn)
    
    bot.send_message(message.chat.id, points_text, 
                    reply_markup=markup, parse_mode="Markdown")

# Watch command handler
@bot.message_handler(commands=['watch'])
def watch_video(message):
    send_random_video(message)

# Function to send random video
def send_random_video(message):
    user_id = message.from_user.id
    points = get_user_points(user_id)
    
    if points <= 0:
        # Create inline keyboard with buy button
        markup = types.InlineKeyboardMarkup()
        buy_btn = types.InlineKeyboardButton("💳 Buy Points", callback_data="buy_points")
        markup.add(buy_btn)
        
        bot.send_message(message.chat.id, 
                        f"❌ *You're out of points for today!*\n\nPoints reset at midnight.\n\n💳 Tap the button below to buy more points.", 
                        reply_markup=markup,
                        parse_mode="Markdown")
        return
    
    # Get user's recently watched videos to exclude
    conn = sqlite3.connect('video_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT video_id FROM video_access WHERE user_id = ? AND access_time > datetime("now", "-1 hour")', (user_id,))
    recent_videos = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Get a random video excluding recently watched ones
    video = get_random_video(recent_videos)
    
    if not video:
        bot.send_message(message.chat.id, "❌ No videos available to watch at the moment. Check back later!")
        return
    
    video_id, file_id, caption = video
    cap_text = f"\n\n📝 *Caption:* {caption}" if caption else ""
    
    # Send the video with a custom keyboard and prevent forwarding
    markup = types.InlineKeyboardMarkup()
    next_btn = types.InlineKeyboardButton("➡️ Next Video", callback_data=f"next_video_{user_id}")
    markup.add(next_btn)
    
    msg = bot.send_video(message.chat.id, file_id, 
                        caption=f"🎥 *Here's your video!*{cap_text}\n\n_This video will disappear in 5 minutes._",
                        reply_markup=markup, parse_mode="Markdown",
                        protect_content=True)  # This prevents forwarding
    
    # Deduct point
    update_user_points(user_id, points - 1)
    record_video_access(user_id, video_id)
    
    # Schedule deletion after 5 minutes
    threading.Timer(300, delete_message, args=[message.chat.id, msg.message_id]).start()
    
    # Show remaining points
    remaining = get_user_points(user_id)
    bot.send_message(message.chat.id, f"✅ *Video sent!* You have *{remaining}* points remaining today.", parse_mode="Markdown")

# Handle text messages
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_messages(message):
    user_id = message.from_user.id
    text = message.text
    
    if text == "🎥 Watch Video":
        send_random_video(message)
    elif text == "📊 My Points":
        show_points(message)
    elif text == "📤 Upload Video":
        bot.send_message(message.chat.id, "📤 Simply send me a video file and I'll store it for you!")
    elif text == "📞 Contact Admin":
        bot.send_message(message.chat.id, f"📞 Contact {ADMIN_USERNAME} for support, more points, or any questions!")
    elif text == "💳 Buy Points":
        show_buy_points(message)
    elif text == "🛠️ Admin Panel" and user_id == ADMIN_ID:
        admin_panel(message)
    else:
        bot.send_message(message.chat.id, "Please use the buttons below to interact with me!", 
                        reply_markup=create_main_menu(user_id))

# Show buy points options
def show_buy_points(message):
    user_id = message.from_user.id
    points = get_user_points(user_id)
    
    buy_text = f"""
    💰 *Buy More Points*
    
    Your current points: *{points}*
    
    Select a package below to get more points:
    """
    
    # Create package buttons
    markup = create_buy_points_markup()
    
    bot.send_message(message.chat.id, buy_text, 
                    reply_markup=markup, parse_mode="Markdown")

# Function to delete message
def delete_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"Error deleting message: {e}")

# Admin command handler
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.reply_to(message, "⛔ Access denied. You are not authorized to use this command.")
        return
    
    # Create admin keyboard with back button
    markup = create_admin_markup()
    
    bot.send_message(message.chat.id, "🛠️ *Admin Panel*", reply_markup=markup, parse_mode="Markdown")

# Create admin markup with back button
def create_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    stats_btn = types.InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
    users_btn = types.InlineKeyboardButton("👥 Users", callback_data="admin_users")
    videos_btn = types.InlineKeyboardButton("🎥 All Videos", callback_data="admin_videos")
    add_points_btn = types.InlineKeyboardButton("➕ Add Points", callback_data="admin_add_points")
    delete_videos_btn = types.InlineKeyboardButton("🗑️ Delete Videos", callback_data="admin_delete_videos")
    markup.add(stats_btn, users_btn, videos_btn, add_points_btn, delete_videos_btn)
    return markup

# Callback query handler for admin panel, next video button, and buy points
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_actions(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data.startswith("next_video_"):
        # Handle next video request
        requested_user_id = int(call.data.split("_")[2])
        
        # Verify the user who clicked is the same as the one who requested
        if user_id != requested_user_id:
            bot.answer_callback_query(call.id, "This button is not for you!")
            return
            
        # Check if user has points
        points = get_user_points(user_id)
        if points <= 0:
            bot.answer_callback_query(call.id, "You're out of points for today!")
            return
            
        # Delete the previous video message
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
            
        # Send a new random video
        message = type('Message', (object,), {
            'chat': type('Chat', (object,), {'id': chat_id}),
            'from_user': type('User', (object,), {'id': user_id})
        })()
        send_random_video(message)
        bot.answer_callback_query(call.id)
    
    elif call.data == "buy_points":
        # Show buy points options
        show_buy_points(call.message)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("buy_"):
        if call.data == "buy_cancel":
            bot.delete_message(chat_id, message_id)
            bot.answer_callback_query(call.id, "Purchase cancelled")
            return
        
        # Handle point purchase selection
        points = int(call.data.split("_")[1])
        price = POINT_PACKAGES[points]
        
        # Record the purchase
        purchase_id = record_purchase(user_id, points, price)
        
        # Create payment instructions with QR code
        payment_text = f"""
        💰 *Point Purchase - {points} points*
        
        You've selected {points} points for ₹{price}.
        
        *Payment Instructions:*
        1. Send ₹{price} to our payment address
        2. Contact {ADMIN_USERNAME} with your payment proof
        3. Include this ID: #{purchase_id}
        4. Admin will add your points after verification
        
        Click the button below to contact admin now:
        """
        
        # Create contact button
        markup = types.InlineKeyboardMarkup()
        contact_btn = types.InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME[1:]}")
        done_btn = types.InlineKeyboardButton("✅ I've Paid", callback_data=f"paid_{purchase_id}")
        markup.add(contact_btn, done_btn)
        
        # Try to send QR code if it exists
        try:
            if os.path.exists(QR_CODE_PATH):
                with open(QR_CODE_PATH, 'rb') as qr_code:
                    # Add QR code info to caption
                    payment_text_with_qr = payment_text + "\n\n📱 Scan the QR code below to pay:"
                    bot.send_photo(chat_id, qr_code, caption=payment_text_with_qr, reply_markup=markup, parse_mode="Markdown")
            else:
                # If QR code doesn't exist, send text only
                bot.send_message(chat_id, payment_text, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            print(f"Error sending payment info: {e}")
            # Fallback to text message if there's any error
            bot.send_message(chat_id, payment_text, reply_markup=markup, parse_mode="Markdown")
        
        # Delete the package selection message
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("paid_"):
        # User claims they've paid
        purchase_id = int(call.data.split("_")[1])
        
        # Notify admin
        admin_text = f"""
        ⚠️ *Payment Claim*
        
        User #{user_id} claims they've paid for purchase #{purchase_id}.
        
        Please verify payment and add points if confirmed.
        """
        
        # Create admin buttons
        markup = types.InlineKeyboardMarkup()
        verify_btn = types.InlineKeyboardButton("✅ Verify Payment", callback_data=f"verify_{purchase_id}")
        reject_btn = types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{purchase_id}")
        markup.add(verify_btn, reject_btn)
        
        try:
            bot.send_message(ADMIN_ID, admin_text, reply_markup=markup, parse_mode="Markdown")
        except:
            pass
        
        # Notify user
        bot.answer_callback_query(call.id, "Admin notified. Please wait for verification.")
        
        # Update message
        try:
            bot.edit_message_caption(chat_id=chat_id, message_id=message_id, 
                                   caption="✅ Admin notified of your payment. Please wait for verification.",
                                   reply_markup=None)
        except:
            try:
                bot.edit_message_text("✅ Admin notified of your payment. Please wait for verification.", 
                                     chat_id, message_id)
            except:
                pass
    
    elif call.data.startswith("verify_"):
        # Admin verifies payment
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ Access denied.")
            return
        
        purchase_id = int(call.data.split("_")[1])
        
        # Get purchase details
        conn = sqlite3.connect('video_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, points FROM purchases WHERE id = ?', (purchase_id,))
        purchase = cursor.fetchone()
        
        if not purchase:
            bot.answer_callback_query(call.id, "Purchase not found.")
            return
        
        purchase_user_id, points = purchase
        
        # Add points to user
        current_points = get_user_points(purchase_user_id)
        update_user_points(purchase_user_id, current_points + points)
        
        # Update purchase status
        cursor.execute('UPDATE purchases SET status = "completed" WHERE id = ?', (purchase_id,))
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            bot.send_message(purchase_user_id, f"✅ Payment verified! {points} points have been added to your account.")
        except:
            pass
        
        # Notify admin
        bot.answer_callback_query(call.id, f"✅ {points} points added to user #{purchase_user_id}")
        
        # Update admin message
        bot.edit_message_text(f"✅ Payment verified for purchase #{purchase_id}. {points} points added to user #{purchase_user_id}.", 
                             chat_id, message_id)
    
    elif call.data.startswith("reject_"):
        # Admin rejects payment
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ Access denied.")
            return
        
        purchase_id = int(call.data.split("_")[1])
        
        # Update purchase status
        conn = sqlite3.connect('video_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE purchases SET status = "rejected" WHERE id = ?', (purchase_id,))
        conn.commit()
        conn.close()
        
        # Notify admin
        bot.answer_callback_query(call.id, "Purchase rejected.")
        
        # Update admin message
        bot.edit_message_text(f"❌ Purchase #{purchase_id} rejected.", 
                             chat_id, message_id)
    
    elif user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Access denied.")
        return
        
    elif call.data == "admin_stats":
        video_count, user_count, access_count = get_stats()
        stats_text = f"""
        📊 *Bot Statistics*
        
        📹 Stored Videos: {video_count}
        👥 Total Users: {user_count}
        👀 Total Views: {access_count}
        """
        
        # Create markup with back button
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton("⬅️ Back", callback_data="admin_back")
        markup.add(back_btn)
        
        bot.edit_message_text(stats_text, chat_id, message_id, 
                             reply_markup=markup, parse_mode="Markdown")
    
    elif call.data == "admin_users":
        users = get_all_users()
        users_text = f"👥 *Registered Users: {len(users)}*\n\n"
        
        for user in users[:10]:  # Show first 10 users
            user_id, username, first_name, last_name, last_interaction, points, last_reset = user
            username = f"@{username}" if username else "No username"
            last_interaction = datetime.strptime(last_interaction, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
            users_text += f"• {first_name} {last_name or ''} ({username}) - Points: {points} - Last active: {last_interaction}\n"
        
        if len(users) > 10:
            users_text += f"\n...and {len(users) - 10} more users."
        
        # Create markup with back button
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton("⬅️ Back", callback_data="admin_back")
        markup.add(back_btn)
        
        bot.edit_message_text(users_text, chat_id, message_id, 
                             reply_markup=markup, parse_mode="Markdown")
    
    elif call.data == "admin_videos":
        videos = get_all_videos()
        videos_text = f"🎥 *All Stored Videos: {len(videos)}*\n\n"
        
        for video in videos[:5]:  # Show first 5 videos
            video_id, file_id, caption, uploader_id = video
            cap_text = f"Caption: {caption}" if caption else "No caption"
            videos_text += f"• Video #{video_id}: {cap_text} (Uploader: {uploader_id})\n"
        
        if len(videos) > 5:
            videos_text += f"\n...and {len(videos) - 5} more videos."
        
        # Create markup with back button
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton("⬅️ Back", callback_data="admin_back")
        markup.add(back_btn)
        
        bot.edit_message_text(videos_text, chat_id, message_id, 
                             reply_markup=markup, parse_mode="Markdown")
    
    elif call.data == "admin_add_points":
        # Ask for user ID
        msg = bot.send_message(chat_id, "Please send the user ID to add points to:")
        bot.register_next_step_handler(msg, process_add_points_user)
    
    elif call.data == "admin_delete_videos":
        videos = get_all_videos()
        
        if not videos:
            bot.answer_callback_query(call.id, "No videos to delete.")
            return
        
        # Create a list of videos with delete buttons
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for video in videos[:10]:  # Show first 10 videos
            video_id, file_id, caption, uploader_id = video
            cap_text = f" - {caption}" if caption else ""
            btn = types.InlineKeyboardButton(f"Delete #{video_id}{cap_text}", callback_data=f"delete_vid_{video_id}")
            markup.add(btn)
        
        # Add back button
        back_btn = types.InlineKeyboardButton("⬅️ Back", callback_data="admin_back")
        markup.add(back_btn)
        
        bot.edit_message_text("🗑️ Select a video to delete:", chat_id, message_id, 
                             reply_markup=markup)
    
    elif call.data.startswith("delete_vid_"):
        video_id = int(call.data.split("_")[2])
        video = get_video_by_id(video_id)
        
        if not video:
            bot.answer_callback_query(call.id, "Video not found.")
            return
        
        # Delete the video
        success = delete_video(video_id)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Video deleted successfully!")
            
            # Go back to delete videos menu
            videos = get_all_videos()
            
            if not videos:
                markup = types.InlineKeyboardMarkup()
                back_btn = types.InlineKeyboardButton("⬅️ Back", callback_data="admin_back")
                markup.add(back_btn)
                
                bot.edit_message_text("🗑️ No videos to delete.", chat_id, message_id, 
                                     reply_markup=markup)
                return
            
            # Create updated delete menu
            markup = types.InlineKeyboardMarkup(row_width=2)
            
            for video in videos[:10]:  # Show first 10 videos
                video_id, file_id, caption, uploader_id = video
                cap_text = f" - {caption}" if caption else ""
                btn = types.InlineKeyboardButton(f"Delete #{video_id}{cap_text}", callback_data=f"delete_vid_{video_id}")
                markup.add(btn)
            
            # Add back button
            back_btn = types.InlineKeyboardButton("⬅️ Back", callback_data="admin_back")
            markup.add(back_btn)
            
            bot.edit_message_text("🗑️ Select a video to delete:", chat_id, message_id, 
                                 reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ Failed to delete video.")
    
    elif call.data == "admin_back":
        # Return to main admin panel
        markup = create_admin_markup()
        bot.edit_message_text("🛠️ *Admin Panel*", chat_id, message_id, 
                             reply_markup=markup, parse_mode="Markdown")
    
    bot.answer_callback_query(call.id)

# Process add points user ID
def process_add_points_user(message):
    try:
        user_id = int(message.text)
        user_info = get_user_info(user_id)
        
        if user_info:
            msg = bot.send_message(message.chat.id, f"User found: {user_info[2]} {user_info[3] or ''}\nCurrent points: {user_info[5]}\n\nHow many points to add?")
            bot.register_next_step_handler(msg, process_add_points_amount, user_id)
        else:
            bot.send_message(message.chat.id, "User not found. Please check the user ID and try again.")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid user ID. Please send a numeric user ID.")

# Process add points amount
def process_add_points_amount(message, user_id):
    try:
        points_to_add = int(message.text)
        if points_to_add <= 0:
            bot.send_message(message.chat.id, "Please enter a positive number of points.")
            return
        
        current_points = get_user_points(user_id)
        new_points = current_points + points_to_add
        update_user_points(user_id, new_points)
        
        user_info = get_user_info(user_id)
        bot.send_message(message.chat.id, f"✅ {points_to_add} points added to {user_info[2]} {user_info[3] or ''}!\nNew total: {new_points} points")
        
        # Notify the user
        try:
            bot.send_message(user_id, f"🎉 You received {points_to_add} points from admin!\nYou now have {new_points} points available.")
        except:
            pass  # User might have blocked the bot or not started it
    except ValueError:
        bot.send_message(message.chat.id, "Invalid number. Please enter a numeric value.")

# Video message handler - restrict forwarding of videos from bot
@bot.message_handler(content_types=['video'])
def handle_video(message):
    # Check if this is a forwarded video from our bot
    if message.forward_from and message.forward_from.is_bot:
        bot.reply_to(message, "❌ Forwarding videos from this bot is not allowed. Please upload your own videos.")
        return
        
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        bot.reply_to(message, "❌ Forwarding videos from channels is not allowed. Please upload your own videos.")
        return
        
    user_id = message.from_user.id
    file_id = message.video.file_id
    caption = message.caption
    
    video_id = store_video(file_id, user_id, caption)
    bot.reply_to(message, "✅ Video stored successfully!")

# Contact command handler
@bot.message_handler(commands=['contact'])
def contact_admin(message):
    contact_text = f"""
    📞 Contact Information:
    
    For support, more points, or any questions, please contact {ADMIN_USERNAME}
    
    We're here to help you!
    """
    
    bot.reply_to(message, contact_text)

# Start the bot
if __name__ == "__main__":
    print("Video Storage Bot is running...")
    # Check if QR code file exists
    if not os.path.exists(QR_CODE_PATH):
        print(f"Warning: QR code file '{QR_CODE_PATH}' not found. Payment instructions will be text-only.")
    bot.infinity_polling()
