"""
PPT Agent — generates student-facing PowerPoint content.
"""

from .base_agent import BaseAgent
from utils.prompts import ppt_prompt


class PPTAgent(BaseAgent):
    """Generates student-facing PPT slide content."""

    def __init__(self, model: str, branding: dict = None, max_tokens: int = 4096):
        super().__init__(
            name="PPTAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        self.branding = branding or {}

    def generate(
        self,
        lesson_plan: dict,
        grade: int,
        guardrail_rules: str,
    ) -> dict:
        """
        Generate PPT slide content from the lesson plan.

        Args:
            lesson_plan: The generated lesson plan dict.
            grade: Target grade.
            guardrail_rules: Global guardrail rules.

        Returns:
            Structured PPT content dict with slide-by-slide content.
        """
        system_prompt = ppt_prompt()

        topic = lesson_plan.get("topic", "Unknown")
        session_number = lesson_plan.get("session_number", "?")
        objectives = lesson_plan.get("learning_objectives", [])
        vocab = lesson_plan.get("vocabulary", [])
        tangible = lesson_plan.get("tangible_outcome", "")
        phases = lesson_plan.get("5e_phases", {})

        # Grade-specific graphics guidance
        grade_graphics = {
            6: "Simple, colourful, cartoon-style. Batteries, LEDs, circuit symbols as friendly icons.",
            7: "Slightly technical but friendly. Arduino diagrams, robot illustrations.",
            8: "Technical but accessible. IoT diagrams, drone schematics, data charts.",
        }
        graphics_guidance = grade_graphics.get(grade, "Age-appropriate and engaging.")

        # Build phase summaries
        phase_summaries = []
        for phase_name in ["engage", "explore", "explain", "elaborate"]:
            phase = phases.get(phase_name, {})
            if phase:
                student_act = phase.get("student_activity", "")
                key_concepts = phase.get("key_concepts", [])
                if student_act:
                    phase_summaries.append(f"[{phase_name.upper()}] {student_act}")
                if key_concepts:
                    phase_summaries.append(f"  Key concepts: {', '.join(key_concepts)}")

        user_message = f"""Generate student-facing PPT slide content for this lesson.

## LESSON DATA
Topic: {topic}
Session: {session_number}
Grade: {grade}
Tangible Outcome: {tangible}

Learning Objectives:
{chr(10).join(f'  - {obj}' for obj in objectives)}

Key Vocabulary:
{chr(10).join(f'  - {v.get("term", "")}: {v.get("definition", "")}' for v in vocab)}

Lesson Flow (what students will do):
{chr(10).join(f'  {s}' for s in phase_summaries)}

## DESIGN REQUIREMENTS
- Slides: 8-12 total
- Grade {grade} style: {graphics_guidance}
- Indian settings and diverse students in all graphic descriptions
- Max 4 bullets per slide, max 10 words per bullet

## GUARDRAIL RULES
{guardrail_rules}

## CRITICAL RULES
- Do NOT add facts not covered in the lesson
- Keep language simple (max 15-word sentences)
- First slide: Title slide
- Last slide: Summary/What We Learned Today
- Include a vocabulary slide
- Return ONLY valid JSON, no explanation"""

        return self.call(system_prompt, user_message)
