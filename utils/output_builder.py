"""
Output Builder
Generates .docx lesson plans, .docx assessments, .pptx student slides, and .csv equipment lists.
Uses python-docx and python-pptx for file generation.
"""

import csv
import json
from pathlib import Path


class OutputBuilder:
    """Builds the final output files for each session."""

    def __init__(self, output_dir: str, branding: dict):
        self.output_dir = Path(output_dir)
        self.branding = branding

    def build_all(
        self,
        session_number: int,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
    ) -> dict:
        """
        Build all output files for a session.

        Returns dict mapping file type → file path.
        """
        session_dir = self.output_dir / f"session_{session_number}"
        session_dir.mkdir(parents=True, exist_ok=True)

        files = {}

        # Save raw JSON outputs
        self._save_json(session_dir / "lesson_plan.json", lesson_plan)
        self._save_json(session_dir / "assessment.json", assessment)
        self._save_json(session_dir / "ppt_content.json", ppt_data)
        self._save_json(session_dir / "equipment.json", equipment_data)

        # Build formatted documents
        files["lesson_plan_docx"] = self._build_lesson_plan_docx(session_dir, session_number, lesson_plan)
        files["assessment_docx"] = self._build_assessment_docx(session_dir, session_number, assessment)
        files["equipment_csv"] = self._build_equipment_csv(session_dir, session_number, equipment_data)
        files["ppt_json"] = str(session_dir / "ppt_content.json")  # PPT JSON for downstream tools

        return files

    # ── Lesson Plan .docx ────────────────────────────────────────────────────

    def _build_lesson_plan_docx(self, session_dir: Path, session_number: int, lesson_plan: dict) -> str:
        """Generate a .docx lesson plan file."""
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()
            company = self.branding.get("company", "ENpower")
            tagline = self.branding.get("tagline", "THINK . CREATE . LEAD.")

            # Title
            heading = doc.add_heading(f"{company} STEM Labs", 0)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

            sub = doc.add_paragraph(f"{tagline} | Lesson Plan")
            sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

            doc.add_heading(
                f"Session {session_number}: {lesson_plan.get('topic', '')}",
                level=1,
            )

            # Metadata table
            table = doc.add_table(rows=4, cols=2)
            table.style = "Table Grid"
            rows_data = [
                ("Grade", str(lesson_plan.get("grade", ""))),
                ("Duration", f"{lesson_plan.get('duration_minutes', 50)} minutes"),
                ("Tangible Outcome", lesson_plan.get("tangible_outcome", "")),
                ("Prior Knowledge", ", ".join(lesson_plan.get("prior_knowledge", []))),
            ]
            for i, (label, value) in enumerate(rows_data):
                table.rows[i].cells[0].text = label
                table.rows[i].cells[1].text = value

            # Learning objectives
            doc.add_heading("Learning Objectives", level=2)
            for obj in lesson_plan.get("learning_objectives", []):
                doc.add_paragraph(obj, style="List Bullet")

            # Vocabulary
            vocab = lesson_plan.get("vocabulary", [])
            if vocab:
                doc.add_heading("Vocabulary", level=2)
                for v in vocab:
                    p = doc.add_paragraph(style="List Bullet")
                    run = p.add_run(f"{v.get('term', '')}: ")
                    run.bold = True
                    p.add_run(v.get("definition", ""))

            # 5E Phases
            five_e = lesson_plan.get("five_e", {})
            phase_labels = {
                "engage": "Engage",
                "explore": "Explore",
                "explain": "Explain",
                "elaborate": "Elaborate",
                "evaluate": "Evaluate",
            }
            phase_durations = {"engage": 5, "explore": 15, "explain": 10, "elaborate": 15, "evaluate": 5}

            doc.add_heading("5E Lesson Plan", level=2)

            for phase_key, phase_label in phase_labels.items():
                phase = five_e.get(phase_key, {})
                duration = phase.get("duration_minutes", phase_durations.get(phase_key, 0))
                doc.add_heading(f"{phase_label} ({duration} min)", level=3)

                if phase_key == "engage":
                    doc.add_paragraph(f"Teacher: {phase.get('teacher_action', '')}")
                    doc.add_paragraph(f"Students: {phase.get('student_action', '')}")
                    if phase.get("indian_context"):
                        p = doc.add_paragraph()
                        r = p.add_run("Indian Context: ")
                        r.bold = True
                        p.add_run(phase.get("indian_context", ""))
                    for q in phase.get("questions_to_ask", []):
                        doc.add_paragraph(f"• {q}", style="List Bullet")

                elif phase_key in ("explore", "elaborate"):
                    doc.add_paragraph(f"Activity: {phase.get('activity_name', '')}")
                    for step in phase.get("instructions", []):
                        doc.add_paragraph(step, style="List Number")
                    if phase.get("student_deliverable"):
                        p = doc.add_paragraph()
                        r = p.add_run("Deliverable: ")
                        r.bold = True
                        p.add_run(phase.get("student_deliverable", ""))

                elif phase_key == "explain":
                    for concept in phase.get("key_concepts", []):
                        doc.add_paragraph(concept, style="List Bullet")
                    if phase.get("teacher_script_notes"):
                        doc.add_paragraph(f"Notes: {phase.get('teacher_script_notes', '')}")

                elif phase_key == "evaluate":
                    for check in phase.get("formative_checks", []):
                        doc.add_paragraph(f"• {check}", style="List Bullet")

            # Teacher notes
            notes = lesson_plan.get("teacher_notes", [])
            if notes:
                doc.add_heading("Teacher Notes", level=2)
                for note in notes:
                    doc.add_paragraph(note, style="List Bullet")

            # Homework
            hw = lesson_plan.get("homework_extension", "")
            if hw:
                doc.add_heading("Homework / Extension", level=2)
                doc.add_paragraph(hw)

            filepath = session_dir / f"session_{session_number}_lesson_plan.docx"
            doc.save(str(filepath))
            return str(filepath)

        except ImportError:
            # Fallback: save as text file
            return self._build_lesson_plan_txt(session_dir, session_number, lesson_plan)

    def _build_lesson_plan_txt(self, session_dir: Path, session_number: int, lesson_plan: dict) -> str:
        """Fallback text-based lesson plan if python-docx not available."""
        lines = [
            f"ENpower STEM Labs | Lesson Plan",
            f"Session {session_number}: {lesson_plan.get('topic', '')}",
            "=" * 60,
            f"Grade: {lesson_plan.get('grade')}  |  Duration: {lesson_plan.get('duration_minutes', 50)} min",
            f"Tangible Outcome: {lesson_plan.get('tangible_outcome', '')}",
            "",
            "LEARNING OBJECTIVES",
        ]
        for obj in lesson_plan.get("learning_objectives", []):
            lines.append(f"  - {obj}")

        lines.append("")
        five_e = lesson_plan.get("five_e", {})
        for phase in ["engage", "explore", "explain", "elaborate", "evaluate"]:
            p = five_e.get(phase, {})
            dur = p.get("duration_minutes", 0)
            lines.append(f"\n{phase.upper()} ({dur} min)")
            lines.append("-" * 40)
            for k, v in p.items():
                if k != "duration_minutes":
                    lines.append(f"  {k}: {v}")

        filepath = session_dir / f"session_{session_number}_lesson_plan.txt"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        return str(filepath)

    # ── Assessment .docx ─────────────────────────────────────────────────────

    def _build_assessment_docx(self, session_dir: Path, session_number: int, assessment: dict) -> str:
        """Generate a .docx assessment file."""
        try:
            from docx import Document
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()
            company = self.branding.get("company", "ENpower")

            doc.add_heading(f"{company} STEM Labs — Assessment", 0)
            doc.add_paragraph(
                f"Session {session_number}: {assessment.get('topic', '')} | Grade {assessment.get('grade', '')}"
            )
            doc.add_paragraph(assessment.get("instructions_to_student", "Answer all questions."))
            doc.add_paragraph("")

            # MCQs
            mcqs = assessment.get("mcq", [])
            if mcqs:
                doc.add_heading("Section A: Multiple Choice Questions", level=2)
                doc.add_paragraph("Circle the correct answer. (1 mark each)")
                for i, q in enumerate(mcqs, 1):
                    p = doc.add_paragraph()
                    p.add_run(f"Q{i}. {q.get('question', '')}").bold = True
                    for key, val in q.get("options", {}).items():
                        doc.add_paragraph(f"    {key}) {val}")

            # Fill in blank
            fibs = assessment.get("fill_in_blank", [])
            if fibs:
                doc.add_heading("Section B: Fill in the Blanks", level=2)
                for i, q in enumerate(fibs, 1):
                    doc.add_paragraph(f"Q{i}. {q.get('question', '')} ___________")

            # Match the following
            mtf = assessment.get("match_the_following", {})
            if mtf:
                doc.add_heading("Section C: Match the Following", level=2)
                doc.add_paragraph(mtf.get("instructions", "Match Column A with Column B."))
                table = doc.add_table(rows=1, cols=2)
                table.style = "Table Grid"
                hdr = table.rows[0].cells
                hdr[0].text = "Column A"
                hdr[1].text = "Column B"
                col_a = mtf.get("column_a", [])
                col_b = mtf.get("column_b", [])
                for a, b in zip(col_a, col_b):
                    row = table.add_row().cells
                    row[0].text = a
                    row[1].text = b

            # True/False
            tfs = assessment.get("true_false", [])
            if tfs:
                doc.add_heading("Section D: True or False", level=2)
                for i, q in enumerate(tfs, 1):
                    doc.add_paragraph(f"Q{i}. {q.get('statement', '')}  [True / False]")

            # Short answer
            sas = assessment.get("short_answer", [])
            if sas:
                doc.add_heading("Section E: Short Answer", level=2)
                for i, q in enumerate(sas, 1):
                    doc.add_paragraph(f"Q{i}. ({q.get('marks', 2)} marks) {q.get('question', '')}")
                    doc.add_paragraph("Answer: " + "_" * 60)

            # Answer key (separate page)
            doc.add_page_break()
            doc.add_heading("ANSWER KEY (Teacher Copy)", level=1)

            for i, q in enumerate(mcqs, 1):
                doc.add_paragraph(f"MCQ {i}: {q.get('correct_answer')} — {q.get('explanation', '')}")
            for i, q in enumerate(fibs, 1):
                doc.add_paragraph(f"FIB {i}: {q.get('answer', '')}")
            if mtf.get("correct_matches"):
                doc.add_paragraph(f"MTF: {json.dumps(mtf['correct_matches'])}")
            for i, q in enumerate(tfs, 1):
                ans = "True" if q.get("answer") else "False"
                correction = f" — Correction: {q.get('correction', '')}" if not q.get("answer") else ""
                doc.add_paragraph(f"T/F {i}: {ans}{correction}")
            for i, q in enumerate(sas, 1):
                doc.add_paragraph(f"SA {i}: {q.get('model_answer', '')}")

            filepath = session_dir / f"session_{session_number}_assessment.docx"
            doc.save(str(filepath))
            return str(filepath)

        except ImportError:
            return self._build_assessment_txt(session_dir, session_number, assessment)

    def _build_assessment_txt(self, session_dir: Path, session_number: int, assessment: dict) -> str:
        """Fallback text assessment."""
        lines = [f"Assessment — Session {session_number}: {assessment.get('topic', '')}", "=" * 60]
        for i, q in enumerate(assessment.get("mcq", []), 1):
            lines.append(f"\nQ{i}. {q.get('question', '')}")
            for k, v in q.get("options", {}).items():
                lines.append(f"  {k}) {v}")
        for i, q in enumerate(assessment.get("fill_in_blank", []), 1):
            lines.append(f"\nFIB {i}. {q.get('question', '')} ___")
        lines.append("\n\nANSWER KEY")
        for i, q in enumerate(assessment.get("mcq", []), 1):
            lines.append(f"MCQ {i}: {q.get('correct_answer')}")
        filepath = session_dir / f"session_{session_number}_assessment.txt"
        filepath.write_text("\n".join(lines), encoding="utf-8")
        return str(filepath)

    # ── Equipment .csv ───────────────────────────────────────────────────────

    def _build_equipment_csv(self, session_dir: Path, session_number: int, equipment_data: dict) -> str:
        """Generate a .csv equipment list."""
        filepath = session_dir / f"session_{session_number}_equipment.csv"

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow([
                "Item", "Description", "Qty/Group", "Total Qty", "Unit",
                "Price (INR)", "Supplier", "Reusable", "Notes"
            ])

            for item in equipment_data.get("equipment_list", []):
                writer.writerow([
                    item.get("item_name", ""),
                    item.get("description", ""),
                    item.get("quantity_per_group", ""),
                    item.get("total_quantity", ""),
                    item.get("unit", ""),
                    item.get("estimated_price_inr", ""),
                    item.get("supplier", ""),
                    "Yes" if item.get("reusable") else "No",
                    item.get("notes", ""),
                ])

            # Consumables section
            consumables = equipment_data.get("consumables", [])
            if consumables:
                writer.writerow([])
                writer.writerow(["CONSUMABLES", "", "", "", "", "", "", "", ""])
                for c in consumables:
                    writer.writerow([
                        c.get("item_name", ""),
                        "",
                        "",
                        c.get("quantity_total", ""),
                        "",
                        c.get("estimated_price_inr", ""),
                        "",
                        "No",
                        c.get("notes", ""),
                    ])

            writer.writerow([])
            writer.writerow(["TOTAL ESTIMATED COST (INR)", equipment_data.get("total_estimated_cost_inr", "")])
            writer.writerow(["Note", equipment_data.get("cost_notes", "[VERIFY_PRICE] before ordering")])

        return str(filepath)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _save_json(self, path: Path, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
