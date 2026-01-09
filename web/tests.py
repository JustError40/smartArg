from django.test import TestCase, Client
from django.urls import reverse
from core.models import Chat, Message
from analysis.models import KnowledgeEntry

class WebViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.chat = Chat.objects.create(tg_chat_id=123, title="Test Chat", chat_type="group")
        self.message = Message.objects.create(
            chat=self.chat,
            tg_message_id=1,
            text="Deadline tomorrow",
            sent_at="2023-01-01 12:00:00"
        )
        self.entry = KnowledgeEntry.objects.create(
            source_message=self.message,
            entry_type='deadline',
            content='Test Deadline'
        )

    def test_dashboard_status_code(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Дашборд аналитики")

    def test_chat_list_view(self):
        response = self.client.get(reverse('chat_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Chat")

    def test_knowledge_base_view(self):
        response = self.client.get(reverse('knowledge_base'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Deadline")
