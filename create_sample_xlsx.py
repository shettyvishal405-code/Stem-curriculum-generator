"""
Creates a sample framework xlsx file for testing the pipeline.
This is for development/testing only.
"""
import openpyxl
from pathlib import Path

def create_sample_grade6_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Grade 6"

    # Headers
    ws.append(["Topic", "Session Count", "Learning Outcomes", "Tangible Outcome"])

    # Topic 1: Introduction to STEM
    rows = [
        ("What is STEM, Introduction to Technologies", 2,
         "Identify the four pillars of STEM (Science, Technology, Engineering, Mathematics)",
         "Understand lab components and lab etiquette"),
        (None, None, "Name common tools and equipment in the STEM lab", None),
        (None, None, "Understand lab safety rules and etiquette", None),

        # Topic 2: Basic Electronics
        ("Basic Electronics", 10,
         "Explain the concept of electric current and voltage",
         "Build and debug simple electronic circuits"),
        (None, None, "Build simple series and parallel circuits on a breadboard", None),
        (None, None, "Identify common electronic components (LED, resistor, capacitor, diode)", None),
        (None, None, "Build circuits with buzzers and switches", None),
        (None, None, "Use RGB LEDs and potentiometers in sessions 9-12", None),

        # Topic 3: Design Thinking
        ("Design Thinking", 3,
         "Apply the empathise-define-ideate stages of design thinking",
         "Analyse problems using Design Thinking, propose tech solutions"),
        (None, None, "Identify real-world problems in school or community", None),
        (None, None, "Propose technology-based solutions using a structured canvas", None),

        # Topic 4: Working with Sensors
        ("Working with Sensors", 8,
         "Distinguish between sensors (input) and actuators (output)",
         "Understand input/output devices and basics of automation"),
        (None, None, "Describe how common sensors work (light, temperature, sound, motion)", None),
        (None, None, "Apply if-then logic to describe simple automation scenarios", None),

        # Topic 5: Simulation
        ("Simulation (Tinkercad)", 5,
         "Create and test simple circuits in Tinkercad",
         "Build and simulate circuits in Tinkercad"),
        (None, None, "Relate simulated circuits to physical circuits built earlier", None),

        # Topic 6: Microcontroller Basics
        ("Microcontroller Basics", 2,
         "Identify and name key components of an Arduino Uno board",
         "Name Arduino Uno parts and use in simulation"),
        (None, None, "Distinguish between analog and digital pins", None),

        # Topic 7: Sensor-Based Automation
        ("Sensor-Based Automation using Microcontrollers", 4,
         "Write simple Arduino code to read sensor data",
         "Simulated robot follows a line"),
        (None, None, "Design a basic line-following algorithm using if-else logic", None),

        # Topic 8: Robotics
        ("Robotics", 10,
         "Classify robots by type and application",
         "Design and demonstrate a simple working robotic project"),
        (None, None, "Assemble a basic robot chassis with motors", None),
        (None, None, "Integrate sensors into a robot system", None),
        (None, None, "Program a robot to perform a simple task", None),
    ]

    for row in rows:
        ws.append(row)

    path = Path("sample_framework_grade6.xlsx")
    wb.save(str(path))
    print(f"Created: {path}")
    return str(path)


if __name__ == "__main__":
    create_sample_grade6_xlsx()
