from aiogram import Bot, Dispatcher
from django.conf import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
