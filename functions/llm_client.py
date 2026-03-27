"""
llm_client.py
-------------
Unified LLM client for DrawerDissect transcription steps.

Supports:
  - Anthropic Claude API (default)
  - Any OpenAI-compatible local server: Ollama, LM Studio, vLLM, Jan, etc.

Both clients expose the same create_message_sync() interface so OCR scripts
are provider-agnostic. Responses mimic the Anthropic shape:
  response.content[0].text  — the model's text output
  response.usage.input_tokens / .output_tokens  — token counts
"""

import logging

logging.getLogger("httpx").disabled = True
logging.getLogger("openai").disabled = True
logging.getLogger("httpcore").disabled = True


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------

class _TextBlock:
    def __init__(self, text: str):
        self.text = text


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class MessageResponse:
    """Thin wrapper that unifies Anthropic and OpenAI response shapes."""

    def __init__(self, text: str, input_tokens: int = 0, output_tokens: int = 0):
        self.content = [_TextBlock(text)]
        self.usage = _Usage(input_tokens, output_tokens)


# ---------------------------------------------------------------------------
# Content format conversion
# ---------------------------------------------------------------------------

def _to_openai_content(content_blocks: list) -> list:
    """
    Convert Anthropic-format content blocks to OpenAI chat content.

    Anthropic image block:
      {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}}
    OpenAI image block:
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    """
    result = []
    for block in content_blocks:
        if block["type"] == "text":
            result.append({"type": "text", "text": block["text"]})
        elif block["type"] == "image":
            src = block.get("source", {})
            if src.get("type") == "base64":
                url = f"data:{src['media_type']};base64,{src['data']}"
                result.append({"type": "image_url", "image_url": {"url": url}})
    return result


# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------

class AnthropicLLMClient:
    """Wraps the Anthropic SDK to produce MessageResponse objects."""

    def __init__(self, api_key: str):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic is required for Anthropic API access. "
                "Install with: pip install anthropic"
            )
        self._client = Anthropic(api_key=api_key)

        # Cache exception classes for provider-aware error handling
        try:
            from anthropic import RateLimitError, APIError
            self._RateLimitError = RateLimitError
            self._APIError = APIError
        except ImportError:
            self._RateLimitError = None
            self._APIError = None

    def create_message_sync(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: list,
        temperature: float = 0,
    ) -> MessageResponse:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return MessageResponse(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def is_rate_limit_error(self, exc) -> bool:
        return self._RateLimitError is not None and isinstance(exc, self._RateLimitError)

    def is_retryable_server_error(self, exc) -> bool:
        return (
            self._APIError is not None
            and isinstance(exc, self._APIError)
            and getattr(exc, "status_code", 0) >= 500
        )

    def is_non_retryable_client_error(self, exc) -> bool:
        return (
            self._APIError is not None
            and isinstance(exc, self._APIError)
            and getattr(exc, "status_code", 0) < 500
        )


# ---------------------------------------------------------------------------
# OpenAI-compatible client (Ollama, LM Studio, vLLM, etc.)
# ---------------------------------------------------------------------------

class OpenAICompatibleLLMClient:
    """
    Wraps an OpenAI-compatible endpoint for local model inference.

    Compatible servers (configure base_url accordingly):
      Ollama:    http://localhost:11434/v1
      LM Studio: http://localhost:1234/v1
      vLLM:      http://localhost:8000/v1
    """

    def __init__(self, base_url: str, api_key: str = "ollama"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai is required for local model support. "
                "Install with: pip install openai"
            )
        self._client = OpenAI(base_url=base_url, api_key=api_key)

        try:
            from openai import RateLimitError, APIStatusError
            self._RateLimitError = RateLimitError
            self._APIStatusError = APIStatusError
        except ImportError:
            self._RateLimitError = None
            self._APIStatusError = None

    def create_message_sync(
        self,
        model: str,
        max_tokens: int,
        system: str,
        messages: list,
        temperature: float = 0,
    ) -> MessageResponse:
        # Build OpenAI-format messages.
        # For multimodal messages (content is a list), some vLLM backends
        # cannot handle a separate system role alongside list-type content.
        # Instead, prepend the system prompt as the first text block in the
        # first user message to ensure compatibility.
        openai_messages = []
        first_user_done = False
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, list):
                content = _to_openai_content(content)
                if not first_user_done and role == "user" and system:
                    content = [{"type": "text", "text": system}] + content
                    first_user_done = True
            openai_messages.append({"role": role, "content": content})

        # If no multimodal message was found, fall back to standard system msg
        if not first_user_done and system:
            openai_messages.insert(0, {"role": "system", "content": system})

        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=openai_messages,
        )
        text = (response.choices[0].message.content or "").strip()
        usage = response.usage
        return MessageResponse(
            text=text,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    def is_rate_limit_error(self, exc) -> bool:
        return self._RateLimitError is not None and isinstance(exc, self._RateLimitError)

    def is_retryable_server_error(self, exc) -> bool:
        return (
            self._APIStatusError is not None
            and isinstance(exc, self._APIStatusError)
            and getattr(exc, "status_code", 0) >= 500
        )

    def is_non_retryable_client_error(self, exc) -> bool:
        return (
            self._APIStatusError is not None
            and isinstance(exc, self._APIStatusError)
            and getattr(exc, "status_code", 0) < 500
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_llm_client(config):
    """
    Return the correct LLM client based on config.llm_config['provider'].

    Args:
        config: DrawerDissectConfig instance

    Returns:
        AnthropicLLMClient or OpenAICompatibleLLMClient
    """
    llm_cfg = config.llm_config
    provider = llm_cfg.get("provider", "anthropic")

    if provider == "anthropic":
        return AnthropicLLMClient(api_key=config.api_keys["anthropic"])

    if provider == "openai_compatible":
        oc = llm_cfg.get("openai_compatible", {})
        return OpenAICompatibleLLMClient(
            base_url=oc.get("base_url", "http://localhost:11434/v1"),
            api_key=oc.get("api_key", "ollama"),
        )

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. "
        "Set llm.provider to 'anthropic' or 'openai_compatible' in config.yaml."
    )
