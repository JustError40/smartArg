from django.db import models
from core.models import Message

class AnalysisResult(models.Model):
    CATEGORIES = [
        ('announcement', 'Announcement'),
        ('deadline', 'Deadline'),
        ('link', 'Link'),
        ('other', 'Other'),
    ]

    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='analysis_result')
    category = models.CharField(max_length=50, choices=CATEGORIES, default='other')
    importance_score = models.IntegerField(default=0, help_text="Score from 0 to 10")
    summary = models.TextField(blank=True, null=True)
    extracted_links = models.JSONField(default=list, blank=True)
    extracted_deadlines = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis of Msg {self.message_id} ({self.category})"


class CourseTask(models.Model):
    """
    Represents a distinct task or topic identified from the chat.
    Aggregates information from multiple messages.
    """
    TASK_TYPES = [
        ('one_time', 'Разовая'),
        ('periodic', 'Периодическая'),
    ]
    STATUSES = [
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default='one_time')
    status = models.CharField(max_length=20, choices=STATUSES, default='active')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Stores the vector ID from Qdrant to easily sync or specific metadata
    vector_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class KnowledgeEntry(models.Model):
    ENTRY_TYPES = [
        ('deadline', 'Deadline'),
        ('link', 'Link'),
        ('explanation', 'Explanation'), # Q&A or teacher clarifications
        ('generic', 'Generic Info'),
    ]

    source_message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='knowledge_entries')
    # Link entry to a specific task
    course_task = models.ForeignKey(CourseTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='entries')
    
    entry_type = models.CharField(max_length=50, choices=ENTRY_TYPES)
    content = models.TextField()
    
    # For structured data if needed
    metadata = models.JSONField(default=dict, blank=True) 

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.entry_type}] {self.content[:50]}"
