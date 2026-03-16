"""
Base Agent
Handles Anthropic API calls, retries, JSON parsing, and usage tracking.
"""

import json
import time
import re
import anthropic


class BaseAgent:
    """Base class for all curriculum pipeline agents."""

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
        self._client = anthropic.Anthropic()
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._calls = 0

    def call(self, system_prompt: str, user_message: str, max_retries: int = 3) -> dict:
        """
        Call the Claude API and return parsed JSON.

        Retries on transient errors with exponential backoff.
        Extracts JSON from markdown code fences if present.
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

                self._calls += 1
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens

                raw = response.content[0].text
                return self._parse_json(raw)

            except anthropic.RateLimitError as e:
                wait = 2 ** attempt * 5
                print(f"  [{self.name}] Rate limit — waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                last_error = e
            except anthropic.APIStatusError as e:
                wait = 2 ** attempt * 2
                print(f"  [{self.name}] API error {e.status_code} — waiting {wait}s")
                time.sleep(wait)
                last_error = e
            except (json.JSONDecodeError, ValueError) as e:
                print(f"  [{self.name}] JSON parse error on attempt {attempt + 1}: {e}")
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(1)

        raise RuntimeError(f"[{self.name}] Failed after {max_retries} attempts: {last_error}")

    def _parse_json(self, text: str) -> dict:
        """Extract and parse JSON from raw API response text."""
        # Strip markdown code fences
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
        if fence_match:
            text = fence_match.group(1)

        # Try to find a JSON object in the text
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            text = brace_match.group(0)

        return json.loads(text)

    def get_usage_summary(self) -> dict:
        """Return token usage statistics for this agent."""
        return {
            "agent": self.name,
            "calls": self._calls,
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
        }
