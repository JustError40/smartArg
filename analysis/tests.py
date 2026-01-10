import json
from unittest.mock import patch

from django.test import TestCase

from analysis.ai_engine import AIService
from analysis.schemas import IngestionData


class AIServiceTests(TestCase):
    @patch("analysis.ai_engine.ChatOpenAI")
    def test_analyze_content_parses_json(self, mock_llm):
        mock_llm.return_value.invoke.return_value = type(
            "FakeResponse",
            (),
            {"content": json.dumps({
                "category": "announcement",
                "importance_score": 7,
                "summary": "Тестовое объявление",
                "extracted_links": ["https://example.com"],
                "extracted_deadlines": [{"date": "2024-05-20", "description": "Сдать отчёт"}],
            })},
        )()

        service = AIService()
        data = IngestionData(
            text="Test message",
            source_type="telegram",
            source_id="1",
            metadata={"sender_role": "teacher"},
        )
        result = service.analyze_content(data)

        self.assertEqual(result["category"], "announcement")
        self.assertEqual(result["importance_score"], 7)
        self.assertEqual(result["summary"], "Тестовое объявление")
        self.assertEqual(result["extracted_links"], ["https://example.com"])
        self.assertEqual(result["extracted_deadlines"][0]["date"], "2024-05-20")

    @patch("analysis.ai_engine.ChatOpenAI")
    def test_analyze_content_handles_invalid_json(self, mock_llm):
        mock_llm.return_value.invoke.return_value = type(
            "FakeResponse",
            (),
            {"content": "not a json response"},
        )()

        service = AIService()
        data = IngestionData(
            text="Test message",
            source_type="telegram",
            source_id="2",
            metadata={"sender_role": "student"},
        )
        result = service.analyze_content(data)

        self.assertEqual(result["category"], "other")
        self.assertEqual(result["summary"], "Test message")
        self.assertEqual(result["importance_score"], 2)
