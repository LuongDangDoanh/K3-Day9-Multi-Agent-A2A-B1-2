"""Optional structured-output policy audit using the requested OpenAI model."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .config import MAX_LLM_AUDIT_TOKENS, MODEL_NAME


class OpenAIAuditClient:
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is empty; omit --llm-audit or put a key in .env")

    def review(self, case_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
        schema = {
            "name": "policy_audit",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "consistent": {"type": "boolean"},
                    "note": {"type": "string"},
                },
                "required": ["consistent", "note"],
                "additionalProperties": False,
            },
        }
        body = {
            "model": MODEL_NAME,
            "temperature": 0,
            "max_tokens": MAX_LLM_AUDIT_TOKENS,
            "messages": [
                {"role": "system", "content": "Audit internal consistency only. Never invent evidence or change numeric values."},
                {"role": "user", "content": json.dumps({"case_id": case_id, "candidate": candidate}, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_schema", "json_schema": schema},
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"OpenAI audit failed with HTTP {exc.code}: {detail}") from exc
        return json.loads(payload["choices"][0]["message"]["content"])
