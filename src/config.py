from pathlib import Path
import os

# Detectar si está corriendo en contenedor
# En contenedor: /src/config.py → usar /app para datos persistentes
# En local: src/config.py → usar el padre del directorio src
_current_file = Path(__file__).resolve()

# Si el archivo está en /src (montaje del contenedor)
if _current_file.parts[1:2] == ("src",) and len(_current_file.parts) > 2:
    # Estamos en /src dentro del contenedor
    PROJECT_ROOT = Path("/app")
else:
    # Estamos en local: src/ es subdirectorio del proyecto
    PROJECT_ROOT = _current_file.parents[1]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"

DEFAULT_DATASET_NAME = "dataset_practica_final.csv"
RAW_DATASET_PATH = RAW_DATA_DIR / DEFAULT_DATASET_NAME
TARGET_COLUMN = "is_canceled"

REQUIRED_COLUMNS = [
    "hotel",
    "is_canceled",
    "lead_time",
    "arrival_date_year",
    "arrival_date_month",
    "arrival_date_week_number",
    "arrival_date_day_of_month",
    "stays_in_weekend_nights",
    "stays_in_week_nights",
    "adults",
    "children",
    "babies",
    "meal",
    "country",
    "market_segment",
    "distribution_channel",
    "is_repeated_guest",
    "previous_cancellations",
    "previous_bookings_not_canceled",
    "reserved_room_type",
    "assigned_room_type",
    "booking_changes",
    "deposit_type",
    "agent",
    "company",
    "days_in_waiting_list",
    "customer_type",
    "adr",
    "required_car_parking_spaces",
    "total_of_special_requests",
]
