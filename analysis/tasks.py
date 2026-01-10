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
                
                target_task = None
                
                # Try to interpret task logic if it's significant
                if task_title and (importance > 4 or category in ['deadline', 'announcement']):
                    
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
                            elif action == 'update':
                                # Maybe create a knowledge entry about the update
                                pass
                                
                        except CourseTask.DoesNotExist:
                            logger.warning(f"Vector ID {vector_id} found in Qdrant but not in DB")
                    
                    if not target_task and action in ['new', 'update', 'info']:
                        # Create new task if it looks like a new one or we didn't find the old one to update
                         # Use uuid for vector id
                        new_vector_id = str(uuid.uuid4())
                        target_task = CourseTask.objects.create(
                            title=task_title,
                            description=summary,
                            task_type=analysis_result.get('task_type', 'one_time'),
                            vector_id=new_vector_id
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
