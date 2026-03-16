# CLAUDE.md — Claude Code Operating Instructions

## What This Project Does

A multi-agent curriculum pipeline for ENpower STEM Labs (ThinkEdge) that generates complete education packages for Indian schools (Grades 6-8). Given the framework spreadsheet (`DB_50_session_Learning_outcomes.xlsx`), it produces per-session:

1. **Lesson Plans** (.docx) — 5E format with ENpower branding
2. **Assessments** (.docx) — MCQs, FIBs, MTF, T/F, Short Answer
3. **Student PPTs** (.pptx) — Age-appropriate, Indian-context presentations
4. **Equipment Lists** (.csv) — Lab equipment with Indian supplier pricing

## Curriculum Structure (from Framework)

### Grade 6 — 44 Sessions
```
Sessions  1-2   Introduction to STEM (unplugged, no electronics)
Sessions  3-12  Basic Electronics (no coding, no Arduino, physical circuits)
Sessions 13-15  Design Thinking (no electronics, senses-as-input bridge)
Sessions 16-23  Working with Sensors (conceptual, no Arduino coding)
Sessions 24-28  Simulation / Tinkercad (first computer use, no Arduino code)
Sessions 29-30  Microcontroller Basics (first Arduino, identification only)
Sessions 31-34  Sensor-Based Automation (first Arduino coding with sensors)
Sessions 35-44  Robotics (capstone, integrates all prior learning)
```

### Grade 7 — 41 Sessions
```
Sessions  1-2   Design Thinking: Empathy & Definition
Sessions  3     Intermediate Electronics & Actuation (DC motor, no coding)
Sessions  4-5   Arduino IDE setup (first coding — LED blink)
Sessions  6-11  Digital Prototyping / Tinkercad (traffic light, sensors)
Sessions 12-13  Electronic Circuits (first REAL Arduino circuits)
Sessions 14-15  RC Robotics Theory (connection mapping, not building)
Sessions 16-17  Autonomous Systems: Motors (directional control)
Sessions 18-21  Sensor Integration (headlights, horn, test reports)
Sessions 22-27  RC Robot Build (6-session progressive build)
Sessions 28-31  Autonomous Line Follower (calibration, debugging)
Sessions 32-35  3D Design Fundamentals (Tinkercad, NO printing)
Sessions 36-41  Miniproject + Capstone
```

### Grade 8 — 25 Sessions
```
Sessions  1-2   Entrepreneurial Design Thinking (market research)
Sessions  3-5   IoT Foundations (NodeMCU/ESP8266, Bluetooth, web server)
Sessions  6-8   Bio-Medical & Environmental Sensing (PIR, pulse, gas)
Sessions  9-11  Robotics: Navigation (maze-solving, ultrasonic)
Sessions 12-15  Aerospace & Drone Technology (theory→flight cert)
Sessions 16-17  Data Science & Analytics (spreadsheet-based)
Sessions 18-19  Advanced 3D Manufacturing (STL, slicing, printing)
Sessions 20-25  Miniproject + Capstone
```

## How to Run

### Prerequisites
```bash
cd curriculum-pipeline
pip install anthropic pyyaml openpyxl --break-system-packages
npm install -g docx pptxgenjs
```

### Full Pipeline (Session 1 + HIL pause)
```bash
python main.py --framework /path/to/DB_50_session_Learning_outcomes.xlsx --grade 7
```

### Single Session
```bash
python main.py --framework DB_50_session_Learning_outcomes.xlsx --grade 6 --session 5
```

### Batch Mode (After Session 1 Approval)
```bash
python main.py --framework DB_50_session_Learning_outcomes.xlsx --grade 7 --batch 2-41
```

### Re-run with Feedback
```bash
python main.py --framework DB_50_session_Learning_outcomes.xlsx --grade 7 --session 1 \
  --feedback "Make explore activity simpler, add more Indian examples in engage"
```

## Architecture

