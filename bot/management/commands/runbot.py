import asyncio
import logging
from django.core.management.base import BaseCommand
from bot.loader import bot, dp
# Import handlers to register them
import bot.handlers

class Command(BaseCommand):
    help = 'Runs the Telegram Bot'

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        print("Starting Bot...")
        asyncio.run(self.run_bot())

    async def run_bot(self):
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
