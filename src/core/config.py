import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

# Database Configuration
DB_PATH = DATA_DIR / "opd_hospital.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Smart Overbooking Constraints
MAX_OVERBOOK_PER_SLOT = 1             # Max 1 extra patient per slot
OVERBOOK_NO_SHOW_THRESHOLD = 0.50     # Patient must have P(no-show) >= 50%
MAX_SHIFT_OVERBOOK_RATE = 0.20        # Max +20% extra patients per doctor shift
