# Guardrails System — Technical Reference

## Overview

The guardrails system operates at **four layers** to catch both known and unknown GenAI failure modes.

```
Layer 1: PROMPT ENGINEERING (Prevention)
  ↓
Layer 2: LOCAL DETERMINISTIC CHECKS (Detection)
  ↓
Layer 3: AI CROSS-VALIDATION (Deep Analysis)
  ↓
Layer 4: HUMAN-IN-THE-LOOP (Final Gate)
```

---

## Layer 1: Prompt Engineering (Prevention)

Each agent's system prompt includes specific anti-hallucination and safety rules.

### Anti-Hallucination Techniques

| Technique | Implementation | Agent |
|-----------|---------------|-------|
| **Source grounding** | "EVERY factual claim MUST be traceable to the framework document" | All |
| **Low temperature** | 0.0 for extraction, 0.1-0.3 for generation | All |
| **[VERIFY] tagging** | "Flag uncertain content with [VERIFY]" | All |
| **Source citation** | Assessment questions require `source_in_lesson` field | Assessment |
| **Explicit constraints** | "Do NOT invent activities requiring unlisted equipment" | Lesson Plan |
| **Negative instructions** | "Do NOT add facts not covered in the lesson" | PPT |
| **Fabrication ban** | "Do NOT fabricate prices — use [VERIFY_PRICE]" | Equipment |

### Known GenAI Failure Modes Addressed

| Failure Mode | How Addressed |
|-------------|---------------|
| **Hallucinated facts** | Source grounding + [VERIFY] tags + cross-validation |
| **Confident fabrication** | Low temperature + explicit uncertainty flagging |
| **Style drift** | Strict format specs (5E structure, MCQ format rules) |
| **Sycophancy** | Validator agent is instructed to be "STRICT" and "assume there are issues" |
| **Prompt injection** | Framework text is marked as DATA, not instructions |
| **Context overflow** | Token budgets + content truncation in validation prompts |
| **Inconsistency across outputs** | Cross-validation checks lesson ↔ PPT ↔ assessment ↔ equipment |
| **Age-inappropriate content** | Banned terms list + reading level checks + explicit age targeting |
| **Cultural insensitivity** | Indian context rules + inclusive example requirements |
| **Over-generation** | Max constraints (3 objectives, 12 slides, 25-word sentences) |

---

## Layer 2: Local Deterministic Checks

These are code-based checks that don't require AI — they're fast, reliable, and catch structural issues.

### Checks Performed

```python
# Timing validation
- Total phase durations == 50 minutes

# Question count validation
- Exactly 5 MCQs
- Exactly 3 Fill-in-blanks
- Exactly 3 True/False
- Exactly 2 Short Answer

# Format validation
- MCQs start with "Which of the following"
- Fill-in-blanks start with "Name the"
- False statements have corrections

# Slide count validation
- Minimum 8 slides
- Maximum 12 slides

# Banned term detection
- Scans student-facing content for: "stupid", "dumb", "obviously", "simply", "easy"

# [VERIFY] flag counting
- Aggregates across all outputs

# Source grounding check
- Every assessment question has `source_in_lesson`
```

### Why Local Checks Matter

AI validation can miss obvious structural issues or be "convinced" to ignore them. Local checks provide a hard floor of quality that can't be bypassed.

---

## Layer 3: AI Cross-Validation

The `GuardrailValidator` agent receives ALL outputs and the source framework, then runs a comprehensive review.

### Validation Dimensions

1. **Hallucination Check** — Is every fact grounded in the framework?
2. **Alignment Check** — Do objectives → activities → assessment → PPT all align?
3. **Age-Appropriateness** — Is language suitable for 11-14 year olds?
4. **Indian Context** — Are examples, pricing, suppliers Indian?
5. **Consistency Check** — No contradictions between outputs?
6. **Curriculum Constraint Check** — Session-specific rules followed?

### Output Format

```json
{
  "overall_status": "PASS | FAIL | NEEDS_REVIEW",
  "confidence_score": 0.85,
  "critical_issues": ["Must fix before proceeding"],
  "warnings": ["Should fix but not blocking"],
  "suggestions": ["Nice to have"],
  "requires_human_review": ["Needs human judgment"]
}
```

### When Validation Fails

- **FAIL**: Pipeline halts. Critical issues must be fixed.
- **NEEDS_REVIEW**: Pipeline flags issues for HIL review.
- **PASS**: Pipeline continues (but HIL still happens at checkpoint).

---

## Layer 4: Human-in-the-Loop (HIL)

### When HIL Triggers

1. **Mandatory**: After Session 1 generation (always)
2. **Auto-triggered**: When validation returns FAIL or NEEDS_REVIEW
3. **Manual**: When operator requests review of any session

### What the Human Reviews

```
outputs/session_1/review/
├── lesson_plan.json      ← Full lesson plan
├── assessment.json       ← Assessment with answer key
├── ppt_content.json      ← Slide content and descriptions
├── equipment_list.json   ← Equipment with pricing
└── validation_report.json ← All validation results
```

### Human Actions

| Action | Effect |
|--------|--------|
| **APPROVE** | Pipeline proceeds to batch-generate Sessions 2-11 |
| **REJECT + Feedback** | Session 1 regenerated with human feedback injected into prompts |
| **EDIT** | Human edits JSON directly, files rebuilt from edited JSON |

---

## Unknown Risk Mitigation

For GenAI failure modes we haven't anticipated:

### 1. Structural Diversity
Multiple independent agents reduce single-point-of-failure risk. If one agent hallucinates, the cross-validator (a different agent instance) is more likely to catch it.

### 2. Defense in Depth
Four independent layers mean a failure must pass through ALL of:
- Prompt engineering (prevention)
- Local code checks (detection)
- AI cross-validation (analysis)
- Human review (judgment)

### 3. Low Temperature + Structured Output
- Extraction: 0.0 temperature (fully deterministic)
- Generation: 0.1-0.3 (minimal creativity)
- Validation: 0.0 (deterministic checking)
- JSON structured output reduces free-form hallucination space

### 4. Progressive Trust
Session 1 gets full HIL review. Only after human approval do Sessions 2-11 run. This catches systematic issues early before they multiply across 10 sessions.

### 5. Audit Trail
Every output preserves:
- Raw JSON from each agent
- Validation reports
- Token usage logs
- HIL review decisions
- Session summaries for continuity

### 6. Framework as Single Source of Truth
The framework document is the ONLY source of content. Agents are explicitly forbidden from adding external knowledge. This eliminates the largest hallucination vector.

---

## Configuration Overrides

All guardrail parameters are configurable in `config/pipeline_config.yaml`:

```yaml
guardrails:
  hallucination:
    require_source_grounding: true  # Can disable for creative tasks
    max_unsourced_claims: 0         # Increase if framework is sparse
  age_check:
    max_sentence_length: 25         # Adjust per grade level
  content_safety:
    banned_terms: [...]             # Add/remove per requirements
```
