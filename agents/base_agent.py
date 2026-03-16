"""
Base Agent — API calls, retry logic, and JSON parsing.
All other agents inherit from this class.
"""

import json
import os
import re
import time
from pathlib import Path

import anthropic

# Load .env if present (for local development)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass


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
        self.client = anthropic.Anthropic()

        # Usage tracking
        self._calls = 0
        self._total_tokens = 0

    def call(self, system_prompt: str, user_message: str, max_retries: int = 3) -> dict:
        """
        Call the Claude API with retry logic.

        Args:
            system_prompt: The system prompt for this agent.
            user_message: The user-facing message/task.
            max_retries: Number of retries on failure.

        Returns:
            Parsed JSON dict from the model response.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                self._calls += 1
                usage = response.usage
                self._total_tokens += usage.input_tokens + usage.output_tokens

                content = response.content[0].text
                return self._parse_json(content)

            except anthropic.RateLimitError as e:
                wait_time = 2 ** attempt * 5  # Longer wait for rate limits
                print(f"  [{self.name}] Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                last_error = e

            except anthropic.APIError as e:
                wait_time = 2 ** attempt
                print(f"  [{self.name}] API error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                last_error = e

            except json.JSONDecodeError as e:
                print(f"  [{self.name}] JSON parse error (attempt {attempt + 1}/{max_retries}): {e}")
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(1)

        raise RuntimeError(f"[{self.name}] Failed after {max_retries} attempts. Last error: {last_error}")

    def _parse_json(self, content: str) -> dict:
        """
        Extract and parse JSON from model response.

        Handles:
        1. Pure JSON response
        2. JSON wrapped in markdown code blocks
        3. JSON embedded in text
        """
        content = content.strip()

        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to extract from ```json ... ``` block
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find the outermost JSON object
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # Try to find a JSON array
        match = re.search(r"\[[\s\S]*\]", content)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError(
            f"[{self.name}] Could not parse JSON from response:\n{content[:500]}",
            content,
            0,
        )

    def get_usage_summary(self) -> dict:
        """Return token usage statistics."""
        return {
            "agent": self.name,
            "calls": self._calls,
            "total_tokens": self._total_tokens,
        }
