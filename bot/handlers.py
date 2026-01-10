import logging
import asyncio
from aiogram import types
from aiogram.filters import CommandStart, Command, CommandObject
from asgiref.sync import sync_to_async
from core.models import Chat, Message
from analysis.schemas import IngestionData
from analysis.tasks import process_content_task
from .loader import dp, bot

logger = logging.getLogger(__name__)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Bot is running. Add me to a group chat to start analyzing.")

@dp.message(Command("set_teacher"))
async def cmd_set_teacher(message: types.Message, command: CommandObject):
    if message.chat.type not in ['group', 'supergroup']:
        await message.answer("Эта команда работает только в группах.")
        return

    # Check if sender is admin
    try:
        member = await message.chat.get_member(message.from_user.id)
        if member.status not in ['creator', 'administrator']:
            await message.answer("Только администраторы могут назначать преподавателя.")
            return
    except Exception:
        return

    target_id = None
    target_name = None
    args = command.args

    if args:
        # Check for mentions in entities (e.g. text_mention)
        if message.entities:
            for entity in message.entities:
                if entity.type == "text_mention" and entity.user:
                    target_id = entity.user.id
                    target_name = entity.user.full_name
                    break
        
        # If no text_mention, try parsing ID
        if not target_id:
            # Clean args just in case
            possible_id = args.split()[0]
            if possible_id.isdigit():
                target_id = int(possible_id)
                target_name = f"ID: {target_id}"
            elif possible_id.startswith("@"):
                await message.answer("К сожалению, боты не могут определять ID пользователя по @username напрямую.\nПожалуйста, используйте ID пользователя или ответьте на его сообщение командой.")
                return
            else:
                 await message.answer("Неверный формат ID. Пожалуйста, введите числовой ID или ответьте на сообщение.")
                 return

    elif message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.full_name
    else:
        # Defaults to self if no reply and no args
        target_id = message.from_user.id
        target_name = message.from_user.full_name

    if target_id:
        await sync_to_async(set_chat_teacher)(message.chat.id, target_id)
        # Verify by mention
        mention_link = f"tg://user?id={target_id}"
        await message.answer(f"Преподаватель закреплен: <a href='{mention_link}'>{target_name}</a> (ID: {target_id})", parse_mode="HTML")

def set_chat_teacher(chat_id, teacher_id):
    chat, _ = Chat.objects.update_or_create(
        tg_chat_id=chat_id,
        defaults={} 
    )
    chat.pinned_teacher_id = teacher_id
    chat.save()

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

    if event.new_chat_member.status == 'member':
        await bot.send_message(chat_id, "Всем привет! Я теперь слушаю эту группу. Вы можете закрепить преподавателя командой /set_teacher")

def update_chat(chat_id, title, chat_type, status):
    if status in ['member', 'administrator']:
        Chat.objects.update_or_create(
            tg_chat_id=chat_id,
            defaults={
                'title': title,
                'chat_type': chat_type
            }
        )

def get_pinned_teacher_id(chat_id):
    try:
        chat = Chat.objects.get(tg_chat_id=chat_id)
        return chat.pinned_teacher_id
    except Chat.DoesNotExist:
        return None

@dp.message()
async def on_message(message: types.Message):
    """
    Handle incoming messages. Checks role and dispatches analysis task.
    """
    if not message.text:
        return

    sender_role = 'student'
    
    # Check pinned teacher first
    pinned_teacher_id = await sync_to_async(get_pinned_teacher_id)(message.chat.id)
    
    if pinned_teacher_id:
        if message.from_user.id == pinned_teacher_id:
            sender_role = 'teacher'
    else:
        # Check if sender is admin (Teacher) fallback
        if message.chat.type in ['group', 'supergroup']:
            try:
                member = await message.chat.get_member(message.from_user.id)
                if member.status in ['creator', 'administrator']:
                    sender_role = 'teacher'
            except Exception:
                pass

    # Save to DB
    db_message = await sync_to_async(save_message)(message, sender_role)

    # Logic: 
    # 1. If it's a teacher message, process it as usual (high priority).
    # 2. If it's a student message, BUT it is a reply to a teacher message (context), 
    #    OR a reply FROM a teacher to a student, we want to capture that.
    
    # Actually, the user wants: "read not only teacher messages, but also messages... to which the teacher replied"
    # So if Teacher replies -> we need the original message too.
    
    should_process = False
    context_text = ""

    if sender_role == 'teacher':
        should_process = True
        context_text = message.text
        # If teacher replies to someone, include that context
        if message.reply_to_message:
             if message.reply_to_message.text:
                 context_text = f"Student Question: {message.reply_to_message.text}\nTeacher Answer: {message.text}"
    
    # We could also process student messages if they are replies TO a teacher, but usually the teacher's ANSWER is the trigger.
    # Let's stick to triggering primarily on Teacher actions, but capturing the context.
    
    if should_process:
        ingestion_data = IngestionData(
            text=context_text,
            source_type='telegram',
            source_id=str(db_message.id),
            metadata={
                'sender_role': sender_role,
                'chat_title': message.chat.title or 'Private',
                'is_reply': bool(message.reply_to_message)
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
