"""Generate faculty Workflow A Excel template. Run from backend/: python scripts/generate_marks_template.py"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "templates" / "Course_Marks_Template.xlsx"
OUT.parent.mkdir(parents=True, exist_ok=True)

# Single sheet — all semester assessments as columns (Workflow A consolidated file)
columns = [
    "Quiz1",
    "Quiz1.1",
    "Quiz2",
    "MidSem",
    "MidSem.1",
    "EndSem",
    "EndSem.1",
    "Project",
    "Result",
    "Grade_Point",
]

data = {
    "CO": ["CO1,CO2", "CO1", "CO2,CO3", "CO1,CO2,CO3", "CO1,CO2,CO3", "CO1,CO2,CO3", "", "CO3", "", ""],
    "Max_Marks": [10, 10, 10, 30, 30, 50, 50, 20, "", ""],
    "2023001": [8, 7, 9, 25, 24, 40, 38, 18, 162, "A-"],
    "2023002": [6, 8, 7, 22, 20, 35, 33, 15, 140, "B"],
    "2023003": [9, 9, 8, 28, 27, 45, 42, 17, 170, "A"],
}
df = pd.DataFrame(data, index=columns).T
df.index.name = "Roll No"

with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Marks")
    readme = pd.DataFrame(
        {
            "Topic": [
                "Workflow",
                "Sheets required",
                "Student ID",
                "Required rows (index)",
                "Required columns",
                "Assessment columns",
                "CO row",
                "Max_Marks row",
                "Branch column",
            ],
            "Detail": [
                "ONE consolidated file at end of semester (all quizzes/mids/endsem in columns)",
                "Single sheet named Marks (or first sheet with standard layout)",
                "Roll numbers as row index (e.g. 2023001). Not CO/Max_Marks rows.",
                "CO, Max_Marks (or Max_Marks_scaled), then one row per student roll",
                "Result, Grade_Point required; other columns are assessments",
                "Quiz/MidSem/EndSem/Project etc. — all components in ONE file",
                "Each assessment column: CO1 or CO1,CO2 in CO row; empty CO on group total column",
                "Maximum marks per assessment column",
                "Optional: Branch column in raw layout (auto-detected by parser)",
            ],
        }
    )
    readme.to_excel(writer, sheet_name="Instructions", index=False)

print(f"Wrote {OUT}")
