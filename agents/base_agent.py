"""
Base Agent — wraps Anthropic API calls with retry, JSON parsing, and token tracking.
"""

import json
import os
import time
import anthropic


class BaseAgent:
    """Base class for all curriculum agents."""

    def __init__(
        self,
        name: str,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ):
        self.name = name
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        token_file = os.environ.get("CLAUDE_SESSION_INGRESS_TOKEN_FILE")
        if not api_key and not auth_token and token_file and os.path.exists(token_file):
            auth_token = open(token_file).read().strip()
        if auth_token:
            self._client = anthropic.Anthropic(auth_token=auth_token)
        else:
            self._client = anthropic.Anthropic(api_key=api_key or "dummy")
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._call_count = 0

    def call(self, system_prompt: str, user_message: str, max_retries: int = 3) -> dict:
        """
        Call the Claude API and return parsed JSON.

        Retries on transient errors with exponential backoff.
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                self._call_count += 1
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens

                content = response.content[0].text
                return self._parse_json(content)

            except anthropic.RateLimitError as e:
                wait = 2 ** (attempt + 1)
                print(f"  [{self.name}] Rate limit hit, waiting {wait}s...")
                time.sleep(wait)
                last_error = e

            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    wait = 2 ** (attempt + 1)
                    print(f"  [{self.name}] API error {e.status_code}, retrying in {wait}s...")
                    time.sleep(wait)
                    last_error = e
                else:
                    raise

            except json.JSONDecodeError as e:
                print(f"  [{self.name}] JSON parse error on attempt {attempt + 1}: {e}")
                last_error = e

        raise RuntimeError(f"[{self.name}] Failed after {max_retries} attempts. Last error: {last_error}")

    def _parse_json(self, text: str) -> dict:
        """Extract and parse JSON from the response text."""
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        for marker in ["```json", "```"]:
            if marker in text:
                start = text.find(marker) + len(marker)
                end = text.find("```", start)
                if end > start:
                    try:
                        return json.loads(text[start:end].strip())
                    except json.JSONDecodeError:
                        pass

        # Try to find JSON object boundaries
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError("No valid JSON found in response", text, 0)

    def get_usage_summary(self) -> dict:
        return {
            "agent": self.name,
            "calls": self._call_count,
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
        }
