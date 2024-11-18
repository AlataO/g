import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import random
from PIL import Image, ImageDraw, ImageFont
import requests

# Импортируем TOKEN из файла конфигурации
try:
    from config.config import TOKEN
except ImportError:
    print("Ошибка: Файл config.py не найден. Пожалуйста, создайте файл config/config.py и укажите в нем ваш токен.")
    exit(1)

# Шрифты для демотиватора
FONT_PATH = 'arial.ttf'  # Укажите путь к существующему шрифту
FONT_SIZE_TITLE = 40
FONT_SIZE_SUBTITLE = 20

def create_demotivator(image_path, title, subtitle):
    # Открываем изображение
    img = Image.open(image_path)
    img_width, img_height = img.size

    # Создаем новое изображение с черным фоном
    new_height = img_height + 200
    new_img = Image.new('RGB', (img_width, new_height), color='black')

    # Вставляем исходное изображение
    new_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(new_img)

    # Настраиваем шрифты
    font_title = ImageFont.truetype(FONT_PATH, FONT_SIZE_TITLE)
    font_subtitle = ImageFont.truetype(FONT_PATH, FONT_SIZE_SUBTITLE)

    # Вычисляем размеры текста
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]

    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]

    # Пишем заголовок
    draw.text(
        ((img_width - title_width) / 2, img_height + 20),
        title,
        font=font_title,
        fill='white'
    )

    # Пишем подзаголовок
    draw.text(
        ((img_width - subtitle_width) / 2, img_height + 80),
        subtitle,
        font=font_subtitle,
        fill='white'
    )

    # Сохраняем демотиватор
    demotivator_path = 'demotivator.jpg'
    new_img.save(demotivator_path)

    return demotivator_path

def get_random_messages(peer_id):
    history = vk.messages.getHistory(peer_id=peer_id, count=200)
    messages = [msg['text'] for msg in history['items'] if msg['text']]
    if len(messages) < 2:
        return 'Недостаточно сообщений для создания демотиватора.', ''
    return random.choice(messages), random.choice(messages)

def get_random_image_from_conversation(peer_id):
    # Получаем историю сообщений
    history = vk.messages.getHistory(peer_id=peer_id, count=200)
    messages = history['items']
    
    # Список для хранения ссылок на фотографии
    photos = []

    for msg in messages:
        if 'attachments' in msg:
            for attachment in msg['attachments']:
                if attachment['type'] == 'photo':
                    # Выбираем фото самого высокого качества
                    photo_sizes = attachment['photo']['sizes']
                    max_size_photo = max(photo_sizes, key=lambda size: size['width'] * size['height'])
                    photos.append(max_size_photo['url'])
    
    if not photos:
        return None  # Если фотографий нет

    # Выбираем случайное фото
    photo_url = random.choice(photos)
    return photo_url

def main():
    global vk  # Добавляем глобальную переменную vk

    vk_session = vk_api.VkApi(token=TOKEN)
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()

    # Основной цикл
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            msg = event.text.lower()
            peer_id = event.peer_id

            if msg == '/g':
                # Получаем случайное изображение из беседы
                photo_url = get_random_image_from_conversation(peer_id)
                if not photo_url:
                    vk.messages.send(peer_id=peer_id, message="В беседе нет доступных изображений для создания демотиватора.", random_id=0)
                    continue

                # Скачиваем изображение
                image_response = requests.get(photo_url)
                image_path = 'temp_image.jpg'
                with open(image_path, 'wb') as f:
                    f.write(image_response.content)

                # Получаем два случайных сообщения
                title, subtitle = get_random_messages(peer_id)
                if not subtitle:
                    vk.messages.send(peer_id=peer_id, message=title, random_id=0)
                    continue

                # Создаем демотиватор
                demotivator_path = create_demotivator(image_path, title, subtitle)

                # Загружаем изображение в VK
                upload = vk_api.VkUpload(vk_session)
                photo = upload.photo_messages(demotivator_path)[0]

                attachment = f'photo{photo["owner_id"]}_{photo["id"]}'
                vk.messages.send(peer_id=peer_id, attachment=attachment, random_id=0)

                # Удаляем временные файлы
                os.remove(demotivator_path)
                os.remove(image_path)

if __name__ == '__main__':
    main()
