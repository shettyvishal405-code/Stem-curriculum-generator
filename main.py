"""
Main Pipeline Orchestrator
Coordinates all agents, guardrails, and human-in-the-loop review.

Usage:
  python main.py --framework path/to/framework.docx --grade 7 --subject "Robotics & AI"
  python main.py --framework path/to/framework.txt --grade 8 --session 1
  python main.py --batch 2-11 --approved-session1 outputs/session_1/
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_loader import PipelineConfig
from agents.framework_parser import FrameworkParserAgent
from agents.lesson_plan_agent import LessonPlanAgent
from agents.assessment_agent import AssessmentAgent
from agents.ppt_agent import PPTAgent
from agents.equipment_agent import EquipmentAgent
from guardrails.validator import GuardrailValidator
from utils.hil import HILReview
from utils.output_builder import OutputBuilder


class CurriculumPipeline:
    """
    Multi-agent curriculum generation pipeline.

    Flow:
    1. Parse framework document → structured sessions
    2. For Session 1:
       a. Generate lesson plan (5E format)
       b. Generate assessment (aligned to lesson)
       c. Generate student PPT (age-appropriate)
       d. Generate equipment list (Indian suppliers)
       e. Run guardrail validation
       f. HIL checkpoint — human reviews Session 1
    3. On approval: batch generate Sessions 2-11
    4. On rejection: re-run Session 1 with feedback
    """

    def __init__(self, config_path: str = None):
        self.config = PipelineConfig(config_path)
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)

        # Initialize agents
        model = self.config.model
        validator_model = self.config.validator_model

        self.parser = FrameworkParserAgent(model=model)
        self.lesson_agent = LessonPlanAgent(model=model, max_tokens=self.config.max_tokens)
        self.assessment_agent = AssessmentAgent(model=model, max_tokens=self.config.max_tokens)
        self.ppt_agent = PPTAgent(model=model, branding=self.config.branding, max_tokens=self.config.max_tokens)
        self.equipment_agent = EquipmentAgent(model=model, max_tokens=self.config.max_tokens)
        self.validator = GuardrailValidator(model=validator_model)

        # HIL and output builder
        self.hil = HILReview(output_dir=str(self.output_dir))
        self.builder = OutputBuilder(output_dir=str(self.output_dir), branding=self.config.branding)

        # State tracking
        self.framework_data = None
        self.session_outputs = {}
        self.previous_sessions_summary = ""

    def run(
        self,
        framework_path: str,
        grade: int,
        session_range: tuple = None,
        hil_feedback: str = None,
    ):
        """
        Run the full pipeline.

        Args:
            framework_path: Path to the framework document (.docx, .txt, .md)
            grade: Target grade (6, 7, or 8)
            session_range: Tuple (start, end) for batch mode, or None for full run
            hil_feedback: Feedback from previous HIL rejection (for re-runs)
        """
        print("\n" + "=" * 70)
        print("  ENpower Curriculum Pipeline")
        print(f"  Grade: {grade} | Framework: {framework_path}")
        print("=" * 70)

        start_time = time.time()

        # ── Step 1: Parse Framework ──────────────────────────
        print("\n[STEP 1] Parsing framework document...")
        framework_input = self._load_framework(framework_path)
        self.framework_data = self.parser.parse(framework_input, grade=grade)

        total_sessions = len(self.framework_data.get("sessions", []))
        grade_total = self.config.get_total_sessions(grade)
        print(f"  Extracted {total_sessions} sessions from framework (Grade {grade}: {grade_total} expected)")

        # Save parsed framework
        self._save_json("parsed_framework.json", self.framework_data)

        # Determine session range
        if session_range:
            start_session, end_session = session_range
        else:
            start_session, end_session = 1, min(total_sessions, grade_total)

        # ── Step 2: Generate Session 1 (with HIL) ────────────
        if start_session == 1:
            print(f"\n[STEP 2] Generating Session 1 (HIL checkpoint)...")
            session_1_result = self._generate_session(
                session_number=1,
                grade=grade,
                hil_feedback=hil_feedback,
            )

            if session_1_result["validation"]["overall_status"] == "FAIL":
                print("\n  ❌ Session 1 failed validation. Review critical issues above.")
                print("  Re-run with --feedback to provide corrections.")
                return

            # ── Step 3: HIL Review ───────────────────────────
            print(f"\n[STEP 3] Requesting human review of Session 1...")
            hil_decision = self.hil.request_review(
                session_number=1,
                lesson_plan=session_1_result["lesson_plan"],
                assessment=session_1_result["assessment"],
                ppt_data=session_1_result["ppt_data"],
                equipment_data=session_1_result["equipment_data"],
                validation_report=session_1_result["validation"],
            )

            # Build output files for Session 1
            print(f"\n[STEP 3b] Building Session 1 output files...")
            files = self.builder.build_all(
                session_number=1,
                lesson_plan=session_1_result["lesson_plan"],
                assessment=session_1_result["assessment"],
                ppt_data=session_1_result["ppt_data"],
                equipment_data=session_1_result["equipment_data"],
            )

            print(f"\n  Session 1 files generated:")
            for name, path in files.items():
                print(f"    📄 {name}: {path}")

            # Update session summary for continuity
            self._update_session_summary(1, session_1_result["lesson_plan"])

            print("\n" + "=" * 70)
            print("  ⏸️  PIPELINE PAUSED — Awaiting human review of Session 1")
            print("  Review files in: outputs/session_1/review/")
            print("")
            print("  To continue after review:")
            print(f"    APPROVE:  python main.py --framework {framework_path} --grade {grade} --batch 2-{end_session}")
            print(f"    REJECT:   python main.py --framework {framework_path} --grade {grade} --session 1 --feedback \"your feedback\"")
            print("=" * 70)

            start_session = 2  # If continuing, start from 2

        # ── Step 4: Batch Generate Remaining Sessions ────────
        if start_session > 1:
            # Load framework data if not already loaded
            if self.framework_data is None:
                framework_input = self._load_framework(framework_path)
                self.framework_data = self.parser.parse(framework_input, grade=grade)

            # Load previous session summaries
            self._load_previous_summaries(start_session - 1)

            print(f"\n[STEP 4] Batch generating Sessions {start_session}-{end_session}...")

            for session_num in range(start_session, end_session + 1):
                print(f"\n{'─' * 50}")
                print(f"  Generating Session {session_num}/{end_session}...")
                print(f"{'─' * 50}")

                result = self._generate_session(
                    session_number=session_num,
                    grade=grade,
                )

                # Build output files
                files = self.builder.build_all(
                    session_number=session_num,
                    lesson_plan=result["lesson_plan"],
                    assessment=result["assessment"],
                    ppt_data=result["ppt_data"],
                    equipment_data=result["equipment_data"],
                )

                # Update continuity summary
                self._update_session_summary(session_num, result["lesson_plan"])

                # Check validation
                status = result["validation"]["overall_status"]
                status_icon = {"PASS": "✅", "FAIL": "❌", "NEEDS_REVIEW": "⚠️"}.get(status, "❓")
                print(f"  Session {session_num}: {status_icon} {status}")

                if status == "FAIL":
                    print(f"  ⚠️  Session {session_num} has critical issues — review before proceeding")

        # ── Final Summary ────────────────────────────────────
        elapsed = time.time() - start_time
        self._print_summary(elapsed)

    def _generate_session(
        self,
        session_number: int,
        grade: int,
        hil_feedback: str = None,
    ) -> dict:
        """Generate all outputs for a single session."""
        sessions = self.framework_data.get("sessions", [])

        if session_number > len(sessions):
            raise ValueError(f"Session {session_number} not found in framework (only {len(sessions)} sessions)")

        session_data = sessions[session_number - 1]
        constraints = self.config.get_constraint_prompt(grade, session_number)
        guardrail_rules = self.config.get_guardrail_prompt()

        # Add HIL feedback if re-running
        if hil_feedback:
            constraints += f"\n\nHUMAN FEEDBACK FROM REVIEW:\n{hil_feedback}\nAddress ALL feedback points."

        # ── Agent 1: Lesson Plan ─────────────────────────────
        print(f"  [1/5] Generating lesson plan...")
        lesson_plan = self.lesson_agent.generate(
            session_data=session_data,
            grade=grade,
            session_number=session_number,
            constraints=constraints,
            guardrail_rules=guardrail_rules,
            previous_sessions_summary=self.previous_sessions_summary,
        )

        # ── Agent 2: Assessment ──────────────────────────────
        print(f"  [2/5] Generating assessment...")
        assessment = self.assessment_agent.generate(
            lesson_plan=lesson_plan,
            grade=grade,
            guardrail_rules=guardrail_rules,
        )

        # ── Agent 3: Student PPT ─────────────────────────────
        print(f"  [3/5] Generating student PPT content...")
        ppt_data = self.ppt_agent.generate(
            lesson_plan=lesson_plan,
            grade=grade,
            guardrail_rules=guardrail_rules,
        )

        # ── Agent 4: Equipment List ──────────────────────────
        print(f"  [4/5] Generating equipment list...")
        equipment_data = self.equipment_agent.generate(
            lesson_plan=lesson_plan,
            guardrail_rules=guardrail_rules,
        )

        # ── Guardrail Validation ─────────────────────────────
        print(f"  [5/5] Running guardrail validation...")
        validation = self.validator.validate(
            framework_session=session_data,
            lesson_plan=lesson_plan,
            assessment=assessment,
            ppt_data=ppt_data,
            equipment_data=equipment_data,
            session_number=session_number,
            constraints=constraints,
        )

        result = {
            "session_number": session_number,
            "lesson_plan": lesson_plan,
            "assessment": assessment,
            "ppt_data": ppt_data,
            "equipment_data": equipment_data,
            "validation": validation,
        }

        self.session_outputs[session_number] = result
        return result

    def _load_framework(self, path: str) -> str:
        """
        Load framework document.

        For .xlsx files: returns the filepath (parsed directly by the Excel parser).
        For text files: returns the text content.
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Framework file not found: {path}")

        # Excel files — return path for direct parsing
        if path.suffix in [".xlsx", ".xls"]:
            return str(path)

        if path.suffix in [".docx"]:
            import subprocess
            result = subprocess.run(
                ["pandoc", str(path), "-t", "plain"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["python", "-m", "markitdown", str(path)],
                    capture_output=True, text=True,
                )
            return result.stdout

        elif path.suffix in [".txt", ".md"]:
            return path.read_text(encoding="utf-8")

        elif path.suffix in [".pdf"]:
            import subprocess
            result = subprocess.run(
                ["python", "-m", "markitdown", str(path)],
                capture_output=True, text=True,
            )
            return result.stdout

        else:
            return path.read_text(encoding="utf-8")

    def _update_session_summary(self, session_number: int, lesson_plan: dict):
        """Update the running summary of completed sessions for continuity."""
        topic = lesson_plan.get("topic", "Unknown")
        objectives = lesson_plan.get("learning_objectives", [])
        vocab = [v.get("term", "") for v in lesson_plan.get("vocabulary", [])]

        summary_line = (
            f"Session {session_number}: '{topic}' — "
            f"Covered: {', '.join(objectives[:2])}. "
            f"Key terms: {', '.join(vocab[:5])}."
        )

        self.previous_sessions_summary += summary_line + "\n"

        # Save to file for batch mode
        summary_path = self.output_dir / "session_summaries.txt"
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(summary_line + "\n")

    def _load_previous_summaries(self, up_to_session: int):
        """Load previous session summaries from file."""
        summary_path = self.output_dir / "session_summaries.txt"
        if summary_path.exists():
            self.previous_sessions_summary = summary_path.read_text(encoding="utf-8")
            print(f"  Loaded summaries for {up_to_session} previous sessions")

    def _save_json(self, filename: str, data: dict):
        """Save data as JSON."""
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _print_summary(self, elapsed: float):
        """Print final pipeline summary."""
        print("\n" + "=" * 70)
        print("  PIPELINE COMPLETE")
        print(f"  Time: {elapsed:.1f}s")
        print("=" * 70)

        # Agent usage
        print("\n  Token Usage:")
        agents = [self.parser, self.lesson_agent, self.assessment_agent,
                  self.ppt_agent, self.equipment_agent, self.validator]
        total_tokens = 0
        for agent in agents:
            usage = agent.get_usage_summary()
            if usage["calls"] > 0:
                print(f"    {usage['agent']}: {usage['calls']} calls, {usage['total_tokens']:,} tokens")
                total_tokens += usage["total_tokens"]
        print(f"    ────────────────────────")
        print(f"    TOTAL: {total_tokens:,} tokens")

        # Output files
        print(f"\n  Output directory: {self.output_dir}/")
        for session_dir in sorted(self.output_dir.glob("session_*")):
            files = list(session_dir.glob("*.*"))
            non_json = [f for f in files if f.suffix != ".json" and not f.is_dir()]
            if non_json:
                print(f"    📁 {session_dir.name}/")
                for f in non_json:
                    print(f"       📄 {f.name}")


def main():
    parser = argparse.ArgumentParser(
        description="ENpower Multi-Agent Curriculum Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full run (Session 1 + HIL pause)
  python main.py --framework curriculum_framework.docx --grade 7

  # Re-run Session 1 with feedback
  python main.py --framework curriculum_framework.docx --grade 7 --session 1 --feedback "Make the explore activity simpler"

  # Batch mode (after Session 1 approval)
  python main.py --framework curriculum_framework.docx --grade 7 --batch 2-11

  # Single session
  python main.py --framework curriculum_framework.docx --grade 8 --session 5
        """,
    )

    parser.add_argument("--framework", required=True, help="Path to framework document (.docx, .txt, .md, .pdf)")
    parser.add_argument("--grade", type=int, required=True, choices=[6, 7, 8], help="Target grade")
    parser.add_argument("--session", type=int, help="Generate a single session")
    parser.add_argument("--batch", help="Batch range (e.g., '2-11')")
    parser.add_argument("--feedback", help="HIL feedback for re-run")
    parser.add_argument("--config", help="Path to custom config YAML")
    parser.add_argument("--subject", help="Subject name (for display only)")

    args = parser.parse_args()

    pipeline = CurriculumPipeline(config_path=args.config)

    if args.session:
        # Single session mode
        pipeline.run(
            framework_path=args.framework,
            grade=args.grade,
            session_range=(args.session, args.session),
            hil_feedback=args.feedback,
        )
    elif args.batch:
        # Batch mode
        start, end = map(int, args.batch.split("-"))
        pipeline.run(
            framework_path=args.framework,
            grade=args.grade,
            session_range=(start, end),
        )
    else:
        # Full run (Session 1 + HIL)
        pipeline.run(
            framework_path=args.framework,
            grade=args.grade,
            hil_feedback=args.feedback,
        )


if __name__ == "__main__":
    main()
