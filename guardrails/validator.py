"""
Guardrail Validator
Cross-validates all agent outputs against the framework and constraints.
Combines AI-based review with fast local checks.
"""

import re
from agents.base_agent import BaseAgent
from utils.prompts import validator_prompt

# Terms banned in student-facing content
BANNED_TERMS = ["stupid", "dumb", "easy", "obviously", "simply", "just", "basic", "no-brainer"]


class GuardrailValidator(BaseAgent):
    """Validates all session outputs against the framework and constraints."""

    def __init__(self, model: str, max_tokens: int = 2048):
        super().__init__(
            name="GuardrailValidator",
            model=model,
            max_tokens=max_tokens,
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
        """
        Run full validation on session outputs.

        Returns a validation report dict with overall_status and per-check results.
        """
        # Fast local checks first
        local_issues = self._local_checks(lesson_plan, assessment, ppt_data, equipment_data)

        # AI cross-validation
        ai_report = self._ai_validate(
            framework_session=framework_session,
            lesson_plan=lesson_plan,
            assessment=assessment,
            ppt_data=ppt_data,
            equipment_data=equipment_data,
            session_number=session_number,
            constraints=constraints,
        )

        # Merge local issues into AI report
        if local_issues:
            existing_critical = ai_report.get("critical_issues", [])
            ai_report["critical_issues"] = existing_critical + local_issues
            if local_issues:
                ai_report["overall_status"] = "FAIL"

        return ai_report

    def _local_checks(
        self,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
    ) -> list:
        """Fast, deterministic local validation checks."""
        issues = []

        # Timing check
        five_e = lesson_plan.get("five_e", {})
        total_time = sum(
            five_e.get(phase, {}).get("duration_minutes", 0)
            for phase in ["engage", "explore", "explain", "elaborate", "evaluate"]
        )
        if total_time != 50:
            issues.append(f"5E timing error: phases sum to {total_time} minutes, expected 50.")

        # Banned terms check (lesson + assessment + PPT)
        all_text = self._extract_text(lesson_plan) + self._extract_text(assessment) + self._extract_text(ppt_data)
        for term in BANNED_TERMS:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, all_text, re.IGNORECASE):
                issues.append(f"Banned term found: '{term}'")

        # MCQ count
        mcqs = assessment.get("mcq", [])
        if len(mcqs) < 5:
            issues.append(f"Assessment has {len(mcqs)} MCQs, expected 5.")

        # MCQ format check
        for i, q in enumerate(mcqs):
            question_text = q.get("question", "")
            if not question_text.startswith("Which of the following"):
                issues.append(f"MCQ {i + 1} must start with 'Which of the following...'")

        # Fill-in-blank format
        fibs = assessment.get("fill_in_blank", [])
        if len(fibs) < 3:
            issues.append(f"Assessment has {len(fibs)} fill-in-blank, expected 3.")
        for i, f in enumerate(fibs):
            if not f.get("question", "").startswith("Name the"):
                issues.append(f"Fill-in-blank {i + 1} must start with 'Name the...'")

        # T/F correction check
        for i, tf in enumerate(assessment.get("true_false", [])):
            if tf.get("answer") is False and not tf.get("correction"):
                issues.append(f"True/False {i + 1} is FALSE but has no correction.")

        # PPT slide count
        slides = ppt_data.get("slides", [])
        if not (8 <= len(slides) <= 12):
            issues.append(f"PPT has {len(slides)} slides, expected 8-12.")

        return issues

    def _extract_text(self, data: dict) -> str:
        """Recursively extract all string values from a dict."""
        if isinstance(data, str):
            return data
        if isinstance(data, list):
            return " ".join(self._extract_text(i) for i in data)
        if isinstance(data, dict):
            return " ".join(self._extract_text(v) for v in data.values())
        return ""

    def _ai_validate(
        self,
        framework_session: dict,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
        session_number: int,
        constraints: str,
    ) -> dict:
        """AI-based cross-validation."""
        import json

        system_prompt = validator_prompt()

        # Summarise outputs to stay within context
        lesson_summary = {
            "topic": lesson_plan.get("topic"),
            "learning_objectives": lesson_plan.get("learning_objectives", []),
            "tangible_outcome": lesson_plan.get("tangible_outcome"),
            "materials": [
                m.get("item") if isinstance(m, dict) else m
                for m in lesson_plan.get("materials_needed", [])
            ],
            "five_e_phases": {
                k: {
                    "duration": v.get("duration_minutes"),
                    "activity": v.get("activity_name", v.get("teacher_action", "")),
                }
                for k, v in lesson_plan.get("five_e", {}).items()
            },
        }

        assessment_summary = {
            "mcq_count": len(assessment.get("mcq", [])),
            "fib_count": len(assessment.get("fill_in_blank", [])),
            "tf_count": len(assessment.get("true_false", [])),
            "sa_count": len(assessment.get("short_answer", [])),
            "first_mcq": assessment.get("mcq", [{}])[0].get("question", "") if assessment.get("mcq") else "",
        }

        ppt_summary = {
            "slide_count": len(ppt_data.get("slides", [])),
            "titles": [s.get("title") for s in ppt_data.get("slides", [])],
        }

        user_message = f"""Validate the following session outputs against the framework and constraints.

## FRAMEWORK SESSION
{json.dumps(framework_session, indent=2, ensure_ascii=False, default=str)}

## CONSTRAINTS APPLIED
{constraints}

## LESSON PLAN SUMMARY
{json.dumps(lesson_summary, indent=2, ensure_ascii=False)}

## ASSESSMENT SUMMARY
{json.dumps(assessment_summary, indent=2, ensure_ascii=False)}

## PPT SUMMARY
{json.dumps(ppt_summary, indent=2, ensure_ascii=False)}

## EQUIPMENT
Items: {len(equipment_data.get("equipment_list", []))} listed

Perform a thorough validation. Be strict — flag all violations.
Return a complete validation report as JSON."""

        try:
            return self.call(system_prompt, user_message)
        except Exception as e:
            print(f"  [GuardrailValidator] AI validation failed: {e} — using local results only")
            return {
                "session_number": session_number,
                "overall_status": "NEEDS_REVIEW",
                "checks": {},
                "critical_issues": [f"AI validation unavailable: {e}"],
                "recommendations": [],
                "verify_flags": [],
            }
