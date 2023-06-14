import asyncio
import re
import unicodedata
import os
import shutil
from telethon.sync import TelegramClient
from telethon.events import NewMessage
from telethon.tl.types import MessageEntityMention
from config import api_id, api_hash, phone_number, source_channel_id, destination_channel_id, hidden_link_text, hidden_link_url, COPY_DELAY

def remove_md_links(text):
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', '', text)

def add_own_link(text, own_link):
    return f"{text}\n\n{own_link}"

def is_emoji(c):
    return unicodedata.category(c) in ["So", "Sm", "Sc", "Sk", "Pc"]

def remove_emojis(text):
    return ''.join(c for c in text if not is_emoji(c))

async def copy_messages():
    client = TelegramClient('session_name', api_id, api_hash)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone_number)
            await client.sign_in(phone_number, input('Введите код подтверждения: '))

        source_channel = await client.get_entity(source_channel_id)
        destination_channel = await client.get_entity(destination_channel_id)

        own_link = f"[{hidden_link_text}]({hidden_link_url})"
        lightning_emoji = "⚡️"

        async def handle_new_message(event):
            message = event.message

            new_message_text = message.text

            new_message_text = remove_md_links(new_message_text)
            new_message_text = remove_emojis(new_message_text)

            if new_message_text.strip() or message.media:
                new_message_text_with_link = add_own_link(new_message_text.lstrip(), own_link)
                new_message_text_with_emoji = f"{lightning_emoji} {new_message_text_with_link}"

                await asyncio.sleep(COPY_DELAY)

                try:
                    updated_message = await client.get_messages(source_channel, ids=[message.id])
                    if updated_message and updated_message[0]:
                        if updated_message[0].media:
                            media_files = []

                            # Копируем только первый файл
                            if isinstance(updated_message[0].media, list):
                                media = updated_message[0].media[0]
                            else:
                                media = updated_message[0].media

                            media_file = await client.download_media(media)
                            media_files.append(media_file)

                            destination_folder = "путь_к_папке_назначения"
                            os.makedirs(destination_folder, exist_ok=True)
                            copied_file = os.path.join(destination_folder, os.path.basename(media_file))
                            shutil.copy2(media_file, copied_file)
                            media = await client.upload_file(copied_file)

                            # Проверяем, является ли сообщение ответом
                            if message.reply_to_msg_id:
                                replied_message = await client.get_messages(source_channel, ids=[message.reply_to_msg_id])
                                if replied_message and replied_message[0]:
                                    reply_message = await client.send_file(destination_channel, media, caption=new_message_text_with_emoji)
                                    await client.forward_messages(destination_channel, replied_message[0], from_peer=source_channel, silent=True, as_reply=True)
                                    await client.delete_messages(destination_channel, [reply_message])
                                else:
                                    await client.send_file(destination_channel, media, caption=new_message_text_with_emoji)
                            else:
                                await client.send_file(destination_channel, media, caption=new_message_text_with_emoji)
                            print(f"Скопировано сообщение с медиафайлом ID: {message.id}.")
                            os.remove(copied_file)
                        else:
                            # Проверяем, является ли сообщение ответом
                            if message.reply_to_msg_id:
                                replied_message = await client.get_messages(source_channel, ids=[message.reply_to_msg_id])
                                if replied_message and replied_message[0]:
                                    reply_message = await client.send_message(destination_channel, new_message_text_with_emoji)
                                    await client.forward_messages(destination_channel, replied_message[0], from_peer=source_channel, silent=True, as_reply=True)
                                    await client.delete_messages(destination_channel, [reply_message])
                                else:
                                    await client.send_message(destination_channel, new_message_text_with_emoji)
                            else:
                                await client.send_message(destination_channel, new_message_text_with_emoji)
                            print(f"Скопировано сообщение без файла ID: {message.id}.")
                    else:
                        print(f"Сообщение удалено ID: {message.id}.")
                except Exception as e:
                    print(f"Ошибка при копировании сообщения ID: {message.id}")
                    print(e)
            else:
                print(f"Пропущено пустое сообщение ID: {message.id}.")

        client.add_event_handler(handle_new_message, NewMessage(chats=source_channel))

        try:
            await client.run_until_disconnected()
        finally:
            pass

    finally:
        await client.disconnect()

asyncio.run(copy_messages())
