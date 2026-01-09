import logging
import asyncio
from aiogram import types
from aiogram.filters import CommandStart
from asgiref.sync import sync_to_async
from core.models import Chat, Message
from analysis.schemas import IngestionData
from analysis.tasks import process_content_task
from .loader import dp, bot

logger = logging.getLogger(__name__)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Bot is running. Add me to a group chat to start analyzing.")

@dp.my_chat_member()
async def on_my_chat_member(event: types.ChatMemberUpdated):
    """
    Handle bot being added or removed from a chat.
    """
    chat_id = event.chat.id
    title = event.chat.title
    chat_type = event.chat.type

    # Wrap DB operations in sync_to_async
    await sync_to_async(update_chat)(chat_id, title, chat_type, event.new_chat_member.status)

def update_chat(chat_id, title, chat_type, status):
    if status in ['member', 'administrator']:
        Chat.objects.update_or_create(
            tg_chat_id=chat_id,
            defaults={
                'title': title,
                'chat_type': chat_type
            }
        )

@dp.message()
async def on_message(message: types.Message):
    """
    Handle incoming messages. Checks role and dispatches analysis task.
    """
    if not message.text:
        return

    sender_role = 'student'
    # Check if sender is admin (Teacher)
    if message.chat.type in ['group', 'supergroup']:
        try:
            member = await message.chat.get_member(message.from_user.id)
            if member.status in ['creator', 'administrator']:
                sender_role = 'teacher'
        except Exception:
            pass

    # Save to DB
    db_message = await sync_to_async(save_message)(message, sender_role)

    ingestion_data = IngestionData(
        text=message.text,
        source_type='telegram',
        source_id=str(db_message.id),
        metadata={
            'sender_role': sender_role,
            'chat_title': message.chat.title or 'Private'
        }
    )

    process_content_task.delay(ingestion_data.model_dump())

def save_message(message: types.Message, role: str) -> Message:
    chat, _ = Chat.objects.get_or_create(
        tg_chat_id=message.chat.id,
        defaults={
            'title': message.chat.title,
            'chat_type': message.chat.type
        }
    )

    return Message.objects.create(
        chat=chat,
        tg_message_id=message.message_id,
        sender_name=message.from_user.full_name if message.from_user else "Unknown",
        sender_role=role,
        text=message.text,
        sent_at=message.date
    )
