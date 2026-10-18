"""A deterministic stand-in for Gemini, so agent wiring can be tested without a key or network.
It is only a model substitute: all numbers in the tests still come from the engine through MCP."""

import json
from typing import AsyncGenerator, Callable, Optional
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class ScriptedLlm(BaseLlm):
    model: str = "scripted"
    extract: Optional[dict] = None            # JSON returned when an output_schema is requested
    mutate_args: Optional[Callable] = None    # lets a test make the "model" tamper with tool arguments
    skip_tools: bool = False                  # a lazy model that never calls the tool

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        cfg = llm_request.config
        if cfg is not None and getattr(cfg, "response_schema", None) is not None and not (cfg.tools):
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=json.dumps(self.extract or {"claims": []}))]))
            return
        first_user = next((c for c in llm_request.contents if c.role == "user"), None)
        planned = json.loads(first_user.parts[0].text) if first_user and first_user.parts and first_user.parts[0].text else []
        done = [p.function_response for c in llm_request.contents for p in (c.parts or []) if p.function_response]
        if self.skip_tools or len(done) >= len(planned):
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="done")]))
            return
        args = dict(planned[len(done)])
        if self.mutate_args:
            args = self.mutate_args(args)
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(name="check_applicant_claim", args=args))]))
