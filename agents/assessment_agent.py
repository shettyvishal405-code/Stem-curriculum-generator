"""
Assessment Agent
Generates curriculum-aligned assessments: MCQs, FIBs, MTF, T/F, Short Answer.
"""

from .base_agent import BaseAgent
from utils.prompts import assessment_prompt


class AssessmentAgent(BaseAgent):
    """Generates assessments aligned to a lesson plan."""

    def __init__(self, model: str, max_tokens: int = 4096):
        super().__init__(
            name="AssessmentAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.2,
        )

    def generate(
        self,
        lesson_plan: dict,
        grade: int,
        guardrail_rules: str,
    ) -> dict:
        """
        Generate an assessment aligned to the lesson plan.

        Args:
            lesson_plan: Generated lesson plan dict.
            grade: Target grade.
            guardrail_rules: Quality and alignment rules.

        Returns:
            Structured assessment dict.
        """
        system_prompt = assessment_prompt()

        objectives = "\n".join(f"  - {o}" for o in lesson_plan.get("learning_objectives", []))
        vocab = "\n".join(
            f"  - {v['term']}: {v['definition']}"
            for v in lesson_plan.get("vocabulary", [])
        )

        five_e = lesson_plan.get("five_e", {})
        key_concepts = five_e.get("explain", {}).get("key_concepts", [])
        concepts_str = "\n".join(f"  - {c}" for c in key_concepts)

        tangible = lesson_plan.get("tangible_outcome", "")

        user_message = f"""Generate a complete assessment for the following lesson.

## LESSON SUMMARY
- Session: {lesson_plan.get("session_number")}
- Grade: {grade}
- Topic: {lesson_plan.get("topic")}
- Tangible Outcome: {tangible}

## LEARNING OBJECTIVES (assess ONLY these)
{objectives}

## KEY VOCABULARY TAUGHT
{vocab}

## KEY CONCEPTS TAUGHT (from Explain phase)
{concepts_str}

## ASSESSMENT REQUIREMENTS
- 5 MCQs (format: "Which of the following...")
- 3 Fill-in-blank (format: "Name the...")
- 1 Match-the-following set (4 pairs)
- 3 True/False (include correction for all false items)
- 2 Short Answer (max 50 words each)

## GUARDRAIL RULES
{guardrail_rules}
- NEVER assess content NOT in the lesson above
- Every question MUST cite source_in_lesson

Return a complete assessment as a JSON object following the specified format."""

        result = self.call(system_prompt, user_message)
        result.setdefault("session_number", lesson_plan.get("session_number"))
        result.setdefault("grade", grade)
        result.setdefault("topic", lesson_plan.get("topic", ""))
        return result
