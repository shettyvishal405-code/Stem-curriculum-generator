"""
Equipment Agent
Generates lab equipment lists with Indian supplier pricing.
"""

from .base_agent import BaseAgent
from utils.prompts import equipment_prompt


class EquipmentAgent(BaseAgent):
    """Generates equipment lists for lab sessions."""

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
        Generate an equipment list for a lesson.

        Args:
            lesson_plan: Generated lesson plan dict.
            guardrail_rules: Quality rules.

        Returns:
            Structured equipment list dict.
        """
        system_prompt = equipment_prompt()

        materials = lesson_plan.get("materials_needed", [])
        materials_str = "\n".join(
            f"  - {m.get('item', m) if isinstance(m, dict) else m}"
            for m in materials
        )

        five_e = lesson_plan.get("five_e", {})
        explore_steps = five_e.get("explore", {}).get("instructions", [])
        elaborate_steps = five_e.get("elaborate", {}).get("instructions", [])

        user_message = f"""Generate a complete equipment list for the following lab session.

## SESSION INFO
- Session: {lesson_plan.get("session_number")}
- Grade: {lesson_plan.get("grade")}
- Topic: {lesson_plan.get("topic")}
- Tangible Outcome: {lesson_plan.get("tangible_outcome", "")}

## MATERIALS LISTED IN LESSON PLAN
{materials_str}

## KEY ACTIVITIES (determine equipment from these)
Explore activity: {five_e.get("explore", {}).get("activity_name", "")}
Steps: {"; ".join(explore_steps[:5])}

Elaborate activity: {five_e.get("elaborate", {}).get("activity_name", "")}
Steps: {"; ".join(elaborate_steps[:5])}

## CLASS CONFIG
- Class size: 30 students
- Group size: 5 students
- Number of groups: 6

## GUARDRAIL RULES
{guardrail_rules}
- All prices in INR, mark with [VERIFY_PRICE]
- Preferred suppliers: Robocraze, Amazon.in, Robu.in, Electronicscomp.com
- List ONLY equipment needed for THIS session's activities

Return a complete equipment list as JSON following the specified format."""

        result = self.call(system_prompt, user_message)
        result.setdefault("session_number", lesson_plan.get("session_number"))
        result.setdefault("grade", lesson_plan.get("grade"))
        result.setdefault("topic", lesson_plan.get("topic", ""))
        return result
