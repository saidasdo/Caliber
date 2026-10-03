import os
from pathlib import Path

PRODUCT_NAME = "PlantPulse"

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_SEED_DIR = ROOT_DIR / "data" / "seed"
SCHEMA_PATH = ROOT_DIR / "db" / "schema.sql"

# On Vercel the deployment bundle is read-only except /tmp, and each serverless
# instance is ephemeral, so the writable database lives in /tmp there instead of
# repo-relative db/plantpulse.sqlite; main.py rebuilds it from data/raw/ on cold start.
DB_DIR = Path("/tmp") if os.environ.get("VERCEL") else ROOT_DIR / "db"
DB_PATH = DB_DIR / "plantpulse.sqlite"

PRODUCTION_DATA_DIR = DATA_RAW_DIR / "Production Data"
EQUIPMENT_PERFORMANCE_DIR = DATA_RAW_DIR / "Equipment Performance"
INCIDENT_DB_PATH = DATA_RAW_DIR / "Incident Database" / "Incident Database.xlsx"
RCA_PPTX_DIR = DATA_RAW_DIR / "RCA - Downtime Data"

# RCA -> equipment tag -> plant code, per SPEC section 2
RCA_EQUIPMENT = [
    {"rca_id": 1, "tag": "PU-2101B", "plant_code": "ARP"},
    {"rca_id": 2, "tag": "KO-3201", "plant_code": "ZCU"},
    {"rca_id": 3, "tag": "PM-4405B", "plant_code": "NUP"},
    {"rca_id": 4, "tag": "HE-3301", "plant_code": "ZCU"},
    {"rca_id": 5, "tag": "BL-5702", "plant_code": "OPP"},
]

SENSOR_PLANTS = {"ARP", "ZCU", "NUP", "OPP"}

# Generic signal names for the FEED/DISP/VIB/TEMP/AMP columns (section 2)
SIGNAL_MAP = {
    "FEED": "feed",
    "DISP": "discharge_pressure",
    "VIB": "vibration",
    "TEMP": "temperature",
    "AMP": "motor_current",
}
