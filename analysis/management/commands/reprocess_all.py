import logging
import time
from django.core.management.base import BaseCommand
from analysis.models import AnalysisResult, KnowledgeEntry, CourseTask
from core.models import Message
from analysis.tasks import process_content_task
from analysis.schemas import IngestionData
from analysis.vector_db import VectorDBService
from qdrant_client.http import models

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Reprocess all messages in the database'

    def handle(self, *args, **options):
        self.stdout.write("Starting full reprocessing...")

        # 1. Clear Derived Data
        self.stdout.write("Clearing AnalysisResults, KnowledgeEntries, CourseTasks...")
        AnalysisResult.objects.all().delete()
        KnowledgeEntry.objects.all().delete()
        CourseTask.objects.all().delete()
        
        # 2. Reset Vector DB
        self.stdout.write("Resetting Qdrant collection...")
        vdb = VectorDBService()
        try:
            vdb.client.delete_collection(vdb.collection_name)
            self.stdout.write("Deleted old collection.")
        except Exception as e:
            self.stdout.write(f"Collection deletion skipped or failed: {e}")
            
        # Re-init (creates collection)
        vdb._ensure_collection()
        self.stdout.write("Collection recreated.")

        # 3. Process Messages
        messages = Message.objects.all().order_by('sent_at')
        total = messages.count()
        self.stdout.write(f"Found {total} messages to process.")

        for i, msg in enumerate(messages):
            self.stdout.write(f"[{i+1}/{total}] Processing Message {msg.id}...")
            
            # Construct Ingestion Data matching handlers.py logic
            
            # Now we have reply_to_id in the model!
            reply_to_id = msg.reply_to_id
            is_reply = bool(reply_to_id)
            
            # Determine sender role? 
            # Stored in message model
            
            ingestion_data = IngestionData(
                text=msg.text or "",
                source_type='telegram',
                source_id=str(msg.id),
                metadata={
                    'sender_role': msg.sender_role,
                    'chat_title': msg.chat.title if msg.chat else "Private",
                    'is_reply': is_reply,
                    'reply_to_msg_id': reply_to_id,
                    'tg_chat_id': msg.chat.tg_chat_id,
                    'timestamp': msg.sent_at.isoformat()
                }
            )

            try:
                # Call task logic directly or via delay? 
                # Ideally via delay to use worker, but for script we might want synchronous 
                # to ensure order?
                # Using delay is fine as long as they are processed somewhat in order.
                # But parallel processing might cause race conditions for task creation (duplicates).
                # Since we cleared everything, first message (Teacher task) needs to be processed 
                # before second message (Student reply).
                # So we should call the logic SYNCHRONOUSLY here.
                
                process_content_task(ingestion_data.dict())
                self.stdout.write(self.style.SUCCESS(f"Processed Message {msg.id}"))
                
                # Sleep briefly to ensure Qdrant consistency?
                # process_content_task is synchronous if called directly (except it has @shared_task decorator)
                # Calling it as a function executes it in current process? 
                # Celery tasks are functions, so yes.
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to process {msg.id}: {e}"))

        self.stdout.write(self.style.SUCCESS("Reprocessing complete."))
