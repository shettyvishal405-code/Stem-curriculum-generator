"""
Output Builder — generates .docx, .pptx, and .csv files from agent outputs.
"""

import csv
import json
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class OutputBuilder:

    def __init__(self, output_dir: str = "outputs", branding: dict = None):
        self.output_dir = Path(output_dir)
        self.branding = branding or {}

    def build_all(
        self,
        session_number: int,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
    ) -> dict:
        session_dir = self.output_dir / f"session_{session_number}"
        session_dir.mkdir(parents=True, exist_ok=True)

        files = {}

        # Always save JSON
        for name, data in [
            ("lesson_plan", lesson_plan),
            ("assessment", assessment),
            ("ppt_data", ppt_data),
            ("equipment", equipment_data),
        ]:
            p = session_dir / f"{name}.json"
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        # Generate .docx files
        if DOCX_AVAILABLE:
            lp_path = session_dir / f"Session_{session_number}_Lesson_Plan.docx"
            self._build_lesson_plan_docx(lesson_plan, lp_path)
            files["lesson_plan"] = str(lp_path)

            as_path = session_dir / f"Session_{session_number}_Assessment.docx"
            self._build_assessment_docx(assessment, as_path)
            files["assessment"] = str(as_path)

        # Equipment CSV
        eq_path = session_dir / f"Session_{session_number}_Equipment.csv"
        self._build_equipment_csv(equipment_data, eq_path)
        files["equipment"] = str(eq_path)

        return files

    # ── Lesson Plan .docx ────────────────────────────

    def _build_lesson_plan_docx(self, lesson_plan: dict, path: Path):
        doc = Document()

        # Title
        title = doc.add_heading(
            f"Session {lesson_plan.get('session_number', '?')} — {lesson_plan.get('topic', '')}",
            level=1,
        )

        # Branding subtitle
        sub = doc.add_paragraph(
            f"ENpower STEM Labs | Grade {lesson_plan.get('grade', '')} | "
            f"Duration: {lesson_plan.get('duration_minutes', 50)} minutes"
        )
        sub.style = "Subtitle" if "Subtitle" in [s.name for s in doc.styles] else sub.style

        doc.add_paragraph()

        # Header info table
        table = doc.add_table(rows=3, cols=2)
        table.style = "Table Grid"
        rows_data = [
            ("Tangible Outcome", lesson_plan.get("tangible_outcome", "")),
            ("Prior Knowledge", ", ".join(lesson_plan.get("prior_knowledge", []))),
            ("Materials Needed", ", ".join(lesson_plan.get("materials_needed", []))),
        ]
        for i, (key, val) in enumerate(rows_data):
            row = table.rows[i]
            row.cells[0].text = key
            row.cells[1].text = val

        doc.add_paragraph()

        # Learning Objectives
        doc.add_heading("Learning Objectives", level=2)
        for obj in lesson_plan.get("learning_objectives", []):
            doc.add_paragraph(f"• {obj}", style="List Bullet")

        doc.add_paragraph()

        # Vocabulary
        vocab = lesson_plan.get("vocabulary", [])
        if vocab:
            doc.add_heading("Key Vocabulary", level=2)
            for v in vocab:
                p = doc.add_paragraph()
                run = p.add_run(v.get("term", "") + ": ")
                run.bold = True
                p.add_run(v.get("definition", ""))

            doc.add_paragraph()

        # 5E Phases
        phases_config = [
            ("engage", "Engage", "5 minutes", "🎯"),
            ("explore", "Explore", "15 minutes", "🔍"),
            ("explain", "Explain", "10 minutes", "📖"),
            ("elaborate", "Elaborate", "15 minutes", "🛠️"),
            ("evaluate", "Evaluate", "5 minutes", "✅"),
        ]

        phases = lesson_plan.get("5e_phases", {})

        for phase_key, phase_name, duration, icon in phases_config:
            phase_data = phases.get(phase_key, {})
            if not phase_data:
                continue

            doc.add_heading(f"{icon} {phase_name} ({duration})", level=2)

            if phase_key == "engage":
                self._add_labeled_para(doc, "Teacher Action", phase_data.get("teacher_action", ""))
                self._add_labeled_para(doc, "Student Action", phase_data.get("student_action", ""))
                self._add_labeled_para(doc, "Indian Context", phase_data.get("indian_context", ""))
                questions = phase_data.get("discussion_questions", [])
                if questions:
                    doc.add_paragraph("Discussion Questions:").bold = True
                    for q in questions:
                        doc.add_paragraph(f"  • {q}")

            elif phase_key == "explore":
                self._add_labeled_para(doc, "Activity", phase_data.get("activity_name", ""))
                instructions = phase_data.get("instructions", [])
                if instructions:
                    doc.add_paragraph("Instructions:").bold = True
                    for i, step in enumerate(instructions, 1):
                        doc.add_paragraph(f"  {i}. {step}")
                self._add_labeled_para(doc, "Teacher Facilitation", phase_data.get("teacher_facilitation", ""))
                obs = phase_data.get("expected_observations", [])
                if obs:
                    doc.add_paragraph("Expected Observations:").bold = True
                    for o in obs:
                        doc.add_paragraph(f"  • {o}")

            elif phase_key == "explain":
                concepts = phase_data.get("key_concepts", [])
                if concepts:
                    doc.add_paragraph("Key Concepts:").bold = True
                    for c in concepts:
                        doc.add_paragraph(f"  • {c}")
                self._add_labeled_para(doc, "Teacher Script", phase_data.get("teacher_script", ""))
                self._add_labeled_para(doc, "Board Work", phase_data.get("board_work", ""))

            elif phase_key == "elaborate":
                self._add_labeled_para(doc, "Activity", phase_data.get("activity_name", ""))
                instructions = phase_data.get("instructions", [])
                if instructions:
                    doc.add_paragraph("Instructions:").bold = True
                    for i, step in enumerate(instructions, 1):
                        doc.add_paragraph(f"  {i}. {step}")
                diff = phase_data.get("differentiation", {})
                if diff:
                    doc.add_paragraph("Differentiation:").bold = True
                    if diff.get("support"):
                        doc.add_paragraph(f"  Support: {diff['support']}")
                    if diff.get("extension"):
                        doc.add_paragraph(f"  Extension: {diff['extension']}")

            elif phase_key == "evaluate":
                self._add_labeled_para(doc, "Method", phase_data.get("method", ""))
                questions = phase_data.get("questions", [])
                if questions:
                    doc.add_paragraph("Questions:").bold = True
                    for q in questions:
                        doc.add_paragraph(f"  • {q}")
                criteria = phase_data.get("success_criteria", [])
                if criteria:
                    doc.add_paragraph("Success Criteria:").bold = True
                    for c in criteria:
                        doc.add_paragraph(f"  ✓ {c}")

            doc.add_paragraph()

        # Differentiation
        diff = lesson_plan.get("differentiation", {})
        if diff:
            doc.add_heading("Differentiation Strategies", level=2)
            for key, val in diff.items():
                if val:
                    p = doc.add_paragraph()
                    r = p.add_run(key.replace("_", " ").title() + ": ")
                    r.bold = True
                    p.add_run(val)
            doc.add_paragraph()

        # Teacher Notes
        notes = lesson_plan.get("teacher_notes", [])
        if notes:
            doc.add_heading("Teacher Notes", level=2)
            for note in notes:
                doc.add_paragraph(f"📌 {note}")
            doc.add_paragraph()

        # Homework / Extension
        hw = lesson_plan.get("homework_extension", "")
        if hw:
            doc.add_heading("Homework / Extension", level=2)
            doc.add_paragraph(hw)
            doc.add_paragraph()

        # Cross-curricular links
        links = lesson_plan.get("cross_curricular_links", [])
        if links:
            doc.add_heading("Cross-Curricular Links", level=2)
            for link in links:
                doc.add_paragraph(f"• {link}")

        doc.save(str(path))

    def _add_labeled_para(self, doc, label: str, text: str):
        if not text:
            return
        p = doc.add_paragraph()
        r = p.add_run(label + ": ")
        r.bold = True
        p.add_run(text)

    # ── Assessment .docx ─────────────────────────────

    def _build_assessment_docx(self, assessment: dict, path: Path):
        doc = Document()

        doc.add_heading(
            f"Assessment — Session {assessment.get('session_number', '?')}: {assessment.get('topic', '')}",
            level=1,
        )
        doc.add_paragraph(f"Grade {assessment.get('grade', '')} | ENpower STEM Labs")
        doc.add_paragraph()

        # MCQs
        mcqs = assessment.get("mcqs", [])
        if mcqs:
            doc.add_heading("Section A: Multiple Choice Questions (1 mark each)", level=2)
            for i, q in enumerate(mcqs, 1):
                doc.add_paragraph(f"Q{i}. {q.get('question', '')}")
                for opt, text in q.get("options", {}).items():
                    doc.add_paragraph(f"    ({opt}) {text}")
                doc.add_paragraph()

        # Fill in the blank
        fibs = assessment.get("fill_in_blank", [])
        if fibs:
            doc.add_heading("Section B: Fill in the Blanks (1 mark each)", level=2)
            for i, q in enumerate(fibs, 1):
                doc.add_paragraph(f"Q{i}. {q.get('question', '')} ___________")
            doc.add_paragraph()

        # Match the following
        mtf = assessment.get("match_the_following", {})
        if mtf:
            doc.add_heading("Section C: Match the Following (4 marks)", level=2)
            col_a = mtf.get("column_a", [])
            col_b = mtf.get("column_b", [])
            table = doc.add_table(rows=len(col_a) + 1, cols=2)
            table.style = "Table Grid"
            table.rows[0].cells[0].text = "Column A"
            table.rows[0].cells[1].text = "Column B"
            for i, (a, b) in enumerate(zip(col_a, col_b), 1):
                table.rows[i].cells[0].text = f"{i}. {a}"
                table.rows[i].cells[1].text = f"{chr(64+i)}. {b}"
            doc.add_paragraph()

        # True / False
        tfs = assessment.get("true_false", [])
        if tfs:
            doc.add_heading("Section D: True or False (1 mark each)", level=2)
            for i, q in enumerate(tfs, 1):
                doc.add_paragraph(f"Q{i}. {q.get('statement', '')}  [True / False]")
            doc.add_paragraph()

        # Short answers
        sas = assessment.get("short_answers", [])
        if sas:
            doc.add_heading("Section E: Short Answer Questions (2 marks each)", level=2)
            for i, q in enumerate(sas, 1):
                doc.add_paragraph(f"Q{i}. {q.get('question', '')}")
                doc.add_paragraph("Answer: _______________________________________________")
                doc.add_paragraph()

        # Answer Key (separate section)
        doc.add_page_break()
        doc.add_heading("ANSWER KEY (Teacher Copy)", level=1)

        if mcqs:
            doc.add_heading("MCQ Answers", level=2)
            for i, q in enumerate(mcqs, 1):
                doc.add_paragraph(f"Q{i}: {q.get('correct_answer', '')} — {q.get('explanation', '')}")

        if fibs:
            doc.add_heading("Fill in the Blank Answers", level=2)
            for i, q in enumerate(fibs, 1):
                doc.add_paragraph(f"Q{i}: {q.get('answer', '')}")

        if mtf:
            doc.add_heading("Match the Following Answers", level=2)
            matches = mtf.get("correct_matches", {})
            for k, v in matches.items():
                doc.add_paragraph(f"{k} → {v}")

        if tfs:
            doc.add_heading("True/False Answers", level=2)
            for i, q in enumerate(tfs, 1):
                answer = "True" if q.get("answer") else "False"
                line = f"Q{i}: {answer}"
                if not q.get("answer") and q.get("corrected_statement"):
                    line += f" (Correction: {q['corrected_statement']})"
                doc.add_paragraph(line)

        if sas:
            doc.add_heading("Short Answer Model Answers", level=2)
            for i, q in enumerate(sas, 1):
                doc.add_paragraph(f"Q{i}: {q.get('model_answer', '')}")

        doc.save(str(path))

    # ── Equipment CSV ─────────────────────────────────

    def _build_equipment_csv(self, equipment_data: dict, path: Path):
        items = equipment_data.get("items", [])
        if not items:
            return

        fieldnames = [
            "item_name", "quantity_per_group", "total_quantity", "unit",
            "estimated_price_inr", "supplier", "notes", "price_verified",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(items)

            # Summary row
            total = equipment_data.get("total_estimated_cost_inr", 0)
            f.write(f"\nTotal Estimated Cost (INR):,,,,,{total},,\n")
