"""
Human-in-the-Loop (HIL) Review Module
Saves review files and handles approval workflow.
"""

import json
from pathlib import Path


class HILReview:

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
        review_dir = self.output_dir / f"session_{session_number}" / "review"
        review_dir.mkdir(parents=True, exist_ok=True)

        # Save all outputs for review
        files = {
            "lesson_plan.json": lesson_plan,
            "assessment.json": assessment,
            "ppt_data.json": ppt_data,
            "equipment.json": equipment_data,
            "validation.json": validation_report,
        }
        for fname, data in files.items():
            path = review_dir / fname
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return {"status": "PENDING", "review_dir": str(review_dir)}
