"""
Human-in-the-Loop (HIL) Review Module.

Saves review files and handles the HIL checkpoint for Session 1.
In production, this pauses for human review. In batch/CI mode, it auto-approves.
"""

import json
import os
from pathlib import Path


class HILReview:
    """Manages human-in-the-loop review checkpoints."""

    def __init__(self, output_dir: str = "outputs"):
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
        Save review files and return the HIL decision.

        In this implementation, files are saved to the review directory
        and the pipeline pauses with instructions for the human reviewer.
        The actual approval happens via re-running with --batch flag.

        Returns:
            dict with 'decision': 'PENDING' (human must re-run to approve)
        """
        review_dir = self.output_dir / f"session_{session_number}" / "review"
        review_dir.mkdir(parents=True, exist_ok=True)

        # Save all outputs for review
        self._save_review_file(review_dir / "lesson_plan.json", lesson_plan)
        self._save_review_file(review_dir / "assessment.json", assessment)
        self._save_review_file(review_dir / "ppt_content.json", ppt_data)
        self._save_review_file(review_dir / "equipment_list.json", equipment_data)
        self._save_review_file(review_dir / "validation_report.json", validation_report)

        # Create a human-readable summary
        summary = self._create_summary(session_number, lesson_plan, validation_report)
        (review_dir / "REVIEW_SUMMARY.txt").write_text(summary, encoding="utf-8")

        print(f"\n  Review files saved to: {review_dir}/")
        print(f"  Open REVIEW_SUMMARY.txt for a quick overview.")

        return {"decision": "PENDING", "review_dir": str(review_dir)}

    def _save_review_file(self, path: Path, data: dict):
        """Save data as formatted JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _create_summary(self, session_number: int, lesson_plan: dict, validation: dict) -> str:
        """Create a human-readable review summary."""
        topic = lesson_plan.get("topic", "Unknown")
        objectives = lesson_plan.get("learning_objectives", [])
        tangible = lesson_plan.get("tangible_outcome", "Not specified")
        status = validation.get("overall_status", "Unknown")
        critical = validation.get("critical_issues", [])
        warnings = validation.get("warnings", [])

        lines = [
            "=" * 70,
            f"  ENpower Curriculum — Session {session_number} Review",
            "=" * 70,
            "",
            f"TOPIC: {topic}",
            f"TANGIBLE OUTCOME: {tangible}",
            "",
            "LEARNING OBJECTIVES:",
        ]
        for obj in objectives:
            lines.append(f"  • {obj}")

        lines += [
            "",
            f"VALIDATION STATUS: {status}",
        ]

        if critical:
            lines.append("\nCRITICAL ISSUES (must fix):")
            for issue in critical:
                lines.append(f"  ❌ {issue}")

        if warnings:
            lines.append("\nWARNINGS (should fix):")
            for w in warnings:
                lines.append(f"  ⚠️  {w}")

        lines += [
            "",
            "=" * 70,
            "  ACTIONS:",
            "  APPROVE → python main.py --framework <path> --grade <N> --batch 2-<total>",
            "  REJECT  → python main.py --framework <path> --grade <N> --session 1 --feedback \"your feedback\"",
            "=" * 70,
        ]

        return "\n".join(lines)
