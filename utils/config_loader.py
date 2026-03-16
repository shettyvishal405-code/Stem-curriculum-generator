"""
Configuration loader for the curriculum pipeline.
Supports grade-specific phase constraints derived from the framework document.
"""

import yaml
from pathlib import Path


class PipelineConfig:
    """Loads and provides access to pipeline configuration with grade-aware constraints."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # Try config/ subdirectory first, then root
            candidates = [
                Path(__file__).parent.parent / "config" / "pipeline_config.yaml",
                Path(__file__).parent.parent / "pipeline_config.yaml",
            ]
            for p in candidates:
                if p.exists():
                    config_path = p
                    break
            else:
                raise FileNotFoundError("pipeline_config.yaml not found")
        with open(config_path, "r") as f:
            self._config = yaml.safe_load(f)

    # ── Basic accessors ──────────────────────────────

    @property
    def model(self) -> str:
        return self._config["models"]["primary"]

    @property
    def validator_model(self) -> str:
        return self._config["models"]["validator"]

    @property
    def max_tokens(self) -> int:
        return self._config["models"]["max_tokens_generation"]

    @property
    def temperature(self) -> float:
        return self._config["models"]["temperature_generation"]

    @property
    def branding(self) -> dict:
        return self._config["branding"]

    @property
    def audience(self) -> dict:
        return self._config["audience"]

    @property
    def lesson_plan(self) -> dict:
        return self._config["lesson_plan"]

    @property
    def assessment(self) -> dict:
        return self._config["assessment"]

    @property
    def ppt(self) -> dict:
        return self._config["ppt"]

    @property
    def equipment(self) -> dict:
        return self._config["equipment"]

    @property
    def guardrails(self) -> dict:
        return self._config["guardrails"]

    @property
    def hil_checkpoint(self) -> int:
        return self._config["pipeline"]["hil_checkpoint"]

    @property
    def cross_grade_constraints(self) -> dict:
        return self._config.get("cross_grade_constraints", {})

    # ── Grade-specific methods ───────────────────────

    def get_grade_config(self, grade: int) -> dict:
        key = f"grade_{grade}"
        if key not in self._config:
            raise ValueError(f"Grade {grade} not found in config.")
        return self._config[key]

    def get_total_sessions(self, grade: int) -> int:
        return self.get_grade_config(grade)["total_sessions"]

    def get_phase_for_session(self, grade: int, session_number: int) -> dict:
        grade_config = self.get_grade_config(grade)
        phases = grade_config.get("phases", {})

        for phase_name, phase_data in phases.items():
            session_list = phase_data.get("sessions", [])
            if session_number in session_list:
                return {
                    "phase_name": phase_name,
                    "topic": phase_data.get("topic", ""),
                    "constraints": phase_data.get("constraints", []),
                    "tools": phase_data.get("tools", []),
                    "tangible": phase_data.get("tangible", ""),
                    "sessions": session_list,
                    "session_position": session_list.index(session_number) + 1,
                    "total_in_phase": len(session_list),
                }

        raise ValueError(f"Session {session_number} not found for Grade {grade}")

    def get_constraint_prompt(self, grade: int, session_number: int) -> str:
        phase = self.get_phase_for_session(grade, session_number)
        lines = []

        lines.append("## SESSION CONSTRAINTS")
        lines.append(f"Grade: {grade} | Session: {session_number} of {self.get_total_sessions(grade)}")
        lines.append(f"Phase: {phase['phase_name']} — \"{phase['topic']}\"")
        lines.append(f"Position in phase: Session {phase['session_position']} of {phase['total_in_phase']}")
        lines.append("")

        if phase["constraints"]:
            lines.append("### PHASE RULES (MANDATORY)")
            for c in phase["constraints"]:
                lines.append(f"- {c}")
            lines.append("")

        if phase["tools"]:
            lines.append("### ALLOWED TOOLS/MATERIALS")
            lines.append(f"ONLY use these: {', '.join(phase['tools'])}")
            lines.append("Do NOT introduce tools not in this list.")
            lines.append("")

        if phase["tangible"]:
            lines.append("### REQUIRED TANGIBLE OUTCOME")
            lines.append(f"{phase['tangible']}")
            lines.append("The lesson MUST build toward this tangible outcome.")
            lines.append("")

        pos = phase["session_position"]
        total = phase["total_in_phase"]
        if total > 1:
            lines.append("### PACING GUIDANCE")
            if pos == 1:
                lines.append(f"This is the FIRST session of {total} in this topic. Introduce concepts. Do NOT rush.")
            elif pos == total:
                lines.append(f"This is the LAST session of {total}. Consolidate and produce the tangible outcome.")
            else:
                pct = round(pos / total * 100)
                lines.append(f"Session {pos} of {total} ({pct}% through this topic). Build progressively.")
            lines.append("")

        # Prior phase context
        grade_config = self.get_grade_config(grade)
        phases_list = list(grade_config.get("phases", {}).items())
        current_phase_idx = None
        for idx, (pname, _) in enumerate(phases_list):
            if pname == phase["phase_name"]:
                current_phase_idx = idx
                break

        if current_phase_idx and current_phase_idx > 0:
            prev_name, prev_data = phases_list[current_phase_idx - 1]
            lines.append("### PRIOR PHASE CONTEXT")
            lines.append(f"Students completed: \"{prev_data.get('topic', prev_name)}\" ({len(prev_data.get('sessions', []))} sessions)")
            lines.append(f"They can do: {prev_data.get('tangible', 'N/A')}")
            lines.append("")

        return "\n".join(lines)

    def get_guardrail_prompt(self) -> str:
        g = self.guardrails
        rules = []

        if g["hallucination"]["require_source_grounding"]:
            rules.append("EVERY factual claim must be traceable to the framework or universally verified knowledge. Do NOT invent facts.")
        if g["hallucination"]["flag_uncertain_content"]:
            rules.append("Flag uncertain content with [VERIFY] rather than guessing.")

        ac = g["age_check"]
        rules.append(f"Use language appropriate for {self.audience['age_range']} year old students.")
        rules.append(f"Max sentence length: {ac.get('max_sentence_length_student', 20)} words (student-facing).")
        rules.append("Define technical terms on first use.")

        cs = g["content_safety"]
        if cs["check_gender_neutrality"]:
            rules.append("Use gender-neutral language. Alternate he/she or use 'they'.")
        banned = cs.get("banned_terms", [])
        if banned:
            rules.append(f"NEVER use these terms in student-facing content: {', '.join(banned)}.")

        al = g["alignment"]
        if al["no_assessment_without_teaching"]:
            rules.append("NEVER assess content that was not explicitly taught in the lesson.")
        if al["bloom_taxonomy_check"]:
            rules.append("Learning objectives MUST use Bloom's taxonomy verbs.")

        return "\n".join(f"- {r}" for r in rules)

    def get_ppt_graphics_guidance(self, grade: int) -> str:
        guidance = self.ppt.get("graphics_guidance", {})
        grade_key = f"grade_{grade}"
        parts = []
        if grade_key in guidance:
            parts.append(f"Grade {grade} style: {guidance[grade_key]}")
        if "all_grades" in guidance:
            parts.append(f"General: {guidance['all_grades']}")
        return " | ".join(parts) if parts else ""
