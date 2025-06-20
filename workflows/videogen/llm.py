"""
Large language model.
"""

from abc import ABC, abstractmethod
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel


class BaseLargeLanguageModel(ABC):
    """
    Base class for LLM providers.
    """

    @abstractmethod
    async def generate_content(
        self, prompt: str, response_schema: BaseModel | list[BaseModel]
    ) -> str:
        """
        Generate content from the LLM.
        """
        raise NotImplementedError("Subclasses must implement this method")


class GoogleGemini(BaseLargeLanguageModel):
    """
    Using Google Gemini as a large language model.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    async def generate_content(
        self,
        prompt: str,
        response_schema: BaseModel | list[BaseModel] | None = None,
    ) -> Any:
        if response_schema:
            gemini_config = types.GenerateContentConfig(
                # Enable dynamic thinking
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                response_mime_type="application/json",
                response_schema=response_schema,
            )
        else:
            gemini_config = types.GenerateContentConfig(
                # Enable dynamic thinking
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
            )

        response = await self._client.aio.models.generate_content(
            model=self._model_name, contents=prompt, config=gemini_config
        )
        return response.parsed if response_schema else response.text
