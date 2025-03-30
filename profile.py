@bot.message_handler(commands=['profile'])
def profile_command(message):
    user_id = message.from_user.id
    username = message.from_user.first_name

    
    with sqlite3.connect('praise.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT praise_count FROM praises WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        praise_count = result[0] if result else 0

    
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

        
        draw.text((224, 163), praise_text, font=font_praise, fill="white")

        
        byte_io = BytesIO()
        background.save(byte_io, format="PNG")
        byte_io.seek(0)

        
        bot.send_photo(message.chat.id, byte_io, caption="Твой профиль", reply_to_message_id=message.message_id)

    except Exception as e:
        print(f"Ошибка при создании профиля: {e}")
        bot.reply_to(message, "Не удалось создать профиль. Попробуй позже.")