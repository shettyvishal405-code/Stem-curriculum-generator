"""Generic session generator — re-uses all pipeline infrastructure."""
import sys
sys.path.insert(0, '/home/user/Stem-curriculum-generator')

import json
from pathlib import Path
from utils.config_loader import PipelineConfig
from agents.lesson_plan_agent import LessonPlanAgent
from agents.assessment_agent import AssessmentAgent
from agents.ppt_agent import PPTAgent
from agents.equipment_agent import EquipmentAgent
from guardrails.validator import GuardrailValidator
from utils.output_builder import OutputBuilder

GRADE = 6
SESSION = 20

# Per-session data for Grade 6 Sensors phase (sessions 16-23)
# Session 20 = 5th of 8 → motion/sound sensors, if-then logic applied
SESSION_DATA = {
    "session_number": SESSION,
    "topic": "Working with Sensors — Motion and Sound Sensors",
    "subtopics": [
        "What is a motion sensor? (PIR concept)",
        "What is a sound sensor? (microphone concept)",
        "How sensors detect changes in the environment",
        "If-Then logic with motion/sound triggers (unplugged)",
        "Indian real-world applications: automatic lights, smart doorbells, burglar alarms",
    ],
    "learning_outcomes": [
        "Describe how motion sensors and sound sensors detect environmental changes",
        "Differentiate between sensors (input) and actuators (output) using examples",
        "Apply if-then logic to motion and sound sensor scenarios without coding",
        "Identify at least three Indian real-world applications of motion and sound sensors",
    ],
    "tangible_outcome": "Understand input/output devices and basics of automation",
    "suggested_activities": [
        "Human motion-sensor role-play (one student = sensor, one = actuator)",
        "If-Then logic worksheet for motion/sound scenarios",
        "Sensor identification chart from printed images",
    ],
    "tools_software": ["Worksheets", "Printed images of sensors"],
    "duration_minutes": 50,
    "prerequisites": [
        "Sessions 16-19: Introduction to sensors/actuators, light sensors, temperature sensors, if-then logic unplugged"
    ],
    "session_position_in_topic": 5,
    "total_sessions_in_topic": 8,
    "notes": (
        "Session 5 of 8 in Sensors phase (62%). Students have already covered: "
        "sensor vs actuator distinction, LDR (light sensor), temperature sensor, basic if-then logic. "
        "Now introduce motion (PIR concept) and sound sensors. "
        "Keep fully unplugged — NO Arduino, NO coding, NO simulation. "
        "Use role-play and worksheets only."
    ),
}

# Previous sessions summary for continuity
PREV_SUMMARY = (
    "Session 16: 'Introduction to Sensors & Actuators' — Covered: sensor definition, actuator definition. Key terms: sensor, actuator, input, output, automation.\n"
    "Session 17: 'Light Sensors (LDR)' — Covered: how LDR works, light-dependent resistance concept. Key terms: LDR, resistance, light intensity, photocell.\n"
    "Session 18: 'Temperature Sensors' — Covered: thermistor concept, temperature-based automation. Key terms: thermistor, temperature sensor, thermal energy.\n"
    "Session 19: 'If-Then Logic (Unplugged)' — Covered: if-then logic statements, condition-action pairs. Key terms: if-then, condition, action, logic, trigger.\n"
)

def main():
    print("=" * 60)
    print(f"  ENpower Curriculum Pipeline")
    print(f"  Grade {GRADE} | Session {SESSION} | Motion & Sound Sensors")
    print("=" * 60)

    import os; os.chdir('/home/user/Stem-curriculum-generator')

    config = PipelineConfig()
    model = config.model
    constraints = config.get_constraint_prompt(GRADE, SESSION)
    guardrail_rules = config.get_guardrail_prompt()
    phase = config.get_phase_for_session(GRADE, SESSION)

    print("\n[1/5] Generating lesson plan...")
    lesson_agent = LessonPlanAgent(model=model, max_tokens=config.max_tokens)
    lesson_plan = lesson_agent.generate(
        session_data=SESSION_DATA,
        grade=GRADE,
        session_number=SESSION,
        constraints=constraints,
        guardrail_rules=guardrail_rules,
        previous_sessions_summary=PREV_SUMMARY,
    )
    print(f"  ✓ Lesson plan: {lesson_plan.get('topic')}")

    print("\n[2/5] Generating assessment...")
    assessment_agent = AssessmentAgent(model=model, max_tokens=config.max_tokens)
    assessment = assessment_agent.generate(
        lesson_plan=lesson_plan, grade=GRADE, guardrail_rules=guardrail_rules
    )
    print(f"  ✓ Assessment: {len(assessment.get('mcqs', []))} MCQs, {len(assessment.get('fill_in_blank', []))} FIBs")

    print("\n[3/5] Generating PPT content...")
    ppt_agent = PPTAgent(model=model, branding=config.branding, max_tokens=config.max_tokens)
    ppt_data = ppt_agent.generate(
        lesson_plan=lesson_plan, grade=GRADE, guardrail_rules=guardrail_rules
    )
    print(f"  ✓ PPT: {ppt_data.get('total_slides', len(ppt_data.get('slides', [])))} slides")

    print("\n[4/5] Generating equipment list...")
    equipment_agent = EquipmentAgent(model=model, max_tokens=config.max_tokens)
    equipment_data = equipment_agent.generate(
        lesson_plan=lesson_plan,
        guardrail_rules=guardrail_rules,
        allowed_tools=phase["tools"],
    )
    print(f"  ✓ Equipment: {len(equipment_data.get('items', []))} items")

    print("\n[5/5] Running guardrail validation...")
    validator = GuardrailValidator(model=config.validator_model)
    validation = validator.validate(
        framework_session=SESSION_DATA,
        lesson_plan=lesson_plan,
        assessment=assessment,
        ppt_data=ppt_data,
        equipment_data=equipment_data,
        session_number=SESSION,
        constraints=constraints,
    )
    status = validation.get("overall_status", "UNKNOWN")
    icon = {"PASS": "✅", "FAIL": "❌", "NEEDS_REVIEW": "⚠️"}.get(status, "❓")
    print(f"  {icon} Validation: {status}")

    print("\nBuilding output files...")
    builder = OutputBuilder(output_dir="outputs", branding=config.branding)
    files = builder.build_all(
        session_number=SESSION,
        lesson_plan=lesson_plan,
        assessment=assessment,
        ppt_data=ppt_data,
        equipment_data=equipment_data,
    )

    print("\n" + "=" * 60)
    print(f"  COMPLETE — Grade {GRADE} Session {SESSION}")
    print("=" * 60)
    for name, path in files.items():
        print(f"  📄 {name}: {path}")

    for issue in validation.get("critical_issues", []):
        print(f"  ❌ {issue}")
    for warn in validation.get("warnings", []):
        print(f"  ⚠️  {warn}")

if __name__ == "__main__":
    main()
