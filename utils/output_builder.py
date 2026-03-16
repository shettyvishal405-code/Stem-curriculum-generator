"""
Output Builder — generates .docx, .pptx, and .csv files from agent outputs.
Falls back to JSON/text if optional libraries are not installed.
"""

import csv
import json
from pathlib import Path


class OutputBuilder:
    """Builds output files from agent-generated content."""

    def __init__(self, output_dir: str = "outputs", branding: dict = None):
        self.output_dir = Path(output_dir)
        self.branding = branding or {}

        # Check optional library availability
        try:
            from docx import Document
            self._has_docx = True
        except ImportError:
            self._has_docx = False

        try:
            from pptx import Presentation
            self._has_pptx = True
        except ImportError:
            self._has_pptx = False

    def build_all(
        self,
        session_number: int,
        lesson_plan: dict,
        assessment: dict,
        ppt_data: dict,
        equipment_data: dict,
    ) -> dict:
        """Build all output files for a session. Returns dict of {name: path}."""
        session_dir = self.output_dir / f"session_{session_number}"
        session_dir.mkdir(parents=True, exist_ok=True)

        files = {}

        # Always save raw JSON
        self._save_json(session_dir / "lesson_plan.json", lesson_plan)
        self._save_json(session_dir / "assessment.json", assessment)
        self._save_json(session_dir / "ppt_content.json", ppt_data)
        self._save_json(session_dir / "equipment_list.json", equipment_data)

        # Build formatted files
        if self._has_docx:
            lp_path = self._build_lesson_plan_docx(session_dir, session_number, lesson_plan)
            files["lesson_plan"] = str(lp_path)

            assess_path = self._build_assessment_docx(session_dir, session_number, assessment)
            files["assessment"] = str(assess_path)
        else:
            lp_path = self._build_lesson_plan_txt(session_dir, session_number, lesson_plan)
            files["lesson_plan"] = str(lp_path)

            assess_path = self._build_assessment_txt(session_dir, session_number, assessment)
            files["assessment"] = str(assess_path)

        if self._has_pptx:
            ppt_path = self._build_ppt(session_dir, session_number, ppt_data)
            files["ppt"] = str(ppt_path)
        else:
            ppt_path = self._build_ppt_txt(session_dir, session_number, ppt_data)
            files["ppt"] = str(ppt_path)

        eq_path = self._build_equipment_csv(session_dir, session_number, equipment_data)
        files["equipment"] = str(eq_path)

        return files

    # ── .docx builders ──────────────────────────────────────────────────

    def _build_lesson_plan_docx(self, session_dir: Path, session_num: int, lp: dict) -> Path:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Title
        title = doc.add_heading(f"Session {session_num}: {lp.get('topic', '')}", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Metadata
        doc.add_paragraph(f"Grade: {lp.get('grade', '')} | Duration: 50 minutes | Format: 5E")
        doc.add_paragraph(f"Tangible Outcome: {lp.get('tangible_outcome', '')}")

        # Learning objectives
        doc.add_heading("Learning Objectives", level=2)
        for obj in lp.get("learning_objectives", []):
            doc.add_paragraph(obj, style="List Bullet")

        # Prior knowledge
        doc.add_heading("Prior Knowledge Required", level=2)
        for pk in lp.get("prior_knowledge", []):
            doc.add_paragraph(pk, style="List Bullet")

        # Materials
        doc.add_heading("Materials Needed", level=2)
        for mat in lp.get("materials_needed", []):
            doc.add_paragraph(mat, style="List Bullet")

        # Vocabulary
        vocab = lp.get("vocabulary", [])
        if vocab:
            doc.add_heading("Key Vocabulary", level=2)
            for v in vocab:
                p = doc.add_paragraph()
                run = p.add_run(f"{v.get('term', '')}: ")
                run.bold = True
                p.add_run(v.get("definition", ""))

        # 5E Phases
        doc.add_heading("5E Lesson Phases", level=2)
        phases_data = lp.get("5e_phases", {})
        phase_names = ["engage", "explore", "explain", "elaborate", "evaluate"]
        phase_labels = {
            "engage": "ENGAGE (5 min)",
            "explore": "EXPLORE (15 min)",
            "explain": "EXPLAIN (10 min)",
            "elaborate": "ELABORATE (15 min)",
            "evaluate": "EVALUATE (5 min)",
        }

        for phase_key in phase_names:
            phase = phases_data.get(phase_key, {})
            if not phase:
                continue
            doc.add_heading(phase_labels.get(phase_key, phase_key.upper()), level=3)

            duration = phase.get("duration_minutes", "")
            if duration:
                doc.add_paragraph(f"Duration: {duration} minutes")

            teacher = phase.get("teacher_activity", "")
            if teacher:
                p = doc.add_paragraph()
                p.add_run("Teacher Activity: ").bold = True
                p.add_run(teacher)

            student = phase.get("student_activity", "")
            if student:
                p = doc.add_paragraph()
                p.add_run("Student Activity: ").bold = True
                p.add_run(student)

            indian = phase.get("indian_context", "")
            if indian:
                p = doc.add_paragraph()
                p.add_run("Indian Context: ").bold = True
                p.add_run(indian)

            hands_on = phase.get("hands_on_task", "")
            if hands_on:
                p = doc.add_paragraph()
                p.add_run("Hands-On Task: ").bold = True
                p.add_run(hands_on)

            app_task = phase.get("application_task", "")
            if app_task:
                p = doc.add_paragraph()
                p.add_run("Application Task: ").bold = True
                p.add_run(app_task)

            key_concepts = phase.get("key_concepts", [])
            if key_concepts:
                doc.add_paragraph("Key Concepts:")
                for kc in key_concepts:
                    doc.add_paragraph(kc, style="List Bullet")

            formative = phase.get("formative_assessment", "")
            if formative:
                p = doc.add_paragraph()
                p.add_run("Formative Assessment: ").bold = True
                p.add_run(formative)

        # Differentiation
        diff = lp.get("differentiation", {})
        if diff:
            doc.add_heading("Differentiation", level=2)
            struggling = diff.get("struggling_learners", "")
            if struggling:
                p = doc.add_paragraph()
                p.add_run("Struggling Learners: ").bold = True
                p.add_run(struggling)
            advanced = diff.get("advanced_learners", "")
            if advanced:
                p = doc.add_paragraph()
                p.add_run("Advanced Learners: ").bold = True
                p.add_run(advanced)

        # Teacher notes
        notes = lp.get("teacher_notes", "")
        if notes:
            doc.add_heading("Teacher Notes", level=2)
            doc.add_paragraph(notes)

        # Homework
        hw = lp.get("homework_extension", "")
        if hw:
            doc.add_heading("Homework / Extension", level=2)
            doc.add_paragraph(hw)

        # Safety
        safety = lp.get("safety_reminders", [])
        if safety:
            doc.add_heading("Safety Reminders", level=2)
            for s in safety:
                doc.add_paragraph(s, style="List Bullet")

        path = session_dir / f"session_{session_num}_lesson_plan.docx"
        doc.save(str(path))
        return path

    def _build_assessment_docx(self, session_dir: Path, session_num: int, assessment: dict) -> Path:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Title
        title = doc.add_heading(f"Assessment — Session {session_num}: {assessment.get('topic', '')}", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # MCQs
        mcqs = assessment.get("mcqs", [])
        if mcqs:
            doc.add_heading("A. Multiple Choice Questions (1 mark each)", level=2)
            for i, mcq in enumerate(mcqs, 1):
                doc.add_paragraph(f"{i}. {mcq.get('question', '')}")
                for key, val in mcq.get("options", {}).items():
                    doc.add_paragraph(f"   ({key}) {val}", style="List Bullet")
                doc.add_paragraph("")

        # Fill in blank
        fibs = assessment.get("fill_in_blank", [])
        if fibs:
            doc.add_heading("B. Fill in the Blanks (1 mark each)", level=2)
            for i, fib in enumerate(fibs, 1):
                doc.add_paragraph(f"{i}. {fib.get('question', '')}")

        # Match the following
        mtf = assessment.get("match_the_following", {})
        if mtf:
            doc.add_heading("C. Match the Following (5 marks)", level=2)
            col_a = mtf.get("column_a", [])
            col_b = mtf.get("column_b", [])
            for i, (a, b) in enumerate(zip(col_a, col_b), 1):
                doc.add_paragraph(f"  {i}. {a}    |    {chr(64+i)}. {b}")

        # True/False
        tfs = assessment.get("true_false", [])
        if tfs:
            doc.add_heading("D. True or False (1 mark each)", level=2)
            for i, tf in enumerate(tfs, 1):
                doc.add_paragraph(f"{i}. {tf.get('statement', '')} [True / False]")

        # Short answer
        sas = assessment.get("short_answer", [])
        if sas:
            doc.add_heading("E. Short Answer Questions (3 marks each)", level=2)
            for i, sa in enumerate(sas, 1):
                doc.add_paragraph(f"{i}. {sa.get('question', '')}")
                doc.add_paragraph("   Answer: _" * 10)

        # Answer key
        doc.add_page_break()
        doc.add_heading("ANSWER KEY (Teacher Copy)", level=1)

        if mcqs:
            doc.add_heading("MCQ Answers:", level=2)
            for i, mcq in enumerate(mcqs, 1):
                doc.add_paragraph(f"{i}. {mcq.get('correct_answer', '')} — {mcq.get('explanation', '')}")

        if fibs:
            doc.add_heading("Fill in the Blank Answers:", level=2)
            for i, fib in enumerate(fibs, 1):
                doc.add_paragraph(f"{i}. {fib.get('answer', '')}")

        if tfs:
            doc.add_heading("True/False Answers:", level=2)
            for i, tf in enumerate(tfs, 1):
                answer = "True" if tf.get("answer") else "False"
                correction = tf.get("correction", "")
                line = f"{i}. {answer}"
                if correction:
                    line += f" — Correction: {correction}"
                doc.add_paragraph(line)

        if sas:
            doc.add_heading("Short Answer Model Answers:", level=2)
            for i, sa in enumerate(sas, 1):
                doc.add_paragraph(f"{i}. {sa.get('model_answer', '')}")

        path = session_dir / f"session_{session_num}_assessment.docx"
        doc.save(str(path))
        return path

    # ── .pptx builder ──────────────────────────────────────────────────

    def _build_ppt(self, session_dir: Path, session_num: int, ppt_data: dict) -> Path:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor

        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        branding_colors = self.branding.get("colors", {})
        primary_color = branding_colors.get("primary_purple", "723991")

        for slide_data in ppt_data.get("slides", []):
            slide_type = slide_data.get("slide_type", "content")

            if slide_type == "title":
                layout = prs.slide_layouts[0]  # Title slide
            else:
                layout = prs.slide_layouts[1]  # Title and content

            slide = prs.slides.add_slide(layout)

            # Set title
            if slide.shapes.title:
                slide.shapes.title.text = slide_data.get("title", "")

            # Set content
            if len(slide.placeholders) > 1:
                tf = slide.placeholders[1].text_frame
                tf.clear()
                bullets = slide_data.get("bullets", [])
                for i, bullet in enumerate(bullets):
                    if i == 0:
                        tf.text = bullet
                    else:
                        p = tf.add_paragraph()
                        p.text = bullet
                        p.level = 0

            # Add speaker notes
            notes = slide_data.get("speaker_notes", "")
            if notes:
                notes_slide = slide.notes_slide
                notes_slide.notes_text_frame.text = notes

        path = session_dir / f"session_{session_num}_student_ppt.pptx"
        prs.save(str(path))
        return path

    # ── .csv builder ──────────────────────────────────────────────────

    def _build_equipment_csv(self, session_dir: Path, session_num: int, eq_data: dict) -> Path:
        path = session_dir / f"session_{session_num}_equipment_list.csv"

        equipment = eq_data.get("equipment", [])
        if not equipment:
            path.write_text("No equipment required for this session.\n")
            return path

        fieldnames = [
            "Item", "Qty per Group", "Total Qty", "Unit",
            "Cost per Unit (INR)", "Total Cost (INR)", "Supplier",
            "Reusable", "Notes"
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in equipment:
                unit_cost = item.get("approximate_cost_inr", 0)
                total_qty = item.get("total_quantity", 0)
                writer.writerow({
                    "Item": item.get("item", ""),
                    "Qty per Group": item.get("quantity_per_group", ""),
                    "Total Qty": total_qty,
                    "Unit": item.get("unit", ""),
                    "Cost per Unit (INR)": unit_cost,
                    "Total Cost (INR)": item.get("total_cost_inr", unit_cost * total_qty),
                    "Supplier": item.get("supplier", ""),
                    "Reusable": "Yes" if item.get("reusable") else "No",
                    "Notes": item.get("notes", ""),
                })

            # Summary rows
            writer.writerow({})
            writer.writerow({
                "Item": "TOTAL",
                "Total Cost (INR)": eq_data.get("total_estimated_cost_inr", ""),
            })
            writer.writerow({
                "Item": "Cost per student (INR)",
                "Total Cost (INR)": eq_data.get("cost_per_student_inr", ""),
            })

        return path

    # ── Text fallbacks (when python-docx / python-pptx not installed) ──

    def _build_lesson_plan_txt(self, session_dir: Path, session_num: int, lp: dict) -> Path:
        lines = [
            f"SESSION {session_num}: {lp.get('topic', '')}",
            f"Grade: {lp.get('grade', '')} | Duration: 50 minutes | Format: 5E",
            f"Tangible Outcome: {lp.get('tangible_outcome', '')}",
            "",
            "LEARNING OBJECTIVES:",
        ]
        for obj in lp.get("learning_objectives", []):
            lines.append(f"  • {obj}")

        lines += ["", "MATERIALS NEEDED:"]
        for mat in lp.get("materials_needed", []):
            lines.append(f"  • {mat}")

        lines += ["", "5E PHASES:"]
        phases = lp.get("5e_phases", {})
        for phase_key in ["engage", "explore", "explain", "elaborate", "evaluate"]:
            phase = phases.get(phase_key, {})
            if phase:
                lines.append(f"\n{phase_key.upper()} ({phase.get('duration_minutes', '?')} min)")
                if phase.get("teacher_activity"):
                    lines.append(f"  Teacher: {phase['teacher_activity']}")
                if phase.get("student_activity"):
                    lines.append(f"  Students: {phase['student_activity']}")

        path = session_dir / f"session_{session_num}_lesson_plan.txt"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _build_assessment_txt(self, session_dir: Path, session_num: int, assessment: dict) -> Path:
        lines = [f"ASSESSMENT — Session {session_num}: {assessment.get('topic', '')}", ""]

        mcqs = assessment.get("mcqs", [])
        if mcqs:
            lines.append("A. MULTIPLE CHOICE QUESTIONS")
            for i, mcq in enumerate(mcqs, 1):
                lines.append(f"{i}. {mcq.get('question', '')}")
                for k, v in mcq.get("options", {}).items():
                    lines.append(f"   ({k}) {v}")
                lines.append("")

        fibs = assessment.get("fill_in_blank", [])
        if fibs:
            lines.append("B. FILL IN THE BLANKS")
            for i, fib in enumerate(fibs, 1):
                lines.append(f"{i}. {fib.get('question', '')}")
            lines.append("")

        tfs = assessment.get("true_false", [])
        if tfs:
            lines.append("C. TRUE OR FALSE")
            for i, tf in enumerate(tfs, 1):
                lines.append(f"{i}. {tf.get('statement', '')} [True / False]")
            lines.append("")

        sas = assessment.get("short_answer", [])
        if sas:
            lines.append("D. SHORT ANSWER")
            for i, sa in enumerate(sas, 1):
                lines.append(f"{i}. {sa.get('question', '')}")
            lines.append("")

        # Answer key
        lines += ["", "--- ANSWER KEY ---"]
        if mcqs:
            answers = [f"{i}. {m.get('correct_answer', '')}" for i, m in enumerate(mcqs, 1)]
            lines.append("MCQ: " + " | ".join(answers))
        if fibs:
            answers = [f"{i}. {f.get('answer', '')}" for i, f in enumerate(fibs, 1)]
            lines.append("FIB: " + " | ".join(answers))
        if tfs:
            answers = [f"{i}. {'T' if t.get('answer') else 'F'}" for i, t in enumerate(tfs, 1)]
            lines.append("T/F: " + " | ".join(answers))

        path = session_dir / f"session_{session_num}_assessment.txt"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _build_ppt_txt(self, session_dir: Path, session_num: int, ppt_data: dict) -> Path:
        lines = [f"PPT CONTENT — Session {session_num}: {ppt_data.get('topic', '')}", ""]

        for slide in ppt_data.get("slides", []):
            lines.append(f"Slide {slide.get('slide_number', '?')}: {slide.get('title', '')}")
            for bullet in slide.get("bullets", []):
                lines.append(f"  • {bullet}")
            graphic = slide.get("graphic_description", "")
            if graphic:
                lines.append(f"  [Graphic: {graphic}]")
            lines.append("")

        path = session_dir / f"session_{session_num}_student_ppt.txt"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _save_json(self, path: Path, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
