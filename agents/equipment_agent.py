"""
Equipment Agent — generates lab equipment lists with INR pricing.
"""

from .base_agent import BaseAgent
from utils.prompts import equipment_prompt


class EquipmentAgent(BaseAgent):
    """Generates equipment lists with Indian supplier information."""

    def __init__(self, model: str, max_tokens: int = 4096):
        super().__init__(
            name="EquipmentAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.1,
        )

    def generate(
        self,
        lesson_plan: dict,
        guardrail_rules: str,
    ) -> dict:
        """
        Generate an equipment list for the lesson.

        Args:
            lesson_plan: The generated lesson plan dict.
            guardrail_rules: Global guardrail rules.

        Returns:
            Structured equipment list with quantities and INR pricing.
        """
        system_prompt = equipment_prompt()

        topic = lesson_plan.get("topic", "Unknown")
        session_number = lesson_plan.get("session_number", "?")
        grade = lesson_plan.get("grade", "?")
        materials = lesson_plan.get("materials_needed", [])

        # Extract all activities that might need equipment
        phases = lesson_plan.get("5e_phases", {})
        activities = []
        resources = []
        for phase_name, phase_data in phases.items():
            if isinstance(phase_data, dict):
                student_act = phase_data.get("student_activity", "")
                hands_on = phase_data.get("hands_on_task", "")
                app_task = phase_data.get("application_task", "")
                phase_resources = phase_data.get("resources", [])

                if student_act:
                    activities.append(f"[{phase_name}] {student_act}")
                if hands_on:
                    activities.append(f"[{phase_name}] Hands-on: {hands_on}")
                if app_task:
                    activities.append(f"[{phase_name}] Application: {app_task}")
                resources.extend(phase_resources)

        user_message = f"""Generate a complete equipment list for this STEM lab session.

## SESSION DETAILS
Topic: {topic}
Session: {session_number}
Grade: {grade}
Class: 30 students in 6 groups of 5

## MATERIALS LISTED IN LESSON PLAN
{chr(10).join(f'  - {m}' for m in materials)}

## HANDS-ON ACTIVITIES (derive equipment needs from these)
{chr(10).join(f'  - {a}' for a in activities)}

## RESOURCES MENTIONED
{chr(10).join(f'  - {r}' for r in set(resources))}

## REQUIREMENTS
- Preferred suppliers: Robocraze, Amazon.in, Robu.in, Electronicscomp.com
- All prices in INR
- Flag uncertain prices with [VERIFY_PRICE]
- Calculate quantities for 6 groups of 5 students
- Mark reusable items appropriately
- Include consumables (tapes, wires, papers) separately

## GUARDRAIL RULES
{guardrail_rules}

## CRITICAL RULES
- Only list equipment actually needed for the activities
- Do NOT invent equipment not required
- Return ONLY valid JSON, no explanation"""

        return self.call(system_prompt, user_message)
