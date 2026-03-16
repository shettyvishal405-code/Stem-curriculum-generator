"""
Lesson Plan Agent
Generates 5E format lesson plans with ENpower branding and Indian context.
"""

from .base_agent import BaseAgent
from utils.prompts import lesson_plan_prompt


class LessonPlanAgent(BaseAgent):
    """Generates 5E lesson plans for a given session."""

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
        """
        Generate a lesson plan for the given session.

        Args:
            session_data: Parsed session info from the framework.
            grade: Target grade (6, 7, or 8).
            session_number: Session number within the grade.
            constraints: Grade/phase-specific constraint prompt.
            guardrail_rules: Anti-hallucination and quality rules.
            previous_sessions_summary: Rolling summary of prior sessions.

        Returns:
            Structured lesson plan dict.
        """
        system_prompt = lesson_plan_prompt()

        continuity_section = ""
        if previous_sessions_summary:
            continuity_section = f"""
## PREVIOUS SESSIONS (for continuity)
{previous_sessions_summary}
Build on this prior knowledge naturally. Do NOT repeat content already covered.
"""

        user_message = f"""Generate a complete 5E lesson plan for the following session.

## SESSION DATA FROM FRAMEWORK
- Session Number: {session_number}
- Grade: {grade}
- Topic: {session_data.get("topic", "NOT_SPECIFIED")}
- Learning Outcomes: {", ".join(session_data.get("learning_outcomes", []))}
- Tangible Outcome: {session_data.get("tangible_outcome", "NOT_SPECIFIED")}
- Duration: {session_data.get("duration_minutes", 50)} minutes
- Session Position: {session_data.get("session_position_in_topic", 1)} of {session_data.get("total_sessions_in_topic", 1)} in this topic
- Notes: {session_data.get("notes", "")}

{constraints}

## GUARDRAIL RULES (MANDATORY)
{guardrail_rules}
{continuity_section}

Return a complete, detailed lesson plan as a JSON object following the specified format.
Every field must be filled. Use [VERIFY] for uncertain content."""

        result = self.call(system_prompt, user_message)

        # Ensure required fields
        result.setdefault("session_number", session_number)
        result.setdefault("grade", grade)
        result.setdefault("topic", session_data.get("topic", ""))

        return result
