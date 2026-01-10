import json
import logging
import re
from typing import Any, Dict, Optional

from django.conf import settings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .schemas import IngestionData

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"(https?://[^\s<>)]+)")
DATE_PATTERN = re.compile(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b")
RUS_MONTH_PATTERN = re.compile(
    r"\b(\d{1,2})\s+"
    r"(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря"
    r"|янв|фев|мар|апр|май|июн|июл|авг|сен|сент|окт|ноя|дек)\b"
    r"(?:\s+(\d{4}))?",
    re.IGNORECASE,
)
RELATIVE_PATTERN = re.compile(
    r"\b(сегодня|завтра|послезавтра|на следующ(?:ей|ую) недел(?:е|ю)"
    r"|следующ(?:ий|ая|ее|ую)\s+(?:понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье))\b",
    re.IGNORECASE,
)

RUS_MONTHS = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
    "янв": "01",
    "фев": "02",
    "мар": "03",
    "апр": "04",
    "май": "05",
    "июн": "06",
    "июл": "07",
    "авг": "08",
    "сен": "09",
    "сент": "09",
    "окт": "10",
    "ноя": "11",
    "дек": "12",
}

DEADLINE_KEYWORDS = (
    "deadline",
    "дедлайн",
    "срок",
    "срок сдачи",
    "сдать",
    "сдача",
    "до сдачи",
    "submit",
    "due",
)
ANNOUNCEMENT_KEYWORDS = (
    "объявление",
    "announcement",
    "внимание",
    "важно",
    "срочное",
    "лекция",
    "занятие",
    "экзамен",
    "контрольная",
    "расписание",
    "пара",
    "встреча",
)
URGENT_KEYWORDS = (
    "срочно",
    "urgent",
    "asap",
    "немедленно",
)

class PromptFactory:
    """
    Returns appropriate prompts based on source type.
    """

    @staticmethod
    def get_prompt(source_type: str) -> ChatPromptTemplate:
        if source_type == 'telegram':
            return ChatPromptTemplate.from_messages([
                ("system", """
Ты — интеллектуальный помощник для анализа сообщений из российских учебных Telegram-чатов.
Твоя задача — извлечь учебные задачи и важную информацию и структурировать её для базы знаний.

Если сообщение содержит информацию о задаче (лабораторная, курсовая, экзамен, встреча и т.д.):
1. Сформулируй четкое название задачи (task_title).
2. Опиши подробности задачи на русском языке (summary).
3. Определи тип задачи (task_type): 'one_time' (разовая) или 'periodic' (периодическая, например "каждый вторник").
4. Определи тип действия (action): 
   - 'new' (новая задача)
   - 'update' (обновление условий, перенос сроков существующей задачи)
   - 'cancel' (отмена задачи)
   - 'info' (просто информация, не задача)
5. Извлеки дедлайны. Если задача периодическая, укажи паттерн в description, а в deadline укажи ближайшую дату.
6. Оцени важность (0-10). Сообщения преподавателя — 8-10.

ВАЖНО: Результат должен быть JSON.
Формат JSON:
{{
    "category": "deadline" | "announcement" | "link" | "other",
    "importance_score": 8,
    "task_title": "Название задачи",
    "task_type": "one_time" | "periodic",
    "action": "new" | "update" | "cancel" | "info",
    "summary": "Подробное описание...",
    "extracted_links": ["url1"],
    "extracted_deadlines": [
        {{"date": "20.05.2024", "description": "Срок сдачи"}}
    ]
}}
                """),
                ("human", "Sender Role: {sender_role}\nMessage: {text}")
            ])
        elif source_type == 'web_schedule':
            return ChatPromptTemplate.from_messages([
                ("system", """
Ты — интеллектуальный помощник, анализирующий расписание с веб-страницы.
Извлеки детали расписания, дедлайны и ссылки. Результат — краткое резюме на русском.
Формат даты: DD.MM.YYYY (если есть год) или DD.MM. Относительные даты — "relative: следующий понедельник".
Верни ТОЛЬКО JSON (без markdown, без лишнего текста) в формате:
{
    "category": "...",
    "importance_score": 0,
    "summary": "...",
    "extracted_links": ["url1", "url2"],
    "extracted_deadlines": [
        {"date": "20.05.2024", "description": "Сдать отчёт"}
    ]
}
                """),
                ("human", "Content: {text}")
            ])
        else:
            # Fallback generic prompt
            return ChatPromptTemplate.from_messages([
                ("system", "Проанализируй текст и сделай краткое резюме на русском."),
                ("human", "{text}")
            ])

