import telebot
from PIL import Image
import io
import requests
from io import BytesIO
from telebot.apihelper import ApiException
import sqlite3

TOKEN = '7663452669:AAHDu1u6bcE8kHk62G_ra8NXCZ-gqYi7K0I'
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

TRIGGER_WORDS = {"тип", "типнуть", "похвала", "похвалить", "типайте"}

conn = sqlite3.connect('praise.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                praise_count INTEGER DEFAULT 0,
                shards INTEGER DEFAULT 150
            )
        ''')
        conn.commit()

init_db()

def add_praise(user_id, username):
    cursor.execute('SELECT * FROM praises WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        cursor.execute('UPDATE praises SET praise_count = praise_count + 1 WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('INSERT INTO praises (user_id, username, praise_count) VALUES (?, ?, 1)', (user_id, username))
    conn.commit()

def get_praise_count(user_id):
    cursor.execute('SELECT praise_count FROM praises WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def add_shards(user_id, username, amount=2):
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            cursor.execute('UPDATE users SET shards = shards + ? WHERE user_id = ?', (amount, user_id))
        else:
            cursor.execute('INSERT INTO users (user_id, username, shards) VALUES (?, ?, ?)', (user_id, username, 150 + amount))
        conn.commit()

def create_praise_image(praising_user, original_sender):
    try:
        img = Image.new('RGB', (500, 300), color=(255, 255, 255))
        left_width, right_width, center_width = 125, 125, 250

        def get_user_avatar(user_id):
            url = f"https://api.telegram.org/bot{TOKEN}/getUserProfilePhotos?user_id={user_id}"
            response = requests.get(url).json()
            if response.get('ok') and response.get('result', {}).get('total_count', 0) > 0:
                photo_file_id = response['result']['photos'][0][0]['file_id']
                file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={photo_file_id}").json()
                file_path = file_info.get('result', {}).get('file_path')
                if not file_path:
                    return None
                avatar_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
                avatar_response = requests.get(avatar_url)
                avatar_img = Image.open(BytesIO(avatar_response.content))
                return avatar_img.resize((left_width, 300))
            return None

        praising_avatar = get_user_avatar(praising_user.id)
        original_avatar = get_user_avatar(original_sender.id)

        sticker = Image.open("./img/sticker.webp").resize((center_width, 300))
        if praising_avatar:
            img.paste(praising_avatar, (0, 0))
        if original_avatar:
            img.paste(original_avatar, (left_width + center_width, 0))
        img.paste(sticker, (left_width, 0))

        byte_io = io.BytesIO()
        img.save(byte_io, format='PNG')
        byte_io.seek(0)

        return byte_io
    except Exception as e:
        print(f"бабах: {e}")
        return None

@bot.message_handler(func=lambda message: message.reply_to_message is not None and message.text.lower() in TRIGGER_WORDS)
def praise_user(message):
    original_sender = message.reply_to_message.from_user
    praising_user = message.from_user
    bot_info = bot.get_me()

    if original_sender.id == praising_user.id:
        bot.reply_to(message, "блять ты ебаклак")
        return

    if original_sender.id == bot_info.id:
        bot.reply_to(message, "ты чё ваще страх потерял осёл")
        return

    praising_mention = f"[{praising_user.first_name}](tg://user?id={praising_user.id})"
    original_mention = f"[{original_sender.first_name}](tg://user?id={original_sender.id})"

    caption = f"{praising_mention} *типает* {original_mention}\n\n"
    image = create_praise_image(praising_user, original_sender)

    
    add_praise(original_sender.id, original_sender.first_name)

    try:
        if image:
            bot.send_photo(
                message.chat.id,
                image,
                caption=caption,
                parse_mode='Markdown',
                reply_to_message_id=message.reply_to_message.message_id
            )
        else:
            bot.send_message(
                message.chat.id,
                caption,
                parse_mode='Markdown',
                reply_to_message_id=message.reply_to_message.message_id
            )
    except ApiException as e:
        print(f"Ошибка при отправке фото: {e}")
        bot.send_message(
            message.chat.id,
            caption,
            parse_mode='Markdown',
            reply_to_message_id=message.reply_to_message.message_id
        )

@bot.message_handler(commands=['типы'])
def show_user_praise_count(message):
    
    if message.reply_to_message:
        
        target_user = message.reply_to_message.from_user
        user_id = target_user.id
        username = target_user.first_name
    else:
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) > 1:
            target = command_parts[1]
            if target.startswith('@'):  
                username = target[1:]  
                cursor.execute('SELECT user_id, praise_count FROM praises WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result:
                    user_id, praise_count = result
                    user_mention = f"[{username}](tg://user?id={user_id})"
                    bot.reply_to(message, f"{user_mention} типали {praise_count} раз нахуй", parse_mode='Markdown')
                else:
                    bot.reply_to(message, f"Пользователь {target} не найден в базе данных.", parse_mode='Markdown')
                return
            elif target.isdigit():  
                user_id = int(target)
                cursor.execute('SELECT username, praise_count FROM praises WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                if result:
                    username, praise_count = result
                    user_mention = f"[{username}](tg://user?id={user_id})"
                    bot.reply_to(message, f"{user_mention} типали {praise_count} раз нахуй", parse_mode='Markdown')
                else:
                    bot.reply_to(message, f"Пользователь с ID {user_id} не найден в базе данных.", parse_mode='Markdown')
                return
            else:
                bot.reply_to(message, "Неверный формат команды. Укажите @username или user-id.", parse_mode='Markdown')
                return
        else:
            
            user_id = message.from_user.id
            username = message.from_user.first_name

    
    praise_count = get_praise_count(user_id)
    user_mention = f"[{username}](tg://user?id={user_id})"
    if message.reply_to_message or len(command_parts) > 1:
        bot.reply_to(message, f"{user_mention} типали {praise_count} раз нахуй", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"тя типали {praise_count} раз нахуй", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.startswith('whatistip'))
def send_welcome(message):
    bot.reply_to(message, "Карочи в дотке есть такая механика как тип (похвала), она изначально задумывалась как похвала за ахуенную игру, но игроки её юзают как оск. типо чел хуйню сделал и его типают", parse_mode='Markdown')

@bot.message_handler(commands=['shards'])
def get_shards(message):
    user_id = message.from_user.id
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        shards = result[0] if result else 150
    bot.reply_to(message, f"У тебя {shards} осколков")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    add_shards(user_id, username)

print("Бот запущен...")
bot.infinity_polling()