"""
PPT Agent
Generates student-facing PowerPoint slide content with ENpower branding.
"""

from .base_agent import BaseAgent
from utils.prompts import ppt_prompt


class PPTAgent(BaseAgent):
    """Generates slide content for student-facing PPTs."""

    def __init__(self, model: str, branding: dict, max_tokens: int = 4096):
        super().__init__(
            name="PPTAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        self.branding = branding

    def generate(
        self,
        lesson_plan: dict,
        grade: int,
        guardrail_rules: str,
    ) -> dict:
        """
        Generate PPT slide content for a lesson.

        Args:
            lesson_plan: Generated lesson plan dict.
            grade: Target grade (6, 7, or 8).
            guardrail_rules: Quality rules.

        Returns:
            Structured PPT content dict.
        """
        system_prompt = ppt_prompt()

        objectives = "\n".join(f"  - {o}" for o in lesson_plan.get("learning_objectives", []))
        five_e = lesson_plan.get("five_e", {})
        explore = five_e.get("explore", {})
        explain = five_e.get("explain", {})
        elaborate = five_e.get("elaborate", {})

        style_map = {
            6: "Simple, colourful, cartoon-style. Batteries, LEDs, circuit symbols as friendly icons.",
            7: "Slightly technical but friendly. Arduino diagrams, robot illustrations.",
            8: "Technical but accessible. IoT diagrams, drone schematics, data charts.",
        }
        style = style_map.get(grade, "Clear and age-appropriate.")

        user_message = f"""Generate a complete set of PowerPoint slides for the following lesson.

## LESSON INFO
- Session: {lesson_plan.get("session_number")}
- Grade: {grade}
- Topic: {lesson_plan.get("topic")}
- Duration: {lesson_plan.get("duration_minutes", 50)} minutes
- Tangible Outcome: {lesson_plan.get("tangible_outcome", "")}

## LEARNING OBJECTIVES
{objectives}

## KEY CONCEPTS (from Explain phase)
{chr(10).join(f"  - {c}" for c in explain.get("key_concepts", []))}

## ACTIVITIES
- Explore: {explore.get("activity_name", "")} — {explore.get("student_deliverable", "")}
- Elaborate: {elaborate.get("activity_name", "")}

## BRANDING
- Company: {self.branding.get("company", "ENpower")} | {self.branding.get("tagline", "")}
- Primary colour: #{self.branding.get("colors", {}).get("primary_purple", "723991")}
- Heading font: {self.branding.get("fonts", {}).get("heading", "Georgia")}

## STYLE GUIDE FOR GRADE {grade}
{style}
All grades: Indian settings, diverse students (skin tones, genders, attire).

## GUARDRAIL RULES
{guardrail_rules}

Generate 8-12 slides (plus title and summary). Return as JSON following the specified format."""

        result = self.call(system_prompt, user_message)
        result.setdefault("session_number", lesson_plan.get("session_number"))
        result.setdefault("grade", grade)
        result.setdefault("topic", lesson_plan.get("topic", ""))
        return result
