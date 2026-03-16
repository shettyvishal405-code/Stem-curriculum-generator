"""
Guardrail Validator — cross-validates all agent outputs against the framework.

Operates at two levels:
1. Local deterministic checks (fast, rule-based)
2. AI cross-validation (deep analysis using a separate model instance)
"""

import json
import re
from agents.base_agent import BaseAgent
from utils.prompts import validator_prompt


class GuardrailValidator(BaseAgent):
    """Cross-validates curriculum outputs against framework and rules."""

    def __init__(self, model: str):
        super().__init__(
            name="GuardrailValidator",
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
        """
        Run all validation layers and return a consolidated report.

        Args:
            framework_session: Source session data from the framework.
            lesson_plan: Generated lesson plan.
            assessment: Generated assessment.
            ppt_data: Generated PPT content.
            equipment_data: Generated equipment list.
            session_number: Current session number.
            constraints: Phase-specific constraints.

        Returns:
            Validation report dict.
        """
        # Layer 1: Local deterministic checks
        local_issues = self._run_local_checks(
            lesson_plan, assessment, ppt_data, equipment_data
        )

        # Layer 2: AI cross-validation
        try:
            ai_report = self._run_ai_validation(
                framework_session, lesson_plan, assessment, ppt_data,
                equipment_data, session_number, constraints
            )
        except Exception as e:
            print(f"  [GuardrailValidator] AI validation failed: {e}")
            ai_report = {
                "overall_status": "NEEDS_REVIEW",
                "confidence_score": 0.5,
                "critical_issues": [f"AI validation unavailable: {e}"],
                "warnings": local_issues.get("warnings", []),
                "suggestions": [],
                "requires_human_review": ["AI validation failed — manual review required"],
            }

        # Merge local issues into AI report
        merged = self._merge_reports(local_issues, ai_report)

        # Print summary
        status = merged.get("overall_status", "UNKNOWN")
        icon = {"PASS": "✅", "FAIL": "❌", "NEEDS_REVIEW": "⚠️"}.get(status, "❓")
        print(f"    {icon} Validation: {status}")

        critical = merged.get("critical_issues", [])
        if critical:
            for issue in critical[:3]:
                print(f"      ❌ {issue}")

        warnings = merged.get("warnings", [])
        if warnings:
            for w in warnings[:3]:
                print(f"      ⚠️  {w}")

        verify_count = merged.get("verify_tags_found", 0)
        if verify_count:
            print(f"      [VERIFY] tags found: {verify_count}")

        return merged

    def _run_local_checks(
        self,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
    ) -> dict:
        """
        Layer 1: Fast, deterministic local checks.
        These check structural correctness without AI.
        """
        critical = []
        warnings = []

        # ── Lesson Plan Checks ──────────────────────────────
        phases = lesson_plan.get("5e_phases", {})
        total_duration = sum(
            p.get("duration_minutes", 0)
            for p in phases.values()
            if isinstance(p, dict)
        )
        if total_duration != 50:
            critical.append(f"Lesson duration is {total_duration} min, must be exactly 50 min")

        if not lesson_plan.get("learning_objectives"):
            critical.append("Lesson plan missing learning objectives")

        if not lesson_plan.get("tangible_outcome"):
            warnings.append("Lesson plan missing tangible outcome")

        # Bloom's taxonomy check
        bloom_verbs = [
            "identify", "describe", "explain", "apply", "analyze", "analyse",
            "create", "evaluate", "compare", "demonstrate", "design", "build",
            "list", "define", "classify", "construct", "distinguish", "predict"
        ]
        for obj in lesson_plan.get("learning_objectives", []):
            obj_lower = obj.lower()
            if not any(verb in obj_lower for verb in bloom_verbs):
                warnings.append(f"Objective may not use Bloom's verb: '{obj[:60]}'")

        # ── Assessment Checks ──────────────────────────────
        mcqs = assessment.get("mcqs", [])
        if len(mcqs) != 5:
            critical.append(f"Assessment has {len(mcqs)} MCQs, expected 5")

        for mcq in mcqs:
            q = mcq.get("question", "")
            if not q.lower().startswith("which of the following"):
                warnings.append(f"MCQ doesn't start with 'Which of the following': '{q[:50]}'")
            if not mcq.get("source_in_lesson"):
                warnings.append(f"MCQ missing source_in_lesson: '{q[:50]}'")

        fibs = assessment.get("fill_in_blank", [])
        if len(fibs) != 3:
            critical.append(f"Assessment has {len(fibs)} fill-in-blanks, expected 3")

        for fib in fibs:
            q = fib.get("question", "")
            if not q.lower().startswith("name the"):
                warnings.append(f"Fill-in-blank doesn't start with 'Name the': '{q[:50]}'")

        tfs = assessment.get("true_false", [])
        if len(tfs) != 3:
            critical.append(f"Assessment has {len(tfs)} T/F questions, expected 3")

        for tf in tfs:
            if tf.get("answer") is False and not tf.get("correction"):
                warnings.append(f"False statement missing correction: '{str(tf.get('statement', ''))[:50]}'")

        sas = assessment.get("short_answer", [])
        if len(sas) != 2:
            critical.append(f"Assessment has {len(sas)} short answers, expected 2")

        # ── PPT Checks ──────────────────────────────────────
        slides = ppt_data.get("slides", [])
        if len(slides) < 8:
            critical.append(f"PPT has {len(slides)} slides, minimum is 8")
        elif len(slides) > 12:
            warnings.append(f"PPT has {len(slides)} slides, maximum is 12")

        for slide in slides:
            bullets = slide.get("bullets", [])
            if len(bullets) > 4:
                warnings.append(f"Slide '{slide.get('title', '?')}' has {len(bullets)} bullets, max is 4")

        # ── Banned Terms Check ──────────────────────────────
        banned_terms = ["stupid", "dumb", "easy", "obviously", "simply", "basic", "no-brainer"]
        all_text = json.dumps(lesson_plan) + json.dumps(ppt_data)
        for term in banned_terms:
            if re.search(r'\b' + term + r'\b', all_text, re.IGNORECASE):
                critical.append(f"Banned term found in student-facing content: '{term}'")

        # ── [VERIFY] Tag Count ──────────────────────────────
        all_content = json.dumps({
            "lp": lesson_plan, "a": assessment,
            "ppt": ppt_data, "eq": equipment_data
        })
        verify_count = len(re.findall(r'\[VERIFY\]', all_content))
        verify_price_count = len(re.findall(r'\[VERIFY_PRICE\]', all_content))

        return {
            "critical": critical,
            "warnings": warnings,
            "verify_tags": verify_count,
            "verify_price_tags": verify_price_count,
        }

    def _run_ai_validation(
        self,
        framework_session: dict,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
        session_number: int,
        constraints: str,
    ) -> dict:
        """Layer 2: AI cross-validation."""
        system_prompt = validator_prompt()

        # Truncate large content to stay within token limits
        lp_summary = {
            "topic": lesson_plan.get("topic"),
            "grade": lesson_plan.get("grade"),
            "learning_objectives": lesson_plan.get("learning_objectives"),
            "tangible_outcome": lesson_plan.get("tangible_outcome"),
            "materials_needed": lesson_plan.get("materials_needed"),
            "vocabulary": lesson_plan.get("vocabulary"),
        }

        assessment_summary = {
            "mcq_count": len(assessment.get("mcqs", [])),
            "fib_count": len(assessment.get("fill_in_blank", [])),
            "tf_count": len(assessment.get("true_false", [])),
            "sa_count": len(assessment.get("short_answer", [])),
            "first_mcq": assessment.get("mcqs", [{}])[0].get("question", "") if assessment.get("mcqs") else "",
        }

        ppt_summary = {
            "slide_count": len(ppt_data.get("slides", [])),
            "slide_titles": [s.get("title") for s in ppt_data.get("slides", [])],
        }

        user_message = f"""Validate these curriculum outputs for Session {session_number}.

## FRAMEWORK SESSION (source of truth)
{json.dumps(framework_session, indent=2, default=str)[:1500]}

## CONSTRAINTS (must be respected)
{constraints[:800]}

## LESSON PLAN SUMMARY
{json.dumps(lp_summary, indent=2, default=str)[:1000]}

## ASSESSMENT SUMMARY
{json.dumps(assessment_summary, indent=2, default=str)}

## PPT SUMMARY
{json.dumps(ppt_summary, indent=2, default=str)}

## YOUR TASK
Run a strict validation. Check:
1. Does the lesson align with the framework session data?
2. Are constraints respected?
3. Is content age-appropriate for Grade {lesson_plan.get('grade', '?')} (11-14 year olds)?
4. Are Indian context examples present?
5. Do objectives → activities → assessment → PPT align?

Return ONLY valid JSON with the validation report."""

        return self.call(system_prompt, user_message)

    def _merge_reports(self, local: dict, ai: dict) -> dict:
        """Merge local check results into the AI validation report."""
        local_critical = local.get("critical", [])
        local_warnings = local.get("warnings", [])

        ai_critical = ai.get("critical_issues", [])
        ai_warnings = ai.get("warnings", [])

        all_critical = list(set(local_critical + ai_critical))
        all_warnings = list(set(local_warnings + ai_warnings))

        # Determine final status
        if all_critical:
            final_status = "FAIL"
        elif all_warnings or ai.get("overall_status") == "NEEDS_REVIEW":
            final_status = "NEEDS_REVIEW"
        else:
            final_status = ai.get("overall_status", "PASS")

        verify_tags = local.get("verify_tags", 0)
        if verify_tags > 0 and final_status == "PASS":
            final_status = "NEEDS_REVIEW"

        return {
            "overall_status": final_status,
            "confidence_score": ai.get("confidence_score", 0.5),
            "critical_issues": all_critical,
            "warnings": all_warnings,
            "suggestions": ai.get("suggestions", []),
            "requires_human_review": ai.get("requires_human_review", []),
            "check_results": ai.get("check_results", {}),
            "verify_tags_found": verify_tags,
            "verify_price_tags_found": local.get("verify_price_tags", 0),
            "local_checks": {
                "critical_count": len(local_critical),
                "warning_count": len(local_warnings),
            },
        }
