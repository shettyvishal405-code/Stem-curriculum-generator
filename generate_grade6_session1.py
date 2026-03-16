"""
Standalone generator for Grade 6 Session 1 lesson plan.
Uses the pipeline infrastructure without requiring a framework xlsx file.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.config_loader import PipelineConfig
from agents.lesson_plan_agent import LessonPlanAgent
from agents.assessment_agent import AssessmentAgent
from agents.ppt_agent import PPTAgent
from agents.equipment_agent import EquipmentAgent
from guardrails.validator import GuardrailValidator
from utils.output_builder import OutputBuilder


def main():
    print("=" * 60)
    print("  ENpower Curriculum Pipeline")
    print("  Grade 6 | Session 1 | Introduction to STEM")
    print("=" * 60)

    config = PipelineConfig()
    model = config.model

    # Session 1 data (derived from pipeline_config.yaml)
    session_data = {
        "session_number": 1,
        "topic": "What is STEM? Introduction to Technologies and the STEM Lab",
        "subtopics": [
            "What is STEM?",
            "Science, Technology, Engineering, Mathematics",
            "STEM in everyday Indian life",
            "Lab rules and safety",
            "Tools and equipment identification",
        ],
        "learning_outcomes": [
            "Understand what STEM stands for and its importance",
            "Identify common lab tools and their safe use",
            "Know and follow lab safety rules and etiquette",
            "Connect STEM to real-life examples in India",
        ],
        "tangible_outcome": "Understand lab components and lab etiquette",
        "suggested_activities": [
            "STEM scavenger hunt using printed images",
            "Lab safety pledge",
            "Tool identification chart",
        ],
        "tools_software": ["Chart paper", "Markers", "Printed images"],
        "duration_minutes": 50,
        "prerequisites": [],
        "session_position_in_topic": 1,
        "total_sessions_in_topic": 2,
        "notes": "First of 2 sessions on Introduction to STEM. This is the very first session of Grade 6. Students are entering the STEM lab for the first time. Focus on excitement, curiosity, and safety.",
    }

    constraints = config.get_constraint_prompt(grade=6, session_number=1)
    guardrail_rules = config.get_guardrail_prompt()

    # Generate lesson plan
    print("\n[1/5] Generating lesson plan...")
    lesson_agent = LessonPlanAgent(model=model, max_tokens=config.max_tokens)
    lesson_plan = lesson_agent.generate(
        session_data=session_data,
        grade=6,
        session_number=1,
        constraints=constraints,
        guardrail_rules=guardrail_rules,
        previous_sessions_summary="",
    )
    print(f"  ✓ Lesson plan: {lesson_plan.get('topic')}")

    # Generate assessment
    print("\n[2/5] Generating assessment...")
    assessment_agent = AssessmentAgent(model=model, max_tokens=config.max_tokens)
    assessment = assessment_agent.generate(
        lesson_plan=lesson_plan,
        grade=6,
        guardrail_rules=guardrail_rules,
    )
    print(f"  ✓ Assessment: {len(assessment.get('mcqs', []))} MCQs, {len(assessment.get('fill_in_blank', []))} FIBs")

    # Generate PPT
    print("\n[3/5] Generating PPT content...")
    ppt_agent = PPTAgent(model=model, branding=config.branding, max_tokens=config.max_tokens)
    ppt_data = ppt_agent.generate(
        lesson_plan=lesson_plan,
        grade=6,
        guardrail_rules=guardrail_rules,
    )
    print(f"  ✓ PPT: {ppt_data.get('total_slides', len(ppt_data.get('slides', [])))} slides")

    # Generate equipment list
    print("\n[4/5] Generating equipment list...")
    phase = config.get_phase_for_session(grade=6, session_number=1)
    equipment_agent = EquipmentAgent(model=model, max_tokens=config.max_tokens)
    equipment_data = equipment_agent.generate(
        lesson_plan=lesson_plan,
        guardrail_rules=guardrail_rules,
        allowed_tools=phase["tools"],
    )
    print(f"  ✓ Equipment: {len(equipment_data.get('items', []))} items")

    # Validate
    print("\n[5/5] Running guardrail validation...")
    validator = GuardrailValidator(model=config.validator_model)
    validation = validator.validate(
        framework_session=session_data,
        lesson_plan=lesson_plan,
        assessment=assessment,
        ppt_data=ppt_data,
        equipment_data=equipment_data,
        session_number=1,
        constraints=constraints,
    )
    status = validation.get("overall_status", "UNKNOWN")
    icon = {"PASS": "✅", "FAIL": "❌", "NEEDS_REVIEW": "⚠️"}.get(status, "❓")
    print(f"  {icon} Validation: {status}")

    # Build output files
    print("\nBuilding output files...")
    builder = OutputBuilder(output_dir="outputs", branding=config.branding)
    files = builder.build_all(
        session_number=1,
        lesson_plan=lesson_plan,
        assessment=assessment,
        ppt_data=ppt_data,
        equipment_data=equipment_data,
    )

    print("\n" + "=" * 60)
    print("  COMPLETE — Grade 6 Session 1")
    print("=" * 60)
    for name, path in files.items():
        print(f"  📄 {name}: {path}")

    if validation.get("warnings"):
        print("\nWarnings:")
        for w in validation["warnings"]:
            print(f"  ⚠️  {w}")

    if validation.get("critical_issues"):
        print("\nCritical Issues:")
        for c in validation["critical_issues"]:
            print(f"  ❌ {c}")

    return files


if __name__ == "__main__":
    main()
