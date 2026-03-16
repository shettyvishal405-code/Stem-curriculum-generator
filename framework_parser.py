"""
Framework Parser Agent
Handles both Excel (.xlsx) and text-based framework documents.
The Excel parser handles the specific multi-row format from DB_50_session_Learning_outcomes.xlsx.
"""

import json
import openpyxl
from pathlib import Path
from .base_agent import BaseAgent
from utils.prompts import framework_parser_prompt


class FrameworkParserAgent(BaseAgent):
    """Parses a framework document into structured session data."""

    def __init__(self, model: str, max_tokens: int = 4096):
        super().__init__(
            name="FrameworkParser",
            model=model,
            max_tokens=max_tokens,
            temperature=0.0,
        )

    def parse(self, framework_input: str, grade: int = None) -> dict:
        """
        Parse the framework document.

        Args:
            framework_input: Either a file path (for .xlsx) or raw text content.
            grade: Target grade (required for xlsx to select the right sheet).

        Returns:
            Structured dict with sessions, topics, learning outcomes, etc.
        """
        path = Path(framework_input)

        if path.exists() and path.suffix in [".xlsx", ".xls"]:
            return self._parse_excel(str(path), grade)
        else:
            # Text-based — use AI agent
            return self._parse_text(framework_input)

    def _parse_excel(self, filepath: str, grade: int) -> dict:
        """
        Parse the Excel framework document directly (no AI needed — deterministic).

        Handles the specific format:
        Row 1: Headers (Topic | Session count | Learning Outcomes | Tangible outcome)
        Row 2+: Topics with session counts in first column, outcomes spread across rows.
        """
        wb = openpyxl.load_workbook(filepath, data_only=True)

        # Find the right sheet
        sheet_name = f"Grade {grade}"
        if sheet_name not in wb.sheetnames:
            # Try variations
            for sn in wb.sheetnames:
                if str(grade) in sn:
                    sheet_name = sn
                    break
            else:
                raise ValueError(
                    f"No sheet found for Grade {grade}. Available sheets: {wb.sheetnames}"
                )

        ws = wb[sheet_name]
        print(f"  [FrameworkParser] Parsing sheet: '{sheet_name}' ({ws.max_row} rows)")

        # Parse topics and outcomes
        topics = []
        current_topic = None
        cumulative_session = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            col_topic = str(row[0]).strip() if row[0] else ""
            col_count = row[1] if len(row) > 1 else None
            col_outcome = str(row[2]).strip() if len(row) > 2 and row[2] else ""
            col_tangible = str(row[3]).strip() if len(row) > 3 and row[3] else ""

            # New topic block
            if col_topic and col_topic != "None":
                session_count = int(col_count) if col_count else 0
                start_session = cumulative_session + 1
                cumulative_session += session_count

                current_topic = {
                    "topic": col_topic,
                    "session_count": session_count,
                    "start_session": start_session,
                    "end_session": cumulative_session,
                    "learning_outcomes": [],
                    "tangible_outcome": col_tangible if col_tangible and col_tangible != "None" else "",
                }
                topics.append(current_topic)

            # Outcome row (either on the topic row or continuation rows)
            if col_outcome and col_outcome != "None" and current_topic:
                current_topic["learning_outcomes"].append(col_outcome)

        # Expand topics into individual sessions
        sessions = []
        for topic_block in topics:
            sc = topic_block["session_count"]
            if sc == 0:
                continue

            for i in range(sc):
                session_num = topic_block["start_session"] + i
                session = {
                    "session_number": session_num,
                    "topic": topic_block["topic"],
                    "subtopics": [],
                    "learning_outcomes": topic_block["learning_outcomes"],
                    "tangible_outcome": topic_block["tangible_outcome"],
                    "suggested_activities": [],
                    "tools_software": [],
                    "duration_minutes": 50,
                    "prerequisites": [],
                    "session_position_in_topic": i + 1,
                    "total_sessions_in_topic": sc,
                    "notes": "",
                }

                # Add pacing context
                if sc > 1:
                    if i == 0:
                        session["notes"] = f"First of {sc} sessions on this topic. Introduce foundational concepts."
                    elif i == sc - 1:
                        session["notes"] = f"Last of {sc} sessions. Consolidate learning and produce tangible outcome."
                    else:
                        session["notes"] = f"Session {i + 1} of {sc}. Build progressively on prior sessions."

                sessions.append(session)

        # Build result
        result = {
            "subject": f"ENpower STEM Lab — Grade {grade}",
            "grade": grade,
            "total_sessions": cumulative_session,
            "target_grades": [grade],
            "board": "CBSE/ICSE",
            "topic_blocks": topics,
            "sessions": sessions,
            "extraction_warnings": [],
            "source_file": filepath,
            "source_sheet": sheet_name,
        }

        # Validate
        self._validate_extraction(result)

        print(f"  [FrameworkParser] Extracted {len(topics)} topic blocks, {len(sessions)} sessions")
        return result

    def _parse_text(self, framework_text: str) -> dict:
        """Parse text-based framework using AI agent."""
        system_prompt = framework_parser_prompt()

        user_message = f"""Parse the following framework document and extract ALL session details.

## FRAMEWORK DOCUMENT
---
{framework_text}
---

Extract every session with its topic, learning outcomes, activities, tools, and tangible outcomes.
Return the result as a JSON object following the specified format.
Remember: Extract ONLY what is in the document. Use "NOT_SPECIFIED" for missing fields."""

        result = self.call(system_prompt, user_message)
        self._validate_extraction(result)
        return result

    def _validate_extraction(self, data: dict):
        """Validate the extracted data has minimum required fields."""
        warnings = data.get("extraction_warnings", [])

        if "sessions" not in data or not data["sessions"]:
            raise ValueError("Framework parser extracted zero sessions. Check the input document.")

        for session in data["sessions"]:
            sn = session.get("session_number", "?")

            if not session.get("topic"):
                warnings.append(f"Session {sn}: No topic extracted")

            los = session.get("learning_outcomes", [])
            if not los or los == ["NOT_SPECIFIED"]:
                warnings.append(f"Session {sn}: No learning outcomes — will need to derive from topic")

            tangible = session.get("tangible_outcome", "")
            if not tangible or tangible == "NOT_SPECIFIED":
                warnings.append(f"Session {sn}: No tangible outcome specified")

        data["extraction_warnings"] = warnings

        if warnings:
            print(f"  [FrameworkParser] {len(warnings)} extraction warnings:")
            for w in warnings[:10]:
                print(f"    ⚠ {w}")
            if len(warnings) > 10:
                print(f"    ... and {len(warnings) - 10} more")
