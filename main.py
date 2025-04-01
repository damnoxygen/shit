import telebot
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import requests
from io import BytesIO
from telebot.apihelper import ApiException
import sqlite3
import time
import threading
import random

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
                shards INTEGER DEFAULT 150,
                last_reward_time INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

init_db()

def add_new_user(user_id, username):
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone() is None:
            cursor.execute('INSERT INTO users (user_id, username, shards) VALUES (?, ?, ?)', (user_id, username, 150))
            conn.commit()
            
def add_praise(user_id, username):
    cursor.execute('SELECT * from users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        cursor.execute('UPDATE users SET praise_count = praise_count + 1 WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('INSERT INTO users (user_id, username, praise_count) VALUES (?, ?, 1)', (user_id, username))
    conn.commit()

def get_praise_count(user_id):
    cursor.execute('SELECT praise_count from users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def add_shards(user_id, username, amount=1):
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

def notify_reward_ready(user_id):
    time.sleep(5400)
    try:
        bot.send_sticker(user_id, "CAACAgIAAxkBAAEONQABZ-rDQ37YCOEFEGuOdo3YkpC9YtIAAgJaAAI-93hJoohQr8u1aOk2BA")
        bot.send_message(user_id, "ало пр у тя награда откатилась забери")
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")

@bot.message_handler(func=lambda message: message.reply_to_message is not None and message.text.lower() in TRIGGER_WORDS)
def praise_user(message):
    original_sender = message.reply_to_message.from_user
    praising_user = message.from_user
    bot_info = bot.get_me()

    if original_sender.id == praising_user.id:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONOxn6r31gbOO2E485bwJ8ENGYlHzjgACWz0AAr0uIEovxGFJMpJp_TYE")
        return

    if original_sender.id == bot_info.id:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONOxn6r31gbOO2E485bwJ8ENGYlHzjgACWz0AAr0uIEovxGFJMpJp_TYE")
        return

    
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (praising_user.id,))
        result = cursor.fetchone()
        praising_user_shards = result[0] if result else 0

    praise_cost = 50
    if praising_user_shards < praise_cost:
        missing_shards = praise_cost - praising_user_shards
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
        bot.reply_to(message, f"Не хватает {missing_shards} осколков чтобы типнуть")
        return

    
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET shards = shards - ? WHERE user_id = ?', (praise_cost, praising_user.id))
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (original_sender.id,))
        result = cursor.fetchone()
        original_sender_shards = result[0] if result else 0
        cursor.execute('INSERT OR IGNORE INTO users (user_id, username, shards) VALUES (?, ?, ?)', (original_sender.id, original_sender.first_name, 150))
        cursor.execute('UPDATE users SET shards = shards + ? WHERE user_id = ?', (praise_cost, original_sender.id))
        conn.commit()

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

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('награда'))
def reward_command(message):
    user_id = message.from_user.id
    current_time = int(time.time())  

    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT last_reward_time FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result:
            last_reward_time = result[0] if result[0] else 0
            if current_time - last_reward_time < 5400:
                remaining_time = 5400 - (current_time - last_reward_time)
                hours = remaining_time // 3600
                minutes = (remaining_time % 3600) // 60
                bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
                bot.reply_to(message, f"Ты уже получал награду. Попробуй снова через {hours} часов и {minutes} минут.")
                return
        else:
            cursor.execute('INSERT OR IGNORE INTO users (user_id, username, shards, last_reward_time) VALUES (?, ?, ?, ?)',
                           (user_id, message.from_user.first_name, 150, 0))

        
        cursor.execute('UPDATE users SET shards = shards + 5000, last_reward_time = ? WHERE user_id = ?', (current_time, user_id))
        conn.commit()

        bot.send_message(
            message.chat.id,
            f"[{message.from_user.first_name}](tg://user?id={user_id}) *залутал свои +500 осколков. Следующая награда через полтора часа*",
            parse_mode='Markdown'
    )
    
    threading.Thread(target=notify_reward_ready, args=(user_id,)).start()
        
