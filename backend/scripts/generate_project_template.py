"""Write BTP/IP import template to data/templates/."""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.projects.services.import_service import build_template_bytes

PROJECT_ROOT = Path(__file__).resolve().parents[2]
dest = PROJECT_ROOT / "data" / "templates" / "btp_ip_import_template.xlsx"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_bytes(build_template_bytes())
print(f"Wrote {dest}")