class AIService:
    def __init__(self):
        # Configure LLM based on environment variables
        # This supports OpenAI and compatible APIs (Z.AI, Ollama, etc.)
        self.llm = None
        try:
            self.llm = ChatOpenAI(
                model=settings.AI_MODEL_NAME,
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
                temperature=0.3,
            )
        except Exception:
            logger.exception("AI client initialization failed")
        self.parser = JsonOutputParser()

    def analyze_content(self, data: IngestionData) -> Dict[str, Any]:
        """
        Analyzes the content using the LLM.
        """
        prompt = PromptFactory.get_prompt(data.source_type)
        input_data = {
            "text": data.text,
            **data.metadata
        }

        if self.llm is None:
            return self._heuristic_result(data)

        try:
            messages = prompt.format_messages(**input_data)
            response = self.llm.invoke(messages)
        except Exception:
            logger.exception(
                "AI request failed",
                extra={"source_type": data.source_type, "source_id": data.source_id},
            )
            return self._heuristic_result(data)

        content = getattr(response, "content", str(response))
        parsed = self._parse_json(content)
        if parsed is None:
            logger.warning(
                "AI output was not valid JSON",
                extra={"source_type": data.source_type, "source_id": data.source_id},
            )
            return self._heuristic_result(data)

        normalized = self._normalize_result(parsed)
        return normalized

    def _parse_json(self, content: str) -> Optional[Any]:
        if isinstance(content, dict):
            return content
        if not content:
            return None

        try:
            return self.parser.parse(content)
        except Exception:
            pass

        snippet = self._extract_json_snippet(content)
        if snippet:
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                return None
        return None

    def _extract_json_snippet(self, content: str) -> Optional[str]:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            return content[start:end + 1]
        start = content.find('[')
        end = content.rfind(']')
        if start != -1 and end != -1 and end > start:
            return content[start:end + 1]
        return None

    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return self._fallback_result("Некорректный формат ответа")

        category = str(result.get("category", "other")).lower()
        if category not in {"announcement", "deadline", "link", "other"}:
            category = "other"

        importance_score = result.get("importance_score", 0)
        try:
            importance_score = int(importance_score)
        except (TypeError, ValueError):
            importance_score = 0
        importance_score = max(0, min(10, importance_score))

        summary = result.get("summary") or ""
        summary = str(summary)

        links = result.get("extracted_links", [])
        if isinstance(links, str):
            links = [links]
        elif not isinstance(links, list):
            links = []
        normalized_links = [str(link) for link in links if link]

        deadlines = result.get("extracted_deadlines", [])
        if isinstance(deadlines, dict):
            deadlines = [deadlines]
        elif isinstance(deadlines, str):
            deadlines = [{"date": deadlines, "description": ""}]
        elif not isinstance(deadlines, list):
            deadlines = []

        normalized_deadlines = []
        for item in deadlines:
            if isinstance(item, str):
                normalized_deadlines.append({"date": item, "description": ""})
                continue
            if not isinstance(item, dict):
                continue
            date_value = item.get("date") or item.get("date_iso") or item.get("deadline")
            description = item.get("description") or item.get("text") or item.get("summary") or ""
            if date_value or description:
                normalized_deadlines.append({
                    "date": str(date_value) if date_value else "",
                    "description": str(description) if description else "",
                })

        return {
            "category": category,
            "importance_score": importance_score,
            "summary": summary,
            "extracted_links": normalized_links,
            "extracted_deadlines": normalized_deadlines,
        }

    def _fallback_result(self, summary: str) -> Dict[str, Any]:
        return {
            "category": "other",
            "importance_score": 0,
            "summary": summary,
            "extracted_links": [],
            "extracted_deadlines": [],
        }

    def _heuristic_result(self, data: IngestionData) -> Dict[str, Any]:
        text = (data.text or "").strip()
        if not text:
            return self._fallback_result("Пустой текст")

        lower_text = text.lower()
        links = self._extract_links(text)
        deadlines = self._extract_deadlines(text)
        sender_role = str(data.metadata.get("sender_role", "")).lower()

        if deadlines:
            category = "deadline"
        elif links:
            category = "link"
        elif sender_role == "teacher" or self._contains_keyword(lower_text, ANNOUNCEMENT_KEYWORDS):
            category = "announcement"
        else:
            category = "other"

        base_scores = {
            "deadline": 8,
            "announcement": 6,
            "link": 5,
            "other": 2,
        }
        importance_score = base_scores.get(category, 0)
        if self._contains_keyword(lower_text, URGENT_KEYWORDS):
            importance_score = min(10, importance_score + 2)
        if sender_role == "teacher" and category not in {"deadline"}:
            importance_score = min(10, importance_score + 1)

        return {
            "category": category,
            "importance_score": importance_score,
            "summary": self._summarize_text(text),
            "extracted_links": links,
            "extracted_deadlines": deadlines,
        }

    def _extract_links(self, text: str) -> list:
        matches = URL_PATTERN.findall(text or "")
        cleaned = []
        seen = set()
        for match in matches:
            link = match.strip().rstrip(").,;!?\"']")
            if not link or link in seen:
                continue
            seen.add(link)
            cleaned.append(link)
        return cleaned

    def _extract_deadlines(self, text: str) -> list:
        matches = list(DATE_PATTERN.finditer(text or ""))
        month_matches = list(RUS_MONTH_PATTERN.finditer(text or ""))
        deadlines = []
        if not matches and not month_matches:
            relative_match = RELATIVE_PATTERN.search(text or "")
            if relative_match:
                description = self._extract_sentence(text, relative_match.start(), relative_match.end())
                if not description:
                    description = self._summarize_text(text)
                if description:
                    deadlines.append(
                        {"date": f"relative: {relative_match.group(1).lower()}", "description": description}
                    )
                return deadlines
            if self._contains_keyword(text.lower(), DEADLINE_KEYWORDS):
                description = self._summarize_text(text)
                if description:
                    deadlines.append({"date": "relative: скоро", "description": description})
            return deadlines

        for match in matches:
            date_text = match.group(0)
            description = self._extract_sentence(text, match.start(), match.end())
            if not description:
                description = self._summarize_text(text)
            deadlines.append({"date": date_text, "description": description})

        for match in month_matches:
            date_text = self._format_russian_date(match.group(1), match.group(2), match.group(3))
            description = self._extract_sentence(text, match.start(), match.end())
            if not description:
                description = self._summarize_text(text)
            deadlines.append({"date": date_text, "description": description})

        return self._dedupe_deadlines(deadlines)

    def _extract_sentence(self, text: str, start: int, end: int) -> str:
        left = text.rfind(".", 0, start)
        left = max(left, text.rfind("\n", 0, start))
        right = text.find(".", end)
        if right == -1:
            right = text.find("\n", end)
        snippet = text[left + 1:right] if right != -1 else text[left + 1:]
        return self._summarize_text(snippet, limit=160)

    def _summarize_text(self, text: str, limit: int = 180) -> str:
        collapsed = " ".join((text or "").strip().split())
        if len(collapsed) <= limit:
            return collapsed
        return collapsed[: max(0, limit - 3)].rstrip() + "..."

    def _contains_keyword(self, text: str, keywords: tuple) -> bool:
        return any(keyword in text for keyword in keywords)

    def _dedupe_deadlines(self, deadlines: list) -> list:
        seen = set()
        unique = []
        for item in deadlines:
            key = (item.get("date", ""), item.get("description", ""))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _format_russian_date(self, day_text: str, month_text: str, year_text: Optional[str]) -> str:
        day = day_text.zfill(2)
        month_key = (month_text or "").lower()
        month = RUS_MONTHS.get(month_key, "01")
        if year_text:
            return f"{day}.{month}.{year_text}"
        return f"{day}.{month}"