@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('мой профиль'))
def profile_command(message):
    user_id = message.from_user.id
    username = message.from_user.first_name

    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT praise_count, shards FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        praise_count = result[0] if result else 0
        shards = result[1] if result else 150  

    try:
        
        background = Image.open("./bg.png").resize((800, 400))

        
        avatar_url = f"https://api.telegram.org/bot{TOKEN}/getUserProfilePhotos?user_id={user_id}"
        response = requests.get(avatar_url).json()
        if response.get('ok') and response.get('result', {}).get('total_count', 0) > 0:
            photo_file_id = response['result']['photos'][0][0]['file_id']
            file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={photo_file_id}").json()
            file_path = file_info.get('result', {}).get('file_path')
            avatar_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            avatar_response = requests.get(avatar_url)
            avatar = Image.open(BytesIO(avatar_response.content)).resize((287, 287))
            avatar = ImageOps.fit(avatar, (287, 287), centering=(0.5, 0.5))
            mask = Image.new("L", (287, 287), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, 287, 287), radius=32, fill=255)
            avatar.putalpha(mask)
            background.paste(avatar, (466, 57), avatar)
        else:
            print("Аватарка не найдена, пропускаем.")

        
        font_name = ImageFont.truetype("Montserrat-SemiBold.ttf", 27)
        font_praise = ImageFont.truetype("Montserrat-SemiBold.ttf", 29)

        
        if len(username) > 11:
            username = username[:11] + ".."

        
        draw = ImageDraw.Draw(background)
        draw.text((201, 58), username, font=font_name, fill="white")

        
        praise_text = str(praise_count)
        if len(praise_text) > 11:
            praise_text = praise_text[:11] + "+"

        shards_text = str(shards)
        if len(shards_text) > 11:
            shards_text = shards_text[:11] + "+"

        base_x = 407  
        base_y = 163  

        adjusted_x = base_x - (len(shards_text) * 19)

        draw.text((adjusted_x, base_y), f"{shards_text}", font=font_praise, fill="white")

        base_x2 = 407  
        base_y2 = 283

        adjusted_x2 = base_x2 - (len(praise_text) * 19)
        draw.text((adjusted_x2, base_y2), f"{praise_text}", font=font_praise, fill="white")
        
        byte_io = BytesIO()
        background.save(byte_io, format="PNG")
        byte_io.seek(0)
        bot.send_photo(message.chat.id, byte_io, caption=f"*Смарите какой пидарас его* [{message.from_user.first_name}](tg://user?id={message.from_user.id}) *завут*", reply_to_message_id=message.message_id)

    except Exception as e:
        print(f"Ошибка при создании профиля: {e}")
        bot.reply_to(message, "Сука даун ты всьо сломал нема твоего блядского профиля")

