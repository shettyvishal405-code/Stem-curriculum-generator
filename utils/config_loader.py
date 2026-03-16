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
            config_path = Path(__file__).parent.parent / "config" / "pipeline_config.yaml"
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
        """Get the full configuration block for a grade."""
        key = f"grade_{grade}"
        if key not in self._config:
            raise ValueError(f"Grade {grade} not found in config. Available: grade_6, grade_7, grade_8")
        return self._config[key]

    def get_total_sessions(self, grade: int) -> int:
        """Get total session count for a grade."""
        return self.get_grade_config(grade)["total_sessions"]

    def get_phase_for_session(self, grade: int, session_number: int) -> dict:
        """
        Find which phase a session belongs to and return its config.

        Returns dict with: phase_name, topic, constraints, tools, tangible, sessions
        """
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

        raise ValueError(
            f"Session {session_number} not found in any phase for Grade {grade}. "
            f"Valid sessions: 1-{self.get_total_sessions(grade)}"
        )

    def get_constraint_prompt(self, grade: int, session_number: int) -> str:
        """
        Build a comprehensive constraint prompt for a specific grade+session.

        Combines:
        1. Phase-specific constraints (from the framework-derived config)
        2. Position-in-phase context (e.g., "Session 2 of 10 in this topic")
        3. Cross-grade prerequisite context
        4. Safety-critical topics if relevant
        """
        phase = self.get_phase_for_session(grade, session_number)
        lines = []

        # Header
        lines.append(f"## SESSION CONSTRAINTS")
        lines.append(f"Grade: {grade} | Session: {session_number} of {self.get_total_sessions(grade)}")
        lines.append(f"Phase: {phase['phase_name']} — \"{phase['topic']}\"")
        lines.append(f"Position in phase: Session {phase['session_position']} of {phase['total_in_phase']}")
        lines.append("")

        # Phase constraints
        if phase["constraints"]:
            lines.append("### PHASE RULES (MANDATORY)")
            for c in phase["constraints"]:
                lines.append(f"- {c}")
            lines.append("")

        # Allowed tools
        if phase["tools"]:
            lines.append(f"### ALLOWED TOOLS/MATERIALS")
            lines.append(f"ONLY use these: {', '.join(phase['tools'])}")
            lines.append("Do NOT introduce tools not in this list.")
            lines.append("")

        # Tangible outcome
        if phase["tangible"]:
            lines.append(f"### REQUIRED TANGIBLE OUTCOME")
            lines.append(f"{phase['tangible']}")
            lines.append("The lesson MUST build toward this tangible outcome.")
            lines.append("")

        # Position-specific guidance
        pos = phase["session_position"]
        total = phase["total_in_phase"]
        if total > 1:
            lines.append("### PACING GUIDANCE")
            if pos == 1:
                lines.append(f"This is the FIRST session of {total} in this topic. Introduce concepts. Do NOT rush to the final deliverable.")
            elif pos == total:
                lines.append(f"This is the LAST session of {total} in this topic. Wrap up, consolidate, produce the tangible outcome.")
            else:
                pct = round(pos / total * 100)
                lines.append(f"This is session {pos} of {total} ({pct}% through this topic). Build progressively.")
            lines.append("")

        # Previous phase context
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
            lines.append(f"Students have just completed: \"{prev_data.get('topic', prev_name)}\" ({len(prev_data.get('sessions', []))} sessions)")
            lines.append(f"They can do: {prev_data.get('tangible', 'N/A')}")
            lines.append("Reference and build on this prior knowledge where appropriate.")
            lines.append("")

        # Cross-grade prerequisites
        cross = self.cross_grade_constraints
        prereqs = cross.get("prerequisite_chains", [])
        grade_key = f"G{grade}"
        relevant_prereqs = [p for p in prereqs if grade_key in p]
        if relevant_prereqs:
            lines.append("### PREREQUISITE ASSUMPTIONS")
            for p in relevant_prereqs:
                lines.append(f"- {p}")
            lines.append("")

        # Safety-critical topics
        safety = self.guardrails.get("content_safety", {}).get("safety_critical_topics", [])
        if safety:
            phase_tools_lower = " ".join(phase.get("tools", [])).lower()
            phase_topic_lower = phase.get("topic", "").lower()
            relevant_safety = []
            for s in safety:
                trigger = s.split("—")[0].strip().lower()
                if trigger in phase_tools_lower or trigger in phase_topic_lower:
                    relevant_safety.append(s)
            if relevant_safety:
                lines.append("### SAFETY WARNINGS (include in lesson)")
                for s in relevant_safety:
                    lines.append(f"⚠️ {s}")
                lines.append("")

        # Theory-before-practice rules
        tbp = cross.get("theory_before_practice", [])
        if tbp:
            relevant_tbp = []
            for rule in tbp:
                rule_lower = rule.lower()
                if any(t.lower() in rule_lower for t in phase.get("tools", [])):
                    relevant_tbp.append(rule)
                elif any(kw in rule_lower for kw in phase.get("topic", "").lower().split()):
                    relevant_tbp.append(rule)
            if relevant_tbp:
                lines.append("### SEQUENCING RULES")
                for r in relevant_tbp:
                    lines.append(f"- {r}")
                lines.append("")

        return "\n".join(lines)

    def get_guardrail_prompt(self) -> str:
        """Returns guardrail rules as a prompt section."""
        g = self.guardrails
        rules = []

        # Anti-hallucination
        if g["hallucination"]["require_source_grounding"]:
            rules.append("EVERY factual claim MUST be directly traceable to the framework document or universally verified knowledge. Do NOT invent facts, statistics, or examples that aren't grounded.")
        if g["hallucination"]["flag_uncertain_content"]:
            rules.append("If you are uncertain about any content, flag it with [VERIFY] tag rather than guessing.")

        # Age check
        ac = g["age_check"]
        rules.append(f"Use language appropriate for {self.audience['age_range']} year old students.")
        rules.append(f"Max sentence length: {ac.get('max_sentence_length_student', 20)} words (student-facing), {ac.get('max_sentence_length_teacher', 30)} words (teacher-facing).")
        rules.append("Avoid jargon without explanation. Define technical terms on first use.")

        # Content safety
        cs = g["content_safety"]
        if cs["check_gender_neutrality"]:
            rules.append("Use gender-neutral language. Alternate he/she or use 'they'.")
        if cs["check_cultural_sensitivity"]:
            rules.append("Be culturally sensitive to India's diverse student population.")
        banned = cs.get("banned_terms", [])
        if banned:
            rules.append(f"NEVER use these terms in student-facing content: {', '.join(banned)}.")

        # Alignment
        al = g["alignment"]
        if al["no_assessment_without_teaching"]:
            rules.append("NEVER assess content that was not explicitly taught in the lesson.")
        if al["bloom_taxonomy_check"]:
            rules.append("Learning objectives MUST use Bloom's taxonomy verbs (Identify, Describe, Explain, Apply, Analyze, Create).")
        if al.get("tangible_outcome_required"):
            rules.append("Every lesson MUST build toward the tangible outcome specified in the framework.")

        return "\n".join(f"- {r}" for r in rules)

    def get_ppt_graphics_guidance(self, grade: int) -> str:
        """Get age-appropriate graphics guidance for PPT generation."""
        guidance = self.ppt.get("graphics_guidance", {})
        grade_key = f"grade_{grade}"
        parts = []
        if grade_key in guidance:
            parts.append(f"Grade {grade} style: {guidance[grade_key]}")
        if "all_grades" in guidance:
            parts.append(f"General: {guidance['all_grades']}")
        return " | ".join(parts) if parts else ""
