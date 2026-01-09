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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis of Msg {self.message_id} ({self.category})"


class KnowledgeEntry(models.Model):
    ENTRY_TYPES = [
        ('deadline', 'Deadline'),
        ('info', 'Info'),
        ('link', 'Link'),
    ]

    # Ideally this would be generic to support Web Sources too,
    # but for now we link to the Message as the primary source of truth in this iteration.
    source_message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='knowledge_entries')
    entry_type = models.CharField(max_length=50, choices=ENTRY_TYPES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.entry_type}] {self.content[:50]}"
