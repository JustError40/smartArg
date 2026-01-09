import logging
from celery import shared_task
from django.conf import settings
from .schemas import IngestionData
from .ai_engine import AIService
from .models import AnalysisResult, KnowledgeEntry
from core.models import Message

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
                    }
                )

                # Create KnowledgeEntry if important or specific category
                if analysis_result.get('importance_score', 0) > 5 or \
                   analysis_result.get('category') in ['deadline', 'announcement', 'link']:

                    entry_type = 'info'
                    if analysis_result.get('category') == 'deadline':
                        entry_type = 'deadline'
                    elif analysis_result.get('category') == 'link':
                        entry_type = 'link'

                    KnowledgeEntry.objects.create(
                        source_message=message,
                        entry_type=entry_type,
                        content=analysis_result.get('summary', '')
                    )

                logger.info(f"Successfully processed message {message.id}")

            except Message.DoesNotExist:
                logger.error(f"Message with ID {data.source_id} not found.")

        else:
            # Handle other sources (Stub for now)
            logger.info(f"Processed non-telegram source: {analysis_result}")

    except Exception as e:
        logger.error(f"Error in process_content_task: {e}", exc_info=True)