```
main.py                       ← Pipeline orchestrator
├── agents/
│   ├── base_agent.py         ← API calls, retry, JSON parsing
│   ├── framework_parser.py   ← Parses xlsx (deterministic) or text (AI)
│   ├── lesson_plan_agent.py  ← 5E lesson plans with tangible outcomes
│   ├── assessment_agent.py   ← Curriculum-aligned assessments
│   ├── ppt_agent.py          ← Student PPT content
│   └── equipment_agent.py    ← Lab equipment with INR pricing
├── guardrails/
│   ├── validator.py          ← Cross-validation agent + local checks
│   └── GUARDRAILS.md         ← Guardrails system documentation
├── utils/
│   ├── config_loader.py      ← Grade-aware constraint engine
│   ├── prompts.py            ← All agent system prompts
│   ├── hil.py                ← Human-in-the-loop review module
│   └── output_builder.py     ← .docx/.pptx/.csv file generation
├── config/
│   └── pipeline_config.yaml  ← Grade-specific phases, constraints, branding
└── outputs/                  ← Generated files per session
```

## Constraint System

Constraints are **auto-derived from the framework spreadsheet** and organized by grade → phase → session. The config loader resolves the correct constraints for any (grade, session) pair.

Each session prompt automatically includes:
- **Phase rules** — what's allowed/forbidden (e.g., "NO coding in sessions 1-2")
- **Allowed tools** — only tools listed for that phase
- **Tangible outcome** — the concrete deliverable from the framework
- **Pacing guidance** — session position within the topic (first/middle/last)
- **Prior phase context** — what students completed before this phase
- **Cross-grade prerequisites** — assumed prior knowledge
- **Safety warnings** — if the phase involves drones, soldering, 3D printers, etc.
- **Theory-before-practice rules** — sequencing enforcement

### Key Constraints by Grade

**Grade 6:**
- Sessions 1-2: NO electronics, NO coding — fully unplugged
- Sessions 3-12: NO coding, NO Arduino, NO simulation — physical circuits only
- Sessions 3-8: No RGB/potentiometer (reserved for sessions 9-12)
- Sessions 24-28: First computer use (Tinkercad only, no Arduino code)
- Sessions 29-30: Arduino identification only, no complex coding

**Grade 7:**
- Sessions 1-2: NO electronics or coding — pure Design Thinking
- Sessions 4-5: First coding (Arduino IDE, LED blink)
- Sessions 6-11: Simulation before real circuits
- Sessions 14-15: RC theory only — NOT building
- Sessions 22-27: 6-session progressive build — DO NOT rush
- Sessions 32-35: 3D design only — NO printing (that's Grade 8)

**Grade 8:**
- Sessions 1-2: NO electronics — market research and business canvas
- Sessions 12-15: Drone theory + MANDATORY safety briefing before flight
- Sessions 16-17: Spreadsheet-based data science — NOT Python
- Sessions 18-19: Full 3D manufacturing pipeline (design → slice → print)

## Guardrails

| Layer | What It Catches |
|-------|----------------|
| **Agent prompts** | Hallucination prevention, source grounding, [VERIFY] tags |
| **Local checks** | Timing (50 min), question counts, banned terms, format rules |
| **Cross-validator** | AI review of all outputs against framework |
| **HIL checkpoint** | Human reviews Session 1 before batch generation |

### Anti-Hallucination
- Temperature: 0.0 (extraction), 0.1-0.3 (generation), 0.0 (validation)
- Every claim must trace to framework
- Assessment questions require `source_in_lesson` field
- `[VERIFY]` tags for uncertain content
- Equipment prices flagged with `[VERIFY_PRICE]`

### Safety-Critical Topics (auto-injected when relevant)
- Soldering — adult supervision required
- Battery handling — short circuit warnings
- Drone flying — safety briefing mandatory
- 3D printer — hot nozzle warnings
- Bio-medical sensors — not for real diagnosis

## Output Formats

### Lesson Plan (5E)
- Engage (5 min) → Explore (15 min) → Explain (10 min) → Elaborate (15 min) → Evaluate (5 min)
- Tangible outcome from framework enforced
- Indian context examples required

### Assessment Rules
- MCQs: "Which of the following..." (never "What is...")
- Fill-in-blanks: "Name the..."
- Match-the-following: One correct match per item
- True/False: Corrected statement for false items
- Every question cites its source in the lesson

### PPT Graphics Guidance
- Grade 6: Simple, colourful, cartoon-style icons
- Grade 7: Slightly technical but friendly, Arduino diagrams
- Grade 8: Technical but accessible, IoT diagrams, data charts
- All grades: Indian settings, diverse students
