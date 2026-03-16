"""
Lesson Plan Agent — generates 5E format lesson plans.
"""

from .base_agent import BaseAgent
from utils.prompts import lesson_plan_prompt


class LessonPlanAgent(BaseAgent):
    """Generates 5E lesson plans aligned to the curriculum framework."""

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
        Generate a 5E lesson plan for the given session.

        Args:
            session_data: Parsed session info from the framework.
            grade: Target grade (6, 7, or 8).
            session_number: Current session number.
            constraints: Phase-specific constraint prompt.
            guardrail_rules: Global guardrail rules.
            previous_sessions_summary: Continuity context from prior sessions.

        Returns:
            Structured lesson plan dict.
        """
        system_prompt = lesson_plan_prompt()

        # Build the user message with all context
        user_message = f"""Generate a complete 5E lesson plan for the following session.

## SESSION DATA (from framework — treat as ground truth)
Topic: {session_data.get('topic', 'NOT_SPECIFIED')}
Session Number: {session_number}
Grade: {grade}
Learning Outcomes:
{chr(10).join(f'  - {lo}' for lo in session_data.get('learning_outcomes', []))}
Tangible Outcome: {session_data.get('tangible_outcome', 'NOT_SPECIFIED')}
Session Position: {session_data.get('session_position_in_topic', 1)} of {session_data.get('total_sessions_in_topic', 1)} in this topic
Notes: {session_data.get('notes', '')}

## CONSTRAINTS (MANDATORY — do not violate)
{constraints}

## GUARDRAIL RULES
{guardrail_rules}

{f"## PREVIOUS SESSIONS CONTEXT (for continuity){chr(10)}{previous_sessions_summary}" if previous_sessions_summary else ""}

## YOUR TASK
Generate the complete 5E lesson plan as a JSON object.
- The 5E phase durations MUST sum to exactly 50 minutes
- Learning objectives MUST use Bloom's taxonomy verbs
- Include at least one Indian context example
- Only use materials from the allowed tools list in constraints
- Return ONLY valid JSON, no explanation"""

        return self.call(system_prompt, user_message)
