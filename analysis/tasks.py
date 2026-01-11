import logging
import uuid
from celery import shared_task
from django.conf import settings
from .schemas import IngestionData
from .ai_engine import AIService
from .models import AnalysisResult, KnowledgeEntry, CourseTask
from core.models import Message
from .vector_db import VectorDBService

logger = logging.getLogger(__name__)

@shared_task
def process_content_task(ingestion_data_dict: dict):
    """
    Celery task to process content asynchronously.
    """
    try:
        # Deserialize data
        data = IngestionData(**ingestion_data_dict)
        logger.info(f"Processing content from {data.source_type} ID: {data.source_id}")

        # Call AI Service
        ai_service = AIService()
        analysis_result = ai_service.analyze_content(data)
        
        # Initialize Vector DB
        vector_db = VectorDBService()

        # Save results based on source type
        if data.source_type == 'telegram':
            try:
                message = Message.objects.get(id=data.source_id)

                # Create AnalysisResult
                AnalysisResult.objects.update_or_create(
                    message=message,
                    defaults={
                        'category': analysis_result.get('category', 'other'),
                        'importance_score': analysis_result.get('importance_score', 0),
                        'summary': analysis_result.get('summary', ''),
                        'extracted_links': analysis_result.get('extracted_links', []),
                        'extracted_deadlines': analysis_result.get('extracted_deadlines', []),
                    }
                )
                
                # Logic for Knowledge Base & CourseTask
                category = analysis_result.get('category')
                importance = analysis_result.get('importance_score', 0)
                action = analysis_result.get('action', 'info')
                task_title = analysis_result.get('task_title')
                summary = analysis_result.get('summary', '').strip()
                
                # Auto-generate title if missing but content is likely important
                if not task_title and (importance >= 4 or category in ['deadline', 'announcement']):
                    if category == 'deadline':
                        extracts = analysis_result.get('extracted_deadlines', [])
                        date_str = extracts[0].get('date', '') if extracts and isinstance(extracts, list) and isinstance(extracts[0], dict) else ''
                        task_title = f"Дедлайн {date_str}".strip() or "Новый дедлайн"
                    elif category == 'announcement':
                        # Use first sentence or first few words
                        first_line = summary.split('.')[0]
                        task_title = (first_line[:50] + '...') if len(first_line) > 50 else first_line
                        if not task_title:
                            task_title = "Важное объявление"
                    elif category == 'link':
                         task_title = "Полезные ссылки"
                    elif importance >= 6:
                        task_title = "Важное сообщение"

                target_task = None
                
                # Context Inheritance Logic
                reply_to_msg_id = data.metadata.get('reply_to_msg_id')
                tg_chat_id = data.metadata.get('tg_chat_id')
                
                if reply_to_msg_id and tg_chat_id:
                    try:
                        # Find the parent message in DB. We need to filter by chat because IDs are only unique within a chat (mostly)
                        # But wait, tg_chat_id in metadata might be different from internal chat ID.
                        # Actually data.source_id is the internal Message.id. Message object is already fetched as 'message'.
                        # message.chat.tg_chat_id is available.
                        
                        parent_msg = Message.objects.filter(
                            tg_message_id=reply_to_msg_id,
                            chat=message.chat
                        ).first()
                        
                        if parent_msg:
                            # Look for any task linked to this parent message
                            related_entry = KnowledgeEntry.objects.filter(
                                source_message=parent_msg, 
                                course_task__isnull=False
                            ).first()
                            
                            if related_entry:
                                target_task = related_entry.course_task
                                logger.info(f"Inherited task '{target_task.title}' from parent message {parent_msg.id}")
                    except Exception as e:
                        logger.warning(f"Failed to inherit task: {e}")

                # Try to interpret task logic if it's significant AND we haven't found one yet
                # Rewritten condition: If we have a title, treat it as a task candidate.
                if not target_task and task_title: 
                    
                    # 1. Search for existing task
                    search_query = f"{task_title} {summary}"
                    existing = vector_db.search_tasks(search_query, threshold=0.82)
                    
                    if existing:
                        # Update existing task
                        best_match = existing[0]
                        vector_id = best_match['id']
                        try:
                            target_task = CourseTask.objects.get(vector_id=vector_id)
                            logger.info(f"Matched existing task: {target_task.title} (Score: {best_match['score']})")
                            
                            # Update logic based on action
                            if action == 'cancel':
                                target_task.status = 'cancelled'
                                target_task.save()
                            elif action == 'completed':
                                target_task.status = 'completed'
                                target_task.save()
                                
                        except CourseTask.DoesNotExist:
                            logger.warning(f"Vector ID {vector_id} found in Qdrant but not in DB")
                    
                    if not target_task:
                        # Create new task if not found
                        # Use uuid for vector id
                        new_vector_id = str(uuid.uuid4())
                        target_task = CourseTask.objects.create(
                            title=task_title,
                            description=summary,
                            task_type=analysis_result.get('task_type', 'one_time'),
                            vector_id=new_vector_id,
                            status='active'
                        )
                        
                        # Upsert to Vector DB
                        vector_db.upsert_task(
                            task_id=new_vector_id,
                            text=f"{task_title} {summary}",
                            payload={"title": task_title, "type": analysis_result.get('task_type')}
                        )

                # Create KnowledgeEntry
                if summary:
                    # Determine entry type
                    entry_type = 'generic'
                    if category == 'deadline': entry_type = 'deadline'
                    elif category == 'link': entry_type = 'link'
                    elif data.metadata.get('is_reply'): entry_type = 'explanation'
                    
                    KnowledgeEntry.objects.create(
                        source_message=message,
                        course_task=target_task,
                        entry_type=entry_type,
                        content=summary,
                        metadata={
                            'deadlines': analysis_result.get('extracted_deadlines'),
                            'links': analysis_result.get('extracted_links'),
                            'original_action': action
                        }
                    )

                links = analysis_result.get('extracted_links') or []
                if isinstance(links, str):
                    links = [links]
                if not isinstance(links, list):
                    links = []
                seen_links = set()
                for link in links:
                    link_text = str(link).strip()
                    if not link_text or link_text in seen_links:
                        continue
                    seen_links.add(link_text)
                    KnowledgeEntry.objects.get_or_create(
                        source_message=message,
                        course_task=target_task,
                        entry_type='link',
                        content=link_text,
                    )

                deadlines = analysis_result.get('extracted_deadlines') or []
                if isinstance(deadlines, dict):
                    deadlines = [deadlines]
                if isinstance(deadlines, str):
                    deadlines = [{"date": deadlines, "description": ""}]
                if not isinstance(deadlines, list):
                    deadlines = []
                seen_deadlines = set()
                for item in deadlines:
                    if isinstance(item, str):
                        date_text = item.strip()
                        description = ""
                    elif isinstance(item, dict):
                        date_text = str(item.get("date") or "").strip()
                        description = str(item.get("description") or "").strip()
                    else:
                        continue
                    if not date_text and not description:
                        continue
                    content_parts = [part for part in [date_text, description] if part]
                    content = " - ".join(content_parts)
                    dedupe_key = (date_text, description)
                    if dedupe_key in seen_deadlines:
                        continue
                    seen_deadlines.add(dedupe_key)
                    KnowledgeEntry.objects.get_or_create(
                        source_message=message,
                        course_task=target_task,
                        entry_type='deadline',
                        content=content,
                    )

                logger.info(f"Successfully processed message {message.id}")

            except Message.DoesNotExist:
                logger.error(f"Message with ID {data.source_id} not found.")

        else:
            # Handle other sources (Stub for now)
            logger.info(f"Processed non-telegram source: {analysis_result}")

    except Exception as e:
        logger.error(f"Error in process_content_task: {e}", exc_info=True)
