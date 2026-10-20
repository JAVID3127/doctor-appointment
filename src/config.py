import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

# Flask Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "hospital-opd-secret-key-week6")
DB_PATH = DATA_DIR / "opd_hospital.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Operating standards
OPD_START_HOUR = 9
OPD_END_HOUR = 17
DEFAULT_SLOT_MINUTES = 15
OVERBOOK_NO_SHOW_THRESHOLD = 0.50
