from django.db import models

class Chat(models.Model):
    CHAT_TYPES = [
        ('group', 'Group'),
        ('supergroup', 'Supergroup'),
        ('private', 'Private'),
        ('channel', 'Channel'),
        ('unknown', 'Unknown'),
    ]

    tg_chat_id = models.BigIntegerField(unique=True, verbose_name="Telegram Chat ID")
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chat Title")
    chat_type = models.CharField(max_length=20, choices=CHAT_TYPES, default='unknown', verbose_name="Chat Type")
    pinned_teacher_id = models.BigIntegerField(null=True, blank=True, verbose_name="Pinned Teacher Telegram ID")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or str(self.tg_chat_id)

class Message(models.Model):
    SENDER_ROLES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('unknown', 'Unknown'),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    tg_message_id = models.BigIntegerField(verbose_name="Telegram Message ID")
    sender_name = models.CharField(max_length=255, blank=True, null=True)
    sender_role = models.CharField(max_length=20, choices=SENDER_ROLES, default='unknown')
    text = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(verbose_name="Sent At")

    class Meta:
        unique_together = ('chat', 'tg_message_id')
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.sender_name}: {self.text[:20]}"
