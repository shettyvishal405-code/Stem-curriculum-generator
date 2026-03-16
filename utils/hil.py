"""
Human-in-the-Loop (HIL) Review Module
Saves review packages and reads approval/rejection decisions.
"""

import json
import os
from pathlib import Path


class HILReview:
    """
    Manages the human review checkpoint for Session 1.

    Workflow:
    1. Pipeline calls request_review() — saves a review package to disk.
    2. Human reviews the files in outputs/session_1/review/.
    3. Human creates approved.txt or rejected.txt in that directory.
    4. Pipeline (batch mode) reads the decision from the file.
    """

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def request_review(
        self,
        session_number: int,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
        validation_report: dict,
    ) -> dict:
        """
        Save review package and return review metadata.

        Files saved:
        - session_N/review/lesson_plan.json
        - session_N/review/assessment.json
        - session_N/review/ppt_content.json
        - session_N/review/equipment.json
        - session_N/review/validation_report.json
        - session_N/review/review_checklist.txt
        """
        review_dir = self.output_dir / f"session_{session_number}" / "review"
        review_dir.mkdir(parents=True, exist_ok=True)

        # Save all outputs as JSON for review
        self._save(review_dir / "lesson_plan.json", lesson_plan)
        self._save(review_dir / "assessment.json", assessment)
        self._save(review_dir / "ppt_content.json", ppt_data)
        self._save(review_dir / "equipment.json", equipment_data)
        self._save(review_dir / "validation_report.json", validation_report)

        # Write human-readable checklist
        checklist = self._build_checklist(session_number, lesson_plan, validation_report)
        (review_dir / "review_checklist.txt").write_text(checklist, encoding="utf-8")

        print(f"  [HIL] Review package saved to: {review_dir}/")
        print(f"  [HIL] Validation status: {validation_report.get('overall_status', 'UNKNOWN')}")

        critical = validation_report.get("critical_issues", [])
        if critical:
            print(f"  [HIL] ⚠️  Critical issues ({len(critical)}):")
            for issue in critical:
                print(f"        - {issue}")

        return {
            "session_number": session_number,
            "review_dir": str(review_dir),
            "validation_status": validation_report.get("overall_status"),
            "critical_issues": critical,
        }

    def check_decision(self, session_number: int) -> str:
        """
        Check if a human has made a decision for a session.

        Returns: 'approved', 'rejected', or 'pending'
        """
        review_dir = self.output_dir / f"session_{session_number}" / "review"

        if (review_dir / "approved.txt").exists():
            return "approved"
        if (review_dir / "rejected.txt").exists():
            content = (review_dir / "rejected.txt").read_text(encoding="utf-8")
            return f"rejected: {content}"

        return "pending"

    def _save(self, path: Path, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _build_checklist(self, session_number: int, lesson_plan: dict, validation: dict) -> str:
        """Build a human-readable review checklist."""
        status = validation.get("overall_status", "UNKNOWN")
        critical = validation.get("critical_issues", [])
        verify_flags = validation.get("verify_flags", [])

        lines = [
            f"ENpower Curriculum Pipeline — Session {session_number} Review Checklist",
            "=" * 70,
            f"",
            f"Topic: {lesson_plan.get('topic', 'N/A')}",
            f"Grade: {lesson_plan.get('grade', 'N/A')}",
            f"Validation Status: {status}",
            f"",
        ]

        if critical:
            lines += ["CRITICAL ISSUES (must fix before batch generation):"]
            for issue in critical:
                lines.append(f"  [ ] {issue}")
            lines.append("")

        if verify_flags:
            lines += ["[VERIFY] FLAGS (review these before approving):"]
            for flag in verify_flags:
                lines.append(f"  [ ] {flag}")
            lines.append("")

        lines += [
            "REVIEW CHECKLIST:",
            "  [ ] 1. Lesson plan follows 5E format and 50-minute timing",
            "  [ ] 2. Learning objectives use Bloom's taxonomy verbs",
            "  [ ] 3. Indian context included in Engage phase",
            "  [ ] 4. Tangible outcome is clearly achievable",
            "  [ ] 5. Assessment only tests content taught in lesson",
            "  [ ] 6. MCQs start with 'Which of the following...'",
            "  [ ] 7. Fill-in-blank starts with 'Name the...'",
            "  [ ] 8. False T/F items include corrections",
            "  [ ] 9. PPT has 8-12 slides, max 4 bullets each",
            "  [ ] 10. Equipment list uses INR pricing with [VERIFY_PRICE]",
            "",
            "DECISION:",
            "  To APPROVE: create a file named 'approved.txt' in this directory",
            "  To REJECT:  create 'rejected.txt' with your feedback as the content",
            "",
            "  Batch generation command after approval:",
            f"    python main.py --framework <path> --grade {lesson_plan.get('grade', 'X')} --batch 2-<total>",
        ]

        return "\n".join(lines)
