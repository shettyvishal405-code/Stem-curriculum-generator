"""
Guardrail Validator — cross-validates all session outputs against framework and constraints.
"""

from agents.base_agent import BaseAgent
from utils.prompts import validator_prompt


class GuardrailValidator(BaseAgent):

    def __init__(self, model: str):
        super().__init__(
            name="Validator",
            model=model,
            max_tokens=2048,
            temperature=0.0,
        )

    def validate(
        self,
        framework_session: dict,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
        session_number: int,
        constraints: str,
    ) -> dict:
        system_prompt = validator_prompt()

        user_message = f"""Validate all outputs for Session {session_number}.

## FRAMEWORK SESSION DATA
Topic: {framework_session.get('topic')}
Learning Outcomes: {framework_session.get('learning_outcomes', [])}
Tangible Outcome: {framework_session.get('tangible_outcome')}

## CONSTRAINTS
{constraints}

## LESSON PLAN SUMMARY
Topic: {lesson_plan.get('topic')}
Objectives: {lesson_plan.get('learning_objectives', [])}
Materials: {lesson_plan.get('materials_needed', [])}
5E Timing:
- Engage: {lesson_plan.get('5e_phases', {}).get('engage', {}).get('duration_minutes', 0)} min
- Explore: {lesson_plan.get('5e_phases', {}).get('explore', {}).get('duration_minutes', 0)} min
- Explain: {lesson_plan.get('5e_phases', {}).get('explain', {}).get('duration_minutes', 0)} min
- Elaborate: {lesson_plan.get('5e_phases', {}).get('elaborate', {}).get('duration_minutes', 0)} min
- Evaluate: {lesson_plan.get('5e_phases', {}).get('evaluate', {}).get('duration_minutes', 0)} min

## ASSESSMENT
MCQ count: {len(assessment.get('mcqs', []))}
FIB count: {len(assessment.get('fill_in_blank', []))}
T/F count: {len(assessment.get('true_false', []))}
Short answer count: {len(assessment.get('short_answers', []))}

## EQUIPMENT
Items: {[i.get('item_name') for i in equipment_data.get('items', [])]}

Validate all outputs and return a JSON validation report."""

        try:
            return self.call(system_prompt, user_message)
        except Exception as e:
            return {
                "session_number": session_number,
                "overall_status": "NEEDS_REVIEW",
                "checks": [],
                "critical_issues": [],
                "warnings": [f"Validator error: {e}"],
                "suggestions": [],
            }
