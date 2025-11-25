"""Simple mock LLM server for local development."""

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()


class CompletionRequest(BaseModel):
    model: str
    prompt: str
    temperature: float = 0.0
    max_tokens: int = 1024
    stop: list = None


class ChatRequest(BaseModel):
    model: str
    messages: list
    temperature: float = 0.0
    max_tokens: int = 1024


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/v1/completions")
def completions(request: CompletionRequest):
    """Mock OpenAI-compatible completions endpoint."""
    # Extract query from prompt (simple heuristic)
    prompt = request.prompt
    if "User question:" in prompt:
        query = prompt.split("User question:")[-1].split("\n")[0].strip()
    else:
        query = prompt[-200:]

    # Mock response
    answer = f"""Based on the retrieved documentation, here's what I found regarding "{query}":

The relevant information can be found in the Spectrum documentation. Please refer to the sources below for complete details.

**Sources:**
- [Spectrum Documentation](https://spectrum.adobe.com/)

Note: This is a mock response. Configure a real LLM service for production use."""

    return {
        "choices": [{
            "text": answer,
            "finish_reason": "stop"
        }],
        "model": request.model,
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(answer.split()),
            "total_tokens": len(prompt.split()) + len(answer.split())
        }
    }


@app.post("/v1/chat/completions")
def chat_completions(request: ChatRequest):
    """Mock OpenAI-compatible chat completions endpoint."""
    # Extract user message
    user_message = None
    for msg in request.messages:
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    if not user_message:
        user_message = "How do I use Spectrum components?"

    # Mock response
    answer = f"""Based on the retrieved documentation, here's what I found:

The relevant information can be found in the Spectrum documentation. Please refer to the sources below for complete details.

**Sources:**
- [Spectrum Documentation](https://spectrum.adobe.com/)

Note: This is a mock response. Configure a real LLM service for production use."""

    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": answer
            },
            "finish_reason": "stop"
        }],
        "model": request.model,
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": len(answer.split()),
            "total_tokens": 100 + len(answer.split())
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

