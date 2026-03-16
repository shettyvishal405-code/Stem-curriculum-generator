"""
Lesson Plan Agent — generates 5E format lesson plans for ENpower STEM Labs.
"""

from .base_agent import BaseAgent
from utils.prompts import lesson_plan_prompt


class LessonPlanAgent(BaseAgent):

    def __init__(self, model: str, max_tokens: int = 4096):
        super().__init__(
            name="LessonPlanAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
        )

    def generate(
        self,
        session_data: dict,
        grade: int,
        session_number: int,
        constraints: str,
        guardrail_rules: str,
        previous_sessions_summary: str = "",
    ) -> dict:
        system_prompt = lesson_plan_prompt()

        context_parts = []
        if previous_sessions_summary:
            context_parts.append(f"## PREVIOUS SESSIONS (for continuity)\n{previous_sessions_summary}")

        context_parts.append(constraints)
        context_parts.append(f"## GUARDRAIL RULES\n{guardrail_rules}")

        user_message = f"""Generate a complete 5E lesson plan for:

## SESSION DATA
Session Number: {session_number}
Grade: {grade}
Topic: {session_data.get('topic', '')}
Learning Outcomes: {session_data.get('learning_outcomes', [])}
Tangible Outcome: {session_data.get('tangible_outcome', '')}
Session Position: {session_data.get('session_position_in_topic', 1)} of {session_data.get('total_sessions_in_topic', 1)}
Notes: {session_data.get('notes', '')}

{chr(10).join(context_parts)}

Return a complete JSON lesson plan following the specified format."""

        return self.call(system_prompt, user_message)
