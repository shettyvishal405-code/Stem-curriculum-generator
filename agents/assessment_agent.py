"""
Assessment Agent — generates curriculum-aligned assessments.
"""

from .base_agent import BaseAgent
from utils.prompts import assessment_prompt


class AssessmentAgent(BaseAgent):
    """Generates assessments aligned to lesson plans."""

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
            lesson_plan: The generated lesson plan dict.
            grade: Target grade.
            guardrail_rules: Global guardrail rules.

        Returns:
            Structured assessment dict with answer key.
        """
        system_prompt = assessment_prompt()

        # Extract key info from lesson plan
        topic = lesson_plan.get("topic", "Unknown")
        session_number = lesson_plan.get("session_number", "?")
        objectives = lesson_plan.get("learning_objectives", [])
        vocab = lesson_plan.get("vocabulary", [])
        phases = lesson_plan.get("5e_phases", {})

        # Summarise what was taught
        taught_content = []
        for phase_name, phase_data in phases.items():
            if phase_name != "evaluate" and isinstance(phase_data, dict):
                teacher_act = phase_data.get("teacher_activity", "")
                student_act = phase_data.get("student_activity", "")
                key_concepts = phase_data.get("key_concepts", [])
                if teacher_act:
                    taught_content.append(f"[{phase_name}] {teacher_act}")
                if key_concepts:
                    taught_content.extend(key_concepts)

        user_message = f"""Generate a complete assessment for the following lesson.

## LESSON SUMMARY
Topic: {topic}
Session Number: {session_number}
Grade: {grade}

Learning Objectives:
{chr(10).join(f'  - {obj}' for obj in objectives)}

Key Vocabulary Taught:
{chr(10).join(f'  - {v.get("term", "")}: {v.get("definition", "")}' for v in vocab)}

Content Taught in This Lesson:
{chr(10).join(f'  - {c}' for c in taught_content[:15])}

## GUARDRAIL RULES
{guardrail_rules}

## CRITICAL RULES
- ONLY assess content that was taught in this lesson
- Every question MUST cite its source_in_lesson
- MCQs MUST start with "Which of the following..."
- Fill-in-blanks MUST start with "Name the..."
- False items MUST include a correction
- Return ONLY valid JSON, no explanation"""

        return self.call(system_prompt, user_message)
