"""Generate reference Course_Marks_Template.xlsx (sample layout). Run from backend/: python scripts/generate_marks_template.py"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.copo.schemas import MarksComponentSpec, MarksTemplateGenerateRequest
from app.copo.services.marks_template_builder import build_constraint_workbook

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "templates" / "Course_Marks_Template.xlsx"
OUT.parent.mkdir(parents=True, exist_ok=True)

body = MarksTemplateGenerateRequest(
    course_code="Sample",
    semester="Template",
    components=[
        MarksComponentSpec(name="Quiz", questions=1),
        MarksComponentSpec(name="Quiz", questions=1),
        MarksComponentSpec(name="MidSem", questions=2),
        MarksComponentSpec(name="EndSem", questions=2),
        MarksComponentSpec(name="Project", questions=0),
    ],
)
OUT.write_bytes(build_constraint_workbook(body))
print(f"Wrote {OUT}")
