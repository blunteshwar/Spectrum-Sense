"""LLM inference service with prompt composition."""

import os
from typing import List, Dict, Optional
import httpx
import structlog

logger = structlog.get_logger(__name__)

# System prompt template
SYSTEM_PROMPT_TEMPLATE = """You are SpectrumGPT — an assistant restricted to answering only from the provided retrieved passages.

Rules:
1. Use only the retrieved passages for Spectrum-specific facts. If the answer isn't present, say "I couldn't find an authoritative answer in the indexed Spectrum docs or Slack corpus."
2. Cite every factual claim with the snippet source in brackets: [title — heading — url].
3. Preserve code blocks and include them verbatim with citations.
4. At the end include a "Sources" section listing used snippets.
5. Do not hallucinate versions, commits, or private user data.

Retrieved passages:
{context}
"""


class PromptComposer:
    """Composes prompts for LLM with context and token budget management."""

    def __init__(self, max_context_tokens: int = 3000):
        self.max_context_tokens = max_context_tokens
        # Rough estimate: 1 token ≈ 4 characters
        self.chars_per_token = 4

    def compose_prompt(
        self,
        user_query: str,
        retrieved_chunks: List[Dict],
        system_prompt_template: str = SYSTEM_PROMPT_TEMPLATE
    ) -> str:
        """Compose prompt with retrieved context."""
        # Format context from chunks
        context_parts = []
        total_chars = 0
        max_chars = self.max_context_tokens * self.chars_per_token

        for chunk in retrieved_chunks:
            payload = chunk.get("payload", {})
            title = payload.get("title", "Untitled")
            heading = payload.get("heading_path", "")
            url = payload.get("url", "")
            text = payload.get("chunk_text", "")
            chunk_id = payload.get("id", "")

            # Format chunk
            chunk_text = f"[{chunk_id}] {title}"
            if heading:
                chunk_text += f" > {heading}"
            chunk_text += f"\n{text}\n"

            chunk_chars = len(chunk_text)
            if total_chars + chunk_chars > max_chars:
                break

            context_parts.append(chunk_text)
            total_chars += chunk_chars

        context = "\n---\n".join(context_parts)

        # Compose full prompt
        system_prompt = system_prompt_template.format(context=context)
        full_prompt = f"{system_prompt}\n\nUser question: {user_query}\n\nAnswer:"

        return full_prompt


class LLMService:
    """LLM inference service."""

    def __init__(
        self,
        service_url: str,
        model_name: str = "mistral-7b-instruct",
        temperature: float = 0.0,
        max_tokens: int = 1024
    ):
        self.service_url = service_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = httpx.Client(timeout=120.0)
        self.prompt_composer = PromptComposer()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text from prompt."""
        temp = temperature if temperature is not None else self.temperature
        max_toks = max_tokens if max_tokens is not None else self.max_tokens

        # Try different API formats (prioritize chat format for Ollama)
        try:
            # Format 1: Chat format (preferred for Ollama)
            # Split prompt into system and user messages
            prompt_parts = prompt.split("User question:")
            system_content = prompt_parts[0].strip() if len(prompt_parts) > 1 else ""
            user_content = prompt_parts[-1].strip() if prompt_parts else prompt
            
            messages = []
            if system_content:
                messages.append({"role": "system", "content": system_content})
            messages.append({"role": "user", "content": user_content})
            
            response = self.client.post(
                f"{self.service_url}/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": max_toks,
                    "stop": ["Sources:", "\n\nSources:"]
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        except Exception as e1:
            logger.warning("Chat format failed, trying completions format", error=str(e1))
            try:
                # Format 2: OpenAI-compatible completions
                response = self.client.post(
                    f"{self.service_url}/v1/completions",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "temperature": temp,
                        "max_tokens": max_toks,
                        "stop": ["Sources:", "\n\nSources:"]
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("choices", [{}])[0].get("text", "").strip()

            except Exception as e2:
                logger.error("Both API formats failed", error1=str(e1), error2=str(e2))
                raise

    def answer_query(
        self,
        query: str,
        retrieved_chunks: List[Dict]
    ) -> str:
        """Answer a query using retrieved chunks."""
        prompt = self.prompt_composer.compose_prompt(query, retrieved_chunks)
        answer = self.generate(prompt)
        return answer


class MockLLMService:
    """Mock LLM service for local development."""

    def __init__(self):
        self.prompt_composer = PromptComposer()

    def answer_query(self, query: str, retrieved_chunks: List[Dict]) -> str:
        """Return a mock answer."""
        if not retrieved_chunks:
            return "I couldn't find an authoritative answer in the indexed Spectrum docs or Slack corpus."

        # Simple mock: extract first chunk's title
        first_chunk = retrieved_chunks[0]
        title = first_chunk.get("payload", {}).get("title", "documentation")
        url = first_chunk.get("payload", {}).get("url", "")

        mock_answer = f"""Based on the retrieved documentation about {title}, here's what I found:

The relevant information can be found in the Spectrum documentation. Please refer to the source for complete details.

**Sources:**
- [{title}]({url})

Note: This is a mock response. Configure a real LLM service for production use."""
        return mock_answer


def create_llm_service(
    service_url: Optional[str] = None,
    model_name: str = "mistral:7b",
    use_mock: bool = False
):
    """Factory function to create LLM service."""
    if use_mock or not service_url:
        logger.info("Using mock LLM service")
        return MockLLMService()

    return LLMService(service_url=service_url, model_name=model_name)

