"""
PPT Agent — generates student-facing presentation content.
"""

from .base_agent import BaseAgent
from utils.prompts import ppt_prompt


class PPTAgent(BaseAgent):

    def __init__(self, model: str, branding: dict, max_tokens: int = 4096):
        super().__init__(
            name="PPTAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        self.branding = branding

    def generate(self, lesson_plan: dict, grade: int, guardrail_rules: str) -> dict:
        system_prompt = ppt_prompt()

        user_message = f"""Generate a student PPT for this lesson:

Session: {lesson_plan.get('session_number')}
Grade: {grade}
Topic: {lesson_plan.get('topic')}
Learning Objectives: {lesson_plan.get('learning_objectives', [])}
Key Vocabulary: {lesson_plan.get('vocabulary', [])}
5E Flow:
- Engage hook: {lesson_plan.get('5e_phases', {}).get('engage', {}).get('indian_context', '')}
- Explore activity: {lesson_plan.get('5e_phases', {}).get('explore', {}).get('activity_name', '')}
- Key concepts: {lesson_plan.get('5e_phases', {}).get('explain', {}).get('key_concepts', [])}
- Elaborate activity: {lesson_plan.get('5e_phases', {}).get('elaborate', {}).get('activity_name', '')}
Tangible Outcome: {lesson_plan.get('tangible_outcome', '')}

## GUARDRAIL RULES
{guardrail_rules}

Return a complete JSON PPT following the specified format."""

        return self.call(system_prompt, user_message)
