from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from django.conf import settings
from typing import Dict, Any, List
import json
from .schemas import IngestionData

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
Determine the category: 'announcement', 'deadline', 'link', or 'other'.
Rate importance from 0 to 10.
Summarize the content briefly in Russian.
Extract any links found.
Output JSON format:
{{
    "category": "...",
    "importance_score": 0,
    "summary": "...",
    "extracted_links": ["url1", "url2"]
}}
                """),
                ("human", "Sender Role: {sender_role}\nMessage: {text}")
            ])
        elif source_type == 'web_schedule':
            return ChatPromptTemplate.from_messages([
                ("system", """
You are an intelligent assistant analyzing a schedule from a web page.
Extract the schedule details.
Output JSON format with summary and importance.
                """),
                ("human", "Content: {text}")
            ])
        else:
            # Fallback generic prompt
            return ChatPromptTemplate.from_messages([
                ("system", "Analyze the following text and summarize it."),
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
            print(f"AI Analysis failed: {e}")
            return {
                "category": "other",
                "importance_score": 0,
                "summary": "Analysis failed",
                "extracted_links": []
            }
