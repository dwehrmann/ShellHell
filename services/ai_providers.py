"""AI Provider abstraction for multiple LLM backends."""

import os
from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """Base class for AI providers."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize provider with API key."""
        self.api_key = api_key

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
        """
        Generate text from prompt.

        Args:
            prompt: The prompt text
            temperature: Sampling temperature
            json_mode: Whether to request JSON output

        Returns:
            Generated text
        """
        pass


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini provider."""
        super().__init__(api_key)
        self.client = None
        self.model_name = 'gemini-2.5-flash'

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Gemini init error: {e}")

    def is_available(self) -> bool:
        """Check if Gemini is available."""
        return self.client is not None

    def generate(self, prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
        """Generate text with Gemini."""
        if not self.is_available():
            return ""

        try:
            config = {'temperature': temperature}
            if json_mode:
                config['response_mime_type'] = 'application/json'

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            print(f"Gemini generate error: {e}")
            return ""


class DeepSeekProvider(AIProvider):
    """DeepSeek provider (via OpenAI-compatible API)."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize DeepSeek provider."""
        super().__init__(api_key)
        self.client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com"
                )
            except Exception as e:
                print(f"DeepSeek init error: {e}")

    def is_available(self) -> bool:
        """Check if DeepSeek is available."""
        return self.client is not None

    def generate(self, prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
        """Generate text with DeepSeek."""
        if not self.is_available():
            return ""

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"DeepSeek generate error: {e}")
            return ""


class OpenAIProvider(AIProvider):
    """OpenAI provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """Initialize OpenAI provider."""
        super().__init__(api_key)
        self.client = None
        self.model_name = model

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"OpenAI init error: {e}")

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return self.client is not None

    def generate(self, prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
        """Generate text with OpenAI."""
        if not self.is_available():
            return ""

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI generate error: {e}")
            return ""


def get_provider() -> AIProvider:
    """
    Get the configured AI provider from environment.

    Returns:
        Initialized AIProvider instance
    """
    provider_name = os.getenv('AI_PROVIDER', 'gemini').lower()

    if provider_name == 'gemini':
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('API_KEY')  # Backwards compat
        return GeminiProvider(api_key)
    elif provider_name == 'deepseek':
        api_key = os.getenv('DEEPSEEK_API_KEY')
        return DeepSeekProvider(api_key)
    elif provider_name == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        return OpenAIProvider(api_key, model)
    else:
        print(f"Unknown provider: {provider_name}, falling back to Gemini")
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('API_KEY')
        return GeminiProvider(api_key)
