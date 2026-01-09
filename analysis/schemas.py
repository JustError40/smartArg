from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class IngestionData(BaseModel):
    """
    Standardized payload for content to be analyzed by the AI engine.
    Decouples the source (Telegram, Web, File) from the analysis logic.
    """
    text: str = Field(..., description="The raw text content to analyze")
    source_type: str = Field(..., description="The type of source: 'telegram', 'web_schedule', etc.")
    source_id: str = Field(..., description="Unique identifier in the source system (e.g. msg_id or url)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual info (sender_role, chat_title, etc.)")
