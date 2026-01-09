from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from django.conf import settings
from typing import Dict, Any, List
import logging
import json
from .schemas import IngestionData

logger = logging.getLogger(__name__)

class PromptFactory:
    """
    Returns appropriate prompts based on source type.
    """

    @staticmethod
    def get_prompt(source_type: str) -> ChatPromptTemplate:
        if source_type == 'telegram':
            return ChatPromptTemplate.from_messages([
                ("system", """
You are an intelligent assistant analyzing messages from student Telegram chats.
Your goal is to extract important information and categorize the message.

Tasks:
1. Determine the category: 'announcement', 'deadline', 'link', or 'other'.
2. Rate importance from 0 to 10 (10 is critical, e.g., exams, immediate deadlines).
3. Summarize the content briefly and clearly in Russian.
4. Extract any valid HTTP/HTTPS links found in the text.
5. If a deadline is mentioned, try to extract it as a string (e.g., "2023-10-25" or "next Friday").

Output purely JSON format with no Markdown formatting:
{{
    "category": "category_name",
    "importance_score": integer_0_to_10,
    "summary": "Russian summary text",
    "extracted_links": ["url1", "url2"],
    "deadline_date": "extracted date string or null"
}}
                """),
                ("human", "Sender Role: {sender_role}\nMessage: {text}")
            ])
        elif source_type == 'web_schedule':
            return ChatPromptTemplate.from_messages([
                ("system", """
You are an intelligent assistant analyzing a schedule from a web page.
Extract the schedule details such as subject, time, and location.

Output purely JSON format with no Markdown formatting:
{{
    "category": "announcement",
    "importance_score": 5,
    "summary": "Summary of schedule updates or details in Russian",
    "extracted_links": [],
    "schedule_details": "Extracted details"
}}
                """),
                ("human", "Content: {text}")
            ])
        else:
            # Fallback generic prompt
            return ChatPromptTemplate.from_messages([
                ("system", "Analyze the following text and summarize it. Output JSON with keys: summary, category, importance_score."),
                ("human", "{text}")
            ])

class AIService:
    def __init__(self):
        # Configure LLM based on environment variables
        # This supports OpenAI and compatible APIs (Z.AI, Ollama, etc.)
        self.llm = ChatOpenAI(
            model=settings.AI_MODEL_NAME,
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            temperature=0.3
        )

    def analyze_content(self, data: IngestionData) -> Dict[str, Any]:
        """
        Analyzes the content using the LLM.
        """
        prompt = PromptFactory.get_prompt(data.source_type)
        chain = prompt | self.llm | JsonOutputParser()

        input_data = {
            "text": data.text,
            **data.metadata
        }

        try:
            result = chain.invoke(input_data)
            return result
        except Exception as e:
            # Fallback in case of parsing error or API failure
            logger.error(f"AI Analysis failed: {e}")
            return {
                "category": "other",
                "importance_score": 0,
                "summary": "AI Analysis failed to process this message.",
                "extracted_links": [],
                "deadline_date": None
            }
