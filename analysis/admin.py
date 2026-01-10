from django.contrib import admin

from .models import AnalysisResult, KnowledgeEntry


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("message", "category", "importance_score", "created_at")
    list_filter = ("category",)
    search_fields = ("summary", "message__text", "message__sender_name")


@admin.register(KnowledgeEntry)
class KnowledgeEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_type", "content", "source_message", "created_at")
    list_filter = ("entry_type",)
    search_fields = ("content", "source_message__text", "source_message__sender_name")