@bot.message_handler(commands=['THISHITSOONSUKA'])
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
                cursor.execute('SELECT user_id, praise_count from users WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result:
                    user_id, praise_count = result
                    user_mention = f"[{username}](tg://user?id={user_id})"
                    bot.reply_to(message, f"{user_mention} типали {praise_count} раз нахуй", parse_mode='Markdown')
                else:
                    bot.reply_to(message, f"сука а его чота в бд нема", parse_mode='Markdown')
                return
            elif target.isdigit():  
                user_id = int(target)
                cursor.execute('SELECT username, praise_count from users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                if result:
                    username, praise_count = result
                    user_mention = f"[{username}](tg://user?id={user_id})"
                    bot.reply_to(message, f"{user_mention} типали {praise_count} раз нахуй", parse_mode='Markdown')
                else:
                    bot.reply_to(message, f"Пользователь с ID {user_id} не найден в базе данных.", parse_mode='Markdown')
                return
            else:
                bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
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


@bot.message_handler(commands=['patch'])
def patch_command(message):
    bot.send_message(message.chat.id, "*Изменения баланса:*\n\n`+ Кулдаун награды уменьшен с полтора часа до 1.5`\n`+ Удалён коэфициент который надо указывать в ролле. Теперь он всегда равен 5.`\n`+ Кулдаун награды у всех пользователей был сброшен.`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('отправить'))
def send_shards(message):
    command_parts = message.text.split(maxsplit=2)

    if len(command_parts) < 2 and not message.reply_to_message:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
        return

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        target = command_parts[1]
        if target.startswith('@'):  
            username = target[1:]
            cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            if not result:
                bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
                return
            target_user_id = result[0]
            target_user = type('User', (object,), {'id': target_user_id, 'first_name': username})()
        elif target.isdigit():  
            target_user_id = int(target)
            cursor.execute('SELECT user_id, username FROM users WHERE user_id = ?', (target_user_id,))
            result = cursor.fetchone()
            if not result:
                bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
                return
            target_user = type('User', (object,), {'id': target_user_id, 'first_name': result[1]})()
        else:
            bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
            return

    try:
        shards_to_send = int(command_parts[-1])
        if shards_to_send <= 0:
            bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
            return
    except ValueError:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
        return

    sender_user = message.from_user

    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (sender_user.id,))
        result = cursor.fetchone()
        sender_shards = result[0] if result else 0

    if sender_shards < shards_to_send:
        bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONPhn6r8RcvQ75cIHzxyTJnFhzN-nwwACPEoAAh_rEEsFfetMdwRONTYE")
        bot.reply_to(message, f"Ну тип тобі над ше чуть осколків десь {shards_to_send - sender_shards}.")
        return

    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET shards = shards - ? WHERE user_id = ?', (shards_to_send, sender_user.id))
        cursor.execute('INSERT OR IGNORE INTO users (user_id, username, shards) VALUES (?, ?, ?)', (target_user.id, target_user.first_name, 150))
        print(f"DEBUG: Уменьшено {shards_to_send} осколков у пользователя {sender_user.id}")
        cursor.execute('UPDATE users SET shards = shards + ? WHERE user_id = ?', (shards_to_send, target_user.id))
        conn.commit()
 
    sender_mention = f"[{sender_user.first_name}](tg://user?id={sender_user.id})"
    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    bot.send_sticker(message.chat.id, "CAACAgIAAxkBAAEONRBn6ssczW7x7GFCSaIMe9maD-6-UwAC_U0AAjFyGEsuP0FyHmcEFDYE")
    bot.send_message(message.chat.id, f"{sender_mention} *перевёл* {target_mention} *{shards_to_send} осколкау*", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text and message.text.startswith('!addtodb'))
def add_to_db_command(message):
    command_parts = message.text.split(maxsplit=2)

    if len(command_parts) < 3:
        return  

    try:
        shards_change = int(command_parts[1])  
    except ValueError:
        return  

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        target = command_parts[2]
        if target.startswith('@'):  
            username = target[1:]
            with sqlite3.connect('praise.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                if not result:
                    return  
                target_user_id = result[0]
        elif target.isdigit():  
            target_user_id = int(target)
        else:
            return  

    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (target_user_id,))
        result = cursor.fetchone()
        if not result:
            cursor.execute('INSERT INTO users (user_id, username, shards) VALUES (?, ?, ?)', (target_user_id, target, 150))
        cursor.execute('UPDATE users SET shards = shards + ? WHERE user_id = ?', (shards_change, target_user_id))
        conn.commit()

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('ролл'))
def roll_command(message):
    command_parts = message.text.split()

    if len(command_parts) != 3:
        bot.reply_to(message, "Используй формат: `ролл число ставка`", parse_mode='Markdown')
        return

    try:
        
        user_id = message.from_user.id
        username = message.from_user.first_name

        x1 = int(command_parts[1])  
        x2 = int(command_parts[2])  
    except ValueError:
        bot.reply_to(message, "Убедись, что x1 и x2 — числа. Формат: `ролл число ставка`", parse_mode='Markdown')
        return
    
    if x1 < 1 or x1 > 6:
        bot.reply_to(message, "x1 должно быть числом от 1 до 6.", parse_mode='Markdown')
        return

    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        user_shards = result[0] if result else 0

    if x2 > user_shards:
        bot.reply_to(message, f"У тебя недостаточно осколков. Твой баланс: {user_shards}.", parse_mode='Markdown')
        return

    
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET shards = shards - ? WHERE user_id = ?', (x2, user_id))
        conn.commit()

    
    dice_message = bot.send_dice(message.chat.id, emoji="🎲")
    dice_value = dice_message.dice.value

    
    time.sleep(2.5)

    if dice_value == x1:
        winnings = int(x2 * 6)
        display = int(x2 * 5)

        with sqlite3.connect('praise.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET shards = shards + ? WHERE user_id = ?', (winnings, user_id))
            conn.commit()
        bot.send_message(
            chat_id=message.chat.id,
            text=f"*🎲 ✅* [{message.from_user.first_name}](tg://user?id={user_id}) *Выпало {dice_value}! Ты выиграл {display} осколков*",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text=f"*🎲 ❌* [{message.from_user.first_name}](tg://user?id={user_id}) *Выпало {dice_value}. Ты проиграл {x2} осколков.*",
            parse_mode='Markdown'
        )

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith('монетка'))
def coin_flip_command(message):
    command_parts = message.text.split()

    if len(command_parts) != 3:
        bot.reply_to(message, "Используй формат: `монетка орел/решка ставка`", parse_mode='Markdown')
        return

    try:
        user_id = message.from_user.id
        username = message.from_user.first_name

        choice = command_parts[1].lower()
        bet = int(command_parts[2])
    except ValueError:
        bot.reply_to(message, "Даун ставка это число. Формат: `монетка орел/решка ставка`", parse_mode='Markdown')
        return

    if choice not in ["орел", "решка"]:
        bot.reply_to(message, "есть ток орел и решка", parse_mode='Markdown')
        return

    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT shards FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        user_shards = result[0] if result else 0

    if bet > user_shards:
        bot.reply_to(message, f"У тебя недостаточно осколков. Твой баланс: {user_shards}.", parse_mode='Markdown')
        return

    
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET shards = shards - ? WHERE user_id = ?', (bet, user_id))
        conn.commit()

    
    initial_message = bot.reply_to(message, "*Монетка в воздухе... 🪙*", parse_mode="Markdown")
    time.sleep(2.5)

    result = random.choices(["орел", "решка", "ребро"], weights=[42.5, 42.5, 15], k=1)[0]

    if result == choice:
        winnings = bet * 3
        display = bet * 2
        with sqlite3.connect('praise.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET shards = shards + ? WHERE user_id = ?', (winnings, user_id))
            conn.commit()
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=initial_message.message_id,
            text=f"🪙 ✅ [{message.from_user.first_name}](tg://user?id={user_id}) *Монетка показала {result}, ты выиграл {display} осколков*",
            parse_mode='Markdown'
        )
    elif result == "ребро":
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=initial_message.message_id,
            text=f"🪙 ⁉ [{message.from_user.first_name}](tg://user?id={user_id}) *НИХУЯ СЕБЕ ТЫ ОЛУХ, РЕБРО НАХУЙ. ставка возвращена.*",
            parse_mode='Markdown'
        )
        
        with sqlite3.connect('praise.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET shards = shards + ? WHERE user_id = ?', (bet, user_id))
            conn.commit()
    else:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=initial_message.message_id,
            text=f"🪙 ❌ [{message.from_user.first_name}](tg://user?id={user_id}) *Монетка показала {result}, ты проебал нахуй {bet} осколков*",
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['set0'])
def reset_reward_cooldown(message):
    try:
        with sqlite3.connect('praise.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET last_reward_time = 0')
            conn.commit()
        bot.reply_to(message, "КД награды для всех пользователей успешно сброшено!")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка при сбросе КД: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    add_shards(user_id, username)

print("Бот запущен...")
bot.infinity_polling()