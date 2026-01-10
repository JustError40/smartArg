from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from analysis.models import AnalysisResult, KnowledgeEntry
from core.models import Chat, Message


class WebViewsTests(TestCase):
    def setUp(self):
        self.chat = Chat.objects.create(
            tg_chat_id=12345,
            title="Учебный чат",
            chat_type="group",
        )
        self.message = Message.objects.create(
            chat=self.chat,
            tg_message_id=1,
            sender_name="Тестовый преподаватель",
            sender_role="teacher",
            text="Сдайте работу до пятницы",
            sent_at=timezone.now(),
        )
        AnalysisResult.objects.create(
            message=self.message,
            category="announcement",
            importance_score=8,
            summary="Напоминание о сдаче",
            extracted_links=["https://example.com"],
        )
        KnowledgeEntry.objects.create(
            source_message=self.message,
            entry_type="link",
            content="https://example.com",
        )

    def test_dashboard_view(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_messages", response.context)
        self.assertEqual(response.context["total_messages"], 1)
        self.assertTrue(response.context["pie_chart"])
        self.assertTrue(response.context["bar_chart"])

    def test_chat_list_view(self):
        response = self.client.get(reverse("chat_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("chats", response.context)
        chat = response.context["chats"][0]
        self.assertEqual(chat.message_count, 1)

    def test_knowledge_base_view(self):
        response = self.client.get(reverse("knowledge_base"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("entries", response.context)
        self.assertEqual(response.context["entries"].count(), 1)

        response = self.client.get(reverse("knowledge_base"), {"entry_type": "link"})
        self.assertEqual(response.context["entries"].count(), 1)
