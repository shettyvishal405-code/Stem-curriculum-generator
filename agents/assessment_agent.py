"""
Assessment Agent — generates curriculum-aligned assessments.
"""

from .base_agent import BaseAgent
from utils.prompts import assessment_prompt


class AssessmentAgent(BaseAgent):

    def __init__(self, model: str, max_tokens: int = 4096):
        super().__init__(
            name="AssessmentAgent",
            model=model,
            max_tokens=max_tokens,
            temperature=0.2,
        )

    def generate(self, lesson_plan: dict, grade: int, guardrail_rules: str) -> dict:
        system_prompt = assessment_prompt()

        user_message = f"""Generate a complete assessment for this lesson plan:

## LESSON PLAN SUMMARY
Session: {lesson_plan.get('session_number')}
Grade: {grade}
Topic: {lesson_plan.get('topic')}
Learning Objectives: {lesson_plan.get('learning_objectives', [])}
Key Vocabulary: {[v.get('term') for v in lesson_plan.get('vocabulary', [])]}
5E Activities Summary:
- Engage: {lesson_plan.get('5e_phases', {}).get('engage', {}).get('teacher_action', '')}
- Explore: {lesson_plan.get('5e_phases', {}).get('explore', {}).get('activity_name', '')}
- Explain: {lesson_plan.get('5e_phases', {}).get('explain', {}).get('key_concepts', [])}
- Elaborate: {lesson_plan.get('5e_phases', {}).get('elaborate', {}).get('activity_name', '')}
- Evaluate: {lesson_plan.get('5e_phases', {}).get('evaluate', {}).get('questions', [])}

## GUARDRAIL RULES
{guardrail_rules}

Return a complete JSON assessment following the specified format."""

        return self.call(system_prompt, user_message)
