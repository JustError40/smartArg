from django.contrib import admin

from .models import Chat, Message


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("title", "tg_chat_id", "chat_type", "created_at")
    search_fields = ("title", "tg_chat_id")
    list_filter = ("chat_type",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender_name", "chat", "sender_role", "sent_at")
    search_fields = ("text", "sender_name", "chat__title")
    list_filter = ("sender_role", "chat__chat_type")
    ordering = ("-sent_at",)
