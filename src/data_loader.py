from __future__ import annotations

import json
import pandas as pd
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, RAW_DATASET_PATH, REQUIRED_COLUMNS, TARGET_COLUMN


def ensure_data_dirs() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_raw_dataset(path: str | Path | None = None) -> pd.DataFrame:
    if path is None:
        path = RAW_DATASET_PATH

    if isinstance(path, str):
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el dataset raw en {path}. "
            "Coloca el archivo CSV en data/raw/ con el nombre dataset_practica_final.csv"
        )

    df = pd.read_csv(path)
    _validate_dataset_columns(df)
    return df


def _validate_dataset_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Faltan columnas obligatorias en el dataset: {missing}. "
            "Revisa el archivo CSV o actualiza REQUIRED_COLUMNS en src/config.py"
        )

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"La columna objetivo '{TARGET_COLUMN}' no existe en el dataset.")


def save_processed_dataset(df: pd.DataFrame, filename: str = "dataset_practica_final_processed.csv") -> Path:
    ensure_data_dirs()
    destination = PROCESSED_DATA_DIR / filename
    df.to_csv(destination, index=False)
    return destination


def summarize_dataset(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "target_counts": df[TARGET_COLUMN].value_counts(dropna=False).to_dict(),
        "missing_values": df.isna().sum().to_dict(),
    }


def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

     # Columnas a eliminar (leakage garantizado)
    LEAKAGE_COLUMNS = ['reservation_status', 'reservation_status_date']
    
    # Eliminar columnas
    for col in LEAKAGE_COLUMNS:
        if col in df.columns:
            df = df.drop(columns=[col])
            print(f"Eliminada columna con leakage: {col}")

    # Estandarizar nombres de columnas y texto
    df.columns = df.columns.astype(str).str.lower().str.strip()
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()

    # Rellenar valores faltantes básicos
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].fillna(df[col].median())

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].replace({"nan": None, "None": None})
        df[col] = df[col].fillna("missing")

    return df


def load_dataset_from_db(dataset_id: int, version_id: int | None = None) -> pd.DataFrame:
    """Carga un dataset desde la base de datos usando las utilidades en
    `App/api-server/api/dataBaseManagement`.
    """
    try:
        from dataBaseManagement.dbManagement import get_record_by_id_Generic, get_rows_by_condition_Generic
        from dataBaseManagement.dbConectionPostgres import get_db_tasks
    except Exception as exc:  # pragma: no cover - depends on runtime environment
        raise ImportError(
            "No se pudo importar el paquete 'dataBaseManagement'.\n"
            "Este loader usa las utilidades del servicio API para localizar el CSV\n"
            "en el servidor (tabla dataset_versions). Ejecuta este código dentro\n"
            "del contenedor de la API o asegúrate de que 'App/api-server/api' esté\n"
            "en PYTHONPATH. Error original: " + str(exc)
        )

    # obtener la conexión y consultar la versión
    with get_db_tasks() as conn:
        if version_id is None:
            rows = get_rows_by_condition_Generic(
                "dataset_versions",
                "dataset_id = %s ORDER BY version_number DESC LIMIT 1",
                [dataset_id],
                connection=conn,
            )
            if not rows:
                raise ValueError(f"No se encontró ninguna versión para el dataset {dataset_id}")
            version = rows[0]
        else:
            version = get_record_by_id_Generic("dataset_versions", version_id, connection=conn)
            if not version or int(version.get("dataset_id", -1)) != int(dataset_id):
                raise ValueError(f"La versión {version_id} no corresponde al dataset {dataset_id}")

    storage_path = Path(version["storage_path"]) if version.get("storage_path") else None
    if storage_path is None or not storage_path.exists():
        raise FileNotFoundError(f"El archivo CSV en storage_path no existe: {storage_path}")

    df = pd.read_csv(storage_path)
    _validate_dataset_columns(df)
    return df


def load_dataset_from_api(
    dataset_id: int,
    version_id: int | None = None,
    base_url: str = "http://localhost/apim5",
) -> pd.DataFrame:
    """Carga un dataset consultando metadata de versiones vía API.

    Mantiene la lógica de load_dataset_from_db:
    - Si version_id es None, usa la última versión.
    - Si version_id viene informado, valida que pertenezca al dataset.
    - Carga el CSV desde storage_path y valida columnas obligatorias.
    """
    base_url = base_url.rstrip("/")
    dataset_url = f"{base_url}/datasets/{dataset_id}"

    try:
        with urlopen(dataset_url) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail_payload = json.loads(exc.read().decode("utf-8"))
            detail = detail_payload.get("detail", str(exc))
        except Exception:
            detail = str(exc)

        if exc.code == 404:
            raise ValueError(f"No se encontró el dataset {dataset_id}: {detail}")
        raise ConnectionError(f"Error HTTP al consultar la API ({dataset_url}): {detail}")
    except URLError as exc:
        raise ConnectionError(
            f"No se pudo conectar a la API en {base_url}. Verifica que esté publicada y accesible."
        ) from exc

    if version_id is None:
        version = payload.get("latest_version")
        if not version:
            raise ValueError(f"No se encontró ninguna versión para el dataset {dataset_id}")
    else:
        versions = payload.get("versions") or []
        version = next((row for row in versions if int(row.get("id", -1)) == int(version_id)), None)
        if not version or int(version.get("dataset_id", -1)) != int(dataset_id):
            raise ValueError(f"La versión {version_id} no corresponde al dataset {dataset_id}")

    storage_path = Path(version["storage_path"]) if version.get("storage_path") else None
    if storage_path is None or not storage_path.exists():
        raise FileNotFoundError(f"El archivo CSV en storage_path no existe: {storage_path}")

    df = pd.read_csv(storage_path)
    _validate_dataset_columns(df)
    return df
