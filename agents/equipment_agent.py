"""
Equipment Agent — generates lab equipment lists with Indian supplier pricing.
"""

from .base_agent import BaseAgent
from utils.prompts import equipment_prompt


class EquipmentAgent(BaseAgent):

    def __init__(self, model: str, max_tokens: int = 4096):
        super().__init__(
            name="EquipmentAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,
        )

    def generate(self, lesson_plan: dict, guardrail_rules: str, allowed_tools: list = None) -> dict:
        system_prompt = equipment_prompt()

        allowed_str = ""
        if allowed_tools:
            allowed_str = f"\n\nCRITICAL: ONLY include items from this allowed list: {', '.join(allowed_tools)}. Do NOT add any other items."

        user_message = f"""Generate an equipment list for this lesson:

Session: {lesson_plan.get('session_number')}
Topic: {lesson_plan.get('topic')}
Materials Needed: {lesson_plan.get('materials_needed', [])}
Activities:
- Explore: {lesson_plan.get('5e_phases', {}).get('explore', {}).get('activity_name', '')}
- Elaborate: {lesson_plan.get('5e_phases', {}).get('elaborate', {}).get('activity_name', '')}
{allowed_str}

Return a complete JSON equipment list following the specified format."""

        return self.call(system_prompt, user_message)
